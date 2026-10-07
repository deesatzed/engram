#!/usr/bin/env python3
import sys, os, time, subprocess
from pathlib import Path
from engram_core import ClipType, TriageDecision, TriageDisposition, TaxonomyValidator, MacNotifier, DriveVaultManager

def get_clipboard_content():
    try:
        res = subprocess.run(["pngpaste", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and len(res.stdout) > 0: return ClipType.IMAGE, res.stdout
    except FileNotFoundError: pass
    try: text = subprocess.check_output(["pbpaste"], text=True)
    except Exception: return None, None
    if not text.strip(): return None, None
    
    possible_path = Path(text.strip().strip('"').strip("'"))
    if possible_path.exists() and possible_path.is_file(): return ClipType.DOCUMENT, possible_path
    if text.strip().startswith(("http://", "https://")): return ClipType.URL, text.strip()
    
    lower_text = text.strip().lower()
    if any(ind in lower_text for ind in ["select ", "insert ", "def ", "class ", "import "]): return ClipType.CODE, text
    return ClipType.TEXT, text

def analyze_with_ai(clip_type: ClipType, payload) -> TriageDecision:
    now_str = time.strftime("%Y-%m-%d %H:%M")
    if clip_type == ClipType.CODE:
        nb = "EPIC" if "select" in str(payload).lower() else "Work"
        return TriageDecision(TriageDisposition.KEEP_REFERENCE, f"Code Snippet ({time.strftime('%Y-%m-%d')})", nb, ["SQL"] if nb=="EPIC" else ["Research"], "Captured code snippet.", str(payload))
    elif clip_type == ClipType.URL:
        return TriageDecision(TriageDisposition.KEEP_REFERENCE, f"Web Resource: {str(payload)[:40]}", "Work", ["Research"], f"Captured URL: {payload}", str(payload))
    elif clip_type == ClipType.DOCUMENT:
        return TriageDecision(TriageDisposition.KEEP_REFERENCE, f"Doc: {payload.stem}", "PDF Notebook" if payload.suffix.lower() == ".pdf" else "Work", ["Admin"], f"Captured doc: {payload.name}", clean_filename=payload.name)
    else:
        return TriageDecision(TriageDisposition.KEEP_REFERENCE, f"Quick Note ({now_str})", "Work", ["Keep"], "Captured text note.", str(payload) if isinstance(payload, str) else None)

def main():
    clip_type, payload = get_clipboard_content()
    if not clip_type:
        MacNotifier.notify("Engram", "Clipboard Empty", "Nothing found on clipboard.")
        sys.exit(0)
    decision = analyze_with_ai(clip_type, payload)
    decision.notebook = TaxonomyValidator.validate_notebook(decision.notebook)
    decision.tags = TaxonomyValidator.filter_tags(decision.tags)

    import_dir = Path("~/Evernote_Imports").expanduser() / decision.notebook
    import_dir.mkdir(parents=True, exist_ok=True)

    if clip_type == ClipType.IMAGE:
        img_path = import_dir / f"{time.strftime('%Y%m%d_%H%M%S')}_Clip.png"
        img_path.write_bytes(payload)
        MacNotifier.notify("Engram Filed Screenshot", f"→ {decision.notebook}", f"Tags: {', '.join(decision.tags)}")
    elif clip_type == ClipType.DOCUMENT:
        mgr = DriveVaultManager(Path("~/Google Drive/My Drive/Engram_Vault"), Path("~/Evernote_Imports"))
        routed = mgr.route_file(payload, decision)
        MacNotifier.notify("Engram Filed Document", f"→ {decision.notebook}", f"Saved to {routed.name}")
    else:
        note_path = import_dir / f"{decision.title.replace('/', '-')}.html"
        content = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{decision.title}</title></head><body><div style='background-color:#f4f6f8; padding:12px; border-left:4px solid #2b6cb0;'><strong>🧠 Engram Brief:</strong> {decision.summary}<br/><strong>Tags:</strong> {', '.join(decision.tags)}</div><hr/><pre><code>{decision.extracted_text or ''}</code></pre></body></html>"
        note_path.write_text(content, encoding="utf-8")
        MacNotifier.notify("Engram Captured Clip", f"→ {decision.notebook}", f"Filed as '{decision.title}'")

if __name__ == "__main__": main()
