from __future__ import annotations

import hashlib


def stable_id_from_bytes(b: bytes) -> int:
    # Qdrant point id can be int. Use first 8 bytes of sha1.
    h = hashlib.sha1(b).digest()
    return int.from_bytes(h[:8], "big", signed=False)
