"""Persistent Drive previews and a Canvas strip; networking never runs on Tk's thread."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import random
import threading
import time
import tkinter as tk
import math
import subprocess
import webbrowser
from pathlib import Path
from modules.gacha_widgets import IconWindow
from PIL import Image, ImageOps, ImageTk
from modules.gacha_sources import session_for


class PreviewCache:
    def __init__(self, root, settings, stopped=lambda: False):
        self.root = root / 'previews'
        self.settings = settings.copy()
        self.stopped = stopped
        self.guard = threading.Lock()
        self.locks, self.failures = {}, {}

    def path(self, item):
        ident = item.get('preview_id')
        return self.root / (hashlib.sha256(ident.encode()).hexdigest()+'.img') if ident else None

    @staticmethod
    def decode(data):
        with Image.open(io.BytesIO(data)) as image:
            if image.width*image.height > 8_000_000:
                raise ValueError('Preview too large')
            return ImageOps.contain(image.convert('RGB'), (208, 117), Image.Resampling.LANCZOS)

    def get(self, item):
        path = self.path(item)
        if path is None or self.stopped(): return None
        with self.guard:
            lock = self.locks.setdefault(path, threading.Lock())
        while not lock.acquire(timeout=.1):
            if self.stopped(): return None
        try:
            if path.exists():
                try: return self.decode(path.read_bytes())
                except (OSError, ValueError): path.unlink(missing_ok=True)
            if self.settings.get('offline') or self.stopped(): return None
            if time.monotonic()-self.failures.get(path, -1000) < 60: return None
            with session_for(self.settings.get('ignore_proxy')) as session:
                with session.get('https://drive.usercontent.google.com/download',
                                 params={'id':item['preview_id'], 'export':'download', 'confirm':'t'},
                                 stream=True, timeout=(5, 8)) as response:
                    response.raise_for_status()
                    data = bytearray()
                    deadline = time.monotonic()+15
                    for block in response.iter_content(65536):
                        if self.stopped(): return None
                        data.extend(block)
                        if len(data) > 2*1024*1024 or time.monotonic() > deadline:
                            raise ValueError('Preview download limit')
            image = self.decode(data)
            self.root.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix('.part')
            try:
                temporary.write_bytes(data)
                temporary.replace(path)
            finally: temporary.unlink(missing_ok=True)
            return image
        except Exception:
            self.failures[path] = time.monotonic()
            return None
        finally: lock.release()

    def warm(self, items):
        items = list({i['preview_id']:i for i in items if i.get('preview_id')}.values())
        with ThreadPoolExecutor(max_workers=3, thread_name_prefix='previews') as workers:
            count = sum(image is not None for image in workers.map(self.get, items))
        return count, len(items)

    def prepare(self, candidates, final):
        sample = roulette_candidates(candidates, final)
        with ThreadPoolExecutor(max_workers=3, thread_name_prefix='roulette-preview') as workers:
            images = list(workers.map(self.get, sample))
        entries = [dict(item=item, image=image, path=self.path(item)) for item, image in zip(sample, images)]
        offset=(sample.index(final)-22)%len(sample)
        return [entries[(i+offset)%len(entries)] for i in range(25)]


def roulette_candidates(candidates, final):
    unique={str(i.get('id') or i.get('source') or i['name']):i for i in candidates}
    ident=str(final.get('id') or final.get('source') or final['name'])
    unique.pop(ident,None)
    sample=random.sample(list(unique.values()),min(24,len(unique)))+[final]
    random.shuffle(sample)
    return sample



class RouletteStrip(tk.Canvas):
    PITCH = 220
    WINNER = 22

    def __init__(self, parent, theme):
        super().__init__(parent, height=154, background=theme['panel'], highlightthickness=0)
        self.theme = theme
        self.sequence = None
        self.photos = []
        self.offset = 0
        self.progress = 0
        self.bind('<Configure>', lambda e:self.show(self.sequence,self.progress) if self.sequence else None)
        self.bind('<Button-1>', self.enlarge)
        self.bind('<Button-3>', self.context_menu)

    def entry_at(self, event):
        if not self.sequence: return None
        index = round((event.x-self.offset)/self.PITCH)
        return self.sequence[index % len(self.sequence)]

    def context_menu(self, event):
        entry = self.entry_at(event)
        if not entry: return
        path = entry.get('path')
        menu = tk.Menu(self,tearoff=False)
        english = getattr(self.winfo_toplevel(),'settings',{}).get('language')=='English'
        menu.add_command(label='Show preview in folder' if english else 'Показать превью в папке',
                         state='normal' if path and Path(path).is_file() else 'disabled',
                         command=lambda:subprocess.Popen(['explorer.exe','/select,',str(Path(path).resolve())]))
        if entry['item'].get('preview_id'):
            menu.add_command(label='Open on Google Drive' if english else 'Открыть на Google Drive',
                             command=lambda:webbrowser.open('https://drive.google.com/file/d/'+entry['item']['preview_id']+'/view'))
        try: menu.tk_popup(event.x_root,event.y_root)
        finally: menu.grab_release()

    def enlarge(self, event):
        entry = self.entry_at(event)
        if not entry: return
        open_preview(self.winfo_toplevel(),entry)

    def show(self, sequence, progress):
        self.progress = progress
        padding = math.ceil(max(self.winfo_width(),1)/self.PITCH/2)+2
        if self.sequence is not sequence or getattr(self,'padding',None)!=padding:
            self.padding = padding
            self.delete('all')
            self.photos = []
            self.sequence = sequence
            for index in range(-padding, len(sequence)+padding):
                entry = sequence[index % len(sequence)]
                x = index*self.PITCH
                self.create_rectangle(x-106, 9, x+106, 149, fill=self.theme['card'],
                                      outline=self.theme['muted'], tags='strip')
                if entry['image'] is not None:
                    photo = ImageTk.PhotoImage(entry['image'], master=self)
                    self.photos.append(photo)
                    self.create_image(x, 69, image=photo, tags='strip')
                else:
                    self.create_oval(x-34, 35, x+34, 103, outline=self.theme['accent'], width=3, tags='strip')
                    self.create_text(x, 69, text=entry['item']['rank'], fill=self.theme['text'],
                                     font=('Segoe UI', 18, 'bold'), tags='strip')
                name = entry['item']['name']
                self.create_text(x, 135, text=name if len(name)<30 else name[:27]+'…',
                                 fill=self.theme['text'], font=('Segoe UI', 9), tags='strip')
            self.offset = 0
        width = self.winfo_width()
        # Time-based quintic easing ends exactly at the winning card's centre.
        distance = (2 + (self.WINNER-2)*(1-(1-progress)**5))*self.PITCH
        offset = width/2-distance
        self.move('strip', offset-self.offset, 0)
        self.offset = offset
        self.delete('pointer')
        self.create_rectangle(width/2-108, 8, width/2+108, 150,
                              outline=self.theme['accent'], width=3, tags='pointer')
        self.create_polygon(width/2-7, 0, width/2+7, 0, width/2, 9,
                            fill=self.theme['accent'], tags='pointer')


def open_preview(parent,entry):
    picture = entry['image']
    path = entry.get('path')
    if path and Path(path).is_file():
        try:
            with Image.open(path) as original: picture = original.convert('RGB')
        except OSError: pass
    if picture is None: return
    window = IconWindow(parent)
    window.title(entry['item']['name'])
    window.geometry(f'{min(1000,parent.winfo_screenwidth()-100)}x{min(680,parent.winfo_screenheight()-120)}')
    canvas = tk.Canvas(window,background='#101014',highlightthickness=0)
    canvas.pack(fill='both',expand=True)
    def draw(event=None):
        size=(max(1,canvas.winfo_width()-60),max(1,canvas.winfo_height()-90))
        shown=ImageOps.contain(picture,size,Image.Resampling.LANCZOS)
        canvas.photo=ImageTk.PhotoImage(shown,master=canvas)
        canvas.delete('all')
        canvas.create_image(canvas.winfo_width()/2,canvas.winfo_height()/2,image=canvas.photo,tags='picture')
        canvas.create_text(canvas.winfo_width()-24,24,text='×',fill='white',font=('Segoe UI',24),tags='close')
    canvas.bind('<Configure>',draw)
    canvas.bind('<Button-1>',lambda e:window.destroy() if 'picture' not in canvas.gettags('current') else None)
    window.bind('<Escape>',lambda e:window.destroy())
    window.after(100,window.lift)
    return window
