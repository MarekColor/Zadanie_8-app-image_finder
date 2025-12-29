from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List


HISTORY_PATH = Path("data/history.json")


def load_history(limit: int | None = None) -> List[Dict[str, Any]]:
    if not HISTORY_PATH.exists():
        return []
    try:
        items = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            return []
    except Exception:
        return []
    items = list(reversed(items))  # newest first
    if limit is not None:
        items = items[:limit]
    return items


def append_history(item: Dict[str, Any], max_items: int = 200) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    items: List[Dict[str, Any]] = []
    if HISTORY_PATH.exists():
        try:
            items = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
            if not isinstance(items, list):
                items = []
        except Exception:
            items = []
    item = dict(item)
    item.setdefault("ts", int(time.time()))
    items.append(item)
    if len(items) > max_items:
        items = items[-max_items:]
    HISTORY_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_history() -> None:
    if HISTORY_PATH.exists():
        HISTORY_PATH.unlink()
