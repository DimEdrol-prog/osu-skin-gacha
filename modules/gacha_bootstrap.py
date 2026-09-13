"""One-click setup and bounded automatic repair of the local environment."""
from pathlib import Path
import hashlib
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
ENV_PYTHON = ROOT / '.venv' / 'Scripts' / 'python.exe'
PROBE = 'import tkinter; import customtkinter; import requests; import PIL.Image; import bs4; import pygame.mixer; import rosu_pp_py; assert hasattr(rosu_pp_py, "Beatmap")'
RUNTIME_PROBE = 'import tkinter, venv; r=tkinter.Tk(); r.withdraw(); r.destroy()'


def say(ru, en):
    print(ru, flush=True)
    print(en, flush=True)


def clean_environment():
    env = os.environ.copy()
    for key in ('PYTHONPATH', 'PYTHONHOME', 'TCL_LIBRARY', 'TK_LIBRARY'):
        env.pop(key, None)
    env['PYTHONUTF8'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    return env


def probe(executable, code, env):
    try:
        return subprocess.run([str(executable), '-E', '-c', code], cwd=ROOT, env=env,
                              capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def command(args, env):
    subprocess.run([str(a) for a in args], cwd=ROOT, env=env, check=True)


def main():
    env = clean_environment()
    install_only = '--install' in sys.argv
    base = Path(getattr(sys, '_base_executable', sys.executable))
    runtime_good = ENV_PYTHON.exists() and probe(ENV_PYTHON, RUNTIME_PROBE, env)
    if not runtime_good:
        if not probe(base, RUNTIME_PROBE, env):
            say('Python не может открыть интерфейс Tcl/Tk. Повторите run_skin_gacha.cmd.',
                'Python cannot open the Tcl/Tk interface. Run run_skin_gacha.cmd again.')
            return 1
        folder = ROOT / '.venv'
        if folder.exists():
            # Retain the old environment; never touch user settings, history or skins.
            if folder.is_symlink() or folder.resolve().parent != ROOT.resolve():
                raise ValueError('Unexpected .venv location')
            backup = ROOT / ('.venv-backup-' + str(time.time_ns()))
            folder.rename(backup)
            say('Сохранил старое окружение. Создаю рабочее окружение для этого компьютера.',
                'Old environment retained. Creating a working environment for this computer.')
        else:
            say('Первый запуск: подготавливаю библиотеки. Пожалуйста, подождите.',
                'First launch: preparing dependencies. Please wait.')
        command([base, '-E', '-m', 'venv', folder], env)
    requirements = ROOT / 'requirements.txt'
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    stamp = ROOT / '.venv' / '.gacha-requirements'
    unchanged = stamp.exists() and stamp.read_text(encoding='utf-8') == digest
    dependencies_good = probe(ENV_PYTHON, PROBE, env)
    if install_only or not unchanged or not dependencies_good:
        say('Устанавливаю или восстанавливаю библиотеки. Нужен интернет.',
            'Installing or repairing dependencies. Internet is required.')
        command([ENV_PYTHON, '-E', '-m', 'ensurepip', '--upgrade'], env)
        command([ENV_PYTHON, '-E', '-m', 'pip', 'install', '--upgrade', '--disable-pip-version-check', 'pip'], env)
        args = [ENV_PYTHON, '-E', '-m', 'pip', 'install', '--upgrade', '--prefer-binary', '--disable-pip-version-check']
        if not dependencies_good: args += ['--force-reinstall']
        command([*args, '-r', requirements], env)
        if not probe(ENV_PYTHON, PROBE, env):
            say('Проверка библиотек не прошла. Сохраните текст ошибки и сообщите разработчику.',
                'Dependency validation failed. Save the error text and report it to the developer.')
            return 1
        stamp.write_text(digest, encoding='utf-8')
    if install_only:
        say('Готово! Теперь запустите run_skin_gacha.cmd.', 'Ready! Start run_skin_gacha.cmd.')
        return 0
    say('Запускаю osu!gacha…', 'Starting osu!gacha…')
    return subprocess.call([str(ENV_PYTHON), '-E', str(ROOT / 'skin_gacha.py')], cwd=ROOT, env=env)


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(error)
        say('Не удалось закончить запуск. Проверьте интернет и повторите run_skin_gacha.cmd. Инструкция: HOW_TO_RUN.txt.',
            'Startup could not finish. Check your connection and retry run_skin_gacha.cmd. Instructions: HOW_TO_RUN.txt.')
        raise SystemExit(1)
