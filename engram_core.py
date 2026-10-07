#!/usr/bin/env python3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import subprocess
from typing import List, Optional

class ClipType(str, Enum):
    IMAGE = "image"
    TEXT = "text"
    CODE = "code"
    URL = "url"
    DOCUMENT = "document"

class TriageDisposition(str, Enum):
    KEEP_REFERENCE = "KEEP_REFERENCE"
    KEEP_ACTIONABLE = "KEEP_ACTIONABLE"
    TRASH_EPHEMERAL = "TRASH_EPHEMERAL"

@dataclass
class TriageDecision:
    disposition: TriageDisposition
    title: str
    notebook: str
    tags: List[str]
    summary: str
    extracted_text: Optional[str] = None
    action_item: Optional[str] = None
    due_date: Optional[str] = None
    clean_filename: Optional[str] = None

class TaxonomyValidator:
    ALLOWED_NOTEBOOKS = ["Work", "EPIC", "Home", "ED Arts", "PMC", "PDF Notebook", "Photoshop", "Pics_DL", "Guitar", "Todo", "A-iPad pen", "Secure Chat"]
    ALLOWED_TAGS = ["Epic", "SQL", "Admin", "Academic", "Research", "Receipts", "Home Tasks", "ideas", "Journals", "Keep", "Lectures", "LLSA", "passwords", "Secure Chat", "Sharepoint", "Todo", "#AC", "Advisory", "Bass guitar", "Camera", "Contacts"]

    @classmethod
    def validate_notebook(cls, notebook: str, default: str = "Work") -> str:
        for nb in cls.ALLOWED_NOTEBOOKS:
            if nb.lower() == notebook.lower(): return nb
        return default

    @classmethod
    def filter_tags(cls, candidate_tags: List[str]) -> List[str]:
        valid_tags = []
        for tag in candidate_tags:
            for allowed in cls.ALLOWED_TAGS:
                if tag.lower().strip("#") == allowed.lower().strip("#"):
                    valid_tags.append(allowed)
                    break
        return list(dict.fromkeys(valid_tags))

class MacNotifier:
    @staticmethod
    def notify(title: str, subtitle: str, message: str) -> None:
        script = f'display notification "{message}" with title "{title}" subtitle "{subtitle}" sound name "Tink"'
        try: subprocess.run(["osascript", "-e", script], check=False)
        except Exception: pass

class DriveVaultManager:
    def __init__(self, drive_base: Path, import_base: Path, heavy_threshold_mb: float = 10.0):
        self.drive_base = drive_base.expanduser()
        self.import_base = import_base.expanduser()
        self.heavy_threshold_mb = heavy_threshold_mb

    def is_heavy(self, file_path: Path) -> bool:
        return (file_path.stat().st_size / (1024 * 1024)) >= self.heavy_threshold_mb

    def route_file(self, file_path: Path, decision: TriageDecision) -> Path:
        import shutil
        file_path = file_path.expanduser()
        if self.is_heavy(file_path):
            target_dir = self.drive_base / decision.notebook
            target_dir.mkdir(parents=True, exist_ok=True)
            dest_file = target_dir / file_path.name
            shutil.copy2(file_path, dest_file)
            self._write_drive_index_card(file_path, dest_file, decision)
            return dest_file
        else:
            target_dir = self.import_base / decision.notebook
            target_dir.mkdir(parents=True, exist_ok=True)
            dest_file = target_dir / file_path.name
            shutil.copy2(file_path, dest_file)
            return dest_file

    def _write_drive_index_card(self, original_path: Path, drive_path: Path, decision: TriageDecision) -> None:
        index_dir = self.import_base / decision.notebook
        index_dir.mkdir(parents=True, exist_ok=True)
        index_file = index_dir / f"{decision.title} (Drive Index).html"
        size_mb = original_path.stat().st_size / (1024 * 1024)
        html_content = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{decision.title}</title></head><body><div style="background-color:#f0f7ff; padding:16px; border-left:4px solid #2b6cb0; font-family:sans-serif;"><h2>🧠 Engram Heavy File Index</h2><p><strong>File Name:</strong> {original_path.name} ({size_mb:.2f} MB)</p><p><strong>Google Drive Location:</strong> <code>{drive_path}</code></p><p><strong>Summary:</strong> {decision.summary}</p><p><strong>Tags:</strong> {', '.join(decision.tags)}</p><p><a href="file://{drive_path}" style="background-color:#2b6cb0; color:white; padding:8px 14px; text-decoration:none; border-radius:4px; display:inline-block;">📂 Open File in Local Drive</a></p></div></body></html>"""
        index_file.write_text(html_content, encoding="utf-8")
