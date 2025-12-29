from __future__ import annotations

import time
from pathlib import Path

from PIL import Image

from src.features.embedding import embed_text
from src.features.vision import describe_image, pil_to_png_bytes, parse_caption_and_tags
from src.services.qdrant_service import get_qdrant_client, ensure_collection_exists, upsert_point
from src.utils.ids import stable_id_from_bytes

DATA_DIR = Path("data/images")


def main() -> None:
    qdrant = get_qdrant_client()
    ensure_collection_exists(qdrant)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted([p for p in DATA_DIR.glob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg"}])

    if not files:
        print(f"No images found in {DATA_DIR.resolve()}. Put some JPG/PNG files there first.")
        return

    print(f"Seeding {len(files)} images from {DATA_DIR.resolve()} ...")

    for p in files:
        img = Image.open(p).convert("RGB")
        img_bytes = pil_to_png_bytes(img)
        pid = stable_id_from_bytes(img_bytes)

        raw = describe_image(img_bytes)
        caption, tags = parse_caption_and_tags(raw)
        vector = embed_text(caption)

        payload = {
            "filename": str(p),
            "caption": caption,
            "tags": tags,
            "source": "seed",
            "stock": True,
            "added_at": int(time.time()),
        }
        upsert_point(qdrant, pid, vector, payload)
        print(f"Indexed: {p.name} -> id={pid}")

    print("Done.")


if __name__ == "__main__":
    main()
