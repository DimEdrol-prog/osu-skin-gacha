"""Friendly first-run wizard. Changes stay in a draft until Finish."""
from pathlib import Path
import math
import tkinter as tk
from tkinter import filedialog, messagebox
import webbrowser
import customtkinter as ctk
from modules.gacha_widgets import IconWindow, FastScrollableFrame, bind_api_paste
from modules.gacha_config import THEMES, TEXT, tr, blend
from modules.gacha_settings import SETTING_HELP

def open_setup(self):
    if self.closing:
        return
    if getattr(self,'setup_window',None) and self.setup_window.winfo_exists():
        self.setup_window.lift()
        return
    window = self.setup_window = IconWindow(self)
    window.title('osu! Skin Gacha — Setup')
    window.geometry(f'780x{min(820,max(640,self.winfo_screenheight()-100))}')
    window.minsize(680,640)
    draft = self.settings.copy()
    variables = {key:tk.StringVar(value=str(draft[key])) for key in
        ('language','osu_path','server','user_id','api_key','offline_username','difficulty','slot','theme','skin_source','skin_pack_path','skin_archive','tablet_driver_path','interface_skin','interval','rofl_chance','rofl_pp','offline_total_pp')}
    if draft['offline']:
        variables['server'].set('offline')
    setup_server = [draft['server']]
    setup_ids = dict(draft.get('server_user_ids',{}))
    def switch_setup_server(value):
        setup_ids[setup_server[0]] = variables['user_id'].get().strip()
        if value != 'offline':
            variables['user_id'].set(setup_ids.get(value,''))
            setup_server[0] = value
        render()
    step = [0]
    advanced = [False]
    def ru(a,b):
        return a if variables['language'].get()=='Русский' else b
    def render():
        for child in window.winfo_children():
            child.destroy()
        palette = THEMES[variables['theme'].get()]
        window.configure(fg_color=palette['bg'])
        window.title(ru('osu!gacha — Первичная настройка','osu!gacha — First-time setup'))
        accent = palette['accent']
        rgb=[int(accent[i:i+2],16) for i in (1,3,5)]
        ink='#10151b' if sum(c*w for c,w in zip(rgb,(.2126,.7152,.0722)))>140 else '#ffffff'
        def button(parent, caption, command, secondary=False):
            colour=palette['card' if secondary else 'accent']
            return ctk.CTkButton(parent,text=caption,command=command,height=38,
                fg_color=colour,hover_color=blend(colour,'#000000',.08),text_color=palette['text'] if secondary else ink,
                font=('Segoe UI',14,'bold'),corner_radius=10)
        header=ctk.CTkFrame(window,fg_color='transparent')
        header.pack(fill='x',padx=24,pady=(20,10))
        titles=[('Добро пожаловать','Welcome'),('Игра и скины','Game and skins'),('Твой профиль','Your profile'),
                ('Награды за игру','Gameplay rewards'),('Твоя коллекция','Your collection'),('Всё готово','Ready to begin')]
        captions=[('Несколько шагов — и можно открывать новые скины.','A few steps, then you can start unlocking skins.'),
                  ('Укажи, где установлена игра. Остальное можно оставить как есть.','Choose your game folder. The other defaults are ready to use.'),
                  ('Выбери сервер, на котором играешь. У каждого сервера свой ID.','Choose where you play. Each server has its own user ID.'),
                  ('Выбери, за какие достижения получать скины.','Choose which achievements unlock skins.'),
                  ('Настрой хранение скинов. Всё можно изменить позже.','Choose how to store skins. You can change this later.'),
                  ('Выбери оформление и проверь настройки перед сохранением.','Choose a theme and review your settings before saving.')]
        ctk.CTkLabel(header,text=ru(f'ШАГ {step[0]+1} ИЗ 6',f'STEP {step[0]+1} OF 6'),font=('Segoe UI',12,'bold'),text_color=palette['muted']).pack(anchor='w')
        ctk.CTkLabel(header,text=ru(*titles[step[0]]),font=('Segoe UI',27,'bold'),text_color=palette['text']).pack(anchor='w',pady=(2,2))
        ctk.CTkLabel(header,text=ru(*captions[step[0]]),font=('Segoe UI',14),text_color=palette['muted'],wraplength=620,justify='left').pack(anchor='w')
        progress=ctk.CTkProgressBar(header,height=5,progress_color=accent,fg_color=palette['card'])
        progress.pack(fill='x',pady=(14,0));progress.set((step[0]+1)/6)
        footer=ctk.CTkFrame(window,fg_color=palette['panel'],corner_radius=12)
        footer.pack(side='bottom',fill='x',padx=24,pady=(10,18))
        body=FastScrollableFrame(window,fg_color=palette['bg'])
        body.pack(fill='both',expand=True,padx=20,pady=(0,0))
        def block(title, hint=''):
            frame=ctk.CTkFrame(body,fg_color=palette['panel'],corner_radius=12)
            frame.pack(fill='x',pady=6)
            inner=ctk.CTkFrame(frame,fg_color='transparent')
            inner.pack(fill='x',padx=16,pady=12)
            if title: ctk.CTkLabel(inner,text=title,text_color=palette['text'],font=('Segoe UI',15,'bold'),anchor='w').pack(fill='x',pady=(0,6))
            if hint: ctk.CTkLabel(inner,text=hint,text_color=palette['muted'],font=('Segoe UI',13),wraplength=590,justify='left').pack(side='bottom',anchor='w',pady=(7,0))
            return inner
        def note(a,b): block(ru(a,b))
        def entry(key,a,b,secret=False,hint=''):
            parent=block(ru(a,b),hint)
            widget=ctk.CTkEntry(parent,textvariable=variables[key],show='*' if secret else '',height=38,
                fg_color=palette['card'],text_color=palette['text'],border_color=palette['card'],font=('Segoe UI',14))
            widget.pack(fill='x',pady=2)
            if secret or key=='user_id':bind_api_paste(widget)
            return widget
        def check(key,parent=None):
            parent=parent if parent is not None else block('',ru(*SETTING_HELP[key]) if key in SETTING_HELP else '')
            flag=tk.BooleanVar(value=draft[key])
            ctk.CTkCheckBox(parent,text=tr(key,variables['language'].get()),variable=flag,text_color=palette['text'],
                fg_color=accent,hover_color=blend(accent,'#000000',.08),checkmark_color=ink,font=('Segoe UI',14),
                command=lambda:(draft.update({key:flag.get()}),render() if key=='custom_special_chance' else None)).pack(anchor='w',pady=6)
        def choose(title,key,options,hint='',callback=None):
            parent=block(title,hint)
            def selected(label):
                value=options[label];variables[key].set(value)
                if callback: callback(value)
            menu=ctk.CTkOptionMenu(parent,values=list(options),command=selected,fg_color=palette['card'],button_color=palette['card'],
                button_hover_color=blend(palette['card'],'#000000',.08),text_color=palette['text'],dropdown_fg_color=palette['panel'],
                dropdown_text_color=palette['text'],dropdown_hover_color=palette['card'],height=38,width=350,font=('Segoe UI',14))
            menu.set(next((label for label,value in options.items() if value==variables[key].get()),variables[key].get()))
            menu.pack(anchor='w',pady=2)
        def browse(key,widget,files=None):
            def pick():
                current=Path(variables[key].get()).expanduser()
                if not current.is_dir():current=current.parent
                while not current.is_dir() and current.parent!=current:current=current.parent
                args=dict(parent=window,initialdir=str(current))
                value=filedialog.askopenfilename(**args,filetypes=files) if files else filedialog.askdirectory(**args)
                if value:variables[key].set(value)
            button(widget.master,ru('Выбрать файл' if files else 'Выбрать папку','Choose file' if files else 'Choose folder'),pick,True).pack(anchor='e',pady=(6,0))
        if step[0]==0:
            choose(ru('Язык приложения','App language'),'language',{v:v for v in ('Русский','English')},callback=lambda _:render())
            block(ru('Играй. Открывай. Собирай.','Play. Unlock. Collect.'),ru(
                'Поставь скор — получи награду. Рулетка покажет превью и выберет новый скин для твоей коллекции.',
                'Set a score and earn a reward. The roulette shows previews and picks a new skin for your collection.'))
            block(ru('Личные скины сохраняются','Your personal skins stay safe'),ru(
                'При старте сессии они временно уходят в резервную папку, а при завершении возвращаются. На шаге «Твоя коллекция» можно оставить их в игре.',
                'A session temporarily backs them up and restores them when it ends. You can also keep them in the game on the Collection step.'))
            block(ru('Без спешки','Take your time'),ru('Настройки сохранятся только после «Готово». Любой пункт можно изменить позже.','Nothing is saved until Finish. Every setting can be changed later.'))
        elif step[0]==1:
            game=entry('osu_path','Папка osu!','osu! folder',hint=ru('Выбери папку osu!stable, в которой находится osu!.exe.','Choose the osu!stable folder containing osu!.exe.'))
            browse('osu_path',game);check('osu_launch_enabled',game.master)
            driver=entry('tablet_driver_path','Программа драйвера графического планшета (.exe)','Graphics tablet driver application (.exe)',hint=ru('Необязательно. Например, OpenTabletDriver. При запуске драйвер сворачивается.','Optional. For example, OpenTabletDriver. The driver starts minimized.'))
            browse('tablet_driver_path',driver,[('Программа / Application','*.exe')]);check('tablet_driver_enabled',driver.master)
            source_hint = {
                'drive':('Google Drive уже настроен: превью загружаются заранее, а скин — после выигрыша.', 'Google Drive is ready to use: previews load in advance, skins download when won.'),
                'zip':('Выбери ZIP с папками рангов и скинами .osk. Скин извлекается из архива после выигрыша.', 'Choose a ZIP with rank folders and .osk skins. The winning skin is extracted from the archive.'),
                'folder':('Выбери папку с локальным набором скинов, распределённых по рангам.', 'Choose a local skin pack folder organised by rank.')
            }[variables['skin_source'].get()]
            choose(ru('Откуда брать скины','Skin source'),'skin_source',
                {tr(v,variables['language'].get()):v for v in ('drive','zip','folder')},
                ru(*source_hint),callback=lambda _:render())
            if variables['skin_source'].get()=='zip':
                archive=entry('skin_archive','ZIP со скинами','Skin ZIP archive');browse('skin_archive',archive,[('ZIP','*.zip')])
            if variables['skin_source'].get()!='drive':
                pack=entry('skin_pack_path','Папка набора и данных','Skin pack and data folder',hint=ru(*SETTING_HELP['skin_pack_path']));browse('skin_pack_path',pack)
        elif step[0]==2:
            choose(ru('Где ты играешь?','Where do you play?'),'server',
                {'osu! (Bancho)':'bancho','Gatari':'gatari',ru('Офлайн','Offline'):'offline'},callback=switch_setup_server)
            if variables['server'].get()=='offline':
                entry('offline_total_pp','Общее PP профиля','Total profile PP',hint=ru('Используется для расчёта целей. Если не знаешь, оставь 0.','Used to calculate goals. Leave 0 if unsure.'))
                entry('offline_username','Имя игрока','Player name',hint=ru('Можно оставить пустым: возьмём имя из osu!.db.','Leave blank to use the name from osu!.db.'))
                block(ru('Как работает офлайн','How offline mode works'),ru('Доступны сохранённые результаты и ранее скачанные скины. PP рассчитывается локально.','Uses saved scores and previously downloaded skins. PP is calculated locally.'))
            else:
                example='osu.ppy.sh/users/12345' if variables['server'].get()=='bancho' else 'osu.gatari.pw/u/12345'
                entry('user_id','ID твоего профиля','Your profile ID',hint=ru(f'Число в конце ссылки на профиль: {example} → 12345. Можно вставить через Ctrl+V.',f'The number at the end of your profile URL: {example} → 12345. Ctrl+V works here.'))
                if variables['server'].get()=='bancho':
                    field=entry('api_key','API-ключ osu! v1','osu! API v1 key',True,ru('Нужен для чтения твоих скоров. Хранится только в локальных настройках.','Required to read your scores. Saved only in local settings.'))
                    ctk.CTkCheckBox(field.master,text=ru('Показать ключ','Show key'),text_color=palette['text'],fg_color=accent,checkmark_color=ink,
                        command=lambda:field.configure(show='' if field.cget('show') else '*')).pack(anchor='w',pady=6)
                    button(field.master,ru('Получить API-ключ','Get an API key'),lambda:webbrowser.open('https://osu.ppy.sh/p/api'),True).pack(anchor='w',pady=4)
                else:block(ru('Ключ не нужен','No key needed'),ru('Gatari использует публичный API. Достаточно ID профиля Gatari.','Gatari uses a public API. Your Gatari profile ID is enough.'))
            check('ignore_proxy')
        elif step[0]==3:
            choose(ru('За что получать награды','What earns rewards'),'difficulty',{tr(v,variables['language'].get()):v for v in ('Hard','Medium','Fun')},
                ru('Сложная — место в лидерборде карты (>1000 запусков, онлайн).\nСредняя — PP результата.\nФан — комбо и сложность карты.',
                   'Hard — map leaderboard position (>1000 plays, online).\nMedium — score PP.\nFun — combo and map difficulty.'))
            entry('interval','Интервал API, секунды','API interval, seconds',hint=ru('Обычно достаточно 15 секунд. Допустимы целые числа от 1 до 300; ограничения API сохраняются.','15 seconds is usually enough. Whole numbers from 1 to 300; API pacing still applies.'))
            block(ru('Особый скин','Special skin'),ru('При прибавке от 0,1 PP к профилю стандартный шанс — 5%. Защита от повторных наград на одной сложности сохраняется.',
                'A profile gain of at least 0.1 PP has a default 5% special-skin chance. Repeated rewards on the same difficulty remain blocked.'))
        elif step[0]==4:
            choose(ru('Слот коллекции','Collection slot'),'slot',{ru(f'Слот {n}',f'Slot {n}'):n for n in ('1','2','3')},ru('Три независимые коллекции. Начни с первого слота — сменить его можно позже.','Three independent collections. Start with slot 1; you can switch later.'))
            check('keep_personal');check('exclude_heavy')
            button(body,ru('Скрыть дополнительные настройки' if advanced[0] else 'Дополнительные настройки',
                           'Hide additional settings' if advanced[0] else 'Additional settings'),lambda:(advanced.__setitem__(0,not advanced[0]),render()),True).pack(fill='x',pady=10)
            if advanced[0]:
                choices={ru('Не выбрана','Not selected'):''}
                for folder in (Path(variables['osu_path'].get())/'Skins',self.sandbox.backup):
                    if folder.is_dir():
                        choices.update({p.name:p.name for p in folder.iterdir() if p.is_dir() and (p/'skin.ini').is_file()})
                if variables['interface_skin'].get():choices[variables['interface_skin'].get()]=variables['interface_skin'].get()
                choose(ru('Основа интерфейса','Interface base'),'interface_skin',choices,ru(*SETTING_HELP['interface_skin']))
                check('optimize_skins');check('custom_special_chance')
                if draft['custom_special_chance']:entry('rofl_chance',*TEXT['rofl_chance'])
                check('hide_failed')
        else:
            choose(ru('Тема оформления','Theme'),'theme',{v['ru' if variables['language'].get()=='Русский' else 'en']:k for k,v in THEMES.items()},callback=lambda _:render())
            check('animations');check('roulette_motion')
            server={'bancho':'osu! (Bancho)','gatari':'Gatari','offline':ru('Офлайн','Offline')}[variables['server'].get()]
            block(ru('Проверь перед сохранением','Review before saving'),ru(
                f"Игра: {variables['osu_path'].get()}\nСервер: {server} · Слот: {variables['slot'].get()}\nСложность: {tr(variables['difficulty'].get(),variables['language'].get())}",
                f"Game: {variables['osu_path'].get()}\nServer: {server} · Slot: {variables['slot'].get()}\nDifficulty: {tr(variables['difficulty'].get(),variables['language'].get())}"))
            block(ru('Что дальше?','What next?'),ru(
                'Нажми «Готово», затем «Начать сессию» в главном окне. После первой награды выбери в osu! скин «! osu!gacha — Текущий скин». Для обновления нажимай Ctrl+Shift+Alt+S. После игры заверши сессию в приложении.',
                'Click Finish, then Start session in the main window. After your first reward, select “! osu!gacha — Текущий скин” in osu!. Press Ctrl+Shift+Alt+S to reload it. End the session in the app when done.'))
        def advance():
            if step[0]==1 and not (Path(variables['osu_path'].get())/'osu!.exe').is_file():
                messagebox.showerror('osu!',ru('Выберите папку с osu!.exe.','Select the folder containing osu!.exe.'),parent=window)
                return
            if step[0]==1 and variables['skin_source'].get()=='zip' and not Path(variables['skin_archive'].get()).is_file():
                messagebox.showerror('osu!',ru('Выберите существующий ZIP.','Select an existing ZIP.'),parent=window)
                return
            if step[0]==1 and draft.get('tablet_driver_enabled'):
                driver=Path(variables['tablet_driver_path'].get())
                if not driver.is_file() or driver.suffix.lower()!='.exe':
                    messagebox.showerror('osu!',ru('Выбери .exe драйвера планшета или выключи его запуск с сессией.','Choose a tablet driver .exe or disable starting it with the session.'),parent=window)
                    return
            if step[0]==2 and variables['server'].get()!='offline':
                if not variables['user_id'].get().strip().isdigit() or (variables['server'].get()=='bancho' and not variables['api_key'].get().strip()):
                    messagebox.showerror('osu!',ru('Введите ID и API-ключ для Bancho. Для Gatari нужен только ID.','Enter ID and API key for Bancho; Gatari needs only ID.'),parent=window)
                    return
            limits={1:(),2:('offline_total_pp',),3:('interval',),4:('rofl_chance',)}
            ranges={'interval':(1,300),'offline_total_pp':(0,100000),'rofl_chance':(0,100),'rofl_pp':(0,100000)}
            for key in limits.get(step[0],()):
                try:
                    value=float(variables[key].get())
                    if key in ('interval','rofl_chance') and not value.is_integer(): raise ValueError()
                    low,high=ranges[key]
                    if not math.isfinite(value) or not low<=value<=high: raise ValueError()
                except ValueError:
                    messagebox.showerror('osu!',ru('Проверьте числовое поле: ','Check numeric field: ')+tr(key,variables['language'].get()),parent=window)
                    return
            if step[0]==4 and draft['optimize_skins'] and not variables['interface_skin'].get():
                messagebox.showerror('osu!',ru('Сначала выберите основу интерфейса.','Select an interface base first.'),parent=window)
                return
            if step[0]<5:
                step[0]+=1
                render()
                return
            if self.state_name != 'idle':
                messagebox.showinfo(self.t('settings'),self.t('locked_settings'),parent=window)
                return
            draft.update({k:v.get().strip() for k,v in variables.items()})
            for key in ranges: draft[key]=int(float(draft[key])) if key in ('interval','rofl_chance') else float(draft[key])
            draft['rofl_pp']=0.1
            draft['offline'] = draft['server']=='offline'
            if draft['offline']: draft['server']='bancho'
            setup_ids[setup_server[0]] = variables['user_id'].get().strip()
            draft['server_user_ids'] = setup_ids
            draft['setup_complete']=True
            try: self.store.save(draft)
            except OSError as error:
                messagebox.showerror('osu!',str(error),parent=window)
                return
            self.settings=draft
            window.destroy()
            self.configure_services()
            self.build_ui()
            self.refresh_pool()
        def back():
            step[0]-=1
            render()
        if step[0]: button(footer,ru('Назад','Back'),back,True).pack(side='left',padx=8,pady=8)
        button(footer,ru('Готово' if step[0]==5 else 'Далее','Finish' if step[0]==5 else 'Next'),advance).pack(side='right',padx=8,pady=8)

    render()

