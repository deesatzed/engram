#!/usr/bin/env python3
import time, argparse, shutil
from pathlib import Path
from engram_core import TriageDecision, TriageDisposition, TaxonomyValidator, MacNotifier

def triage_screenshot_image(img_path: Path) -> TriageDecision:
    if img_path.stat().st_size < 15 * 1024:
        return TriageDecision(TriageDisposition.TRASH_EPHEMERAL, "Tiny Capture", "Home", [], "Tiny ephemeral screenshot.")
    date_prefix = time.strftime("%Y-%m-%d", time.localtime(img_path.stat().st_mtime))
    clean_stem = f"{date_prefix}_Screenshot_{img_path.stem[-6:]}"
    return TriageDecision(TriageDisposition.KEEP_REFERENCE, f"Visual: {clean_stem}", "Pics_DL", ["Camera"], "Visual reference.", clean_filename=f"{clean_stem}.png")

def process_file(img_path: Path, trash_dir: Path, org_dir: Path, imp_dir: Path):
    if not img_path.is_file() or img_path.suffix.lower() not in [".png", ".jpg", ".jpeg", ".webp"]: return
    decision = triage_screenshot_image(img_path)
    if decision.disposition == TriageDisposition.TRASH_EPHEMERAL:
        trash_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(img_path), str(trash_dir / img_path.name))
        print(f"🗑️ Trashed: {img_path.name}")
    else:
        nb = TaxonomyValidator.validate_notebook(decision.notebook, "Pics_DL")
        target_name = decision.clean_filename or img_path.name
        
        t_org = org_dir / nb
        t_org.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(img_path), str(t_org / target_name))
        
        t_imp = imp_dir / nb
        t_imp.mkdir(parents=True, exist_ok=True)
        shutil.move(str(img_path), str(t_imp / target_name))
        
        MacNotifier.notify("Engram Filed Screenshot", f"→ {nb}", f"{target_name}")
        print(f"✅ Filed {img_path.name} → {nb}/{target_name}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sweep", type=str, help="Sweep a directory")
    args = parser.parse_args()
    watch_dir = Path(args.sweep or "~/Desktop/Screenshots").expanduser()
    trash_dir, org_dir, imp_dir = watch_dir / "_Trash_Review", watch_dir / "Organized", Path("~/Evernote_Imports").expanduser()
    if args.sweep:
        for f in list(watch_dir.glob("*.png")) + list(watch_dir.glob("*.jpg")):
            if "_trash" not in str(f).lower() and "organized" not in str(f).lower(): process_file(f, trash_dir, org_dir, imp_dir)
    else: parser.print_help()

if __name__ == "__main__": main()
