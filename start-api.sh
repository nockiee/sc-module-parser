#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT_DIR"

PYTHON=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON="python"
fi

if [ -z "$PYTHON" ]; then
    echo "Python was not found in PATH."
    exit 1
fi

if ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
    echo "pip is not available. Trying to bootstrap it..."
    "$PYTHON" -m ensurepip --upgrade
fi

if [ -f requirements.txt ]; then
    echo "Installing dependencies from requirements.txt..."
    "$PYTHON" -m pip install -r requirements.txt
fi

exec "$PYTHON" use_api.py "$@"
