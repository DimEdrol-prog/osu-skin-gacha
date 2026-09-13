# osu!skingacha

osu!skingacha - это программа для выбора рандомного скина в osu!stable
# Скачивание
Windows:
- Скачайте [здесь](https://github.com/DimEdrol-prog/osu-skin-gacha/releases/latest) .exe файл и запустите

Linux дистрибутивы:
- Debian/Ubuntu:
  ```bash
  sudo apt update
  sudo apt install python3 python3-tk python3-pip make
  ```

- RHEL/Fedora:
  ```bash
  sudo dnf update
  sudo dnf install python3 python3-tkinter python3-pip make
  ```

- OpenSUSE:
  ```bash
  sudo zypper refresh
  sudo zypper install python3 python3-tk python3-pip make
  ```

- NixOS:
  ```bash
  nix develop # или nix-shell если без flakes
  ```

- Перейдите в директорию с программой соберите:
  ```bash
  make install
  ```

- Запустите:
  ```bash
  ./dist/main
  ```

- Либо скачайте [здесь](https://github.com/DimEdrol-prog/osu-skin-gacha/releases/latest) AppImage

# Структура файлов
```
.
├── assets
│   ├── gacha-logo.png
│   └── gacha.ico
├── docs
│   ├── ARCHITECTURE.md
│   ├── how_to_linux.md
│   └── HOW_TO_RUN.txt
├── drive_catalog.json
├── ensure_python.ps1
├── flake.lock
├── flake.nix
├── install_dependencies.cmd
├── install_dependencies.sh
├── main.py
├── Makefile
├── modules
│   ├── __pycache__
│   │   ├── gacha_api.cpython-313.pyc
│   │   ├── gacha_app.cpython-313.pyc
│   │   ├── gacha_config.cpython-313.pyc
│   │   ├── gacha_connection.cpython-313.pyc
│   │   ├── gacha_insights.cpython-313.pyc
│   │   ├── gacha_previews.cpython-313.pyc
│   │   ├── gacha_reports.cpython-313.pyc
│   │   ├── gacha_rules.cpython-313.pyc
│   │   ├── gacha_settings.cpython-313.pyc
│   │   ├── gacha_setup.cpython-313.pyc
│   │   ├── gacha_skin_apply.cpython-313.pyc
│   │   ├── gacha_skins.cpython-313.pyc
│   │   ├── gacha_sources.cpython-313.pyc
│   │   ├── gacha_storage.cpython-313.pyc
│   │   ├── gacha_updates.cpython-313.pyc
│   │   ├── gacha_widgets.cpython-313.pyc
│   │   └── skin_gacha.cpython-313.pyc
│   ├── gacha_api.py
│   ├── gacha_app.py
│   ├── gacha_audio.py
│   ├── gacha_bootstrap.py
│   ├── gacha_collection.py
│   ├── gacha_config.py
│   ├── gacha_connection.py
│   ├── gacha_driver.py
│   ├── gacha_insights.py
│   ├── gacha_previews.py
│   ├── gacha_python_probe.py
│   ├── gacha_reports.py
│   ├── gacha_rules.py
│   ├── gacha_settings.py
│   ├── gacha_setup.py
│   ├── gacha_skin_apply.py
│   ├── gacha_skins.py
│   ├── gacha_sources.py
│   ├── gacha_storage.py
│   ├── gacha_team.py
│   ├── gacha_transfer.py
│   ├── gacha_updates.py
│   ├── gacha_widgets.py
│   └── skin_gacha.py
├── README.md
├── requirements.txt
├── run_skin_gacha.cmd
├── run_skin_gacha.sh
└── shell.nix
```
