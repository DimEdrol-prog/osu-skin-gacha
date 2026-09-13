Установите зависимости:

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

Перейдите в директорию с программой соберите:
```bash
make install
```

Запустите:
```bash
./dist/main
```