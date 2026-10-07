# Engram: SOTA Second Brain Engine

Engram is an autonomous, zero-friction Second Brain engine bridging Evernote, macOS Edge Capture (Clipboard & Screenshots), and Google Workspace (Drive, Gmail, Calendar).

## Architecture Overview

1. macOS Edge Daemon (engram_clip.py & engram_screenshots.py)
   - Clipboard Hotkey: Press Opt + Space to capture, categorize, and route text, code, URLs, images, or files directly from RAM to Evernote.
   - Screenshot Watcher: Uses gpt-6-luna Decisions API to trash ephemeral junk (2FA codes, blank screens) and route valuable knowledge to Evernote.
   - Heavy File Router: Detects files >= 10MB, moves binary to Google Drive, and creates a clickable Index Card in Evernote.

2. In-Evernote Native AI Pack
   - Pinned AI Prompts: 1-click in-app chips to process voice transcriptions, generate meeting decision logs, and extract native Evernote Tasks.
   - Closed-World Taxonomy: Strict AI Memory rules prevent tag bloat - Engram only routes to existing notebooks and tags.

3. Gemini Cloud Brain (SKILL.md)
   - Batch Inbox Triage: Gemini sweeps default notebooks, rewrites Fwd: titles, and prepends Executive Briefs.
   - Federated Retrieval: Simultaneously queries Evernote Semantic Search and Google Workspace.

## Quickstart Setup

1. Virtual Environment & Dependencies:
   chmod +x install_macos.sh && ./install_macos.sh
   ~/.engram/venv/bin/pip install llm
   ~/.engram/venv/bin/llm install llm-openai-decisions

2. macOS Hotkey:
   Bind Option + Space in Raycast or Shortcuts to run:
   ~/.engram/venv/bin/python ~/.engram/scripts/engram_clip.py

3. Evernote Import:
   Add ~/Evernote_Imports to Evernote Desktop Settings -> Import Folders.

## Unit Tests
   ~/.engram/venv/bin/python -m unittest discover tests/
