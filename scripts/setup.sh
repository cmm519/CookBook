#!/usr/bin/env bash
# Idempotent development setup for the CookBook project.
#
# Installs the system packages needed for a Python virtual environment and for
# media processing, then creates a local ``.venv`` and installs the project in
# editable mode with its dev dependencies. Safe to re-run.
set -euo pipefail

cd "$(dirname "$0")/.."

# --- System packages -------------------------------------------------------
# python3.12-venv is required to create virtual environments on Ubuntu; ffmpeg
# is used by the (optional) media-processing pipeline stages.
APT_PACKAGES=(python3.12-venv ffmpeg)

if command -v apt-get >/dev/null 2>&1; then
    if [ "$(id -u)" -eq 0 ]; then
        SUDO=""
    elif command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
    else
        SUDO=""
    fi
    $SUDO apt-get update -qq
    $SUDO apt-get install -y -qq "${APT_PACKAGES[@]}"
fi

# --- Python environment ----------------------------------------------------
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
. .venv/bin/activate
python -m pip install --quiet --upgrade pip
pip install --quiet -e ".[dev]"

echo "CookBook setup complete. Activate with: source .venv/bin/activate"
