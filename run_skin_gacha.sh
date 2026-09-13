#!/usr/bin/env bash

cd "$(dirname "$0")" || exit 1

unset PYTHONPATH
unset PYTHONHOME
unset TCL_LIBRARY
unset TK_LIBRARY

GACHA_DEV="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python"

if [ -f ".runtime/customtkinter/__init__.py" ] && [ -f "$GACHA_DEV/bin/python3" ]; then
  export PYTHONPATH="$(pwd)/.runtime"
  export TCL_LIBRARY="$GACHA_DEV/lib/tcl8.6"
  export TK_LIBRARY="$GACHA_DEV/lib/tk8.6"

  "$GACHA_DEV/bin/python3" "$(pwd)/main.py"
  if [ $? -ne 0 ]; then
    read -r -p "Press Enter to continue..."
  fi
  exit 0
fi

./ensure_python.sh --run[cite: 1]
if [ $? -ne 0 ]; then
  read -r -p "Press Enter to continue..."
fi
