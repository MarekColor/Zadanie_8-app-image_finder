from __future__ import annotations

import base64
from io import BytesIO
from typing import List, Tuple

from PIL import Image

from src.services.openai_client import get_openai_client
from src.config import settings


def pil_to_png_bytes(img: Image.Image, max_side: int = 1024) -> bytes:
    """Resize (preserving aspect ratio) and return PNG bytes."""
    img = img.convert("RGB")
    w, h = img.size
    scale = min(1.0, float(max_side) / max(w, h))
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)))
    bio = BytesIO()
    img.save(bio, format="PNG", optimize=True)
    return bio.getvalue()


def image_bytes_to_data_url(image_bytes: bytes, mime: str = "image/png") -> str:
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def parse_caption_and_tags(raw: str) -> Tuple[str, List[str]]:
    """Extract caption + tags from model output.

    Expected pattern: description text and somewhere (often last line) tags separated by commas.
    We keep it resilient: if no tags found, return empty list.
    """
    if not raw:
        return "", []
    text = raw.strip()

    # Heuristic: tags often after 'Tags:' or as last line with commas
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    caption = lines[0] if lines else text

    tags: List[str] = []
    # find explicit Tags line
    for ln in reversed(lines):
        low = ln.lower()
        if low.startswith("tags:") or low.startswith("tag:"):
            cand = ln.split(":", 1)[1]
            tags = [t.strip().lstrip("#").lower() for t in cand.split(",") if t.strip()]
            break

    if not tags and lines:
        last = lines[-1]
        if "," in last and len(last) < 80:
            tags = [t.strip().lstrip("#").lower() for t in last.split(",") if t.strip()]

    # Clean caption: if it equals tags line, fallback to full text minus last line
    if tags and lines:
        if caption == lines[-1] and len(lines) > 1:
            caption = " ".join(lines[:-1])

    # Limit to 10 tags
    tags = tags[:10]
    return caption.strip(), tags


def describe_image(image_bytes: bytes) -> str:
    """Use VLM to describe image (for indexing/search)."""
    client = get_openai_client()
    data_url = image_bytes_to_data_url(image_bytes)

    resp = client.chat.completions.create(
        model=settings.vlm_model,
        messages=[
            {"role": "system", "content": "You describe images for search indexing."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image in 1-2 sentences. Then on a new line write: Tags: tag1, tag2, tag3, tag4, tag5"},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
    )
    return (resp.choices[0].message.content or "").strip()
