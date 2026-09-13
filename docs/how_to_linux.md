# Все дистрибутивы
Установите зависимости:

- Debian/Ubuntu:
  ```bash
  sudo apt update
  sudo apt install python3 python3-tk python3-pip
  ```

- RHEL/Fedora:
  ```bash
  sudo dnf update
  sudo dnf install python3 python3-tkinter python3-pip
  ```

- OpenSUSE:
  ```bash
  sudo zypper install python3 python3-tk python3-pip
  ```

 - NixOS:
 ```bash
 nix develop # или nix-shell если без flakes
 ```

Перейдите в директорию с программой и установите остальные зависимости:
```bash
python3 -m pip install -r requirements.txt
```

Скомпилируйте программу:
```bash
python -m PyInstaller --onefile skin_gacha.py
```

Запустите:
```bash
./dist/skin_gacha
```