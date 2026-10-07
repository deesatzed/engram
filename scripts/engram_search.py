#!/usr/bin/env python3
"""
Engram Search CLI — Search across Audit Logs, Google Drive Indexes, and macOS Spotlight.
Usage examples:
  python3 ~/.engram/scripts/engram_search.py "Medical License"
  python3 ~/.engram/scripts/engram_search.py --todo --category EB_Work_Credentials
  python3 ~/.engram/scripts/engram_search.py --facet RD
"""

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List

AUDIT_LOG = Path("~/.engram/logs/engram_audit.jsonl").expanduser()
GOOGBOOK_ROOT = Path(
    "/Users/o2satz/Library/CloudStorage/GoogleDrive-o2satz@gmail.com/"
    "Other computers/My Mac (1)/GOOGbook"
)


def search_audit_log(
    query: str, category: str, todo_only: bool, facet: str
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    if not AUDIT_LOG.exists():
        return results
    q_low = query.lower().strip()
    cat_low = category.lower().strip()
    facet_up = facet.upper().strip()

    for line in AUDIT_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        rec_cat = str(rec.get("category", ""))
        rec_tags = [str(t) for t in rec.get("tags", [])]
        rec_comment = str(rec.get("comment", ""))
        rec_name = str(rec.get("new_filename") or rec.get("filename") or "")
        rec_facet = str(rec.get("facet", ""))

        if cat_low and cat_low not in rec_cat.lower():
            continue
        if todo_only and "Todo" not in rec_tags and not rec.get("todo_tagged"):
            continue
        if facet_up and facet_up not in rec_facet.upper() and f"-{facet_up}_" not in rec_name.upper():
            continue
        haystack = f"{rec_name} {rec_cat} {rec_comment} {' '.join(rec_tags)}".lower()
        if q_low and q_low not in haystack:
            continue
        results.append(rec)
    return results


def search_spotlight(query: str) -> List[str]:
    if not query.strip() or not GOOGBOOK_ROOT.exists():
        return []
    safe_q = query.replace('"', "")
    md_query = (
        f'kMDItemFinderComment == "*{safe_q}*"cd || '
        f'kMDItemFSName == "*{safe_q}*"cd'
    )
    try:
        out = subprocess.check_output(
            ["mdfind", "-onlyin", str(GOOGBOOK_ROOT), md_query],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return [line.strip() for line in out.splitlines() if line.strip()]
    except Exception:
        return []


def main() -> None:
    parser = argparse.ArgumentParser(description="Search Engram outside Evernote.")
    parser.add_argument("query", nargs="?", default="", help="Free-text search keyword(s)")
    parser.add_argument("--category", "-c", default="", help="Filter by EB_ category substring")
    parser.add_argument("--todo", "-t", action="store_true", help="Only show items tagged Todo")
    parser.add_argument("--facet", "-f", default="", help="Filter by 2-letter facet (e.g. RD, RL, PC)")
    args = parser.parse_args()

    hits = search_audit_log(args.query, args.category, args.todo, args.facet)
    print("=" * 72)
    print(f"🔎 Engram Local Search | Hits: {len(hits)}")
    print("=" * 72)
    for idx, h in enumerate(hits, 1):
        fname = h.get("new_filename") or h.get("filename")
        cat = h.get("category")
        tags = h.get("tags", [])
        comment = h.get("comment", "")
        print(f"\n[{idx}] 📄 {fname}")
        print(f"    • Category : {cat} | Tags: {tags}")
        print(f"    • Summary  : {comment}")

    if args.query:
        sp_hits = search_spotlight(args.query)
        if sp_hits:
            print("\n" + "-" * 72)
            print(f"🍎 macOS Spotlight Matches in GOOGbook ({len(sp_hits)}):")
            for p in sp_hits:
                print(f"    • {p}")
    print("=" * 72)


if __name__ == "__main__":
    main()
