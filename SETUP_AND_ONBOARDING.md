# Engram Setup, Onboarding & Provisioning Manifest

## 1. Master Architecture (Option A — Single Master Stack)
- **Evernote Master Stack**: `EB_MAC_MiniM4`
- **Fallback / Triage Notebook**: `EB_2FileLater`
- **Action / Task Tracking**: Universal `Todo` tag applied in both **Evernote** and **macOS Finder Tags** (`kMDItemUserTags`).
  - Example query: *"List my ToDos for my work credentials"* → `notebook:EB_Work_Credentials tag:Todo` (or `stack:EB_MAC_MiniM4 tag:Todo` for all open tasks across the entire system).

---

## 2. Official `EB_` Notebooks & Categories (26 Total)
All notebooks below live inside the **`EB_MAC_MiniM4`** stack in Evernote. Local Google Drive (`GOOGbook/<Category>`) and Evernote import folders (`~/Evernote_Imports/<Category>`) are created **on-demand** only when a file is routed to them:
  - `EB_2FileLater`
  - `EB_Work_EPIC`
  - `EB_Work_EPIC_SQL`
  - `EB_Work_Credentials`
  - `EB_Work_Clinical`
  - `EB_Work_Informatics`
  - `EB_Work_Academic`
  - `EB_Work_Admin`
  - `EB_Home_Finance`
  - `EB_Home_Property`
  - `EB_Home_Vehicles`
  - `EB_Home_Health`
  - `EB_Home_Purchases`
  - `EB_Home_Lifestyle`
  - `EB_Moms_Trust`
  - `EB_Moms_Info`
  - `EB_SWE_AI`
  - `EB_SWE_Repos`
  - `EB_SWE_DevOps`
  - `EB_SWE_Projects`
  - `EB_SWE_Data`
  - `EB_Jobs_Opportunities`
  - `EB_Jobs_Applications`
  - `EB_Jobs_Network`
  - `EB_Proj_Book_WWII`
  - `EB_Proj_Research`

---

## 3. How Images & Comments Land in Evernote Natively (Important!)
- **Never run `open -a Evernote file.enex` from the command line**: Evernote v10+ treats CLI-opened `.enex` files as raw file attachments inside the default notebook (`wsatz's notebook`).
- **Native Visual Image Import**:
  1. Open **Evernote → Settings (⚙️) → Import Folders**.
  2. Link each active subfolder in `/Users/o2satz/Evernote_Imports/<EB_Category>` to its matching `EB_` notebook in `EB_MAC_MiniM4`:
     - `/Users/o2satz/Evernote_Imports/EB_Work_EPIC` → `EB_Work_EPIC`
     - `/Users/o2satz/Evernote_Imports/EB_Work_Credentials` → `EB_Work_Credentials`
     - `/Users/o2satz/Evernote_Imports/EB_SWE_DevOps` → `EB_SWE_DevOps`
     - `/Users/o2satz/Evernote_Imports/EB_SWE_Repos` → `EB_SWE_Repos`
  3. As soon as a folder is linked in Evernote Settings, Evernote automatically ingests the `.png`/`.jpeg` files inside it and renders them as **full visual image notes** titled with their `6A07-XY_Keywords` filename.

---

## 4. Shottr Capture & 24-Hour C&P Hold Workflow
1. **Shottr Settings**:
   - Save Folder: `/Volumes/WS4TB/File_Cab/SS/SS_Oct26`
   - Post-capture actions: **Show**, **Copy**, **Save** all checked.
2. **Throwaway C&P Screenshots (1 file)**:
   - Take screenshot (`Cmd+Shift+7`), paste from clipboard, close preview.
   - Sits untouched in `SS_Oct26` for **24 hours** for reuse, then moves to `/Volumes/WS4TB/File_Cab/SS/_Trash_24h`.
3. **Keep & File Screenshots (`-2.png` trigger)**:
   - Click **Save** (`Cmd+S`) in Shottr preview to create the `-2` duplicate.
   - Engram processes the original with Vision AI, preserves any manual Finder Comment as Gold Truth, writes the combined description into `kMDItemFinderComment` + `_Engram_Index.md`, copies the renamed file to `GOOGbook/<EB_Category>` and `~/Evernote_Imports/<EB_Category>`, and deletes the `-2` trigger clone immediately.

---

## 5. Evernote "Sync folders" & Background Daemon (Verified Working)
1. **Evernote UI Path**: Open **Evernote → Settings → Sync folders → `+ Connect a folder`**.
   - Map each active `/Users/o2satz/Evernote_Imports/EB_<Category>` folder to its matching `EB_<Category>` notebook inside the `EB_MAC_MiniM4` stack.
   - *New Category Alert*: Whenever a new `EB_` category folder is created on-demand for the first time, connect it once in **Evernote → Settings → Sync folders**.
2. **Background Watcher (`launchd`)**:
   - Agent file: `~/Library/LaunchAgents/com.engram.shottr.plist`
   - Watches `/Volumes/WS4TB/File_Cab/SS/SS_Oct26` via `WatchPaths` (triggers immediately when Shottr saves a `-2` file) and runs hourly (`StartInterval: 3600`) to sweep singular C&P files older than 24 hours into `_Trash_24h`.
   - Logs output to `~/.engram/logs/launchd_stdout.log` and `~/.engram/logs/engram_audit.jsonl`.

---

## 6. First-Time Evernote "Sync folders" Reminder System
- **How It Works**: Engram tracks which `EB_` categories have already been linked in **Evernote → Settings → Sync folders** inside `~/.engram/synced_evernote_folders.json`.
- **When a New Folder Is Created On-Demand**: The very first time Engram routes a screenshot into a new `~/Evernote_Imports/EB_<Category>` folder, macOS pops up a 1-time dialog:
  1. Open **Evernote → Settings (⚙️) → Sync folders → `+ Connect a folder`**.
  2. Pick `/Users/o2satz/Evernote_Imports/EB_<Category>` and link it to the matching `EB_<Category>` notebook (inside stack `EB_MAC_MiniM4`).
  3. Click **"Mark Connected"** in the popup so it never asks again for that folder.

---

## 7. Complete Search & Retrieval Guide (Evernote, Gemini, Spotlight & Engram App)

### A. Searching Directly Inside the Evernote App
Use Evernote's search bar (`Cmd+K` or `Cmd+Opt+F`) with these exact operators:
1. **Search All Engram Notebooks Only (Ignore Legacy Notebooks)**:
   - `stack:EB_MAC_MiniM4 <your keywords>`
2. **List Open ToDos for a Specific Category**:
   - `notebook:EB_Work_Credentials tag:Todo`
   - `notebook:EB_SWE_DevOps tag:Todo`
3. **List ALL Open ToDos Across Your Entire Engram Brain**:
   - `stack:EB_MAC_MiniM4 tag:Todo`
4. **Search by Date or Facet Code in the Title**:
   - All October 2026 captures (`6A` = 2026 Oct): `intitle:6A`
   - All Oct 7, 2026 captures: `intitle:6A07`
   - All Reference Licenses (`-RL_`) or Reference Documents (`-RD_`): `intitle:RL` or `intitle:RD`
   - All Project/Code captures (`-PC_` / `-RT_`): `intitle:PC` or `intitle:RT`
5. **Search Inside Screenshot Images (Evernote OCR)**:
   - Just type any word visible inside the screenshot (e.g., `RESTRNOTELIST` or `MD053705L`). Evernote automatically indexes text inside imported PNG/JPEG files.

---

### B. Searching via Gemini (Evernote MCP Integration)
When chatting with Gemini, you can use natural language and Gemini will translate your request into `search_notes` or `semantic_search` calls:
- *"List my ToDos for my work credentials"* → Gemini runs `search_notes(query='notebook:EB_Work_Credentials tag:Todo')`.
- *"Show all my open Engram ToDos"* → Gemini runs `search_notes(query='tag:Todo intitle:6')`.
- *"Find my Epic SmartPhrase screenshot about restraint notes"* → Gemini runs `search_notes(query='notebook:EB_Work_EPIC RESTRNOTELIST')` or `semantic_search`.
- *"Mark my PA Medical License Todo as done"* → Gemini calls `update_note_tags` to remove the `Todo` tag while leaving the note inside `EB_Work_Credentials`.

---

### C. Searching Outside Evernote (Engram Local CLI / App & macOS Spotlight)
Even when you are offline or outside Evernote, every filed screenshot is indexed in **three local places**:
1. **Engram Search CLI (`~/.engram/scripts/engram_search.py`)**:
   - Search by keyword across AI + Manual Finder Comments:
     ```bash
     python3 ~/.engram/scripts/engram_search.py "RESTRNOTELIST"
     ```
   - List all open ToDos in a category:
     ```bash
     python3 ~/.engram/scripts/engram_search.py --todo --category EB_Work_Credentials
     ```
   - List all open ToDos across all categories:
     ```bash
     python3 ~/.engram/scripts/engram_search.py --todo
     ```
2. **macOS Finder / Spotlight Search**:
   - Every image in `GOOGbook/EB_<Category>/` has its AI + Manual summary stored in the native macOS Finder Comment (`kMDItemFinderComment`) and macOS Finder Tags (`Todo`, `EB_<Category>`, `Engram`).
   - In Finder (`Cmd+F`), choose **Comment** → **contains** → type any keyword from your manual note or AI summary.
3. **Google Drive Cloud Search (`_Engram_Index.md`)**:
   - Every `GOOGbook/EB_<Category>/` folder contains an auto-updated `_Engram_Index.md` Markdown file with the filename, timestamp, `[TODO]` badge, and full AI/Manual description so searching inside the Google Drive web or mobile app finds your exact screenshot immediately.
