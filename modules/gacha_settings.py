"""osu! Skin Gacha: gacha_settings."""
from __future__ import annotations
import math
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
import zipfile
import customtkinter as ctk
from modules.gacha_config import THEMES, COLORS, RANKS, tr, blend
from modules.gacha_widgets import FastScrollableFrame, bind_api_paste, IconWindow

SETTING_HELP = {'keep_personal': ('Личные скины остаются в Skins. После сессии убираются только скины программы; default не обязателен.', 'Personal skins stay in Skins. Only session skins are removed after playing; default is not enforced.'),'skin_source': ('Drive скачивает только награду; ZIP извлекает один скин; папки используют локальный набор.',
                 'Drive downloads only the reward; ZIP extracts one skin; folders use a local pack.'),
 'skin_pack_path': ('Папка данных программы: кэш, награды и резерв личных скинов. Не выбирайте папку Skins '
                    'игры.',
                    'App data: cache, rewards and personal-skin backup. Do not select the game Skins folder.'),
 'slot': ('Три независимые коллекции. Слот меняется только после завершения сессии.',
          'Three separate collections. End the session before switching slots.'),
 'difficulty': ('Hard: место в топ-100. Medium: PP. Fun: комбо и звёзды. Точные текущие пороги — в «Твои '
                'цели».',
                'Hard: top-100 position. Medium: PP. Fun: combo and stars. Current thresholds appear in Your '
                'goals.'),
 'interval': ('Секунды между опросами. Меньше — быстрее обнаружение, больше запросов. API хранит только 50 '
              'последних попыток.',
              'Seconds between polls. Lower values detect sooner but use more requests. API recent history '
              'holds 50 attempts.'),
 'rofl_chance': ('Процент шанса дополнительного особого скина при достаточном приросте общего PP.',
                 'Percent chance of an extra special skin when total PP increases enough.'),
 'rofl_pp': ('Минимальный прирост общего PP между опросами для шанса особого скина. Это не PP самой карты.',
             'Minimum total PP gain between polls for a special reward chance, not the score PP.'),
 'exclude_heavy': ('Не выдаёт скины размером больше 30 МБ после распаковки (30 × 1024² байт). Уже полученные скины остаются.',
                   'Excludes new rewards over 30 MiB unpacked. Existing rewards remain.'),
 'optimize_skins': ('Геймплей берётся из награды, меню и HUD — из выбранного личного скина. Исходники не '
                    'изменяются.',
                    'Gameplay comes from the reward; menus and HUD from your chosen personal skin. Originals '
                    'stay intact.'),
 'interface_skin': ('Основа меню и HUD для смешивания скинов. Выберите перед включением оптимизации.',
                    'Menu and HUD base for skin mixing. Select before enabling optimization.'),
 'hide_failed': ('Скрывает игровой ранг F, а не «Награда: F». История не удаляется.',
                 'Hides failed plays, not Reward: F. History is retained.'),
 'ignore_proxy': ('Отключает системный HTTP-прокси для запросов. Сам VPN/TUN продолжает работать.',
                  'Ignores the system HTTP proxy for requests. VPN/TUN itself stays active.'),
 'offline': ('Читает сохранённые локальные результаты osu!standard. PP расчётный; несохранённые попытки '
             'недоступны.',
             'Reads saved local osu!standard results. PP is calculated; unsaved attempts are unavailable.'),
 'offline_total_pp': ('Начальный общий PP для офлайн-целей. Дальнейший прирост оценивается по локальному топу.',
                      'Starting total PP for offline goals. Further gain is estimated from the local top '
                      'scores.'),
 'ui_motion': ('Плавный прогресс и подсветка карточек.',
               'Smooth progress and card highlights.'),
 'animations': ('Снег, дождь или листья зависят от темы и видны в свободных областях фона.',
                'Theme-specific snow, rain or leaves appear in exposed background areas.'),
 'roulette_motion': ('Перемешивание названий при награде. Отключение не отменяет саму выдачу.',
                     'Shuffles names during a reward. Disabling does not disable rewards.'),
 'server': ('Bancho требует API-ключ v1. Gatari использует свой ID без ключа Bancho.',
            'Bancho needs a v1 API key. Gatari uses its own ID without a Bancho key.'),
 'api_key': ('Ключ хранится в настройках на этом компьютере. Не передавайте settings.json другим людям.',
             'The key is saved locally. Do not share settings.json.')}


SETTING_HELP['tablet_driver_enabled'] = ('Выберите .exe драйвера. Он запускается свёрнутым при начале сессии и продолжает работать после её завершения.', 'Choose the driver executable. It starts minimized with a session and remains running afterwards.')
SETTING_HELP['osu_launch_enabled'] = ('Запускает osu!.exe из папки игры, указанной ниже. Игра остаётся открытой после сессии.', 'Launches osu!.exe from the game folder below. The game stays open after the session.')
SETTING_HELP['custom_special_chance'] = ('Особый скин: стандартный шанс 5% при прибавке от 0,1 PP к профилю. Включите галочку, чтобы изменить шанс.', 'Special skin: default 5% chance after a profile gain of at least 0.1 PP. Enable to change the chance.')
SETTING_HELP['interval'] = ('Пауза между опросами: от 1 секунды. Один опрос делает несколько запросов; ограничение частоты API может увеличить ожидание.', 'Pause between polls: at least 1 second. Each poll makes several requests; API pacing can increase the wait.')


SETTING_HELP['keep_current_skin'] = ('Награды сохраняются в коллекцию, но не заменяют текущий скин. Кнопка «Применить» работает вручную.', 'Rewards enter your collection without replacing the current skin. Apply still works manually.')
SETTING_HELP['ui_scale'] = ('Размер текста и элементов во всех окнах. Применяется сразу.', 'Text and control sizes in all windows. Applied immediately.')

SETTING_HELP.update({
    'show_session_summary': ('Отключите автоматическое окно. Итоги всегда можно открыть кнопкой на главном экране.', 'Disable the automatic popup. The Summary button remains available.'),
    'allow_skin_delete': ('В «Скинах» появится кнопка удаления всех неизбранных наград текущего слота. Нужны завершённая сессия и подтверждение. Личные скины, избранное и история сохранятся. Удалённый скин может выпасть снова.', 'Adds a button in Skins to remove all nonfavorite rewards in the current slot. End the session and confirm first. Personal skins, favorites and history are kept. Removed skins may drop again.'),
    'gatari_launch': ('При включённом запуске игры и выбранном сервере Gatari добавляет -devserver osugatari.ru. Перед переключением сервера закройте уже запущенную osu!.', 'With game autostart and Gatari selected, adds -devserver osugatari.ru. Close an already running osu! before switching servers.'),
    'difficulty': ('Сложная: место результата в топ-100 лидерборда карты выбранного сервера; у сложности должно быть больше 1000 запусков. Нужен онлайн-режим. Средняя: PP. Фан: комбо и звёзды. Провалы не дают наград.', 'Hard: this score’s place in the selected server’s map leaderboard, top 100; the difficulty must have over 1000 plays. Online only. Medium: PP. Fun: combo and stars. Failed plays never earn rewards.'),
})

class SettingsWindow(IconWindow):
    """Настройки применяются по изменению; незавершённый ввод не сохраняется."""
    LOCKED = {'api_key','user_id','osu_path','skin_pack_path','skin_source','skin_archive','drive_folder','keep_personal',
              'osu_launch_enabled','tablet_driver_enabled','tablet_driver_path','slot','offline','offline_username','offline_total_pp','server'}
    def __init__(self,parent):
        super().__init__(parent)
        self.app,self.draft,self.theme = parent,parent.settings.copy(),parent.theme
        self.pending = {}
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *_: self.filter_settings())
        self.geometry('780x760')
        self.minsize(740,480)
        self.build()

    def t(self,key):
        return tr(key,self.app.settings['language'])

    def build(self):
        scroll = self.body._parent_canvas.yview()[0] if hasattr(self,'body') else 0
        for widget in self.winfo_children():
            widget.destroy()
        self.theme = self.app.theme
        self.configure(fg_color=self.theme['bg'])
        self.title(self.t('settings'))
        self.variables = {}
        self.searchable = []
        self.app.label(self,'Поиск по настройкам' if self.app.settings['language']!='English' else 'Search settings',muted=True).pack(anchor='w',padx=20,pady=(8,0))
        search = ctk.CTkEntry(self,textvariable=self.search_var,placeholder_text='Поиск по настройкам' if self.app.settings['language']!='English' else 'Search settings',height=36)
        search.pack(fill='x',padx=20,pady=(2,0))
        footer = ctk.CTkFrame(self,fg_color=self.theme['panel'])
        footer.pack(side='bottom',fill='x',padx=18,pady=14)
        self.app.button(footer,self.t('close'),self.destroy).pack(side='right',padx=8,pady=8)
        if self.app.state_name=='idle':
            self.app.button(footer,self.t('setup'),lambda:(self.destroy(),self.app.open_setup()),True).pack(side='right',padx=4)
        self.note = self.app.label(footer,self.t('live_settings'),muted=True,wraplength=300,justify='left')
        self.note.pack(side='left',padx=10)
        categories = [('account','Аккаунт','Account'), ('skins','Скины','Skins'),
                      ('rewards','Награды','Rewards'), ('appearance','Оформление','Appearance'),
                      ('history','История','History'), ('team','Команда','Team')]
        self.category = getattr(self,'category','account')
        nav = ctk.CTkFrame(self,fg_color='transparent')
        nav.pack(fill='x',padx=18,pady=(8,0))
        self.category_frames = {}
        self.category_buttons = {}
        def select(category):
            self.category = category
            for name,frame in self.category_frames.items():
                frame.pack_forget()
                self.category_buttons[name].configure(fg_color=self.theme['accent'] if name==category else self.theme['card'],
                    text_color=self.app.ink if name==category else self.theme['text'],
                    hover_color=blend(self.theme['accent' if name==category else 'card'],'#000000',.08))
            self.category_frames[category].pack(fill='both',expand=True)
            self.body._parent_canvas.yview_moveto(0)
            if self.search_var.get(): self.filter_settings()
        for name,ru,en in categories:
            button = self.app.button(nav,en if self.app.settings['language']=='English' else ru,lambda n=name:self.navigate_category(n),True)
            button.configure(width=95)
            button.pack(side='left',expand=True,fill='x',padx=3)
            self.category_buttons[name] = button
        self.search_nav=nav
        self.search_hint=self.app.label(self,'',muted=True,size=11)
        self.body = body = FastScrollableFrame(self,fg_color=self.theme['bg'])
        body.pack(fill='both',expand=True,padx=18,pady=(18,0))
        locked = self.app.state_name != 'idle'
        if locked:
            self.app.label(body,self.t('locked_settings'),muted=True,wraplength=540).pack(anchor='w')
        for name,_,_ in categories:
            self.category_frames[name] = ctk.CTkFrame(self.body,fg_color='transparent')
        groups = {
            'account': {'account','server','api_key','user_id','offline','offline_username','offline_total_pp','slot','ignore_proxy'},
            'skins': {'allow_skin_delete','gatari_launch','osu_launch_enabled','tablet_driver_enabled','paths','osu_path','tablet_driver_path','skin_pack_path','skin_source','skin_archive','drive_folder','keep_personal','keep_current_skin','exclude_heavy','interface_skin','optimize_skins'},
            'rewards': {'difficulty','interval','custom_special_chance','rofl_chance','custom_rewards'},
            'appearance': {'ui_scale','language','theme','color','animations','ui_motion','roulette_motion'},
            'history': {'show_session_summary','log_mode','hide_failed','show_100','show_50','show_combo','show_accuracy','show_misses'},
        }
        for key in ('account','server','api_key','user_id','offline','offline_username','offline_total_pp','slot',
                    'allow_skin_delete','gatari_launch','osu_launch_enabled','tablet_driver_enabled','paths','osu_path','tablet_driver_path','skin_pack_path','skin_source','skin_archive','drive_folder','keep_personal','keep_current_skin',
                    'exclude_heavy','interface_skin','optimize_skins','difficulty','interval','custom_special_chance','rofl_chance','custom_rewards',
                    'ignore_proxy','ui_scale','language','theme','color','animations','ui_motion','roulette_motion','show_session_summary','log_mode','hide_failed','show_100','show_50','show_combo','show_accuracy','show_misses'):
            if key in ('drive_folder','color','ui_motion','log_mode','rofl_pp'): continue
            if key=='rofl_chance' and not self.draft['custom_special_chance']: continue
            if key=='skin_pack_path' and self.draft['skin_source']=='drive': continue
            body = self.category_frames[next(name for name,keys in groups.items() if key in keys)]
            if key=='skin_archive' and self.draft['skin_source']!='zip':
                continue
            if key=='drive_folder' and self.draft['skin_source']!='drive':
                continue
            if key in ('offline_username','offline_total_pp') and not self.draft['offline']:
                continue
            if key=='api_key' and (self.draft['server']=='gatari' or self.draft['offline']):
                continue
            if key in ('account','paths'):
                self.app.label(body,self.t(key),size=20,bold=True).pack(anchor='w',pady=(18,8))
                continue
            block = ctk.CTkFrame(body,fg_color=self.theme['panel'],corner_radius=12)
            block.pack(fill='x',pady=6)
            help_pair = SETTING_HELP.get(key,('', ''))
            self.searchable.append((block,self.t(key)+' '+help_pair[self.app.settings['language']=='English']))
            content = ctk.CTkFrame(block,fg_color='transparent')
            content.pack(fill='x',padx=14,pady=10)
            body = content
            help_text = SETTING_HELP.get(key)
            if help_text:
                self.app.label(body,help_text[self.app.settings['language']=='English'],size=11,muted=True,wraplength=590,justify='left').pack(side='bottom',anchor='w',pady=(6,0))
            if key in ('show_session_summary','allow_skin_delete','gatari_launch','keep_current_skin','osu_launch_enabled','custom_special_chance','tablet_driver_enabled','custom_rewards','show_100','show_50','show_combo','show_accuracy','show_misses','keep_personal','animations','ui_motion','roulette_motion','log_mode','hide_failed','offline','exclude_heavy','optimize_skins','ignore_proxy'):
                var = tk.BooleanVar(value=self.draft[key])
                self.variables[key] = var
                ctk.CTkCheckBox(body,text=self.t(key),variable=var,text_color=self.theme['text'],fg_color=self.theme['accent'],checkmark_color=self.app.ink,
                    state='disabled' if locked and key in self.LOCKED else 'normal',
                    command=lambda k=key:self.changed(k)).pack(anchor='w',pady=10)
                continue
            self.app.label(body,self.t(key),muted=True).pack(anchor='w',pady=(10,4))
            options = None
            if key == 'ui_scale':
                options = {v:v for v in ('90%','100%','110%','125%')}
            elif key == 'language':
                options = {v:v for v in ('Русский','English')}
            elif key == 'difficulty':
                options = {self.t(v):v for v in ('Hard','Medium','Fun')}
            elif key == 'theme':
                options = {v['en' if self.app.settings['language'] == 'English' else 'ru']:k for k,v in THEMES.items()}
            elif key == 'color':
                options = {v[self.app.settings['language'] == 'English']:k for k,v in COLORS.items()}
            elif key == 'interface_skin':
                options = {self.t('no_base'):''}
                options.update({v:v for v in self.app.base_skins})
                if self.draft[key]:
                    options[self.draft[key]] = self.draft[key]
            elif key == 'skin_source':
                options = {self.t(k):k for k in ('folder','zip','drive')}
            elif key == 'server':
                options = {self.t(k):k for k in ('bancho','gatari')}
            elif key == 'slot':
                options = {self.app.t('slot_label',n=n):n for n in ('1','2','3')}
            var = tk.StringVar(value=str(self.draft[key]))
            self.variables[key] = var
            if options:
                if self.draft[key] not in options.values():
                    self.draft[key] = next(iter(options.values()))
                    var.set(self.draft[key])
                display = next(k for k,v in options.items() if v == self.draft[key])
                def choose(value,key=key,mapping=options,variable=var):
                    variable.set(mapping[value])
                    self.changed(key)
                menu = ctk.CTkOptionMenu(body,values=list(options),command=choose,fg_color=self.theme['card'],button_color=self.theme['card'],button_hover_color=blend(self.theme['card'],'#000000',.08),dropdown_hover_color=blend(self.theme['panel'],'#000000',.08),text_color=self.theme['text'],dropdown_fg_color=self.theme['panel'],dropdown_text_color=self.theme['text'],width=360)
                menu.set(display)
                menu.pack(anchor='w',pady=3)
                if locked and key in self.LOCKED:
                    menu.configure(state='disabled')
            else:
                entry = ctk.CTkEntry(body,textvariable=var,show='*' if key == 'api_key' else '',fg_color=self.theme['card'],text_color=self.theme['text'],border_color=self.theme['card'],height=36)
                entry.pack(fill='x',pady=3)
                if locked and key in self.LOCKED:
                    entry.configure(state='disabled')
                var.trace_add('write',lambda *args,k=key:self.changed(k,delay=550))
                if key in ('tablet_driver_path','skin_archive','osu_path','skin_pack_path'):
                    def browse(k=key,v=var):
                        value = filedialog.askopenfilename(parent=self,initialdir=str(Path(v.get()).parent) if v.get() else None,filetypes=[('EXE','*.exe')] if k=='tablet_driver_path' else [('ZIP','*.zip')]) if k in ('skin_archive','tablet_driver_path') else filedialog.askdirectory(parent=self)
                        if value:
                            v.set(value)
                    browse_button = self.app.button(body,self.t('browse'),browse,True)
                    browse_button.pack(anchor='e',pady=3)
                    if locked:
                        browse_button.configure(state='disabled')
                if key in ('api_key','user_id'): bind_api_paste(entry)
                if key == 'api_key':
                    row = ctk.CTkFrame(body,fg_color='transparent')
                    row.pack(fill='x',pady=4)
                    ctk.CTkCheckBox(row,text=self.t('show'),text_color=self.theme['text'],command=lambda e=entry:e.configure(show='' if e.cget('show') else '*')).pack(side='left',padx=16)
        from modules.gacha_team import build_team
        build_team(self, self.category_frames['team'])
        self.reward_fields()
        if self.draft['offline']:
            self.app.label(self.category_frames['account'],self.t('offline_hint'),muted=True,wraplength=520,justify='left').pack(pady=12)
        reset = self.app.button(self.category_frames['skins'],self.t('reset_skins'),self.app.reset_skins,True)
        reset.pack(fill='x',pady=18)
        if locked:
            reset.configure(state='disabled')
        transfer=ctk.CTkFrame(self.category_frames['history'],fg_color=self.theme['panel'])
        transfer.pack(fill='x',pady=12)
        self.app.label(transfer,'Перенос данных' if self.app.settings['language']!='English' else 'Transfer data',bold=True).pack(anchor='w',padx=12,pady=8)
        self.app.label(transfer,'История, настройки и открытые скины всех слотов. Импорт дополняет коллекцию.' if self.app.settings['language']!='English' else 'History, settings and skins in every slot. Import adds to the collection.',wraplength=600,muted=True).pack(padx=12)
        self.include_key=tk.BooleanVar(value=False)
        ctk.CTkCheckBox(transfer,text='Включить API-ключ в архив' if self.app.settings['language']!='English' else 'Include API key in archive',variable=self.include_key).pack(anchor='w',padx=12,pady=10)
        for importing,label in [(False,'Экспорт' if self.app.settings['language']!='English' else 'Export'),(True,'Импорт' if self.app.settings['language']!='English' else 'Import')]:
            b=self.app.button(transfer,label,lambda i=importing:self.app.transfer_data(i,self.include_key.get()),True)
            b.pack(side='left',padx=12,pady=12)
            if locked:b.configure(state='disabled')
        self.searchable.append((transfer,'Перенос экспорт импорт данные история transfer export import data history'))
        self.layout = {frame:list(frame.pack_slaves()) for frame in self.category_frames.values()}
        self.select_category=select
        self.search_expanded={}
        self.last_search=None
        self.search_headers={};self.search_titles={};self.search_toggles={}
        for name,ru,en in categories:
            header=ctk.CTkFrame(self.category_frames[name],fg_color=self.theme['card'],corner_radius=12)
            self.search_headers[name]=header
            title=self.app.button(header,en if self.app.settings['language']=='English' else ru,lambda n=name:self.navigate_category(n),True)
            title.configure(anchor='w')
            title.pack(side='left',fill='x',expand=True,padx=6,pady=6)
            self.search_titles[name]=(title,en if self.app.settings['language']=='English' else ru)
            toggle=self.app.button(header,'▸',lambda n=name:self.toggle_category(n),True);toggle.configure(width=42)
            toggle.pack(side='right',padx=6,pady=6);self.search_toggles[name]=toggle
        select(self.category)
        self.filter_settings()

    def navigate_category(self,name):
        self.category=name
        self.search_var.set('')
        self.select_category(name)

    def toggle_category(self,name):
        self.search_expanded[name]=not self.search_expanded.get(name,False)
        self.filter_settings()

    def filter_settings(self):
        if not hasattr(self,'category_frames') or not hasattr(self,'searchable'):return
        query=self.search_var.get().strip().casefold()
        if query!=getattr(self,'last_search',None):
            self.search_expanded={};self.last_search=query
        descriptions={block:description for block,description in self.searchable}
        found=0
        if hasattr(self,'search_hint'):self.search_hint.pack_forget()
        for name,button in self.category_buttons.items():
            selected=not query and name==self.category
            button.configure(fg_color=self.theme['accent'] if selected else self.theme['card'],text_color=self.app.ink if selected else self.theme['text'])
        for name,frame in self.category_frames.items():
            frame.pack_forget()
            header=getattr(self,'search_headers',{}).get(name)
            if header:header.pack_forget()
            matches=[]
            for block in getattr(self,'layout',{}).get(frame,[]):
                if not block.winfo_exists():continue
                if not hasattr(block,'_search_pack'):block._search_pack=block.pack_info()
                block.pack_forget()
                match=block in descriptions and all(word in descriptions[block].casefold() for word in query.split())
                if not query or match:matches.append(block)
            if query and matches and header:
                header.pack(fill='x',pady=(8,4))
                title,label=self.search_titles[name]
                found+=len(matches)
                count_text='matches' if self.app.settings['language']=='English' else 'найдено'
                title.configure(text=f'{label}  ·  {count_text}: {len(matches)}  ↗')
                self.search_toggles[name].configure(text='▾' if self.search_expanded.get(name) else '▸')
            if not query or self.search_expanded.get(name):
                for block in matches:
                    options=dict(block._search_pack);options.pop('in',None);block.pack(**options)
            if (query and matches) or (not query and name==self.category):frame.pack(fill='x')
        if query and hasattr(self,'search_hint'):
            english=self.app.settings['language']=='English'
            hint=('Heading opens the category · Arrow reveals matches' if english else 'Название открывает категорию · Стрелка показывает найденные пункты') if found else ('No matching settings' if english else 'Настройки не найдены')
            self.search_hint.configure(text=hint);self.search_hint.pack(fill='x',padx=20,pady=(8,0),after=self.search_nav)
        if hasattr(self,'body'):self.body._parent_canvas.yview_moveto(0)

    def reward_fields(self):
        body = self.category_frames['rewards']
        mode = self.draft['difficulty']
        enabled = bool(self.draft.get('custom_rewards'))
        if not enabled: return
        english = self.app.settings['language']=='English'
        unit = {'Hard':('Позиция в топ-100','Top position'),'Medium':('PP','PP'),'Fun':('Комбо','Combo')}[mode][english]
        self.app.label(body,unit,muted=True).pack(anchor='w',pady=(12,4))
        keys = [('goal_'+mode+'_'+r,r) for r in RANKS]
        if mode=='Fun': keys.append(('goal_stars',('Минимум ★','Minimum ★')[english]))
        for key,label in keys:
            row=ctk.CTkFrame(body,fg_color='transparent');row.pack(fill='x',pady=3)
            self.searchable.append((row,self.t('custom_rewards')+' '+unit+' '+label))
            self.app.label(row,label,width=150).pack(side='left')
            var=tk.StringVar(value=str(self.draft[key]));self.variables[key]=var
            entry=ctk.CTkEntry(row,textvariable=var,state='normal' if enabled else 'disabled')
            entry.pack(side='left',fill='x',expand=True)
            var.trace_add('write',lambda *args,k=key:self.changed(k,delay=700))

    def changed(self,key,delay=0):
        self.draft[key] = self.variables[key].get()
        if key in self.pending:
            self.after_cancel(self.pending.pop(key))
        if delay:
            self.pending[key] = self.after(delay,lambda:self.apply_value(key))
        else:
            self.apply_value(key)

    def apply_value(self,key,rebuild=True):
        self.pending.pop(key,None)
        if key=='server' and 'user_id' in self.pending:
            self.after_cancel(self.pending.pop('user_id'))
            self.apply_value('user_id',rebuild=False)
        value = self.draft[key]
        if self.app.state_name != 'idle' and key in self.LOCKED:
            return
        try:
            limits = {'interval':(1,300),'rofl_chance':(0,100),'rofl_pp':(0,100000),'offline_total_pp':(0,100000)}
            if key.startswith('goal_'):
                value=float(str(value).replace(',','.'))
                maximum = 100 if key.startswith('goal_Hard_') else 20 if key=='goal_stars' else 100000
                if not math.isfinite(value) or not 0 < value <= maximum: raise ValueError()
                if key.startswith(('goal_Hard_','goal_Fun_')) and not value.is_integer(): raise ValueError()
                mode=self.draft['difficulty']
                values=[float(value if key=='goal_'+mode+'_'+r else self.draft['goal_'+mode+'_'+r]) for r in RANKS]
                if values != sorted(values,reverse=mode!='Hard'): raise ValueError(('Пороги SS → D должны идти по порядку','Keep SS → D thresholds ordered')[self.app.settings['language']=='English'])
            if key in limits:
                value = float(str(value).replace(',','.'))
                if key in ('interval','rofl_chance'):
                    if not value.is_integer(): raise ValueError('Введите целое число' if self.app.settings['language']!='English' else 'Enter a whole number')
                    value=int(value)
                low,high = limits[key]
                if not math.isfinite(value) or not low <= value <= high:
                    raise ValueError()
            if key in self.LOCKED and isinstance(value,str):
                value = value.strip()
                if key == 'user_id' and value and not value.isdigit():
                    raise ValueError()
                if key in ('osu_path','skin_pack_path') and (not value or not Path(value).is_dir()):
                    raise ValueError()
                if key=='skin_archive' and value and (not Path(value).is_file() or not zipfile.is_zipfile(value)):
                    raise ValueError()
            self.app.apply_live_setting(key,value)
            if key=='allow_skin_delete':self.app.render_collection()
            self.draft[key] = value
            if key in ('interval','rofl_chance') and self.variables[key].get()!=str(value):
                self.variables[key].set(str(value))
            if key=='server': self.draft['user_id'] = self.app.settings['user_id']
            if key=='offline':
                self.draft['offline_total_pp'] = self.app.settings['offline_total_pp']
            self.note.configure(text=self.t('live_settings'))
            if rebuild and key in ('difficulty','custom_rewards','custom_special_chance','language','theme','color','osu_path','skin_pack_path','skin_source','server','offline','slot'):
                self.build()
        except (ValueError,OSError) as error:
            if isinstance(self.app.settings.get(key),bool):
                self.draft[key] = self.app.settings[key]
                self.variables[key].set(self.draft[key])
            self.note.configure(text=str(error) or self.t('invalid'))

    def language_changed(self,lang):
        self.variables['language'].set(lang)
        self.changed('language')

    def paste(self,var):
        try:
            var.set(self.clipboard_get().strip())
        except tk.TclError:
            self.note.configure(text=self.t('clipboard'))

    def destroy(self):
        for key,timer in list(self.pending.items()):
            self.after_cancel(timer)
            self.apply_value(key,rebuild=False)
        self.pending.clear()
        super().destroy()

