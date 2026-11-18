#!/bin/bash
set -eu
cd "$(dirname "$0")"
set -a
source .env
set +a
exec .venv/bin/python app.py
