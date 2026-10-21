#!/bin/sh
set -eu

# Use the lab's installed modern Python; this app does not require Postgres.
PYTHON_BIN=${PYTHON_BIN:-python3}
VENV_DIR=${VENV_DIR:-.venv}
"$PYTHON_BIN" -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10 or newer is required"'
"$PYTHON_BIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --no-cache-dir -r requirements.txt
"$VENV_DIR/bin/python" manage.py migrate --noinput
"$VENV_DIR/bin/python" manage.py check
printf 'Setup complete. Activate with: . %s/bin/activate\n' "$VENV_DIR"
