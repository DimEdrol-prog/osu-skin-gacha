"""osu! Skin Gacha: gacha_widgets."""
from __future__ import annotations
import math
import random
import time
import os
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
from modules.gacha_config import BASE

class FastScrollableFrame(ctk.CTkScrollableFrame):
    """Оставляем штатную маршрутизацию колеса CTk, удваиваем только шаг Canvas."""
    def _set_scroll_increments(self):
        super()._set_scroll_increments()
        for option in ('xscrollincrement','yscrollincrement'):
            self._parent_canvas.configure(**{option:2*float(self._parent_canvas.cget(option))})


class FastTextbox(ctk.CTkTextbox):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.bind('<MouseWheel>',self.wheel)
        self.bind('<Shift-MouseWheel>',lambda event:self.wheel(event,horizontal=True))
        self.bind('<Button-4>',lambda event:self.wheel(event,pixels=-100))
        self.bind('<Button-5>',lambda event:self.wheel(event,pixels=100))

    def wheel(self,event,horizontal=False,pixels=None):
        if pixels is None:
            if self.tk.call('tk','windowingsystem') == 'aqua':
                pixels = -30*event.delta
            else:
                pixels = 2*((-event.delta)//3 if event.delta >= 0 else (2-event.delta)//3)
        view = self._textbox.xview_scroll if horizontal else self._textbox.yview_scroll
        view(int(pixels),'pixels')
        return 'break'


class Particles(tk.Canvas):
    """Один таймер и постоянные Canvas-объекты, без пересоздания при resize."""
    def __init__(self, master, theme):
        super().__init__(master, bg=theme['bg'], highlightthickness=0, bd=0)
        self.mode, self.timer = theme['anim'], None
        self.items = []
        for _ in range(36 if self.mode != 'none' else 0):
            create = self.create_line if self.mode == 'rain' else self.create_oval
            ident = create(0, 0, 0, 0, fill=theme['secondary'], **({} if self.mode == 'rain' else {'outline':''}))
            self.items.append([ident, random.random(), random.random(), random.uniform(.025,.08), random.uniform(2,4), random.random()*6.28])
        self.last = time.monotonic()
        self.tick()

    def tick(self):
        now = time.monotonic()
        dt, self.last = min(now-self.last,.1), now
        if self.winfo_toplevel().state() != 'iconic':
            w,h = max(1,self.winfo_width()),max(1,self.winfo_height())
            for p in self.items:
                p[2] = (p[2]+p[3]*dt*(4 if self.mode == 'rain' else 1)) % 1
                p[1] = (p[1]+math.sin(now+p[5])*dt*.012) % 1
                x,y,s = p[1]*w,p[2]*h,p[4]
                self.coords(p[0],x,y,x+(5 if self.mode == 'rain' else s*2 if self.mode == 'leaves' else s),y+(14 if self.mode == 'rain' else s))
        if self.items:
            self.timer = self.after(40,self.tick)

    def destroy(self):
        if self.timer:
            self.after_cancel(self.timer)
        super().destroy()


def bind_api_paste(entry):
    def paste(event):
        if event.keycode==86 or event.keysym.lower()=='v':
            try:
                value=entry.clipboard_get().strip()
                entry.delete(0,'end')
                entry.insert(0,value)
            except tk.TclError: pass
            return 'break'
    entry.bind('<Control-KeyPress>',paste,add='+')


def enable_paste(root):
    """Also recognise physical Ctrl+V with a Cyrillic keyboard layout."""
    def paste(event):
        if event.keycode == 86 or event.keysym.lower() == 'v':
            event.widget.event_generate('<<Paste>>')
            return 'break'
    for kind in ('Entry','TEntry','Text','Spinbox','TSpinbox','TCombobox'):
        root.bind_class(kind,'<Control-KeyPress>',paste,add='+')
        root.bind_class(kind,'<Control-KeyPress-v>',paste)


def apply_window_icon(window):
    path = BASE/'assets'/'gacha.ico'
    if path.is_file() and window.winfo_exists():
        try:
            window.iconbitmap(str(path))
            # Передаём Tk полноценные изображения всех размеров, чтобы Windows
            # не растягивала маленький кадр ICO на панели задач при высоком DPI.
            with Image.open(BASE/'assets'/'gacha-logo.png') as original:
                window._gacha_icons = [ImageTk.PhotoImage(original.convert('RGBA').resize((n,n),Image.Resampling.LANCZOS),master=window)
                    for n in (16,20,24,32,40,48,64,96,128,256)]
            window.iconphoto(False,*window._gacha_icons)
        except (tk.TclError,OSError): pass


class IconWindow(ctk.CTkToplevel):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        parent = self.master.winfo_toplevel()
        focused = parent.focus_get()
        if focused is not None:
            parent = focused.winfo_toplevel()
        self.after(100, self.lift)
        self.after(120, self.taskbar_window)
        # CustomTkinter устанавливает стандартную иконку отложенно, заменяем после неё.
        self.after(350,lambda:apply_window_icon(self))

    def taskbar_window(self):
        """Unowned app windows appear as separate thumbnails in the taskbar group."""
        if os.name != 'nt' or not self.winfo_exists(): return
        import ctypes
        from ctypes import wintypes
        user32=ctypes.WinDLL('user32',use_last_error=True)
        user32.GetParent.argtypes=[wintypes.HWND]
        user32.GetParent.restype=wintypes.HWND
        get=user32.GetWindowLongPtrW
        get.argtypes=[wintypes.HWND,ctypes.c_int];get.restype=ctypes.c_ssize_t
        setlong=user32.SetWindowLongPtrW
        setlong.argtypes=[wintypes.HWND,ctypes.c_int,ctypes.c_ssize_t];setlong.restype=ctypes.c_ssize_t
        hwnd=user32.GetParent(self.winfo_id()) or self.winfo_id()
        setlong(hwnd,-20,(get(hwnd,-20)|0x40000)&~0x80)
        setlong(hwnd,-8,0)
        user32.SetWindowPos.argtypes=[wintypes.HWND,wintypes.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.UINT]
        user32.SetWindowPos(hwnd,None,0,0,0,0,0x37)

