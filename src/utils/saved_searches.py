from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

SAVED_PATH = Path("data/saved_searches.json")


def load_saved() -> List[Dict[str, Any]]:
    if not SAVED_PATH.exists():
        return []
    try:
        items = json.loads(SAVED_PATH.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            return []
        return items
    except Exception:
        return []


def save_all(items: List[Dict[str, Any]]) -> None:
    SAVED_PATH.parent.mkdir(parents=True, exist_ok=True)
    SAVED_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def add_saved(name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    name = (name or "").strip()
    if not name:
        raise ValueError("Name is required")
    items = load_saved()
    rec = {
        "id": f"s_{int(time.time()*1000)}",
        "name": name,
        "created_ts": int(time.time()),
        "params": dict(params),
    }
    items.append(rec)
    # keep last 200
    if len(items) > 200:
        items = items[-200:]
    save_all(items)
    return rec


def delete_saved(saved_id: str) -> None:
    items = [it for it in load_saved() if str(it.get("id")) != str(saved_id)]
    save_all(items)
