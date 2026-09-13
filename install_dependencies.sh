#!/usr/bin/env bash

cd "$(dirname "$0")" || exit 1

./ensure_python.sh --install
read -r -p "Press Enter to continue..."
