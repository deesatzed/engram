#!/usr/bin/env python3
"""
Engram Screenshot Watcher & Batch Sweeper powered by OpenRouter (openai/gpt-6-luna-decisions).
Zero external dependencies (uses Python stdlib urllib + base64).
"""

import argparse
import base64
import json
import os
import shutil
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Any, List

from engram_core import (
    TriageDecision,
    TriageDisposition,
    TaxonomyValidator,
    MacNotifier,
)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-6-luna-decisions"


def load_api_key() -> str:
    """Loads OPENROUTER_API_KEY from environment or ~/.engram/.env."""
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key:
        return key
    env_path = Path("~/.engram/.env").expanduser()
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


class OpenRouterLunaClient:
    """Direct HTTP client for OpenRouter gpt-6-luna-decisions."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, timeout: int = 20):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @staticmethod
    def encode_image_data_url(img_path: Path) -> str:
        ext = img_path.suffix.lower().lstrip(".")
        mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
        b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{b64}"

    def _post_json(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("Missing OPENROUTER_API_KEY in ~/.engram/.env")
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            OPENROUTER_URL,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/deesatzed/engram",
                "X-Title": "Engram Second Brain",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def evaluate_predicate(self, img_path: Path, question: str) -> float:
        """Returns probability [0.0, 1.0] that the predicate is true."""
        prompt = (
            f"{question}\n"
            'Respond ONLY with valid JSON: {"type": "predicate", "name": "evaluation", "probability": <float 0.0 to 1.0>}'
        )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": self.encode_image_data_url(img_path)}},
                    ],
                }
            ],
            "response_format": {"type": "json_object"},
        }
        try:
            raw = self._post_json(payload)
            parsed = self.parse_decision_response(raw)
            return float(parsed.get("probability", 0.0))
        except Exception as exc:
            print(f"[Luna Warning] Predicate check fallback on {img_path.name}: {exc}")
            return 0.0

    def evaluate_choice(self, img_path: Path, choices: List[str], instruction: str) -> str:
        """Selects the single highest-probability choice from `choices`."""
        prompt = (
            f"{instruction}\n"
            f"Allowed choices: {', '.join(choices)}\n"
            'Respond ONLY with valid JSON: {"type": "choice", "choice": "<exact allowed choice>", "probability": <float>}'
        )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": self.encode_image_data_url(img_path)}},
                    ],
                }
            ],
            "response_format": {"type": "json_object"},
        }
        try:
            raw = self._post_json(payload)
            parsed = self.parse_decision_response(raw)
            return str(parsed.get("choice", "Pics_DL"))
        except Exception as exc:
            print(f"[Luna Warning] Choice routing fallback on {img_path.name}: {exc}")
            return "Pics_DL"

    @staticmethod
    def parse_decision_response(api_response: Dict[str, Any]) -> Dict[str, Any]:
        """Handles both direct decision JSON and OpenRouter chat.completions wrapper."""
        if "type" in api_response and ("probability" in api_response or "choice" in api_response):
            return api_response
        choices = api_response.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "{}")
            if isinstance(content, str):
                return json.loads(content.strip())
        return {}


def triage_screenshot_image(img_path: Path, client: OpenRouterLunaClient) -> TriageDecision:
    """Runs 2-stage Luna Decisions pipeline (Gate 1: Junk Predicate, Gate 2: Notebook Choice)."""
    if img_path.stat().st_size < 15 * 1024:
        return TriageDecision(
            disposition=TriageDisposition.TRASH_EPHEMERAL,
            title="Tiny Capture",
            notebook="Home",
            tags=[],
            summary="Tiny ephemeral file (<15KB).",
        )

    junk_prob = client.evaluate_predicate(
        img_path,
        "Does this image contain an ephemeral 2FA code, login screen, blank window, or temporary junk?",
    )
    if junk_prob > 0.75:
        return TriageDecision(
            disposition=TriageDisposition.TRASH_EPHEMERAL,
            title="Ephemeral Junk",
            notebook="Home",
            tags=[],
            summary=f"Trashed via Luna Decisions API (junk probability={junk_prob:.2f}).",
        )

    raw_choice = client.evaluate_choice(
        img_path,
        TaxonomyValidator.ALLOWED_NOTEBOOKS,
        "Select the best Evernote Notebook for this screenshot.",
    )
    target_nb = TaxonomyValidator.validate_notebook(raw_choice, default="Pics_DL")

    date_prefix = time.strftime("%Y-%m-%d", time.localtime(img_path.stat().st_mtime))
    clean_stem = f"{date_prefix}_{target_nb.replace(' ', '_')}_Screenshot_{img_path.stem[-4:]}"
    ext = img_path.suffix.lower() or ".png"

    return TriageDecision(
        disposition=TriageDisposition.KEEP_REFERENCE,
        title=f"Visual: {clean_stem}",
        notebook=target_nb,
        tags=["Camera"],
        summary=f"Auto-routed to {target_nb} via OpenRouter {client.model}.",
        clean_filename=f"{clean_stem}{ext}",
    )


def process_file(img_path: Path, trash_dir: Path, org_dir: Path, imp_dir: Path, client: OpenRouterLunaClient) -> None:
    if not img_path.is_file() or img_path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
        return
    decision = triage_screenshot_image(img_path, client)
    if decision.disposition == TriageDisposition.TRASH_EPHEMERAL:
        trash_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(img_path), str(trash_dir / img_path.name))
        print(f"🗑️ Trashed: {img_path.name}")
    else:
        nb = decision.notebook
        target_name = decision.clean_filename or img_path.name

        t_org = org_dir / nb
        t_org.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(img_path), str(t_org / target_name))

        t_imp = imp_dir / nb
        t_imp.mkdir(parents=True, exist_ok=True)
        shutil.move(str(img_path), str(t_imp / target_name))

        MacNotifier.notify("Engram Filed Screenshot", f"→ {nb}", target_name)
        print(f"✅ Filed {img_path.name} → {nb}/{target_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Engram Screenshot Sweeper (OpenRouter Luna)")
    parser.add_argument("--sweep", type=str, help="Directory of screenshots to sweep")
    args = parser.parse_args()

    watch_dir = Path(args.sweep or "~/Desktop/Screenshots").expanduser()
    trash_dir = watch_dir / "_Trash_Review"
    org_dir = watch_dir / "Organized"
    imp_dir = Path("~/Evernote_Imports").expanduser()

    client = OpenRouterLunaClient(api_key=load_api_key())

    if args.sweep:
        files = list(watch_dir.glob("*.png")) + list(watch_dir.glob("*.jpg"))
        print(f"🚀 Sweeping {len(files)} screenshots in {watch_dir}...")
        for f in files:
            if "_trash" not in str(f).lower() and "organized" not in str(f).lower():
                process_file(f, trash_dir, org_dir, imp_dir, client)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
