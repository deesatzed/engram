#!/usr/bin/env python3
"""Engram Shottr Watcher & Live Processor."""

import argparse
import base64
import json
import os
import plistlib
import re
import shutil
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from engram_core import MacNotifier, TaxonomyValidator

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-6-luna-decisions"
FALLBACK_VISION_MODEL = "google/gemini-2.5-flash"

WATCH_FOLDER = Path("/Volumes/WS4TB/File_Cab/SS/SS_Oct26")
TRASH_24H_FOLDER = Path("/Volumes/WS4TB/File_Cab/SS/_Trash_24h")
GOOGBOOK_ROOT = Path(
    "/Users/o2satz/Library/CloudStorage/GoogleDrive-o2satz@gmail.com/"
    "Other computers/My Mac (1)/GOOGbook"
)
EVERNOTE_IMPORT_ROOT = Path("~/Evernote_Imports").expanduser()
CATEGORIES_FILE = Path("~/.engram/categories.json").expanduser()
LEGEND_FILE = Path("~/.engram/legend.json").expanduser()

FACET_LEGEND = {
    "lifecycle": {
        "R": "Reference (Keep permanently)",
        "A": "Action / Todo / Expiring",
        "F": "Financial / Billing / Receipt",
        "P": "Project / Active Build",
    },
    "format": {
        "L": "License / Credential / Official ID",
        "S": "Settings / UI Configuration",
        "C": "Code / SQL / Terminal / Architecture",
        "D": "Document / Text / Policy",
        "P": "Paper / Academic / Article",
        "T": "Table / Chart / Metrics",
    },
}


def load_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key:
        return key
    env_path = Path("~/.engram/.env").expanduser()
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def encode_hex_date(timestamp: float) -> str:
    dt = datetime.fromtimestamp(timestamp)
    year_digit = str(dt.year)[-1]
    month_hex = f"{dt.month:X}"
    day_str = f"{dt.day:02d}"
    return f"{year_digit}{month_hex}{day_str}"


def normalize_keywords(raw_kw: Any) -> str:
    if isinstance(raw_kw, list):
        raw_str = "_".join(str(item) for item in raw_kw if item)
    elif isinstance(raw_kw, str):
        raw_str = raw_kw
    else:
        raw_str = "Capture"
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", raw_str).strip("_")
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned or "Capture"


def get_finder_comment(file_path: Path) -> str:
    try:
        raw = subprocess.check_output(
            ["xattr", "-p", "com.apple.metadata:kMDItemFinderComment", str(file_path)],
            stderr=subprocess.DEVNULL,
        )
        val = plistlib.loads(raw)
        if isinstance(val, str):
            return val.strip()
    except Exception:
        pass
    try:
        out = subprocess.check_output(
            ["mdls", "-raw", "-name", "kMDItemFinderComment", str(file_path)],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if out and out != "(null)":
            return out
    except Exception:
        pass
    return ""


def set_finder_metadata(file_path: Path, comment: str, tags: List[str]) -> None:
    try:
        comment_plist = plistlib.dumps(comment, fmt=plistlib.FMT_BINARY)
        subprocess.run(
            [
                "xattr",
                "-w",
                "com.apple.metadata:kMDItemFinderComment",
                comment_plist.hex(),
                "-x",
                str(file_path),
            ],
            check=False,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass

    if tags:
        try:
            tag_entries = [f"{t}\n0" for t in tags]
            tag_plist = plistlib.dumps(tag_entries, fmt=plistlib.FMT_BINARY)
            subprocess.run(
                [
                    "xattr",
                    "-w",
                    "com.apple.metadata:_kMDItemUserTags",
                    tag_plist.hex(),
                    "-x",
                    str(file_path),
                ],
                check=False,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass


def load_categories() -> Dict[str, str]:
    default_cats = {nb: "both" for nb in TaxonomyValidator.ALLOWED_NOTEBOOKS}
    if CATEGORIES_FILE.exists():
        try:
            saved = json.loads(CATEGORIES_FILE.read_text(encoding="utf-8"))
            default_cats.update(saved)
        except Exception:
            pass
    return default_cats


def save_category(cat_name: str, mode: str = "both") -> None:
    cats = load_categories()
    cats[cat_name] = mode
    CATEGORIES_FILE.parent.mkdir(parents=True, exist_ok=True)
    CATEGORIES_FILE.write_text(json.dumps(cats, indent=2), encoding="utf-8")


def prompt_user_low_confidence(
    img_path: Path, suggested_cat: str, suggested_kw: str, summary: str
) -> Tuple[str, str, str]:
    cats = sorted(load_categories().keys())
    safe_summary = summary.replace('"', "'")[:180]
    msg = (
        f"Engram Low-Confidence Screenshot:\n"
        f"File: {img_path.name}\n"
        f"Suggested: {suggested_cat} ({suggested_kw})\n\n{safe_summary}"
    )
    cmd = [
        "osascript",
        "-e", 'tell application "System Events" to activate',
        "-e",
        f'button returned of (display dialog "{msg}" buttons '
        '{"Delete / C&P Only", "New Category...", "Pick Category..."} '
        'default button "Pick Category..." with title "Engram Screenshot Triage")',
    ]
    try:
        choice = subprocess.check_output(cmd, text=True).strip()
    except Exception:
        return ("file", suggested_cat, "both")

    if choice == "Delete / C&P Only":
        return ("delete", "", "")

    if choice == "New Category...":
        new_cmd = [
            "osascript",
            "-e", 'tell application "System Events" to activate',
            "-e",
            'set dlg to display dialog "Enter New Category Name:" default answer "" '
            'buttons {"Google Drive Only", "Evernote Only", "Evernote + Drive"} '
            'default button "Evernote + Drive" with title "Create New Category"',
            "-e", '(text returned of dlg) & "|||" & (button returned of dlg)',
        ]
        try:
            out = subprocess.check_output(new_cmd, text=True).strip()
            cat_name, btn = out.split("|||", 1)
            cat_name = cat_name.strip() or suggested_cat
            mode_map = {
                "Evernote + Drive": "both",
                "Evernote Only": "evernote",
                "Google Drive Only": "drive",
            }
            mode = mode_map.get(btn, "both")
            save_category(cat_name, mode)
            return ("file", cat_name, mode)
        except Exception:
            return ("file", suggested_cat, "both")

    cat_list_str = ", ".join(f'"{c}"' for c in cats)
    pick_cmd = [
        "osascript",
        "-e", 'tell application "System Events" to activate',
        "-e",
        f'set chosen to choose from list {{{cat_list_str}}} with title "Select Category" '
        f'with prompt "Choose category for {img_path.name}:" default items {{"{suggested_cat}"}}',
        "-e", f'if chosen is false then return "{suggested_cat}"',
        "-e", "return item 1 of chosen",
    ]
    try:
        chosen_cat = subprocess.check_output(pick_cmd, text=True).strip()
        mode = load_categories().get(chosen_cat, "both")
        return ("file", chosen_cat, mode)
    except Exception:
        return ("file", suggested_cat, "both")


def analyze_screenshot_with_ai(
    img_path: Path, manual_comment: str, api_key: str
) -> Dict[str, Any]:
    cats = list(load_categories().keys())
    ext = img_path.suffix.lower().lstrip(".")
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")

    prompt = (
        f"Analyze this screenshot and return ONLY valid JSON with these exact keys:\n"
        f"- \"category\": Best matching category from {cats}\n"
        f"- \"confidence\": Float 0.0 to 1.0 indicating how strongly this image fits\n"
        f"- \"lifecycle_code\": Single letter from [\"R\", \"A\", \"F\", \"P\"]\n"
        f"- \"format_code\": Single letter from [\"L\", \"S\", \"C\", \"D\", \"P\", \"T\"]\n"
        f"- \"keywords\": Single underscore-separated string of 3 to 5 specific keywords\n"
        f"- \"summary\": Concise 1-2 sentence description including key visible text.\n"
        f"User manual Finder comment (treat as gold-standard truth if non-empty): \"{manual_comment}\""
    )

    for model in (FALLBACK_VISION_MODEL, DEFAULT_MODEL):
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    ],
                }
            ],
            "response_format": {"type": "json_object"},
        }
        try:
            req = urllib.request.Request(
                OPENROUTER_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
                content = raw["choices"][0]["message"]["content"].strip()
                content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.DOTALL)
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    return parsed
        except Exception:
            continue

    return {
        "category": "EB_2FileLater",
        "confidence": 0.50,
        "lifecycle_code": "R",
        "format_code": "S",
        "keywords": img_path.stem.replace("-2", ""),
        "summary": manual_comment or "Screenshot captured via Shottr.",
    }


def find_trigger_pairs(watch_dir: Path) -> Tuple[List[Tuple[Path, Path]], List[Path]]:
    all_files = sorted(
        [
            p
            for p in watch_dir.iterdir()
            if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
        ]
    )
    triggers = [
        p for p in all_files if re.search(r"-2\.(png|jpg|jpeg|webp)$", p.name, re.IGNORECASE)
    ]
    paired_set = set()
    pairs: List[Tuple[Path, Path]] = []

    for trig in triggers:
        base_name = re.sub(r"-2(\.(?:png|jpg|jpeg|webp))$", r"\1", trig.name, flags=re.IGNORECASE)
        base_path = trig.parent / base_name
        if base_path.exists():
            pairs.append((base_path, trig))
            paired_set.add(trig)
            paired_set.add(base_path)
        else:
            pairs.append((trig, trig))
            paired_set.add(trig)

    singles = [p for p in all_files if p not in paired_set]
    return pairs, singles



SYNCED_FOLDERS_FILE = Path("~/.engram/synced_evernote_folders.json").expanduser()
AUDIT_LOG_FILE = Path("~/.engram/logs/engram_audit.jsonl").expanduser()


def write_audit_entry(entry: Dict[str, Any]) -> None:
    AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry["timestamp"] = datetime.now().isoformat()
    with AUDIT_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def check_and_remind_evernote_sync_folder(cat_name: str, en_cat_dir: Path) -> None:
    """Pops up a 1-time reminder when a brand-new ~/Evernote_Imports/<EB_Category> folder is created."""
    synced: List[str] = []
    if SYNCED_FOLDERS_FILE.exists():
        try:
            synced = json.loads(SYNCED_FOLDERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            synced = []

    if cat_name in synced:
        return

    msg = (
        f"New Engram Folder Created: {cat_name}\n\n"
        f"Path: {en_cat_dir}\n\n"
        f"To auto-import images into Evernote:\n"
        f"1. Open Evernote -> Settings -> Sync folders\n"
        f"2. Click '+ Connect a folder'\n"
        f"3. Select {en_cat_dir} -> Notebook '{cat_name}' (in stack EB_MAC_MiniM4)"
    )
    cmd = [
        "osascript",
        "-e", 'tell application "System Events" to activate',
        "-e",
        f'display dialog "{msg}" buttons {{"Remind Me Next Time", "Mark Connected"}} '
        f'default button "Mark Connected" with title "Engram 1-Time Evernote Sync Setup"',
    ]
    try:
        out = subprocess.check_output(cmd, text=True).strip()
        if "Mark Connected" in out:
            synced.append(cat_name)
            SYNCED_FOLDERS_FILE.write_text(json.dumps(sorted(set(synced)), indent=2), encoding="utf-8")
    except Exception:
        pass


def append_to_drive_index(cat_dir: Path, filename: str, facet: str, comment: str) -> None:
    idx_file = cat_dir / "_Engram_Index.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"- **`{filename}`** (`{facet}` | {ts}): {comment}\n"
    if not idx_file.exists():
        idx_file.write_text(f"# Engram Semantic Index — {cat_dir.name}\n\n{entry}", encoding="utf-8")
    else:
        with idx_file.open("a", encoding="utf-8") as f:
            f.write(entry)


def run_sweep(watch_dir: Path, dry_run: bool = True) -> None:
    api_key = load_api_key()
    LEGEND_FILE.write_text(json.dumps(FACET_LEGEND, indent=2), encoding="utf-8")
    cats_map = load_categories()

    pairs, singles = find_trigger_pairs(watch_dir)
    now = time.time()

    print("=" * 72)
    print(f"📂 Scanning Shottr Folder: {watch_dir}")
    mode_label = "DRY RUN (Preview Only)" if dry_run else "🚀 LIVE EXECUTION (Filing + Metadata + Cleanup)"
    print(f"🔍 Mode: {mode_label}")
    print(f"📌 Found {len(pairs)} '-2' Save-Trigger Pair(s) | {len(singles)} Singular File(s)")
    print("=" * 72)

    for idx, (base_file, trig_file) in enumerate(pairs, 1):
        manual_comment = get_finder_comment(base_file) or get_finder_comment(trig_file)
        info = analyze_screenshot_with_ai(base_file, manual_comment, api_key)

        hex_date = encode_hex_date(base_file.stat().st_mtime)
        lc = str(info.get("lifecycle_code", "R"))[:1].upper() or "R"
        fc = str(info.get("format_code", "S"))[:1].upper() or "S"
        kw = normalize_keywords(info.get("keywords", "Capture"))
        ext = base_file.suffix.lower()

        new_filename = f"{hex_date}-{lc}{fc}_{kw}{ext}"
        cat = str(info.get("category", "EB_2FileLater"))
        try:
            conf = float(info.get("confidence", 0.0))
        except (TypeError, ValueError):
            conf = 0.0
        ai_summary = str(info.get("summary", ""))

        combined_comment = (
            f"{manual_comment} | {ai_summary} [{hex_date}-{lc}{fc}]"
            if manual_comment
            else f"{ai_summary} [{hex_date}-{lc}{fc}]"
        )
        tags = [cat, f"{lc}{fc}", "Engram"]

        print(f"\n✅ [PAIR #{idx}] Trigger detected: {trig_file.name}")
        print(f"   • Original File  : {base_file.name} (kept in folder for 24h reuse)")
        if manual_comment:
            print(f'   • Manual Comment : "{manual_comment}" (Preserved as Gold Truth!)')
        print(f"   • New Filename   : {new_filename}")
        print(f"   • Category Match : {cat} (Confidence: {conf:.0%})")
        print(f"   • Finder Comment : {combined_comment}")

        if not dry_run:
            dest_mode = cats_map.get(cat, "both")
            action = "file"
            if conf < 0.85:
                action, cat, dest_mode = prompt_user_low_confidence(
                    base_file, cat, kw, combined_comment
                )

            if action == "delete":
                if trig_file.exists():
                    trig_file.unlink()
                if base_file.exists():
                    TRASH_24H_FOLDER.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(base_file), str(TRASH_24H_FOLDER / base_file.name))
                print(f"   🗑️  User selected Delete -> Moved {base_file.name} to _Trash_24h")
                continue

            set_finder_metadata(base_file, combined_comment, tags)
            os.utime(base_file, (now, now))

            if dest_mode in ("both", "drive") and GOOGBOOK_ROOT.parent.exists():
                drive_cat_dir = GOOGBOOK_ROOT / cat
                drive_cat_dir.mkdir(parents=True, exist_ok=True)
                drive_dest = drive_cat_dir / new_filename
                shutil.copy2(str(base_file), str(drive_dest))
                set_finder_metadata(drive_dest, combined_comment, tags)
                append_to_drive_index(drive_cat_dir, new_filename, f"{hex_date}-{lc}{fc}", combined_comment)
                print(f"   ☁️  Filed to Google Drive : {drive_dest}")

            if dest_mode in ("both", "evernote"):
                en_cat_dir = EVERNOTE_IMPORT_ROOT / cat
                en_cat_dir.mkdir(parents=True, exist_ok=True)
                en_dest = en_cat_dir / new_filename
                shutil.copy2(str(base_file), str(en_dest))
                set_finder_metadata(en_dest, combined_comment, tags)
                print(f"   🐘 Filed to Evernote     : {en_dest}")
                check_and_remind_evernote_sync_folder(cat, en_cat_dir)
            write_audit_entry({
                "event": "screenshot_filed",
                "original_file": base_file.name,
                "new_filename": new_filename,
                "category": cat,
                "confidence": conf,
                "facet": f"{hex_date}-{lc}{fc}",
                "tags": tags,
                "comment": combined_comment,
            })

            if trig_file != base_file and trig_file.exists():
                trig_file.unlink()
                print(f"   🧹 Removed Trigger Clone : {trig_file.name}")

            MacNotifier.notify("Engram Filed Screenshot", f"→ {cat}", new_filename)

    print("\n" + "-" * 72)
    print("⏱️  Singular Files (1-Day C&P Reuse Hold):")
    for s in singles:
        age_hours = (now - s.stat().st_mtime) / 3600.0
        manual_c = get_finder_comment(s)
        c_note = f' [Has Manual Comment: "{manual_c}"]' if manual_c else ""
        if age_hours >= 24.0:
            if dry_run:
                print(f"   • {s.name:<30} | Age: {age_hours:5.1f}h | 🗑️  >24h old -> Would Move to _Trash_24h{c_note}")
            else:
                TRASH_24H_FOLDER.mkdir(parents=True, exist_ok=True)
                shutil.move(str(s), str(TRASH_24H_FOLDER / s.name))
                print(f"   • {s.name:<30} | Age: {age_hours:5.1f}h | 🗑️  Moved expired single to {TRASH_24H_FOLDER.name}{c_note}")
        else:
            print(f"   • {s.name:<30} | Age: {age_hours:5.1f}h | ⏳ {24.0 - age_hours:.1f}h remaining before cleanup{c_note}")
    print("=" * 72)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=str, default=str(WATCH_FOLDER))
    parser.add_argument("--live", action="store_true", help="Execute moves, Finder comments, and -2 cleanup")
    args = parser.parse_args()
    run_sweep(Path(args.folder).expanduser(), dry_run=not args.live)
