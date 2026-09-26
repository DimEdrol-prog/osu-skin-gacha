# Как разрабатывать 

Соблюдать единую иерархию структуры проекта.

## Архитектура проекта
- main.py - все импорты.
- modules/ - весь код программы.
- assets/ - ресурсы.
- oauth_worker/ - настройки входа через osu! аккаунт.

## Сборка

На Linux (требуется python 3.12+, gnumake и Tkinter):
```bash
make build
```

На Windows (нужен python 3.12+):

Соберите программу:
```powershell
python -m pip install uv
uv sync
uv run pyinstaller --windowed --add-data "assets;assets" --onefile --name osu-gacha --collect-all customtkinter --collect-all pygame --collect-all rosu_pp_py --collect-all mutagen main.py
```

## Запуск

Linux:
```bash
./dist/skin-gacha
```

Windows:
```powershell
.\dist\skin-gacha
```

## Структура (может устаревать/быть не точной)
```
.
├── assets
│   ├── __init__.py
│   ├── drive_catalog.json
│   ├── gacha-logo.png
│   └── gacha.ico
├── docs
│   ├── ARCHITECTURE.md
│   └── DEVELOPMENT.md
├── flake.lock
├── flake.nix
├── main.py
├── Makefile
├── modules
│   ├── __init__.py
│   ├── gacha_api.py
│   ├── gacha_api_v2.py
│   ├── gacha_app.py
│   ├── gacha_audio.py
│   ├── gacha_bootstrap.py
│   ├── gacha_collection.py
│   ├── gacha_config.py
│   ├── gacha_connection.py
│   ├── gacha_driver.py
│   ├── gacha_insights.py
│   ├── gacha_oauth.py
│   ├── gacha_polish.py
│   ├── gacha_previews.py
│   ├── gacha_python_probe.py
│   ├── gacha_reports.py
│   ├── gacha_rules.py
│   ├── gacha_settings.py
│   ├── gacha_setup.py
│   ├── gacha_skin_apply.py
│   ├── gacha_skin_stats.py
│   ├── gacha_skin_variants.py
│   ├── gacha_skins.py
│   ├── gacha_sources.py
│   ├── gacha_storage.py
│   ├── gacha_team.py
│   ├── gacha_transfer.py
│   ├── gacha_updates.py
│   ├── gacha_widgets.py
│   ├── music_library.py
│   └── skin_gacha.py
├── oauth_worker
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── pnpm-workspace.yaml
│   ├── README.md
│   ├── src
│   │   └── worker.js
│   ├── test
│   │   └── worker.test.mjs
│   └── wrangler.jsonc
├── osu-gacha.spec
├── pyproject.toml
├── README.md
└── uv.lock
```
