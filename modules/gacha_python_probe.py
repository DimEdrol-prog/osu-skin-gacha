"""Probe in a file: PowerShell 5.1 can strip quotes in Python -c arguments."""
import struct
import sys


def main():
    if not (3, 10) <= sys.version_info[:2] < (3, 14) or struct.calcsize('P') != 8:
        return 1
    import tkinter
    import venv
    root = tkinter.Tk()
    root.withdraw()
    root.destroy()
    print(sys.executable)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
