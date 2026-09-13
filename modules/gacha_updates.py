"""Small beta4 windows and profile feedback; all Tk work stays on the UI thread."""
import tkinter as tk
import time
import customtkinter as ctk
from modules.gacha_widgets import IconWindow, FastScrollableFrame
from modules.gacha_config import blend

CHANGELOG = [('beta4 · Новое / Latest',
  [('Полная история изменений из переписки, сгруппированная по разделам.',
    'Full conversation-based changelog grouped by topic.'),
   ('Сворачиваемые результаты поиска настроек; переход в категорию нажатием на заголовок.',
    'Collapsible settings search results; click a heading to open its category.'),
   ('Кнопка прослушивания локального трека на всех карточках скоров. Повторное нажатие останавливает музыку.',
    'Local music playback on every score card. Click again to stop.'),
   ('Увеличение превью в коллекции; закрытие крестиком, Escape или нажатием вне изображения.',
    'Enlarged collection previews; close with ×, Escape or an outside click.'),
   ('Индикатор соединения с сервером: время проверки, причина ошибки и повторная проверка.',
    'Server connection indicator with last check time, error reason and retry.')]),
 ('beta4 · Награды / Rewards',
  [('Сложный режим: место сыгранного результата в лидерборде карты выбранного сервера; больше 1000 запусков '
    'сложности.',
    'Hard rewards use the played score’s map leaderboard position on the selected server; over 1000 '
    'difficulty plays required.'),
   ('Проваленные скоры не дают обычных и DT-наград.', 'Failed scores cannot earn regular or DT rewards.'),
   ('Повторные попытки на одной сложности не позволяют фармить одинаковые награды. Более высокий ранг '
    'открывает новую награду.',
    'Repeated attempts cannot farm the same reward tier; a higher tier can earn another reward.'),
   ('Отдельные пороги по сложностям доступны после включения «Изменить параметры получения наград».',
    'Custom difficulty thresholds appear only after enabling custom reward requirements.'),
   ('Особый скин: стандартный шанс 5% при прибавке от 0,1 PP к профилю; изменение шанса включается отдельно.',
    'Special skin: default 5% chance after at least 0.1 profile PP gained; chance customization has its own '
    'toggle.'),
   ('DT/NC учитывают сложность карты после модов; цель DT размещена рядом с остальными рангами.',
    'DT/NC use mod-adjusted star rating; the DT goal appears alongside other ranks.'),
   ('Анимация прироста PP возле профиля.', 'Floating profile PP gain animation.')]),
 ('beta4 · Коллекция и рулетка / Collection and roulette',
  [('Коллекция «Скины»: сетка превью, названия, ранги и отметки избранного.',
    'Skins collection: preview grid, names, ranks and favorite markers.'),
   ('Поиск по названию, фильтры по рангу, избранному и дате получения; сортировка.',
    'Name search; rank, favorite and acquisition-date filters; sorting.'),
   ('Кнопка применения скина на каждой карточке.', 'Apply button on each skin card.'),
   ('При переключении страниц коллекция прокручивается вверх.', 'Collection page changes scroll to the top.'),
   ('Google Drive: скины и превью сопоставляются по одинаковому имени в папке ранга.',
    'Google Drive pairs skins with identically named previews within rank folders.'),
   ('Превью загружаются заранее и сохраняются в локальном кэше для быстрого старта рулетки.',
    'Previews preload and cache locally for faster roulette starts.'),
   ('Плавная прокрутка рулетки с замедлением и выделением выпавшего скина.',
    'Smooth roulette deceleration and highlighted winning skin.'),
   ('Победитель остаётся в центре при изменении размера окна; лента заполняет всю ширину.',
    'Winner stays centered when resizing; the strip fills the available width.'),
   ('Скины повторяются в ленте после прохода остальных кандидатов; ранг показан рядом с победителем.',
    'Skins repeat after cycling through other candidates; the winning tier appears beside the name.'),
   ('Превью рулетки увеличиваются по нажатию; правая кнопка открывает путь к превью или Google Drive.',
    'Click roulette previews to enlarge; right-click to locate a preview or open Google Drive.'),
   ('Прогресс скачивания: объём, скорость и оценка оставшегося времени.',
    'Download progress shows bytes, speed and estimated time remaining.'),
   ('Удаление неизбранных наград текущего слота: отдельное разрешение, по умолчанию выключено, и '
    'подтверждение.',
    'Nonfavorite cleanup for the current slot requires an opt-in setting, off by default, and '
    'confirmation.')]),
 ('Ранее · Применение скинов / Skin management',
  [('Три независимых слота коллекции.', 'Three independent collection slots.'),
   ('Перенос личных скинов на время сессии и восстановление после завершения; прогресс переноса.',
    'Temporary personal-skin backup and restoration after sessions, with transfer progress.'),
   ('Хранение личных скинов в Skins во время сессии по умолчанию выключено.',
    'Keeping personal skins in Skins during sessions is off by default.'),
   ('Для обновления награды в игре используется постоянный скин «! osu!gacha — Текущий скин» и '
    'Ctrl+Shift+Alt+S.',
    'Reward updates use the permanent “! osu!gacha — Текущий скин” skin and Ctrl+Shift+Alt+S.'),
   ('Подсказка объясняет, какой текущий скин нужно выбрать в osu!.',
    'An in-app hint explains which current skin to select in osu!.'),
   ('Настройка «Не менять текущий скин»: награды сохраняются, ручное применение остаётся доступным.',
    'Keep-current-skin setting saves rewards without automatic replacement; manual Apply stays available.'),
   ('Избранные скины можно скопировать в личную папку игры.',
    'Favorite skins can be copied to the personal game folder.'),
   ('Кнопка тестирования скина убрана.', 'Removed the skin test button.')]),
 ('Ранее · Скоры и статистика / Scores and statistics',
  [('Карточки скоров показывают игровой ранг, ранг награды, PP, моды и звёзды.',
    'Score cards show play grade, reward tier, PP, mods and stars.'),
   ('Комбо, точность, миссы, 100 и 50 можно настраивать; недоступный UR убран.',
    'Combo, accuracy, misses, 100s and 50s have display options; unavailable UR removed.'),
   ('Подписи переведены без двойных названий; «Точность» и «Комбо:».',
    'Localized labels avoid bilingual duplicates; consistent accuracy and combo labels.'),
   ('Компактная компоновка карточек и ссылки на доступные скоры osu!.',
    'Compact score-card layout and links to available osu! scores.'),
   ('Лучшие скоры за всё время: сортировка по PP и комбо, ранги, поиск и скрытие провалов.',
    'All-time best scores: PP/combo sorting, grades, search and failed-score filtering.'),
   ('Скрытие ранга F на главном экране рядом с выбором сессии; устаревшие кнопки листания скоров убраны.',
    'Main-screen F filter beside session selection; obsolete score navigation buttons removed.'),
   ('Сохранение и выбор сессий; технические суффиксы скрыты, поиск появляется после десяти сессий.',
    'Saved session selection; technical suffixes hidden; search appears after ten sessions.'),
   ('Сравнение с прошлой попыткой на той же сложности: комбо, точность и миссы.',
    'Comparison with the previous attempt on the same difficulty: combo, accuracy and misses.'),
   ('График и таблица прогресса по датам; выбор показателя и периода.',
    'Daily progress chart and table with metric and date-range selection.'),
   ('Сглаженная линия графика, шкала по реальным значениям и изменения к предыдущему игровому дню.',
    'Smooth chart line, data-based axis range and changes from the previous playing day.'),
   ('Нажатие на день или точку графика открывает скоры дня.',
    'Click a day or chart point to open that day’s scores.'),
   ('Итоги сессии: длительность, скоры, лучший результат с обложкой, прирост PP, превью наград и ранги.',
    'Session summary: duration, scores, best play with cover, profile PP change, reward previews and tiers.'),
   ('Автоматическое окно итогов можно выключить, сохранив ручной доступ.',
    'Automatic summaries can be disabled while remaining available manually.')]),
 ('Ранее · Настройки и оформление / Settings and appearance',
  [('Общая тема оформления, новая иконка, улучшенные состояния кнопок при наведении и читаемый текст.',
    'Consistent theming, new icon and more readable button hover states.'),
   ('Настройки стали шире и распределены по категориям; подсказки находятся внутри соответствующего пункта.',
    'Wider categorized settings; each hint stays with its own setting.'),
   ('Поиск по настройкам на выбранном языке.', 'Settings search in the selected language.'),
   ('Переведены кнопки выбора файлов, источников скинов и сброса; источник Drive назван Google Drive.',
    'Localized file/source/reset controls; Drive source renamed Google Drive.'),
   ('Убраны лишние настройки папки Drive, акцентного цвета, плавности и показа карточек; плавность и '
    'карточки включены.',
    'Removed redundant Drive-folder, accent, motion and card-visibility controls; smooth UI and score cards '
    'remain enabled.'),
   ('Поля источника показываются по необходимости, в зависимости от папок, ZIP или Google Drive.',
    'Source fields appear as needed for folders, ZIP or Google Drive.'),
   ('Интервал API от одной секунды с учётом ограничений частоты; интервал и шанс задаются целыми числами.',
    'API interval starts at one second subject to request pacing; interval and chance use whole numbers.'),
   ('Вставка Ctrl+V во всех полях, включая русскую раскладку; лишняя кнопка вставки убрана.',
    'Ctrl+V across input fields, including Cyrillic layouts; redundant Paste button removed.'),
   ('Масштаб интерфейса для разных размеров экрана.', 'Interface scaling for different screen sizes.'),
   ('Главное окно увеличено по высоте, основные действия собраны в одну строку.',
    'Taller main window with primary actions arranged in one row.'),
   ('Дочерние окна открываются над вызвавшим их окном, остаются независимыми и доступны на панели задач.',
    'Child windows open above their originating window, remain independent and appear on the taskbar.'),
   ('Кнопка «Избранное» переименована в «Скины»; названия отзывов приведены к выбранному языку.',
    'Favorites renamed Skins; feedback labels follow the selected language.'),
   ('Первичная настройка переработана в дружелюбный мастер в стиле приложения.',
    'First-time setup redesigned as a friendly, consistently styled wizard.')]),
 ('Ранее · Профили и запуск / Profiles and startup',
  [('Поддержка Bancho и Gatari; ID сохраняются отдельно для каждого сервера.',
    'Bancho and Gatari support; separate saved user IDs per server.'),
   ('Ускоренная загрузка и кэширование профиля и аватарки.', 'Faster profile/avatar loading and caching.'),
   ('Некорректные ссылки на скоры Gatari, ведущие только в профиль, убраны.',
    'Removed Gatari score links that only opened the profile.'),
   ('Запуск выбранного драйвера графического планшета вместе с сессией и сворачивание его окна.',
    'Launch a chosen tablet driver with a session and minimize its window.'),
   ('Запуск самой osu! вместе с сессией; обе функции отключаемые.',
    'Optional osu! autostart with sessions; both launch options can be disabled.'),
   ('Для Gatari добавлен отключаемый аргумент -devserver osugatari.ru.',
    'Optional -devserver osugatari.ru launch argument for Gatari.'),
   ('Экспорт и импорт настроек, истории и коллекций; API-ключ по умолчанию исключён.',
    'Export/import settings, history and collections; API key excluded by default.'),
   ('Установка Python с Tcl/Tk и зависимостей через запуск программы; исправлена ситуация WinGet «обновлений '
    'нет».',
    'Launcher installs Python with Tcl/Tk and dependencies; fixed WinGet’s no-upgrade case.'),
   ('Проверка и восстановление окружения после переноса; инструкции на русском и английском.',
    'Environment checks and repair after moving; Russian and English instructions.'),
   ('Текущий выпуск и распространяемый архив переименованы в beta4.',
    'Current release and distribution archive renamed beta4.')]),
 ('Ранее · Превью и обратная связь / Preview tool and feedback',
  [('Отдельная программа skin_preview_tool для генерации превью скинов.',
    'Standalone skin_preview_tool for generating skin previews.'),
   ('Единый игровой паттерн с кругами, цветами скина и интерфейсом; работа с отдельным скином и папкой.',
    'Consistent gameplay pattern with skin circles, colors and HUD; single-skin and folder input.'),
   ('Сохранение превью с именами скинов и распределением по папкам рангов; компактные PNG/JPG.',
    'Previews preserve skin names and rank folders; compact PNG/JPG output.'),
   ('Локальная обработка с ручной отправкой готовых превью на Google Drive.',
    'Local processing with manual upload of finished previews to Google Drive.'),
   ('Дизайн генератора приведён к osu!gacha, исправлена читаемость кнопок.',
    'Preview-tool styling matches osu!gacha; button readability improved.'),
   ('Выбор папки результата начинается с пути, уже указанного в поле.',
    'Output-folder selection starts from the path already entered.'),
   ('Доработана обработка проблемных изображений скинов, включая clearblack.osk.',
    'Improved handling of problematic skin images, including clearblack.osk.'),
   ('В настройках добавлена команда: DimEl, дизайнер anastasena, плейтестеры naru и scoleopa, аватарки и '
    'ссылки на osu!-профили.',
    'Settings include the team: DimEl, designer anastasena, playtesters naru and scoleopa, with avatars and '
    'osu! profile links.'),
   ('Отзывы и сообщения об ошибках через GitHub; прикрепление логов и скрытие API-ключей.',
    'GitHub feedback and bug reports, log attachments and API-key redaction.'),
   ('Длинные логи сворачиваются на GitHub и в окне отзывов.',
    'Long logs collapse on GitHub and in the feedback window.')])]


def words(app,ru,en):return en if app.settings['language']=='English' else ru


def open_changelog(app):
    win=IconWindow(app);win.title(app.t('changelog'));win.geometry('720x620');win.configure(fg_color=app.theme['bg'])
    body=FastScrollableFrame(win,fg_color=app.theme['bg']);body.pack(fill='both',expand=True,padx=18,pady=18)
    app.label(body,app.t('changelog'),size=25,bold=True).pack(anchor='w',pady=(0,14))
    app.label(body,words(app,'История по переписке. Ранние изменения собраны по разделам; текущие правила заменяют прежние.','Conversation history grouped by topic; current rules supersede earlier versions.'),muted=True,wraplength=610,justify='left').pack(anchor='w',pady=(0,12))
    for index,(version,entries) in enumerate(CHANGELOG):
        card=app.panel(body);card.pack(fill='x',pady=8)
        details=ctk.CTkFrame(card,fg_color='transparent')
        version=version.split(' / ')[0] if app.settings['language']!='English' else version.split(' / ')[-1]
        header=app.button(card,f"{'▾' if index==0 else '▸'} {version} · {len(entries)}",lambda:None,True)
        header.pack(fill='x',padx=8,pady=8)
        for ru,en in entries:app.label(details,'• '+words(app,ru,en),wraplength=585,justify='left',anchor='w').pack(fill='x',padx=16,pady=(0,12))
        def toggle(d=details,h=header,v=version,n=len(entries)):
            opened=bool(d.winfo_manager())
            if opened:d.pack_forget()
            else:d.pack(fill='x')
            h.configure(text=f"{'▸' if opened else '▾'} {v} · {n}")
        header.configure(command=toggle)
        if index==0:details.pack(fill='x')
    return win


def open_session_search(app):
    win=IconWindow(app);win.title(words(app,'Найти сессию','Find session'));win.geometry('620x570');win.configure(fg_color=app.theme['bg'])
    query=tk.StringVar()
    app.label(win,words(app,'Поиск по дате, времени и числу скоров','Search date, time or score count'),muted=True).pack(padx=20,pady=(16,6))
    entry=ctk.CTkEntry(win,textvariable=query,height=38);entry.pack(fill='x',padx=20,pady=8)
    body=FastScrollableFrame(win,fg_color=app.theme['bg']);body.pack(fill='both',expand=True,padx=14,pady=10)
    def choose(label):app.select_history(label);win.destroy()
    def refresh(*_):
        for child in body.winfo_children():child.destroy()
        found=[label for label in app.history_options if all(word in label.casefold() for word in query.get().casefold().split())]
        for label in found:app.button(body,label,lambda l=label:choose(l),True).pack(fill='x',pady=4)
        if not found:app.label(body,words(app,'Сессии не найдены','No sessions found'),muted=True).pack(pady=20)
        body._parent_canvas.yview_moveto(0)
    query.trace_add('write',refresh);refresh();entry.focus_set()
    return win


def animate_pp(app,gain):
    if gain<.01 or not app.pp_label.winfo_exists():return
    old=getattr(app,'pp_bubble',None)
    if old and old.winfo_exists():old.destroy()
    anchor=app.pp_label;parent=anchor.master
    bubble=app.label(parent,f'+{gain:.2f}'.rstrip('0').rstrip('.')+' PP',size=20,bold=True,fg_color=app.theme['card'],corner_radius=12)
    app.pp_bubble=bubble
    started=time.monotonic()
    def frame():
        if not bubble.winfo_exists():return
        progress=(time.monotonic()-started)/1.2
        if progress>=1:bubble.destroy();return
        bubble.place(x=anchor.winfo_x()+75,y=anchor.winfo_y()+22-50*progress)
        bubble.configure(text_color=blend(app.theme['accent'],app.theme['card'],max(0,(progress-.45)/.55)))
        bubble.lift();bubble.after(16,frame)
    frame()
