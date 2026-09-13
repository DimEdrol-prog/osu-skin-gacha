"""osu! Skin Gacha: gacha_config."""
from __future__ import annotations
from pathlib import Path
from modules.gacha_sources import DRIVE_FOLDER

BASE = Path(__file__).resolve().parent


DEV_API_KEY_HASH = 'e12fc0e9321297016fde9d93322b58eca741ddb34deeda17322ac6b7c23bfd6e'


RANKS = ("SS", "S", "A", "B", "C", "D")


COMBO = dict(zip(RANKS, (1500, 1000, 750, 500, 350, 250)))


TOP = dict(zip(RANKS, (3, 10, 25, 50, 80, 100)))


RANK_COLORS = dict(zip((*RANKS, "F", "X", "XH", "SH"),
    ("#efb8ff", "#f6cf77", "#95dca2", "#83c9ff", "#baa4fb", "#ffab93", "#a1a7b8", "#f6cf77", "#d4eaff", "#d4eaff")))


_PALETTES = [
    ("Dark Classic", "osu! / Розовый вечер", "osu! / Pink dusk", "#181319 #251e29 #302534 #f8edf4 #bfacbd #f28cbd #a5b8fc", "none", 18),
    ("Discord", "Discord / Общая комната", "Discord / Lounge", "#15161c #202129 #2b2d38 #f2f3fa #b4b8cd #9ca6ff #78d9ba", "none", 12),
    ("Steam", "Steam / Библиотека", "Steam / Library", "#101923 #182838 #22394c #e5f3fc #abc4d6 #79caff #a9d978", "rain", 6),
    ("Twitch", "Twitch / Прямой эфир", "Twitch / Live", "#100e16 #1b1726 #2a2238 #f5eeff #c1aed8 #bc96ff #79e6c1", "none", 10),
    ("Reddit", "Reddit / Лента", "Reddit / Feed", "#0e1517 #192326 #253438 #f2f6f6 #aec4c6 #ffad86 #86cbd3", "none", 22),
    ("Tokyo Night", "Токийская ночь", "Tokyo Night", "#141622 #1c2033 #282e46 #e3e9ff #a8b4d5 #9ebaff #d6a9fc", "rain", 14),
    ("Dracula", "Дракула / Полночь", "Dracula / Midnight", "#20212c #2b2d3c #393c50 #f8f8f2 #bebdd4 #c7a8fc #ff9ed3", "none", 16),
    ("Cyberpunk", "Киберпанк / Неон", "Cyberpunk / Neon", "#100e22 #201735 #302348 #f5edff #c4b3d5 #76f7df #fca1ee", "rain", 2),
    ("Leaves in Wind", "Лес / Листья на ветру", "Forest / Windfall", "#101d19 #1b2e27 #2b4033 #eef7e8 #b0c9b3 #b7dd92 #efc68d", "leaves", 24),
    ("Snowfall", "Снег / Полярная станция", "Snow / Polar station", "#13212d #203342 #2c4558 #f0f9ff #b8d0df #b7e8fa #c6b9f2", "snow", 20),
    ("Rainy Day", "Дождь / За стеклом", "Rain / Window", "#172129 #23333e #314753 #eef6fa #b6cbd6 #9ed4e6 #e0c3a3", "rain", 16),
    ("Nord", "Норд / Северное сияние", "Nord / Aurora", "#242c38 #303b4a #404d60 #edf2f8 #bac8d9 #a2dce3 #c9add0", "snow", 12),
    ("Solarized Dark", "Солярис / Тёмная", "Solarized / Dark", "#00252e #073842 #124952 #e5efdd #adc7bc #f2c66d #80d1c9", "none", 8),
    ("Ember", "Угли / Тёплый свет", "Ember / Warm glow", "#241710 #35241c #493328 #fff0dd #d8b9a2 #ffc18a #e9a3a3", "leaves", 14),
    ("Vampire", "Вампир / Бархат", "Vampire / Velvet", "#1d111b #301c2a #462737 #ffeff4 #d4adbe #f69aaa #dbc188", "none", 4),
    ("Sakura", "Сакура / Весна", "Sakura / Spring", "#faf1f3 #fffafd #eedfe7 #402738 #745667 #a53469 #60509c", "leaves", 24),
    ("Paper", "Бумага / Светлая", "Paper / Light", "#f2f0e9 #fffdf7 #e8e5da #252c30 #596367 #226c77 #875328", "none", 8),
    ("Ocean", "Океан / Глубина", "Ocean / Abyss", "#081e29 #10313e #194454 #e5fbfc #a0cdd3 #82e3d0 #b7b5ff", "rain", 26),
]


THEMES = {k: dict(zip(("bg", "panel", "card", "text", "muted", "accent", "secondary"), colors.split()),
    ru=ru, en=en, anim=anim, radius=radius) for k, ru, en, colors, anim, radius in _PALETTES}


COLORS = {"theme": ("Из темы", "Theme", None), "pink": ("Розовый", "Pink", "#f28cbd"),
          "blue": ("Голубой", "Blue", "#83c9ff"), "green": ("Зелёный", "Green", "#95dca2"),
          "purple": ("Фиолетовый", "Purple", "#c7a8fc"), "gold": ("Золотой", "Gold", "#f6cf77")}


DEFAULTS = dict(api_key="", user_id="", osu_path=r"E:\osu!", skin_pack_path=str(BASE),
    osu_launch_enabled=False, tablet_driver_enabled=False, tablet_driver_path="", interval=15, custom_special_chance=False, rofl_chance=5, rofl_pp=0.1, language="Русский", theme="Dark Classic",
    difficulty="Hard", log_mode=True, animations=True, color="theme", dt_bonus=True, hide_failed=False,
    exclude_heavy=False, optimize_skins=False, interface_skin='', ignore_proxy=False,
    skin_source='drive', skin_archive='', drive_folder='https://drive.google.com/drive/folders/'+DRIVE_FOLDER,
    slot='1', offline=False, offline_username='', offline_total_pp=0, server='bancho',
    setup_complete=False, ui_motion=True, roulette_motion=True, keep_personal=False)

DEFAULTS.update(keep_current_skin=False, ui_scale="100%", custom_rewards=False, show_100=True, show_50=True,
                show_combo=True, show_accuracy=True, show_misses=True)
for rank in RANKS:
    DEFAULTS['goal_Hard_'+rank] = TOP[rank]
    DEFAULTS['goal_Fun_'+rank] = COMBO[rank]
    DEFAULTS['goal_Medium_'+rank] = max(0,397-RANKS.index(rank)*50)
DEFAULTS['goal_stars'] = 5.0


TEXT = {
    'sort_pp': ('По PP', 'By PP'),
    'sort_combo': ('По комбо', 'By combo'),
    'hard_dt_goal': ('DT     топ-50 с DT/NC', 'DT     top 50 with DT/NC'),
    'reset_confirm': ('Удалить выигранные скины во всех трёх слотах? Личные скины и экспортированные копии сохранятся.', 'Delete unlocked skins in all three slots? Personal skins and exported copies will remain.'),

    'browse': ('Выбрать папку / файл', 'Browse'),
    'skin_source': ('Источник скинов', 'Skin source'),
    'drive_folder': ('Папка Google Drive', 'Google Drive folder'),
    'drive': ('Google Drive', 'Google Drive'),
    'folder': ('Локальная папка', 'Local folder'),
    'zip': ('ZIP-архив', 'ZIP archive'),
    'reset_skins': ('Очистить выигранные скины', 'Reset unlocked skins'),
    'custom_rewards': ('Изменить параметры получения наград', 'Customize reward requirements'),
    'show_100': ('Показывать попадания 100', 'Show 100 hits'),
    'show_50': ('Показывать попадания 50', 'Show 50 hits'),
    'show_combo': ('Показывать комбо', 'Show combo'),
    'show_accuracy': ('Показывать точность', 'Show accuracy'),
    'show_misses': ('Показывать миссы', 'Show misses'),

    "applying_skin": ("Передаю новый скин в osu!…", "Importing the new skin into osu!…"),
    "skin_imported": ("Текущий скин готов — нажми Ctrl+Shift+Alt+S в osu! Для автосмены выбери скин «! osu!gacha — Текущий скин».", "Live skin ready — press Ctrl+Shift+Alt+S in osu!"),
    "repeat_map": ("Награда за эту сложность уже получена", "This difficulty already gave a reward"),
    "slot": ("Слот прогресса", "Progress slot"),
    "slot_label": ("Слот {n}", "Slot {n}"),
    "reports": ("Отзывы", "Reports"),
    "best_hide_failed": ("Убрать сфейленные скоры", "Hide failed scores"),
    "best_show_failed": ("Показать сфейленные скоры", "Show failed scores"),
    'coexist_hint': ('Личные скины остаются в игре. Скины программы уберутся после сессии.', 'Personal skins stay in game. Session skins are removed after playing.'),
    'keep_personal': ('Оставлять личные скины в игре', 'Keep personal skins in game'),
    'cancel_start': ('Прервать', 'Cancel'),
    'can_play': ('Можете играть', 'Ready to play'),
    'tablet_driver_enabled': ('Запускать драйвер планшета с сессией', 'Start tablet driver with session'),
    'osu_launch_enabled': ('Запускать osu! с сессией', 'Start osu! with session'),
    'custom_special_chance': ('Изменить шанс', 'Change chance'),
    'tablet_driver_path': ('Программа драйвера графического планшета (.exe)', 'Graphics tablet driver application (.exe)'),
    'restore_progress': ('Возвращено личных скинов: {done}/{total}', 'Personal skins restored: {done}/{total}'),
    'backup_progress': ('Перенесено в бэкап: {done}/{total}', 'Moved to backup: {done}/{total}'),
    'report_bug': ('Сообщить об ошибке', 'Report a bug'),

    'ui_motion': ('Плавные карточки и прогресс', 'Smooth cards and progress'),
    'roulette_motion': ('Анимация рулетки', 'Roulette animation'),
    'setup': ('Первичная настройка', 'First-run setup'),
    'misses': ('Миссы', 'Misses'),
    'copy_logs': ('Копировать все логи', 'Copy all logs'),
    'copied': ('Скопировано', 'Copied'),
    "settings": ("Настройки", "Settings"), "start": ("Начать сессию", "Start session"),
    "stop": ("Завершить сессию", "End session"), "busy": ("Подождите…", "Please wait…"),
    "ready": ("Всё начинается с default.", "It all starts with default."),
    "intro": ("Играй. Превзойди себя. Открой новый скин.", "Play. Push your limits. Unlock a new skin."),
    "waiting": ("Следующий скин — за следующим достижением", "Your next achievement unlocks a new look"),
    "scores": ("Скоры за сессию", "Session scores"), "empty": ("Здесь появится твой первый скор", "Your first score will appear here"),
    "hint": ("Личные скины вернутся после завершения сессии.", "Your personal skins return when the session ends."),
    "account": ("Профиль", "Profile"), "api_key": ("API-ключ osu! v1", "osu! v1 API key"),
    "user_id": ("osu! ID", "osu! ID"), "paste": ("Вставить", "Paste"), "show": ("Показать", "Show"),
    "paths": ("Папки", "Folders"), "osu_path": ("Папка osu! (содержит Skins и Songs)", "osu! folder (contains Skins and Songs)"),
    "skin_pack_path": ("Папка набора скинов", "Skin pack folder"), "language": ("Язык", "Language"),
    "theme": ("Тема", "Theme"), "color": ("Акцентный цвет", "Accent color"),
    "animations": ("Фоновые анимации", "Background animations"), "difficulty": ("Сложность", "Difficulty"),
    "Hard": ("Сложная", "Hard"), "Medium": ("Средняя", "Medium"), "Fun": ("Фан", "Fun"),
    "interval": ("Интервал API, секунды (1–300)", "API interval, seconds (1–300)"),
    "rofl_chance": ("Шанс особого скина, % (0–100)", "Special skin chance, % (0–100)"),
    "rofl_pp": ("Минимальная прибавка PP для особого скина", "Minimum PP gain for a special skin"),
    "log_mode": ("Показывать карточки скоров", "Show score cards"), "dt_bonus": ("Бонус DT в сложном режиме и Фане", "DT bonus in Hard and Fun"),
    "save": ("Сохранить", "Save"), "cancel": ("Отмена", "Cancel"), "error": ("Ошибка", "Error"),
    "credentials": ("Укажи API-ключ и числовой osu! ID в настройках.", "Enter an API key and numeric osu! ID in Settings."),
    "invalid": ("Проверь числовые значения и пути.", "Check numeric values and folder paths."),
    "clipboard": ("В буфере нет текста.", "Clipboard contains no text."),
    "monitoring": ("Мониторинг активен", "Monitoring active"), "restored": ("Личные скины возвращены", "Personal skins restored"),
    "recover": ("Восстановить скины", "Recover skins"), "recovery": ("Найдена незавершённая сессия. Сначала восстанови скины.", "An unfinished session was found. Recover skins first."),
    "test": ("Тест скина", "Test skin"), "logs": ("Логи", "Logs"), "reward": ("Награда", "Reward"),
    "won": ("Открыт скин", "Skin unlocked"), "installed": ("Обнови скины в osu!: Ctrl+Alt+Shift+S", "Refresh skins in osu!: Ctrl+Alt+Shift+S"),
    "no_skin": ("В этой категории нет скинов", "No skins in this category"),
    "cover": ("Нет фона", "No cover"), "combo": ("Комбо", "Combo"), "acc": ("Точность", "Accuracy"),
    "pool": ("В коллекции", "In the pool"), "unlocks": ("Открыто за сессию", "Session unlocks"),
    "rules": ("Твои цели", "Your targets"), "total": ("Общий PP", "Total PP"),
    "next": ("До ранга {rank}: {value}", "To rank {rank}: {value}"), "maximum": ("Максимальный ранг достигнут", "Highest rank reached"),
    "unknown_pp": ("PP недоступен для этого скора", "PP unavailable for this score"),
    "stars": ("Порог карты", "Map threshold"), "test_hint": ("Начни сессию для тестовой выдачи.", "Start a session to test a drop."),
    "api_error": ("API временно недоступен; повторная попытка автоматически.", "API unavailable; retrying automatically."),
    "older": ("Предыдущие скоры", "Older scores"), "newer": ("Новые скоры", "Newer scores"),
    "hide_failed": ("Скрывать скоры с рангом F", "Hide failed scores (F)"),
    "current_session": ("Текущая сессия", "Current session"),
    "close": ("Готово", "Done"),
    "live_settings": ("Изменения применяются и сохраняются автоматически", "Changes apply and save automatically"),
    "locked_settings": ("Профиль и папки можно менять после завершения сессии", "Profile and folders can be changed after the session"),
    "history_error": ("Не удалось сохранить историю", "Could not save session history"),
    "exclude_heavy": ("Убрать лагающие скины (больше 30 МБ)", "Exclude heavy skins (over 30 MB)"),
    "optimize_skins": ("Оптимизировать скины: геймплей + свой интерфейс", "Mix gameplay with my own interface"),
    "interface_skin": ("Личный скин для меню и HUD", "Personal skin for menus and HUD"),
    "ignore_proxy": ("Не использовать системный HTTP-прокси (VPN/TUN)", "Ignore system HTTP proxy (VPN/TUN)"),
    "collection": ("Избранное", "Favourites"),
    "favorite": ("В избранное", "Favourite"), "unfavorite": ("★ В избранном", "★ Favourite"),
    "export_skin": ("В личные скины", "Copy to personal skins"),
    "export_stop": ("Для копирования сначала завершите сессию", "End the session before copying"),
    "exported": ("Скин скопирован в личную папку Skins", "Skin copied to your personal Skins folder"),
    "exhausted": ("Скины ранка {rank} закончились", "No skins left in rank {rank}"),
    "filtered_pool": ("Ранк {rank}: оставшиеся скины больше 30 МБ", "Rank {rank}: remaining skins exceed 30 MB"),
    "best_scores": ("Лучшие за всё время", "All-time best"),
    "best_hint": ("Сохранённые сессии · сортировка по PP или максимальному комбо", "Saved sessions · sort by PP or maximum combo"),
    "score_link": ("Ссылка на скор", "Score link"),
    "score_missing": ("Ссылка на этот скор недоступна в API", "This score has no API link"),
    "fun_dt_goal": ("DT     750× с DT/NC", "DT     750× with DT/NC"),
    "no_base": ("Выберите личный скин для интерфейса", "Choose a personal interface skin"),
    "collection_empty": ("Здесь появятся выигранные скины", "Unlocked skins will appear here"),
}


def tr(key, language="Русский", **values):
    return TEXT.get(key, (key, key))[language == "English"].format(**values)


def blend(first, second, weight=.14):
    return '#' + ''.join(f'{round(int(first[i:i+2],16)*(1-weight)+int(second[i:i+2],16)*weight):02x}' for i in (1,3,5))



def is_developer(key):
    import hashlib
    return hashlib.sha256(str(key).encode()).hexdigest() == DEV_API_KEY_HASH

TEXT.update({
    'collection': ('Скины', 'Skins'),
    'keep_current_skin': ('Не менять текущий скин', 'Keep the current skin'),
    'ui_scale': ('Масштаб интерфейса', 'Interface scale'),
    'progress_view': ('Прогресс скоров', 'Score progress'),
    'summary': ('Итоги сессии', 'Session summary'),
})


DEFAULTS.update(show_session_summary=True, allow_skin_delete=False, gatari_launch=True)
TEXT.update({
    'show_session_summary': ('Показывать итоги после завершения сессии', 'Show summary when a session ends'),
    'allow_skin_delete': ('Разрешить удаление неизбранных скинов', 'Allow removing nonfavorite skins'),
    'gatari_launch': ('Запускать osu! с параметром сервера Gatari', 'Launch osu! with the Gatari server argument'),
    'changelog': ('Что нового', "What's new"),
    'repeat_map': ('Для новой награды нужен более высокий ранг', 'A higher reward rank is needed for another reward'),
})

TEXT['offline_top'] = ('Офлайн-профиль', 'Offline profile')
