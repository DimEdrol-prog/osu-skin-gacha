"""osu! Skin Gacha: gacha_app."""
from __future__ import annotations
import gc
import copy
from datetime import datetime
import io
import json
import math
from pathlib import Path
import queue
import random
import threading
import time
import tkinter as tk
from tkinter import messagebox, filedialog
import webbrowser
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import customtkinter as ctk
import requests
from PIL import Image, ImageOps
from modules.gacha_sources import SkinSources, OfflineAPI, GatariAPI, session_for
from modules.gacha_config import is_developer, RANKS, COMBO, TOP, RANK_COLORS, THEMES, COLORS, TEXT, tr, blend
from modules.gacha_storage import atomic_json, SettingsStore, HistoryStore
from modules.gacha_rules import rank_thresholds, difficulty_key, pp_thresholds, stars_threshold, score_key, accuracy, mods_string, reward_for, dt_reward, score_url, resolve_score_url
from modules.gacha_skins import SkinLibrary, Sandbox
from modules.gacha_api import API, Covers
from modules.gacha_widgets import FastScrollableFrame, FastTextbox, Particles, bind_api_paste, apply_window_icon, IconWindow
from modules.gacha_settings import SETTING_HELP, SettingsWindow
from modules.gacha_reports import ReportsMixin
from modules.gacha_skin_apply import update_live
from modules.gacha_previews import PreviewCache, RouletteStrip
from modules.gacha_widgets import enable_paste
from modules.gacha_connection import ConnectionIndicator, mark as mark_connection, state as connection_state
from modules.gacha_updates import open_changelog, open_session_search, animate_pp
from modules.gacha_rules import special_chance, special_gain, claimed_ranks, reward_upgrade, rank_level
from modules.gacha_insights import all_records, comparison_index, comparison_text, open_progress, open_summary

class SkinGachaApp(ReportsMixin, ctk.CTk):
    def __init__(self):
        super().__init__()
        enable_paste(self)
        # У Tk-объектов есть циклические ссылки. Их финализаторы должны идти в UI-потоке.
        self.gc_enabled = gc.isenabled()
        gc.disable()
        self.background_tasks = []
        self.shutdown_started = False
        self.title('osu! Skin Gacha')
        self.after(350,lambda:apply_window_icon(self))
        self.geometry(f'1180x{min(980, max(640, self.winfo_screenheight()-100))}')
        self.minsize(880,640)
        ctk.set_appearance_mode('dark')
        self.store = SettingsStore()
        self.settings = self.store.load()
        ctk.set_widget_scaling(int(self.settings.get('ui_scale','100%').rstrip('%'))/100)
        self.comparison_cache = {}
        self.history_store = HistoryStore()
        self.history,self.current_session,self.selected_session = {},None,None
        self.history_timer = None
        self.avatar_cache,self.avatar_pending = {},set()
        self.profile_id = str(self.settings['user_id'])
        self.events = queue.Queue()
        self.files = ThreadPoolExecutor(max_workers=1,thread_name_prefix='gacha-files')
        self.images = ThreadPoolExecutor(max_workers=1,thread_name_prefix='gacha-covers')
        self.network = ThreadPoolExecutor(max_workers=2,thread_name_prefix='gacha-network')
        self.logs,self.records,self.rolls = deque(maxlen=2000),deque(),deque()
        self.page = 0
        self.cards = []
        self.state_name,self.generation = 'idle',0
        self.stop_event = threading.Event()
        self.worker = None
        self.closing,self.rolling,self.roll_timer = False,False,None
        self.destroyed = False
        self.total_pp,self.start_pp,self.username = None,None,'—'
        self.unlocked,self.pool = 0,{}
        self.catalog,self.drops,self.base_skins = {},{},[]
        self.collection_window = None
        self.failed_drop = None
        self.latest_skin = None
        self.applied_skin = None
        self.applying_skin = False
        self.enrich_pending = set()
        self.settings_window,self.log_window = None,None
        self.configure_services()
        self.build_ui()
        self.submit(self.files,'history_loaded',self.history_store.load)
        if self.settings['setup_complete']:
            self.refresh_pool()
        else:
            self.after(150,self.open_setup)
        self.protocol('WM_DELETE_WINDOW',self.on_close)
        self.after(40,self.drain_events)
        self.after(2000,self.collect_garbage)
        if is_developer(self.settings["api_key"]) and not self.settings["offline"]:
            self.after(2500,self.check_reports)

    def open_setup(self):
        from modules.gacha_setup import open_setup
        open_setup(self)

    def animate_value(self,widget,start,end,apply,duration=240):
        # Таймер привязан к корневому окну и проверяет жизнь виджета перед каждым кадром.
        token = object()
        widget._motion_token = token
        began = time.monotonic()
        def frame():
            if self.destroyed or not widget.winfo_exists() or widget._motion_token is not token:
                return
            fraction = min(1,(time.monotonic()-began)*1000/duration) if self.settings['ui_motion'] else 1
            eased = 1-(1-fraction)**3
            apply(start+(end-start)*eased)
            if fraction<1: self.after(25,frame)
        frame()

    def smooth_progress(self,value):
        if abs(self.progress.get()-value)>0.001:
            self.animate_value(self.progress,self.progress.get(),value,self.progress.set)

    def collect_garbage(self):
        gc.collect()
        if not self.destroyed:
            self.after(2000,self.collect_garbage)

    def t(self,key,**values):
        return tr(key,self.settings['language'],**values)

    def visible_records(self):
        records = self.records if self.selected_session is None else self.history.get(self.selected_session,{}).get('records',[])
        return [r for r in records if not self.settings['hide_failed'] or r['score'].get('rank') != 'F']

    def update_history_menu(self):
        self.history_options = {self.t('current_session'):None}
        current_id = self.current_session['id'] if self.current_session else None
        for session in sorted(self.history.values(),key=lambda s:s['started_at'],reverse=True):
            if not self.session_matches(session) or session['id'] == current_id:
                continue
            date = datetime.fromisoformat(session['started_at']).strftime('%d.%m.%Y  %H:%M:%S')
            label = f"{date} · {len(session['records'])} " + ('scores' if self.settings['language']=='English' else 'скоров')
            base=label;number=2
            while label in self.history_options:
                label=f'{base} ({number})';number+=1
            self.history_options[label] = session['id']
        if current_id:
            date = datetime.fromisoformat(self.current_session['started_at']).strftime('%d.%m.%Y  %H:%M')
            self.history_options = {f"{self.t('current_session')} · {date}":None,
                                    **{k:v for k,v in self.history_options.items() if v is not None}}
        if self.selected_session not in self.history_options.values():
            self.selected_session = None
        if hasattr(self,'history_search'):
            self.history_search.pack_forget()
            if len(self.history_options)-1+(1 if current_id else 0)>10:self.history_search.pack(side='left',padx=(0,8),before=self.history_menu)
        self.history_menu.configure(values=list(self.history_options))
        self.history_menu.set(next(k for k,v in self.history_options.items() if v == self.selected_session))

    def select_history(self,label):
        self.selected_session = self.history_options[label]
        self.page = 0
        self.show_page(0)

    def request_record_pp(self,records):
        """Дозаполняем PP старых карточек в фоне, не повторяя запрос при перерисовке."""
        missing = [r for r in records if r['score'].get('pp') is None and id(r) not in self.enrich_pending]
        settings = self.settings.copy()
        if not missing or (not settings['offline'] and settings['server']=='bancho' and not settings['api_key']):
            return
        self.enrich_pending.update(id(r) for r in missing)
        def enrich():
            api = self.make_api(settings)
            try:
                for record in missing:
                    if self.destroyed:
                        break
                    try:
                        original = dict(record['score'])
                        if settings['offline']:
                            score,_ = api.maps.calculate(original)
                        else:
                            score = api.enrich_pp(original)
                        if score.get('pp') is not None:
                            self.events.put(('pp_refreshed',None,(record,score)))
                    except (OSError,ValueError,RuntimeError):
                        continue
            finally:
                api.session.close()
        self.background_tasks.append(self.network.submit(enrich))

    def schedule_history(self):
        if self.history_timer:
            self.after_cancel(self.history_timer)
        self.history_timer = self.after(500,self.persist_history)

    def persist_history(self):
        if self.history_timer:
            self.after_cancel(self.history_timer)
            self.history_timer = None
        if not self.current_session:
            return
        snapshot = copy.deepcopy(dict(self.current_session,records=list(self.records)))
        self.history[snapshot['id']] = snapshot
        self.submit(self.files,'history_saved',self.history_store.save,snapshot)

    def open_profile(self):
        if self.profile_id.isdigit():
            host = 'https://osu.gatari.pw/u/' if self.settings['server']=='gatari' else 'https://osu.ppy.sh/users/'
            webbrowser.open(host+self.profile_id)

    @staticmethod
    def fetch_avatar(ident,ignore_proxy=False,server='bancho'):
        # Публичный endpoint osu!: ключ API не требуется. Ошибка не мешает профилю.
        try:
            with session_for(ignore_proxy) as session:
                host = 'https://a.gatari.pw/' if server=='gatari' else 'https://a.ppy.sh/'
                response = session.get(host+ident,timeout=(4,8))
                response.raise_for_status()
                with Image.open(io.BytesIO(response.content)) as img:
                    picture = ImageOps.fit(img.convert('RGBA'),(104,104),method=Image.Resampling.LANCZOS)
            return (server,ident,ignore_proxy),picture
        except (requests.RequestException,OSError,ValueError):
            return (server,ident,ignore_proxy),None

    def avatar_key(self):
        return self.settings['server'],self.profile_id,self.settings['ignore_proxy']

    def request_avatar(self):
        ident = self.profile_id
        key = self.avatar_key()
        if not ident.isdigit() or self.settings['offline']:
            return
        if key in self.avatar_cache:
            self.render_avatar()
        elif key not in self.avatar_pending:
            self.avatar_pending.add(key)
            self.submit(self.network,'avatar',self.fetch_avatar,ident,self.settings['ignore_proxy'],self.settings['server'])

    def render_avatar(self):
        picture = self.avatar_cache.get(self.avatar_key())
        if picture is not None:
            avatar = ctk.CTkImage(light_image=picture,dark_image=picture,size=(52,52))
            self.avatar_label.configure(image=avatar,text='')
            self.avatar_label._avatar_ref = avatar
        else:
            self.avatar_label.configure(image=None,text='♪')

    def apply_live_setting(self,key,value):
        if self.state_name=='transferring' or (self.applying_skin and key in SettingsWindow.LOCKED): return
        if self.settings.get(key) == value:
            return
        if key == 'optimize_skins' and value and self.settings['interface_skin'] not in self.base_skins:
            raise ValueError(self.t('no_base'))
        if key in SettingsWindow.LOCKED and self.state_name != 'idle':
            return
        updated = dict(self.settings,**{key:value})
        if key in ('server','user_id'):
            ids = dict(self.settings.get('server_user_ids',{}))
            ids[self.settings['server']] = str(self.settings.get('user_id',''))
            if key == 'server':
                updated['user_id'] = ids.get(value,'')
            else:
                ids[self.settings['server']] = str(value)
            updated['server_user_ids'] = ids
        if key=='offline' and value and not updated['offline_total_pp'] and self.total_pp is not None:
            updated['offline_total_pp'] = self.total_pp
        self.store.save(updated)
        self.settings = updated
        if key=='ui_scale': ctk.set_widget_scaling(int(value.rstrip('%'))/100)
        profile_changed = key in ('api_key','user_id','server','offline','slot','offline_username')
        if profile_changed:
            self.persist_history()
            self.current_session,self.selected_session = None,None
            self.total_pp,self.username = None,'—'
            self.profile_id = str(self.settings['user_id'])
            self.records.clear()
        service_changed = key in ('osu_path','skin_pack_path','skin_source','skin_archive','drive_folder','keep_personal','slot','offline')
        if service_changed:
            self.configure_services()
        if service_changed or profile_changed or key in ('theme','color','language','animations','ui_motion'):
            self.build_ui()
        elif key in ('hide_failed','log_mode') or key.startswith('show_'):
            if key=='hide_failed': self.failed_var.set(value)
            self.page = 0
            self.show_page(0)
        else:
            self.update_stats()
            if key == 'difficulty':
                self.mode_label.configure(text=self.t('difficulty').upper()+' / '+self.t(value).upper())
        if profile_changed or service_changed:
            self.refresh_pool()
        if key == 'ignore_proxy':
            self.covers.ignore_proxy = value
            self.request_avatar()
            self.library.sources.settings['ignore_proxy'] = value
            if self.state_name == 'idle':
                self.refresh_pool()

    def reset_skins(self):
        if self.state_name!='idle':
            return
        parent = self.settings_window if self.settings_window and self.settings_window.winfo_exists() else self
        if messagebox.askyesno(self.t('reset_skins'),self.t('reset_confirm'),parent=parent):
            self.state_name = 'resetting'
            self.update_controls()
            self.submit(self.files,'skins_reset',self.library.reset_all)

    def session_matches(self,session):
        return (session['user_id']==str(self.settings['user_id']) and
            session.get('server','bancho')==self.settings['server'] and
            session.get('offline',False)==self.settings['offline'] and
            session.get('slot','1')==self.settings['slot'])

    def make_api(self,settings):
        return OfflineAPI(settings) if settings['offline'] else GatariAPI(settings) if settings['server']=='gatari' else API(settings)

    def open_collection(self):
        if self.collection_window and self.collection_window.winfo_exists():
            self.collection_window.lift()
            return
        from modules.gacha_collection import CollectionWindow
        self.collection_window = CollectionWindow(self)

    def render_collection(self):
        if self.collection_window and self.collection_window.winfo_exists():
            self.collection_window.refresh()

    def transfer_data(self, importing=False, include_key=False):
        if self.state_name!='idle' or self.applying_skin: return
        from modules.gacha_transfer import export_data, import_data
        if importing:
            path=filedialog.askopenfilename(parent=self.settings_window or self,title='Импорт / Import',filetypes=[('Gacha data','*.gacha.zip')])
        else:
            path=filedialog.asksaveasfilename(parent=self.settings_window or self,title='Экспорт / Export',defaultextension='.gacha.zip',initialfile='osu-gacha-data.gacha.zip',filetypes=[('Gacha data','*.gacha.zip')])
        if not path:return
        if self.settings_window and self.settings_window.winfo_exists():self.settings_window.destroy()
        self.persist_history()
        self.state_name='transferring';self.update_controls()
        self.status_label.configure(text='Перенос данных…' if self.settings['language']!='English' else 'Transferring data…')
        if self.settings_window and self.settings_window.winfo_exists():self.settings_window.destroy()
        if importing:
            self.submit(self.files,'data_imported',import_data,path,copy.deepcopy(self.settings),copy.deepcopy(self.history),self.sandbox,self.store,self.history_store)
        else:
            self.submit(self.files,'data_exported',export_data,path,copy.deepcopy(self.settings),copy.deepcopy(self.history),self.sandbox.pack,include_key,self.sandbox)

    def export_favorite(self,ident):
        if self.state_name != 'idle':
            self.status_label.configure(text=self.t('export_stop'))
            return
        self.submit(self.files,'exported',self.library.export,ident)

    def best_records(self,mode,hide_failed=None,query=''):
        unique = {}
        for session in self.history.values():
            if self.session_matches(session):
                for record in session['records']:
                    key = score_key(record['score'])
                    if key not in unique or (record.get('position') or 101) < (unique[key].get('position') or 101):
                        unique[key] = record
        for record in self.records:
            key = score_key(record['score'])
            if key not in unique or (record.get('position') or 101) < (unique[key].get('position') or 101):
                unique[key] = record
        hide_failed = self.settings['hide_failed'] if hide_failed is None else hide_failed
        records = [r for r in unique.values() if not hide_failed or r['score'].get('rank') != 'F']
        words = query.casefold().split()
        if words:
            records = [r for r in records if all(word in (' '.join(str(r['map'].get(k,'')) for k in
                ('artist','title','version','creator','beatmap_id'))+' '+mods_string(r['score'].get('enabled_mods'))).casefold() for word in words)]
        def order(r):
            score = r['score']
            pp = float(score['pp']) if score.get('pp') is not None else -1
            combo = int(score.get('maxcombo') or 0)
            return (combo,pp) if mode == 'combo' else (pp,combo)
        return sorted(records,key=order,reverse=True)[:100]

    def open_best(self):
        window = IconWindow(self)
        window.title(self.t('best_scores'))
        window.geometry('820x680')
        window.configure(fg_color=self.theme['bg'])
        self.label(window,self.t('best_hint'),muted=True,wraplength=760).pack(padx=20,pady=14)
        body = FastScrollableFrame(window,fg_color=self.theme['bg'])
        hide_failed = tk.BooleanVar(value=self.settings['hide_failed'])
        search = tk.StringVar()
        def render(label):
            for widget in body.winfo_children():
                if isinstance(widget,ctk.CTkFrame):
                    widget.destroy()
            mode = next(k for k in ('sort_pp','sort_combo') if self.t(k) == label)
            mode = 'combo' if mode=='sort_combo' else 'pp'
            records = self.best_records(mode,hide_failed.get(),search.get())
            if not records:
                empty = self.panel(body)
                empty.pack(fill='x',pady=12)
                self.label(empty,'Ничего не найдено' if self.settings['language']!='English' else 'No matching scores').pack(pady=18)
            self.request_record_pp(records)
            self.comparison_cache=comparison_index(all_records(self))
            for n,record in enumerate(records,1):
                row = self.panel(body)
                row.pack(fill='x',pady=5)
                self.cover_widget(row,record).pack(side='left',padx=10,pady=12)
                info,score = record['map'],record['score']
                rank = score.get('rank','?')
                badge = self.label(row,{'X':'SS','XH':'SSH'}.get(rank,rank),size=28,bold=True,width=64)
                badge.configure(text_color=RANK_COLORS.get(rank,self.theme['accent']) if self.theme['bg'] not in ('#faf1f3','#f2f0e9') else self.theme['accent'])
                badge.pack(side='right',padx=12,pady=12)
                self.label(row,f"#{n}  {info.get('artist','')} — {info.get('title','')} [{info.get('version','')}]",bold=True,wraplength=450).pack(anchor='w',padx=12,pady=8)
                pp = ('≈ ' if score.get('pp_source')=='calculated' else '')+f"{float(score['pp']):.2f}" if score.get('pp') is not None else '—'
                self.label(row,f"{pp} PP · {float(info.get('difficultyrating') or 0):.2f}★ · #{record.get('position') or '—'} · {score.get('date','')}",muted=True).pack(anchor='w',padx=12)
                self.label(row,self.score_stats(score,info)+(('\n'+comparison_text(self,record)) if comparison_text(self,record) else ''),muted=True,wraplength=450,justify='left').pack(anchor='w',padx=12,pady=(4,8))
                if score.get('rank')!='F' and score.get('provider') not in ('offline','gatari'):
                    self.button(row,self.t('score_link'),lambda r=record:self.open_score(r),True).pack(anchor='e',padx=12,pady=8)
        menu = ctk.CTkOptionMenu(window,values=[self.t(k) for k in ('sort_pp','sort_combo')],command=render)
        menu.set(self.t('sort_pp'))
        menu.pack(pady=(0,10))
        self.label(window,'Поиск по скорам' if self.settings['language']!='English' else 'Search scores',muted=True).pack(anchor='w',padx=20)
        search_entry = ctk.CTkEntry(window,textvariable=search,placeholder_text='Search maps, artists, difficulties, mods' if self.settings['language']=='English' else 'Поиск: карта, исполнитель, сложность, моды',height=36)
        search_entry.pack(fill='x',padx=20,pady=6)
        pending_search = [None]
        def queue_search(*args):
            if pending_search[0]: window.after_cancel(pending_search[0])
            pending_search[0] = window.after(250,lambda:render(menu.get()))
        search.trace_add('write',queue_search)
        def toggle_failed():
            hide_failed.set(not hide_failed.get())
            failed_button.configure(text=self.t('best_show_failed' if hide_failed.get() else 'best_hide_failed'))
            render(menu.get())
        failed_button = self.button(window,self.t('best_show_failed' if hide_failed.get() else 'best_hide_failed'),toggle_failed,True)
        failed_button.pack(pady=4)
        body.pack(fill='both',expand=True,padx=12,pady=12)
        render(menu.get())
        self.best_refresh = lambda:render(menu.get()) if window.winfo_exists() else None

    def open_score(self,record):
        if record['score'].get('rank')=='F' or record['score'].get('provider') in ('offline','gatari'):
            return
        url = score_url(record['score'])
        if url:
            self.submit(self.files,'score_page',resolve_score_url,record['score'].copy(),self.settings['ignore_proxy'])
            return
        settings = self.settings.copy()
        if not settings['api_key']:
            self.status_label.configure(text=self.t('score_missing'))
            return
        def lookup():
            api = API(settings)
            try:
                score = record['score']
                for candidate in api.get('get_scores',b=score['beatmap_id'],u=settings['user_id'],type='id',limit=100):
                    candidate['beatmap_id'] = score['beatmap_id']
                    if score_key(candidate) == score_key(score):
                        return record,candidate
                return record,None
            finally:
                api.session.close()
        self.submit(self.files,'score_lookup',lookup)

    def configure_services(self):
        if self.settings['offline'] and hasattr(self, 'covers'):
            # Уже поставленные в очередь обложки тоже не должны обращаться к сети.
            self.covers.offline = True
        self.sandbox = Sandbox(self.settings['osu_path'],self.settings['skin_pack_path'],lambda m:self.events.put(('log',None,m)),slot=self.settings['slot'])
        self.sandbox.identity += (self.settings['skin_source'],self.settings['skin_archive'],self.settings['drive_folder'],self.settings['offline'])
        self.library = SkinLibrary(self.sandbox,SkinSources(self.settings,self.sandbox.pack,log=self.sandbox.log))
        identity=self.sandbox.identity
        self.library.sources.progress=lambda *v:self.events.put(('download_progress',None,(identity,v)))
        cache = PreviewCache(self.library.sources.cache, self.settings,
                             lambda: self.closing or getattr(self, 'preview_cache', None) is not cache)
        self.preview_cache = cache
        self.preview_warm_task = None
        self.roulette_ticket = None
        self.pool,self.catalog,self.drops,self.base_skins = {},{},{},[]
        self.covers = Covers(Path(self.settings['osu_path'])/'Songs', self.settings['offline'], self.settings['ignore_proxy'])
        self.state_name = 'recovery' if self.sandbox.recover_needed() else 'idle'

    def label(self,parent,text,size=13,bold=False,muted=False,**kwargs):
        return ctk.CTkLabel(parent,text=text,font=('Segoe UI',size+2,'bold' if bold else 'normal'),text_color=self.theme['muted' if muted else 'text'],**kwargs)

    def button(self,parent,text,command,secondary=False):
        hover = blend(self.theme['card' if secondary else 'accent'],'#000000',.08)
        return ctk.CTkButton(parent,text=text,command=command,height=42,corner_radius=min(self.theme['radius'],14),fg_color=self.theme['card' if secondary else 'accent'],hover_color=hover,text_color=self.theme['text'] if secondary else self.ink,font=('Segoe UI',15,'bold'))

    def panel(self,parent):
        return ctk.CTkFrame(parent,fg_color=self.theme['panel'],corner_radius=self.theme['radius'])

    def build_ui(self):
        previous_strip = getattr(self,'roulette_strip',None)
        saved_roll = (previous_strip.sequence,previous_strip.progress) if previous_strip else (None,0)
        self.generation += 1
        self.theme = THEMES[self.settings['theme']].copy()
        if COLORS[self.settings['color']][2]:
            self.theme['accent'] = COLORS[self.settings['color']][2]
        rgb = [int(self.theme['accent'][i:i+2],16)/255 for i in (1,3,5)]
        self.ink = '#10151b' if sum(c*w for c,w in zip(rgb,(.2126,.7152,.0722))) > .55 else '#ffffff'
        for child in self.winfo_children():
            if not isinstance(child,tk.Toplevel):
                child.destroy()
        self.cards = []
        self.configure(fg_color=self.theme['bg'])
        self.background = Particles(self,dict(self.theme,anim=self.theme['anim'] if self.settings['animations'] else 'none'))
        self.background.place(x=0,y=0,relwidth=1,relheight=1)
        self.shell = ctk.CTkFrame(self,fg_color='transparent')
        self.shell.pack(fill='both',expand=True,padx=26,pady=22)
        header = ctk.CTkFrame(self.shell,fg_color='transparent')
        header.pack(fill='x',pady=(0,20))
        logo = self.label(header,'osu!',size=32,bold=True,fg_color=self.theme['accent'],corner_radius=24,width=86,height=58)
        logo.configure(text_color=self.ink)
        logo.configure(cursor='hand2')
        logo.bind('<Button-1>',lambda event:webbrowser.open('https://osu.ppy.sh/'))
        logo.pack(side='left')
        titles = ctk.CTkFrame(header,fg_color='transparent')
        titles.pack(side='left',padx=16)
        self.label(titles,'SKIN GACHA',size=25,bold=True).pack(anchor='w')
        self.label(titles,self.t('intro'),muted=True).pack(anchor='w')
        self.settings_button = self.button(header,self.t('settings'),self.open_settings,True)
        self.settings_button.pack(side='right')
        self.button(header,self.t('collection'),self.open_collection,True).pack(side='right',padx=8)
        self.connection_indicator=ConnectionIndicator(self.shell,self)
        self.connection_indicator.pack(fill='x',pady=(0,10))
        content = ctk.CTkFrame(self.shell,fg_color='transparent')
        content.pack(fill='both',expand=True)
        content.grid_columnconfigure(1,weight=1)
        content.grid_rowconfigure(0,weight=1)
        side = self.panel(content)
        side.grid(row=0,column=0,sticky='ns',padx=(0,18))
        side.configure(width=235)
        side.grid_propagate(False)
        side.grid_columnconfigure(0,weight=1)
        self.label(side,self.t('account').upper(),muted=True).grid(row=0,column=0,sticky='w',padx=20,pady=(22,2))
        profile = ctk.CTkFrame(side,fg_color='transparent')
        profile.grid(row=1,column=0,sticky='ew',padx=20,pady=(4,8))
        self.avatar_label = self.label(profile,'♪',size=24,width=52,height=52,fg_color=self.theme['card'],corner_radius=12)
        self.avatar_label.pack(side='left',padx=(0,10))
        self.profile_label = self.label(profile,self.username,size=20,bold=True,wraplength=125,justify='left')
        self.profile_label.pack(side='left')
        for widget in (self.profile_label,self.avatar_label):
            widget.configure(cursor='hand2')
            widget.bind('<Button-1>',lambda event:self.open_profile())
        self.render_avatar()
        self.pp_label = self.label(side,'— PP',size=18)
        self.pp_label.grid(row=2,column=0,sticky='w',padx=20,pady=(0,20))
        self.label(side,self.t('rules').upper(),muted=True).grid(row=3,column=0,sticky='w',padx=20)
        self.rules_label = self.label(side,'',size=14,justify='left',anchor='w',wraplength=192)
        self.rules_label.grid(row=4,column=0,sticky='ew',padx=20,pady=10)
        self.next_label = self.label(side,'',muted=True,wraplength=192,justify='left',anchor='w')
        self.next_label.grid(row=5,column=0,sticky='ew',padx=20,pady=(10,3))
        self.progress = ctk.CTkProgressBar(side,progress_color=self.theme['accent'],fg_color=self.theme['card'],width=190,height=6)
        self.progress.grid(row=6,column=0,padx=20,pady=(0,20))
        self.progress.set(0)
        side.grid_rowconfigure(7,weight=1)
        self.pool_label = self.label(side,'',muted=True)
        self.pool_label.grid(row=8,column=0,sticky='w',padx=20,pady=8)
        self.unlock_label = self.label(side,'',size=15,bold=True)
        self.unlock_label.grid(row=9,column=0,sticky='w',padx=20,pady=(0,16))
        self.label(side,self.t('coexist_hint' if self.settings.get('keep_personal') else 'hint'),muted=True,wraplength=190,justify='left').grid(row=10,column=0,padx=20,pady=(0,20))
        main = ctk.CTkFrame(content,fg_color='transparent')
        main.grid(row=0,column=1,sticky='nsew')
        hero = self.panel(main)
        hero.pack(fill='x',pady=(0,16))
        self.mode_label = self.label(hero,self.t('difficulty').upper()+' / '+self.t(self.settings['difficulty']).upper(),muted=True)
        self.mode_label.pack(anchor='w',padx=22,pady=(20,4))
        self.roulette_label = self.label(hero,self.t('ready'),size=26,bold=True,wraplength=600,anchor='w',justify='left')
        self.roulette_label.pack(fill='x',padx=22,pady=(0,6))
        self.roulette_strip = RouletteStrip(hero, self.theme)
        self.status_label = self.label(hero,self.t('recovery') if self.state_name == 'recovery' else self.t('waiting'),muted=True,wraplength=600,justify='left',anchor='w')
        self.status_label.pack(fill='x',padx=22)
        if saved_roll[0]:
            self.roulette_strip.pack(fill='x',padx=22,pady=(0,8),before=self.status_label)
            self.roulette_strip.show(*saved_roll)
        hero.bind('<Configure>',lambda e:(self.roulette_label.configure(wraplength=max(200,e.width-44)),self.status_label.configure(wraplength=max(200,e.width-44))))
        row = ctk.CTkFrame(hero,fg_color='transparent')
        row.pack(fill='x',padx=22,pady=18)
        self.start_button = self.button(row,'',self.toggle)
        self.start_button.pack(side='left')
        self.retry_button = self.button(row,self.t('retry_drop'),self.retry_drop,True)
        if self.failed_drop:
            self.retry_button.pack(side='right')
        self.button(row,self.t('logs'),self.open_logs,True).pack(side='left',padx=8)
        support = row
        self.button(support,self.t('report_bug'),self.report_bug,True).pack(side='left',padx=4)
        self.reports_button=self.button(support,self.t('reports'),self.open_reports,True)
        self.reports_button.pack(side='left',padx=4)
        for button in row.winfo_children():
            if isinstance(button,ctk.CTkButton):
                button.configure(width=0,font=('Segoe UI',13,'bold'))
        self.session = self.panel(main)
        self.session.pack(fill='both',expand=True)
        self.label(self.session,self.t('scores'),size=19,bold=True).pack(anchor='w',padx=20,pady=(16,8))
        score_tools=ctk.CTkFrame(self.session,fg_color='transparent')
        score_tools.pack(fill='x',padx=16,pady=(0,8))
        self.button(score_tools,self.t('best_scores'),self.open_best,True).pack(side='left')
        self.button(score_tools,self.t('progress_view'),lambda:open_progress(self),True).pack(side='left',padx=8)
        self.button(score_tools,self.t('summary'),lambda:open_summary(self),True).pack(side='left')
        self.button(score_tools,self.t('changelog'),lambda:open_changelog(self),True).pack(side='right')
        history_row = ctk.CTkFrame(self.session,fg_color='transparent')
        history_row.pack(fill='x',padx=16,pady=(0,6))
        self.history_menu = ctk.CTkOptionMenu(history_row,values=[self.t('current_session')],command=self.select_history,
            fg_color=self.theme['card'],button_color=self.theme['card'],text_color=self.theme['text'],
            dropdown_fg_color=self.theme['panel'],dropdown_text_color=self.theme['text'],width=180)
        self.failed_var = tk.BooleanVar(value=self.settings['hide_failed'])
        self.failed_checkbox = ctk.CTkCheckBox(history_row,text=self.t('hide_failed'),variable=self.failed_var,
            text_color=self.theme['text'],fg_color=self.theme['accent'],checkmark_color=self.ink,
            command=lambda:self.apply_live_setting('hide_failed',self.failed_var.get()))
        self.failed_checkbox.pack(side='right',padx=(12,0))
        self.history_search=self.button(history_row,'⌕',lambda:open_session_search(self),True)
        self.history_search.configure(width=38)
        self.history_menu.pack(side='left',fill='x',expand=True)
        self.update_history_menu()
        self.cards_frame = FastScrollableFrame(self.session,fg_color='transparent',scrollbar_button_color=self.theme['card'])
        self.cards_frame.pack(fill='both',expand=True,padx=10,pady=(0,10))
        # CTkScrollableFrame сам является внутренним контейнером. Служебных родителей не трогаем.
        self.empty_label = self.label(self.cards_frame,self.t('empty'),muted=True,height=120)
        self.empty_label.pack(fill='x')
        self.comparison_cache = comparison_index(all_records(self))
        for record in reversed(self.visible_records()):
            self.add_card(record)
        self.update_stats()
        self.update_controls()

    def update_controls(self):
        key = {'idle':'start','running':'stop','recovery':'recover','starting':'cancel_start'}.get(self.state_name,'busy')
        self.start_button.configure(text=self.t(key),state='normal' if key != 'busy' else 'disabled')
        self.settings_button.configure(state='normal' if self.state_name in ('idle','running') else 'disabled')

    def show_page(self,delta):
        # Вся выбранная сессия доступна обычной прокруткой.
        records = self.visible_records()
        self.comparison_cache=comparison_index(all_records(self))
        self.page = 0
        self.clear_cards()
        for record in reversed(records):
            self.add_card(record)
        self.cards_frame._parent_canvas.yview_moveto(0)
        self.request_record_pp(records)

    def update_stats(self,record=None):
        self.profile_label.configure(text=self.username[:18])
        self.pp_label.configure(text=('≈ ' if self.settings['offline'] else '')+f'{self.total_pp:,.0f} PP' if self.total_pp is not None else '— PP')
        mode = self.settings['difficulty']
        if mode == 'Hard':
            rules = '\n'.join(f'{r}: ≤ #{v:g}' for r,v in rank_thresholds('Hard',self.settings).items())
            rules += '\n'+self.t('hard_dt_goal')
            rules += ('\n\nЛидерборд карты\nБольше 1000 запусков' if self.settings['language']!='English' else '\n\nMap leaderboard\nOver 1000 plays')
            if self.settings['offline']:
                rules = ('Нужен онлайн-режим для лидербордов карт' if self.settings['language']!='English' else 'Online mode required for map leaderboards')
        elif mode == 'Medium':
            rules = '\n'.join(f'{r:3}     {v}+ PP' for r,v in pp_thresholds(self.total_pp,self.settings).items()) if self.total_pp is not None else self.t('credentials')
        else:
            rules = '\n'.join(f'{r:3}     {v}×' for r,v in rank_thresholds("Fun",self.settings).items())
            rules += '\n'+self.t('fun_dt_goal')
            if self.total_pp is not None:
                rules += f"\n\n{self.t('stars')}: {stars_threshold(self.total_pp,self.settings):.2f}★"
        self.rules_label.configure(text=rules)
        self.pool_label.configure(text=f"{self.t('pool')}: {sum(map(len,self.pool.values()))}")
        self.unlock_label.configure(text=f"{self.t('unlocks')}: {self.unlocked}")
        if not record:
            return
        reward = record['reward']
        if reward == 'SS':
            self.next_label.configure(text=self.t('maximum'))
            self.smooth_progress(1)
            return
        target = RANKS[RANKS.index(reward)-1] if reward in RANKS else 'D'
        if mode == 'Hard':
            value,limit = record.get('position') or 101,rank_thresholds("Hard",self.settings)[target]
            remaining,ratio = f'#{limit}',min(1,limit/value)
        elif mode == 'Medium':
            value,limit = float(record['score'].get('pp') or 0),pp_thresholds(self.total_pp,self.settings)[target]
            remaining,ratio = f'{max(0,limit-value):.1f} PP',min(1,value/max(1,limit))
        else:
            value,limit = int(record['score']['maxcombo']),rank_thresholds("Fun",self.settings)[target]
            remaining = f'{max(0,limit-value)}× / ≥ {stars_threshold(self.total_pp,self.settings):.2f}★'
            ratio = min(1,value/limit) if float(record['map']['difficultyrating']) >= stars_threshold(self.total_pp,self.settings) else 0
        self.next_label.configure(text=self.t('next',rank=target,value=remaining))
        self.smooth_progress(ratio)

    def submit(self,executor,kind,function,*args,token=None):
        identity = self.sandbox.identity if kind in ('favorites','exported','installed','skins_reset','skins_deleted') else None
        def task():
            try:
                value = function(*args)
                if identity is not None:
                    self.events.put(('service_result',token,(kind,identity,value)))
                else:
                    self.events.put((kind,token,value))
            except Exception as error:
                self.events.put(('failure',token,(kind,str(error))))
        self.background_tasks = [f for f in self.background_tasks if not f.done()]
        self.background_tasks.append(executor.submit(task))

    def refresh_pool(self):
        self.submit(self.files,'pool',self.library.scan)
        if self.settings['offline']:
            self.total_pp = float(self.settings['offline_total_pp'] or 0)
            self.username = self.settings['offline_username'] or self.t('offline_top')
            self.update_stats()
        elif (self.settings['api_key'] or self.settings['server']=='gatari') and self.settings['user_id'].isdigit():
            settings = self.settings.copy()
            def profile():
                api = self.make_api(settings)
                try:
                    rows = [api.profile()] if settings['server']=='gatari' else api.get('get_user',u=api.user,type='id')
                    if not rows:
                        raise RuntimeError('Профиль не найден / Profile not found')
                    return rows[0],(settings['api_key'],settings['user_id'],settings['server'],settings['offline'])
                except Exception as error:
                    return None,(settings['api_key'],settings['user_id'],settings['server'],settings['offline']),str(error)
                finally:
                    api.session.close()
            self.submit(self.network,'preview_profile',profile)

    def open_settings(self):
        if self.state_name not in ('idle','running'):
            return
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
        else:
            self.settings_window = SettingsWindow(self)

    def toggle(self):
        if not self.settings['setup_complete']:
            self.open_setup()
            return
        if self.state_name == 'starting':
            self.stop_event.set()
            self.start_button.configure(state='disabled')
            return
        if self.state_name == 'running':
            self.stop()
        elif self.state_name == 'recovery':
            self.state_name = 'stopping'
            self.update_controls()
            self.submit(self.files,'stopped',self.sandbox.stop, lambda done,total:self.events.put(('restore_progress',None,(done,total))))
        elif self.state_name == 'idle':
            if not self.settings['offline'] and ((self.settings['server']=='bancho' and not self.settings['api_key']) or not self.settings['user_id'].isdigit()):
                messagebox.showerror(self.t('error'),self.t('credentials'),parent=self)
                return
            self.state_name = 'starting'
            if self.settings['offline']:
                self.status_label.configure(text=self.t('offline_indexing'))
            self.stop_event = threading.Event()
            self.update_controls()
            settings = self.settings.copy()
            def start():
                api = self.make_api(settings)
                try:
                    try:
                        snapshot = api.snapshot()  # Проверка профиля до переноса личных скинов.
                    except Exception as error:
                        ident=(settings['server'],str(settings['user_id']),settings.get('api_key',''),settings['offline'])
                        self.events.put(('connection_check',None,(ident,str(error))))
                        raise
                    if self.stop_event.is_set():
                        raise RuntimeError('Запуск отменён / Start cancelled')
                    self.sandbox.start(settings.get('keep_personal',False),
                        lambda done,total:self.events.put(('backup_progress',None,(done,total))),self.stop_event)
                    if settings.get('tablet_driver_enabled') and not self.stop_event.is_set():
                        from modules.gacha_driver import launch_driver
                        try: launch_driver(settings['tablet_driver_path'])
                        except (OSError, ValueError) as error: self.events.put(('log',None,str(error)))
                    if settings.get('osu_launch_enabled') and not self.stop_event.is_set():
                        from modules.gacha_driver import launch_osu
                        try: launch_osu(settings['osu_path'],settings['server'],settings.get('gatari_launch',True))
                        except (OSError, ValueError) as error: self.events.put(('log',None,str(error)))
                    return api,snapshot
                except Exception:
                    api.session.close()
                    if self.sandbox.journal.exists():
                        self.sandbox.stop()
                    self.sandbox.release()
                    raise
            self.submit(self.files,'started',start)

    def start_monitor(self,api,snapshot):
        self.state_name = 'running'
        self.latest_skin = self.applied_skin = None
        self.records.clear()
        self.page = 0
        self.selected_session = None
        now = datetime.now().astimezone()
        self.current_session = dict(id=now.strftime('%Y%m%d_%H%M%S_')+uuid.uuid4().hex[:8],
            started_at=now.isoformat(),ended_at=None,user_id=str(self.settings['user_id']),
            start_pp=float(snapshot[0].get('pp_raw') or 0),end_pp=float(snapshot[0].get('pp_raw') or 0),
            username=snapshot[0].get('username',''),difficulty=self.settings['difficulty'],records=[],drops=[])
        self.current_session.update(server=self.settings['server'],offline=self.settings['offline'],slot=self.settings['slot'])
        self.persist_history()
        self.update_history_menu()
        self.clear_cards()
        self.unlocked = 0
        self.start_pp = float(snapshot[0].get('pp_raw') or 0)
        self.handle_profile(snapshot[0])
        self.status_label.configure(text=self.t('can_play'))
        def clear_ready():
            if not self.destroyed and self.state_name=='running' and self.status_label.cget('text')==self.t('can_play'):
                self.status_label.configure(text=self.t('monitoring'))
        self.after(5000,clear_ready)
        self.update_controls()
        self.log(self.t('monitoring'))
        self.worker = threading.Thread(target=self.monitor,args=(api,snapshot,self.stop_event,self.settings.copy()),daemon=True)
        self.worker.start()
        if self.closing:
            self.stop()

    def monitor(self,api,initial,stop,settings):
        user,best,recent = initial
        seen = {score_key(s) for s in best+recent}
        rewarded,seen_top = set(),{score_key(s) for s in best}
        past=[r for session in list(self.history.values()) if self.session_matches(session) for r in session['records']]
        claimed=claimed_ranks(past)
        dt_claimed={difficulty_key(r['score']) for r in past if r.get('dt_awarded')}
        last_pp = float(user.get('pp_raw') or 0)
        failures = 0
        try:
            while not stop.wait(min(300,settings['interval']*2**min(failures,4))):
                try:
                    # Цельный снимок; изменения настроек видны со следующего опроса.
                    settings = self.settings.copy()
                    api.session.trust_env = not settings.get('ignore_proxy',False)
                    api.language = settings['language']
                    user,best,recent = api.snapshot()
                    self.events.put(('log',None,'Локальные скоры / Local scores — OK' if settings['offline'] else 'API: profile, best, recent — OK'))
                    total = float(user.get('pp_raw') or 0)
                    self.events.put(('profile',None,user))
                    combined = {score_key(s):dict(s) for s in recent}
                    positions = {}
                    for pos,s in enumerate(best,1):
                        key = score_key(s)
                        combined[key],positions[key] = dict(s),pos
                    new = [(key,s) for key,s in combined.items() if key not in seen or
                           (key in positions and key not in seen_top)]
                    # API v1 не сообщает точный вклад отдельного скора в общий PP.
                    bonus = special_gain(last_pp,total) and bool(new)
                    fresh_reward = False
                    for key,score in sorted(new,key=lambda pair:pair[1].get('date','')):
                        if stop.is_set():
                            break
                        info = api.beatmap(score['beatmap_id'],int(score.get('enabled_mods') or 0))
                        score = api.enrich_pp(score)
                        position=positions.get(key)
                        if settings['difficulty']=='Hard':
                            position,plays=(api.leaderboard(score) if hasattr(api,'leaderboard') and score.get('rank')!='F' else (None,None))
                            info=dict(info,leaderboard_playcount=plays)
                            if plays is None or plays<=1000:position=None
                        reward = reward_for(settings['difficulty'],total,score,float(info.get('difficultyrating') or 0),position,settings)
                        record = dict(key=key,score=score,map=info,reward=reward,position=position,difficulty=settings['difficulty'])
                        map_key = difficulty_key(score)
                        eligible = reward_upgrade(score,reward,claimed)
                        record['awarded'] = reward != 'F' and key not in rewarded and eligible
                        record['repeat_difficulty'] = bool(map_key in claimed and not eligible)
                        record['previous_reward_level']=claimed.get(map_key,0)
                        record['dt_awarded']=bool(record['awarded'] and map_key not in dt_claimed and dt_reward(settings['difficulty'],total,score,float(info.get('difficultyrating') or 0),position,settings))
                        self.events.put(('score',None,record))
                        if record['awarded']:
                            claimed[map_key]=rank_level(reward)
                            fresh_reward = True
                            self.events.put(('roll',None,reward))
                            rewarded.add(key)
                            if record['dt_awarded']:
                                dt_claimed.add(map_key)
                                self.events.put(('roll',None,'DT'))
                        seen.add(key)
                        if key in positions:
                            seen_top.add(key)
                    if bonus and fresh_reward and not stop.is_set() and random.random()*100 < special_chance(settings):
                        self.events.put(('roll',None,'special'))
                    last_pp,failures = total,0
                except Exception as error:
                    failures += 1
                    self.events.put(('api_failure',None,str(error)))
        finally:
            api.session.close()

    def stop(self):
        self.roulette_ticket = None
        self.state_name = 'stopping'
        if self.current_session and not self.current_session['ended_at']:
            self.current_session['ended_at'] = datetime.now().astimezone().isoformat()
            self.persist_history()
        self.stop_event.set()
        self.rolls.clear()
        self.rolling = False
        if self.roll_timer:
            self.after_cancel(self.roll_timer)
            self.roll_timer = None
        self.update_controls()
        # Последовательный исполнитель восстанавливает скины после текущей установки.
        self.submit(self.files,'stopped',self.sandbox.stop, lambda done,total:self.events.put(('restore_progress',None,(done,total))))

    def clear_cards(self):
        for card in self.cards:
            card.destroy()
        self.cards.clear()
        self.empty_label.pack(fill='x')

    def handle_profile(self,user):
        mark_connection(self)
        previous=self.total_pp
        same=self.profile_id==str(user.get('user_id') or self.settings['user_id'])
        self.username = user.get('username','—')
        self.profile_id = str(user.get('user_id') or self.settings['user_id'])
        self.total_pp = float(user.get('pp_raw') or 0)
        self.update_stats()
        if self.state_name=='running' and self.current_session:
            self.current_session['end_pp']=self.total_pp
            if same and previous is not None and self.total_pp>previous:animate_pp(self,self.total_pp-previous)
        self.request_avatar()

    def drain_events(self):
        for _ in range(60):
            try:
                kind,token,value = self.events.get_nowait()
            except queue.Empty:
                break
            if token is not None and token != self.generation:
                continue
            if kind=='service_result':
                kind,identity,value = value
                if identity != self.sandbox.identity:
                    continue
            if kind=='connection_check':
                ident,error=value
                if connection_state(self)['identity']==ident:
                    connection_state(self)['pending']=False;mark_connection(self,error,ident)
            elif kind == 'log':
                self.log(value)
            elif kind == 'collection_image':
                widget,picture=value
                if widget.winfo_exists() and picture is not None:
                    img=ctk.CTkImage(light_image=picture,dark_image=picture,size=(208,117))
                    widget.configure(image=img,text='');widget._preview_ref=img;widget._preview_pil=picture
            elif kind == 'download_progress':
                identity,details=value
                if identity==self.sandbox.identity and self.state_name=='running':
                    name,done,total,speed,eta=details
                    amount=f'{done/1048576:.1f} / {total/1048576:.1f}' if total else f'{done/1048576:.1f}'
                    remaining=(f'{eta:.0f} с' if self.settings['language']!='English' else f'{eta:.0f} s') if eta is not None else '—'
                    self.status_label.configure(text=(f'Скачано {amount} МБ · {speed/1048576:.1f} МБ/с · Осталось: {remaining}' if self.settings['language']!='English' else f'Downloaded {amount} MB · {speed/1048576:.1f} MB/s · Remaining: {remaining}'))
            elif kind in ('data_imported','data_exported'):
                self.state_name='idle'
                if kind=='data_imported':
                    self.settings,self.history,count=value
                    self.current_session=self.selected_session=None;self.records.clear()
                    self.total_pp,self.username=None,'—';self.profile_id=str(self.settings['user_id'])
                    ctk.set_widget_scaling(int(self.settings.get('ui_scale','100%').rstrip('%'))/100)
                    self.configure_services();self.build_ui();self.refresh_pool();self.render_collection()
                self.update_controls()
                self.status_label.configure(text=('Данные импортированы' if kind=='data_imported' else 'Архив сохранён: '+value) if self.settings['language']!='English' else ('Data imported' if kind=='data_imported' else 'Archive saved: '+value))
                if self.closing:self.finish_close();return
            elif kind == 'team_avatar':
                from modules.gacha_team import set_avatar
                set_avatar(self,*value)
            elif kind == 'reports':
                self.receive_reports(value)
            elif kind == 'pool':
                if value['roots'] != self.sandbox.identity:
                    continue
                self.pool,self.catalog,self.drops,self.base_skins = value['pool'],value['catalog'],value['drops'],value['bases']
                self.update_stats()
                self.render_collection()
                if self.preview_warm_task is None or self.preview_warm_task.done():
                    cache, items = self.preview_cache, list(self.catalog.values())
                    def warm(cache=cache, items=items):
                        ready, total = cache.warm(items)
                        if total and not cache.stopped():
                            self.events.put(('log', None, f'Превью: {ready}/{total}' if self.settings['language']!='English' else f'Previews: {ready}/{total}'))
                    self.preview_warm_task = self.network.submit(warm)
                    self.background_tasks.append(self.preview_warm_task)
                self.log(f"{self.t('pool')}: {sum(map(len,self.pool.values()))}")
            elif kind == 'roulette_ready':
                ticket, rank, final, sequence = value
                if ticket == self.roulette_ticket and self.state_name == 'running':
                    self.animate_roulette(rank, final, sequence)
            elif kind == 'preview_profile':
                user,identity = value[:2]
                if identity == (self.settings['api_key'],self.settings['user_id'],self.settings['server'],self.settings['offline']):
                    if user is not None:self.handle_profile(user)
                    else:mark_connection(self,value[2])
            elif kind == 'history_loaded':
                self.history = {**value,**self.history}
                self.update_history_menu()
                self.comparison_cache=comparison_index(all_records(self))
            elif kind == 'pp_refreshed':
                record,score = value
                record['score'] = score
                for session in self.history.values():
                    if any(r is record for r in session['records']):
                        self.submit(self.files,'history_saved',self.history_store.save,copy.deepcopy(session))
                self.schedule_history()
                if getattr(self,'pp_refresh_timer',None):
                    self.after_cancel(self.pp_refresh_timer)
                def redraw():
                    self.pp_refresh_timer = None
                    self.show_page(0)
                    if getattr(self,'best_refresh',None):
                        self.best_refresh()
                self.pp_refresh_timer = self.after(500,redraw)
            elif kind == 'avatar':
                ident,picture = value
                self.avatar_pending.discard(ident)
                if picture is not None:
                    self.avatar_cache[ident] = picture
                if ident == self.avatar_key():
                    self.render_avatar()
            elif kind == 'restore_progress':
                if self.state_name in ('stopping','starting'):
                    self.status_label.configure(text=self.t('restore_progress',done=value[0],total=value[1]))
            elif kind == 'backup_progress':
                if self.state_name=='starting':
                    self.status_label.configure(text=self.t('backup_progress',done=value[0],total=value[1]))
            elif kind == 'started':
                if self.stop_event.is_set():
                    value[0].session.close()
                    self.state_name='stopping'
                    self.submit(self.files,'stopped',self.sandbox.stop, lambda done,total:self.events.put(('restore_progress',None,(done,total))))
                else:
                    self.start_monitor(*value)
            elif kind == 'stopped':
                self.await_worker()
            elif kind == 'failure':
                origin,error = value
                self.log(error)
                if origin == 'reports':
                    self.report_error(error)
                    continue
                if origin == 'history_saved':
                    error = self.t('history_error')+': '+error
                if origin in ('started','stopped','skins_reset','skins_deleted'):
                    self.state_name = 'recovery' if self.sandbox.recover_needed() else 'idle'
                    if self.closing and self.state_name=='idle':
                        self.finish_close()
                        return
                    self.closing = False
                    self.update_controls()
                if origin in ('data_imported','data_exported'):
                    self.state_name='idle';self.update_controls()
                    if self.closing:self.finish_close();return
                if origin=='skins_deleted':self.refresh_pool()
                if origin == 'skin_applied':
                    self.applying_skin = False
                    self.render_collection()
                if origin in ('installed', 'roulette_ready'):
                    self.rolling = False
                    self.failed_drop = getattr(self,'installing_rank',None)
                    self.retry_button.pack(side='right')
                self.status_label.configure(text=self.t('error')+': '+error)
            elif kind == 'cover':
                widget,image = value
                if widget.winfo_exists() and image is not None:
                    cimg = ctk.CTkImage(light_image=image,dark_image=image,size=(156,88))
                    widget.configure(image=cimg,text='')
                    widget._cover_ref = cimg
            elif kind == 'skin_applied':
                self.applying_skin = False
                self.applied_skin = value
                self.status_label.configure(text=self.t('skin_imported'))
                self.render_collection()
            elif kind == 'installed':
                if isinstance(value,dict):
                    self.drops[value['id']] = value
                    name = value['name']
                    self.latest_skin = value['installed_name']
                    if self.current_session:
                        self.current_session.setdefault('drops',[]).append({k:value.get(k) for k in ('id','name','rank','unlocked_at')})
                        self.persist_history()
                    if self.state_name=='running' and not self.settings.get('keep_current_skin'):
                        self.applying_skin=True
                        self.submit(self.files,'skin_applied',update_live,self.sandbox,self.latest_skin)
                    self.render_collection()
                else:
                    name = value
                if self.state_name == 'running':
                    self.unlocked += 1
                    self.roulette_label.configure(text=f"{self.t('won')}: [{value.get('rank','?') if isinstance(value,dict) else self.installing_rank}] {name}")
                    self.status_label.configure(text=('Скин добавлен в коллекцию. Текущий скин сохранён.' if self.settings['language']!='English' else 'Skin added to the collection. Current skin unchanged.') if self.settings.get('keep_current_skin') else self.t('installed'))
                    self.update_stats()
                    self.roll_timer = self.after(1400,self.next_roll)
            elif kind == 'favorites':
                self.drops = value
                self.render_collection()
            elif kind == 'skins_deleted':
                self.state_name='idle';self.drops=value
                self.update_stats();self.render_collection();self.update_controls()
                self.status_label.configure(text='Неизбранные скины удалены' if self.settings['language']!='English' else 'Nonfavorite skins removed')
                if self.closing:self.finish_close();return
            elif kind == 'skins_reset':
                self.state_name = 'idle'
                self.drops = {}
                self.render_collection()
                self.refresh_pool()
                self.update_controls()
                self.status_label.configure(text=self.t('reset_done'))
            elif kind == 'exported':
                self.status_label.configure(text=self.t('exported')+': '+value)
            elif kind == 'score_lookup':
                record,score = value
                if score and score_url(score):
                    record['score'].update(score)
                    self.open_score(record)
                else:
                    self.status_label.configure(text=self.t('score_missing'))
            elif kind == 'score_page':
                if value:
                    webbrowser.open(value)
            elif self.state_name == 'running':
                if kind == 'profile':
                    self.handle_profile(value)
                elif kind == 'api_failure':
                    mark_connection(self,value)
                    self.log(value)
                    self.status_label.configure(text=str(value))
                elif kind == 'score':
                    existing = next((r for r in self.records if r['key'] == value['key']),None)
                    if existing is not None:
                        value["awarded"] = existing.get("awarded", False) or value.get("awarded", False)
                        existing.update(value)
                        if self.selected_session is None:
                            self.show_page(0)
                    else:
                        self.records.appendleft(value)
                        self.comparison_cache=comparison_index(all_records(self))
                        if self.selected_session is not None:
                            pass
                        elif self.page:
                            self.show_page(0)
                        elif self.settings['log_mode']:
                            self.add_card(value)
                    self.schedule_history()
                    self.update_stats(value)
                    self.log(f"{value['score']['beatmap_id']} / {self.t('reward')}: {value['reward']}")
                elif kind == 'roll':
                    self.rolls.append(value)
                    if not self.rolling:
                        self.next_roll()
        if not self.destroyed:
            self.after(40,self.drain_events)

    def await_worker(self):
        if self.worker and self.worker.is_alive():
            self.after(100,self.await_worker)
            return
        self.state_name = 'idle'
        self.render_collection()
        self.status_label.configure(text=self.t('restored'))
        self.log(self.t('restored'))
        self.update_controls()
        if self.closing:
            self.finish_close()
        elif self.current_session and self.current_session.get('ended_at') and self.settings.get('show_session_summary',True):
            open_summary(self)

    def next_roll(self):
        self.roll_timer = None
        if self.state_name != 'running' or not self.rolls:
            self.rolling = False
            return
        self.rolling = True
        rank = self.rolls.popleft()
        available = [p for p in self.pool.get(rank,[]) if str(p) in self.catalog and self.catalog[str(p)]['id'] not in self.drops]
        candidates = [p for p in available if not self.settings['exclude_heavy'] or self.catalog[str(p)]['size'] is None or self.catalog[str(p)]['size'] <= 30*1024*1024]
        if not candidates:
            self.status_label.configure(text=self.t('filtered_pool' if available else 'exhausted',rank=rank))
            self.roll_timer = self.after(500,self.next_roll)
            return
        final = random.choice(candidates)
        self.installing_rank = rank
        ticket = self.roulette_ticket = uuid.uuid4().hex
        self.status_label.configure(text=f"{self.t('reward')}: {rank}")
        self.roulette_label.configure(text='Подготовка превью…' if self.settings['language']!='English' else 'Preparing previews…')
        cache = self.preview_cache
        items = [self.catalog[str(p)].copy() for p in candidates]
        winner = self.catalog[str(final)].copy()
        self.submit(self.images, 'roulette_ready',
                    lambda: (ticket, rank, final, cache.prepare(items, winner)))

    def animate_roulette(self, rank, final, sequence):
        started = time.monotonic()
        ticket = self.roulette_ticket
        self.roulette_label.configure(text=f"{self.t('reward')}: {rank}")
        def frame():
            if self.state_name != 'running' or ticket != self.roulette_ticket:
                return
            progress = min(1, (time.monotonic()-started)/2.8) if self.settings['roulette_motion'] else 1
            if not self.roulette_strip.winfo_manager():
                self.roulette_strip.pack(fill='x', padx=22, pady=(0,8), before=self.status_label)
            self.roulette_strip.show(sequence, progress)
            if progress < 1:
                self.roll_timer = self.after(16, frame)
            else:
                self.roll_timer = None
                self.roulette_label.configure(text=f"[{('Особая' if self.settings['language']!='English' else 'Special') if rank=='special' else rank}] {self.catalog[str(final)]['name'][:62]}")
                self.installing_rank = rank
                self.submit(self.files,'installed',self.library.award,final,self.settings.copy())
        frame()

    def retry_drop(self):
        if self.state_name=='running' and self.failed_drop and not self.rolling:
            self.rolls.appendleft(self.failed_drop)
            self.failed_drop = None
            self.retry_button.pack_forget()
            self.next_roll()

    def cover_widget(self,parent,record):
        frame = ctk.CTkFrame(parent,fg_color=self.theme['panel'],corner_radius=12,
            border_width=2,border_color=blend(self.theme['accent'],self.theme['secondary'],.3))
        cover = self.label(frame,self.t('cover'),muted=True,width=156,height=88)
        cover.pack(padx=4,pady=4)
        info,score = record['map'],record['score']
        ident = str(info.get('beatmap_id') or score['beatmap_id'])
        if ident.isdigit():
            cover.configure(cursor='hand2')
            cover.bind('<Button-1>',lambda event:webbrowser.open('https://osu.ppy.sh/beatmaps/'+ident))
        service = self.covers
        self.submit(self.images,'cover',lambda:(cover,service.get(ident,info.get('beatmapset_id',''))),token=self.generation)
        if not hasattr(self,'audio_player'):
            from modules.gacha_audio import AudioPlayer
            self.audio_player=AudioPlayer(self)
        self.audio_player.attach(frame,record)
        return frame

    def add_card(self,record):
        if not self.settings['log_mode'] or (self.settings['hide_failed'] and record['score'].get('rank') == 'F'):
            return
        self.empty_label.pack_forget()
        score,info = record['score'],record['map']
        first = next((w for w in self.cards_frame.pack_slaves() if w.winfo_exists()),None)
        card = ctk.CTkFrame(self.cards_frame,fg_color=self.theme['card'],corner_radius=min(self.theme['radius'],14))
        if self.settings['ui_motion'] and len(self.cards)<8:
            accent,base = self.theme['accent'],self.theme['card']
            def highlight(value):
                color = '#'+''.join(f'{round(int(accent[i:i+2],16)*(1-value)+int(base[i:i+2],16)*value):02x}' for i in (1,3,5))
                card.configure(border_width=1 if value<1 else 0,border_color=color)
            self.animate_value(card,0,1,highlight,360)
        options = dict(fill='x',padx=3,pady=5)
        if first is not None:
            options['before'] = first
        card.pack(**options)
        self.cards.insert(0,card)
        card.grid_columnconfigure(1,weight=1)
        cover = self.cover_widget(card,record)
        cover.grid(row=0,column=0,rowspan=3,padx=10,pady=12)
        title = f"{info.get('artist','')} — {info.get('title','')} [{info.get('version','')}]"
        title_label = self.label(card,title,size=14,bold=True,anchor='w',justify='left',wraplength=330)
        title_label.grid(row=0,column=1,sticky='ew',pady=(12,2))
        stats_label = self.label(card,self.score_stats(score,info)+(('\n'+comparison_text(self,record)) if comparison_text(self,record) else ''),size=12,muted=True,anchor='w',justify='left',wraplength=300)
        stats_label.grid(row=1,column=1,sticky='w')
        def resize_text(event):
            width = max(110,event.width-350)
            title_label.configure(wraplength=width)
            stats_label.configure(wraplength=width)
        card.bind('<Configure>',resize_text)
        pp = ('≈ ' if score.get('pp_source')=='calculated' else '')+f"{float(score['pp']):.1f} PP" if score.get('pp') is not None else '— PP'
        self.label(card,f"{pp} · {mods_string(score.get('enabled_mods'))} · {float(info.get('difficultyrating') or 0):.2f}★",size=12,anchor='w').grid(row=2,column=1,sticky='w',pady=(0,12))
        rank = score.get('rank','?')
        rank_label = self.label(card,{'X':'SS','XH':'SSH'}.get(rank,rank),size=28,bold=True,width=68)
        rank_label.configure(text_color=RANK_COLORS.get(rank,self.theme['accent']) if self.theme['bg'] not in ('#faf1f3','#f2f0e9') else self.theme['accent'])
        rank_label.grid(row=0,column=2,padx=8,sticky='n',pady=(6,0))
        self.label(card,self.t("repeat_map") if record.get("repeat_difficulty") else f"{self.t('reward')}: {record['reward']}",size=11,muted=True).grid(row=1,column=2,padx=8,sticky='n')
        for widget in [card,*card.winfo_children()]:
            if isinstance(widget,(ctk.CTkFrame,ctk.CTkLabel)):
                widget.configure(cursor='hand2')
                ident = str(info.get('beatmap_id') or score['beatmap_id'])
                if ident.isdigit():
                    widget.bind('<Button-1>',lambda event,b=ident:webbrowser.open(f'https://osu.ppy.sh/beatmaps/{b}'))
        if score.get('rank')!='F' and score.get('provider') not in ('offline','gatari'):
            link = self.button(card,self.t('score_link'),lambda:self.open_score(record),True)
            link.configure(height=26)
            link.configure(width=0,font=('Segoe UI',12,'bold'))
            link.grid(row=2,column=2,sticky='e',padx=10,pady=(0,8))

    def score_stats(self,score,info):
        parts = []
        if self.settings.get('show_combo',True): parts.append(f"{self.t('combo')}: {score.get('maxcombo',0)}/{info.get('max_combo') or '—'}")
        if self.settings.get('show_accuracy',True): parts.append(f"{self.t('acc')}: {accuracy(score):.2f}%")
        if self.settings.get('show_misses',True): parts.append(f"{self.t('misses')}: {int(score.get('countmiss') or 0)}")
        for key,label,field in (('show_100','100','count100'),('show_50','50','count50')):
            if self.settings.get(key,True):
                value = score.get(field)
                parts.append(f"{label}: {value if value is not None else '—'}")
        return ' · '.join(parts)

    def copy_logs(self):
        # Копируем весь сохранённый журнал, включая строки за пределами видимой области.
        content = '\n'.join(self.logs)
        secret = self.settings.get('api_key','')
        if secret:
            content = content.replace(secret,'***')
        self.clipboard_clear()
        self.clipboard_append(content)
        self.copy_logs_button.configure(text=self.t('copied'))

    def log(self,value):
        secret = self.settings.get('api_key','')
        if secret:
            value = value.replace(secret,'***')
        self.logs.append(time.strftime('%H:%M:%S')+'  '+value)
        if self.log_window and self.log_window.winfo_exists():
            self.log_text.configure(state='normal')
            self.log_text.delete('1.0','end')
            self.log_text.insert('end','\n'.join(self.logs))
            self.log_text.see('end')
            self.log_text.configure(state='disabled')

    def open_logs(self):
        if self.log_window and self.log_window.winfo_exists():
            self.log_window.lift()
            return
        self.log_window = IconWindow(self)
        self.log_window.title(self.t('logs'))
        self.log_window.geometry('760x480')
        self.copy_logs_button = self.button(self.log_window,self.t('copy_logs'),self.copy_logs)
        self.copy_logs_button.pack(anchor='e',padx=12,pady=(12,0))
        self.log_text = FastTextbox(self.log_window,font=('Consolas',12),fg_color=self.theme['bg'],text_color=self.theme['text'])
        self.log_text.pack(fill='both',expand=True,padx=12,pady=12)
        self.log_text.insert('end','\n'.join(self.logs))
        self.log_text.configure(state='disabled')

    def on_close(self):
        if hasattr(self,'audio_player'):self.audio_player.close()
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.destroy()
        self.closing = True
        if self.state_name == 'running':
            self.stop()
        elif self.state_name == 'recovery':
            self.toggle()
        elif self.state_name == 'starting':
            self.stop_event.set()
        elif self.state_name == 'idle':
            self.finish_close()

    def finish_close(self):
        if not self.shutdown_started:
            if self.current_session:
                self.persist_history()
            self.shutdown_started = True
            self.destroyed = True
            self.sandbox.release()
            # Сохраняем историю и ждём рабочих задач через after, сохраняя отзывчивость окна.
            self.files.shutdown(wait=False,cancel_futures=False)
            self.images.shutdown(wait=False,cancel_futures=True)
            self.network.shutdown(wait=False,cancel_futures=True)
        if any(not task.done() for task in self.background_tasks):
            self.after(80,self.finish_close)
            return
        while not self.events.empty():
            self.events.get_nowait()
        self.destroy()
        gc.collect()
        if self.gc_enabled:
            gc.enable()

