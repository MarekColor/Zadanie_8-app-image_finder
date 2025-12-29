from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List


PENDING_PATH = Path("data/pending_uploads.json")


def load_pending() -> List[Dict[str, Any]]:
    if not PENDING_PATH.exists():
        return []
    try:
        items = json.loads(PENDING_PATH.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            return []
        return items
    except Exception:
        return []


def add_pending(item: Dict[str, Any]) -> None:
    PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
    items = load_pending()
    item = dict(item)
    item.setdefault("ts", int(time.time()))
    items.append(item)
    PENDING_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def remove_pending_by_id(point_id: str) -> None:
    items = [x for x in load_pending() if str(x.get("id")) != str(point_id)]
    PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
    PENDING_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_pending() -> None:
    if PENDING_PATH.exists():
        PENDING_PATH.unlink()
