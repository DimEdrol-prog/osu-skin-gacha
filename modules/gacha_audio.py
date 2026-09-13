"""Local beatmap music, one stream, asynchronous file lookup and decoding."""
import os
import re
import queue
import struct
import weakref
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from tkinter import messagebox
from modules.gacha_sources import LocalMaps


def audio_from_map(path,songs):
    path=Path(path).resolve();songs=Path(songs).resolve()
    if not path.is_relative_to(songs) or not path.is_file() or path.stat().st_size>8*1024*1024:return None
    section=''
    for line in path.read_text(encoding='utf-8-sig',errors='replace').splitlines():
        line=line.strip()
        if line.startswith('['):section=line
        if section=='[General]' and ':' in line:
            key,value=line.split(':',1)
            if key.strip()=='AudioFilename':
                name=value.strip().strip('"').replace('\\','/')
                audio=(path.parent/name).resolve()
                if name and audio.is_relative_to(path.parent) and audio.is_file():return audio
    return None


class AudioLocator:
    def __init__(self,osu):
        self.local=LocalMaps(osu);self.songs=Path(osu)/'Songs'
    def find(self,record):
        info,score=record['map'],record['score']
        ident=str(score.get('beatmap_id') or info.get('beatmap_id') or '')
        paths=[]
        if info.get('path'):paths.append(Path(info['path']))
        try:
            item=self.local.locate(score.get('map_hash') or ident)
            if item:paths.append(Path(item['path']))
        except (OSError,ValueError,EOFError,struct.error):pass
        for path in paths:
            audio=audio_from_map(path,self.songs)
            if audio:return audio
        set_id=str(info.get('beatmapset_id') or '')
        # Numbered set folders also work when osu!.db is absent or unsupported.
        if set_id.isdigit() and self.songs.is_dir():
            for folder in self.songs.iterdir():
                if not folder.is_dir() or not re.match(re.escape(set_id)+r'(?:\s|$)',folder.name):continue
                for path in folder.glob('*.osu'):
                    if not path.resolve().is_relative_to(self.songs.resolve()) or path.stat().st_size>8*1024*1024:continue
                    data=path.read_text(encoding='utf-8-sig',errors='replace')
                    if re.search(r'^BeatmapID\s*:\s*'+re.escape(ident)+r'\s*$',data,re.M):
                        audio=audio_from_map(path,self.songs)
                        if audio:return audio
        return None


class MusicBackend:
    def __init__(self):self.mixer=None
    def play(self,path):
        if self.mixer is None:
            os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
            import pygame.mixer
            self.mixer=pygame.mixer
        if not self.mixer.get_init():self.mixer.init()
        self.mixer.music.load(str(path));self.mixer.music.set_volume(.35)
        self.mixer.music.play(fade_ms=250)
    def stop(self):
        if self.mixer and self.mixer.get_init():self.mixer.music.stop();self.mixer.music.unload()
    def busy(self):return bool(self.mixer and self.mixer.get_init() and self.mixer.music.get_busy())
    def close(self):
        self.stop()
        if self.mixer:self.mixer.quit()


class AudioPlayer:
    def __init__(self,app):
        self.app=app;self.backend=MusicBackend();self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='gacha-music')
        self.events=queue.Queue();self.buttons=weakref.WeakKeyDictionary();self.locators={}
        self.token=0;self.current=None;self.origin=None;self.state='stopped';self.closed=False
        self.timer=app.after(120,self.poll)
    def attach(self,parent,record):
        key=(self.app.settings['osu_path'],str(record['score'].get('beatmap_id') or record['map'].get('path','')))
        button=self.app.button(parent,'▶',lambda:None)
        button.configure(width=30,height=28,corner_radius=9,font=('Segoe UI',13,'bold'))
        button.configure(command=lambda:self.toggle(button,record,key))
        button.place(relx=1,rely=1,anchor='se',x=-7,y=-7)
        self.buttons[button]=key;self.paint();return button
    def submit(self,fn):
        future=self.executor.submit(fn);self.app.background_tasks.append(future)
    def paint(self):
        for button,key in list(self.buttons.items()):
            if button.winfo_exists():button.configure(text=('…' if self.state=='loading' else '■') if key==self.current else '▶')
    def stop(self):
        self.token+=1;self.current=None;self.state='stopped';self.origin=None
        self.submit(self.backend.stop);self.paint()
    def toggle(self,button,record,key):
        if self.closed:return
        if self.current==key:self.stop();return
        self.token+=1;ticket=self.token;self.current=key;self.origin=weakref.ref(button);self.state='loading';self.paint()
        def work():
            try:
                self.backend.stop()
                locator=self.locators.setdefault(key[0],AudioLocator(key[0]))
                path=locator.find(record)
                if ticket!=self.token or self.closed:return
                if path is None:raise FileNotFoundError('local-audio')
                self.backend.play(path)
                self.events.put((ticket,None))
            except FileNotFoundError:self.events.put((ticket,'missing'))
            except Exception:self.events.put((ticket,'playback'))
        self.submit(work)
    def poll(self):
        if self.closed:return
        while not self.events.empty():
            ticket,error=self.events.get()
            if ticket!=self.token:continue
            origin=self.origin() if self.origin else None
            if not origin or not origin.winfo_exists():self.stop();continue
            if error:
                self.stop()
                ru='Аудио карты не найдено в папке Songs. Установите карту в osu! и проверьте папку игры в настройках.' if error=='missing' else 'Не удалось воспроизвести трек. Проверьте устройство вывода звука и файл аудио. Обновите зависимости через install_dependencies.cmd, если программа была перенесена вручную.'
                en='Map audio was not found in Songs. Install the map in osu! and check the game folder in settings.' if error=='missing' else 'Could not play this track. Check your audio output and audio file. Run install_dependencies.cmd if you copied the app manually.'
                messagebox.showinfo('Трек карты' if self.app.settings['language']!='English' else 'Map music',en if self.app.settings['language']=='English' else ru,parent=origin.winfo_toplevel())
            else:self.state='playing';self.paint()
        if self.origin:
            origin=self.origin()
            if not origin or not origin.winfo_exists():self.stop()
            elif self.state=='playing' and not self.backend.busy():self.stop()
        self.timer=self.app.after(120,self.poll)
    def close(self):
        if self.closed:return
        self.closed=True;self.token+=1;self.app.after_cancel(self.timer)
        self.submit(self.backend.close);self.executor.shutdown(wait=False)
