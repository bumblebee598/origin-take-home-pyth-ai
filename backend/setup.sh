#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required to install Manim system dependencies."
  echo "Install Homebrew from https://brew.sh, then run this script again."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required. Install Python 3, then run this script again."
  exit 1
fi

echo "Installing system dependencies..."
brew install cairo pango pkg-config ffmpeg

echo "Creating Python virtual environment..."
python3 -m venv .venv

echo "Installing Python dependencies..."
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# The render agent loads this skill from the user-level Claude skills directory.
echo "Installing the manimce-best-practices skill for the Claude agent..."
SKILL_SRC=".agents/skills/manimce-best-practices"
SKILL_DEST="$HOME/.claude/skills/manimce-best-practices"
if [ -d "$SKILL_SRC" ]; then
  mkdir -p "$HOME/.claude/skills"
  rm -rf "$SKILL_DEST"
  cp -r "$SKILL_SRC" "$SKILL_DEST"
  echo "Skill installed at $SKILL_DEST"
else
  echo "Warning: $SKILL_SRC not found; rendering may fail without it."
fi

echo "Backend setup complete."
echo "To run the API:"
echo "  source .venv/bin/activate"
echo "  uvicorn main:app --reload"
