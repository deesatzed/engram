#!/usr/bin/env bash
set -e
echo "🧠 Setting up Engram: SOTA Second Brain for macOS..."
mkdir -p "$HOME/Evernote_Imports/"{Work,EPIC,Home,Pics_DL,"PDF Notebook"}
mkdir -p "$HOME/Desktop/Screenshots/"{_Trash_Review,Organized}

if command -v uv &> /dev/null; then
    uv venv "$HOME/.engram/venv"
else
    python3 -m venv "$HOME/.engram/venv"
fi
echo "✅ Engram directories and virtual environment created!"
