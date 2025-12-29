from __future__ import annotations

import time
from pathlib import Path

import streamlit as st
from PIL import Image

from src.features.embedding import embed_text
from src.features.vision import describe_image, pil_to_png_bytes, parse_caption_and_tags
from src.services.qdrant_service import upsert_point
from src.utils.ids import stable_id_from_bytes
from src.utils.pending import add_pending, load_pending, remove_pending_by_id
from src.utils.history import append_history


def _save_image(img: Image.Image, images_dir: Path, filename: str) -> Path:
    images_dir.mkdir(parents=True, exist_ok=True)
    out = images_dir / filename
    img.save(out)
    return out


def _index_one(
    qdrant_client,
    img: Image.Image,
    img_bytes: bytes,
    filename: str,
    caption: str,
    tags: list[str],
    source: str,
) -> None:
    point_id = stable_id_from_bytes(img_bytes)
    vector = embed_text(caption)  # raises if OpenAI embeddings unavailable
    payload = {
        "filename": filename,
        "caption": caption,
        "tags": tags,
        "stock": False,
        "source": source,
        "added_at": int(time.time()),
    }
    upsert_point(qdrant_client, point_id=point_id, vector=vector, payload=payload)
    remove_pending_by_id(str(point_id))


def render_add(qdrant_client, images_dir: Path):
    st.subheader("Add photo")

    st.caption(
        "Tip: If AI captioning fails, you can provide caption/tags manually. "
        "If embedding/indexing fails, the upload is kept as *pending* and you can re-index later."
    )

    up = st.file_uploader("Upload image to index", type=["png", "jpg", "jpeg"])
    if up is None:
        _render_pending(qdrant_client, images_dir)
        return

    img = Image.open(up).convert("RGB")
    st.image(img, caption="Uploaded image", use_container_width=True)

    use_ai_caption = st.checkbox("Use AI to generate caption + tags", value=True)

    manual_caption = st.text_area(
        "Caption (optional if AI is on)",
        placeholder="e.g. A foggy forest in the morning with sun rays",
    )
    manual_tags = st.text_input(
        "Tags (comma-separated, optional)",
        placeholder="forest, fog, morning, nature",
    )

    if st.button("Index image", type="primary"):
        img_bytes = pil_to_png_bytes(img)
        point_id = stable_id_from_bytes(img_bytes)

        # Decide caption/tags
        caption_raw = manual_caption.strip()
        tags = [t.strip() for t in manual_tags.split(",") if t.strip()]

        if not caption_raw and use_ai_caption:
            try:
                caption_raw = describe_image(img_bytes)
            except Exception as e:
                st.warning(f"AI caption failed: {e}. Please enter caption manually.")
                append_history({"mode": "add", "status": "caption_failed", "error": str(e)[:300]})
                return

        if not caption_raw:
            st.error("Caption is required (either provide it manually or enable AI captioning).")
            return

        caption, parsed_tags = parse_caption_and_tags(caption_raw)
        # merge tags (manual + parsed) unique
        tags = sorted(set(tags) | set(parsed_tags))

        # Save image locally
        user_dir = images_dir / "user"
        user_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{point_id}.png"
        _save_image(img, user_dir, filename)

        rel_fname = str(Path("data/images/user") / filename)

        try:
            _index_one(
                qdrant_client,
                img,
                img_bytes,
                rel_fname,
                caption,
                tags,
                source="user_upload",
            )
            st.success("Indexed successfully ✅")
            append_history(
                {
                    "mode": "add",
                    "status": "indexed",
                    "id": str(point_id),
                    "filename": rel_fname,
                    "caption": caption,
                    "tags": tags,
                }
            )
        except Exception as e:
            # store pending
            add_pending(
                {
                    "id": str(point_id),
                    "filename": rel_fname,
                    "caption": caption,
                    "tags": tags,
                    "error": str(e)[:500],
                }
            )
            st.warning(
                "Indexing failed — saved as pending. You can retry later from the Pending section below."
            )
            st.code(str(e))
            append_history({"mode": "add", "status": "pending", "id": str(point_id), "error": str(e)[:300]})

    st.divider()
    _render_pending(qdrant_client, images_dir)


def _render_pending(qdrant_client, images_dir: Path):
    st.subheader("Pending uploads")

    pending = load_pending()
    if not pending:
        st.caption("No pending uploads.")
        return

    st.write(f"Pending items: **{len(pending)}**")

    # IMPORTANT: use enumerate to ensure Streamlit widget keys are always unique,
    # even if pending contains duplicate ids.
    for i, item in enumerate(list(reversed(pending))[:50]):
        pid = item.get("id", "")
        fname = item.get("filename", "")
        caption = item.get("caption", "")
        tags = item.get("tags", [])
        err = item.get("error", "")

        with st.expander(f"{pid} • {Path(fname).name}", expanded=False):
            img_path = Path(fname)
            if img_path.exists():
                st.image(str(img_path), use_container_width=True)

            st.write({"caption": caption, "tags": tags})

            if err:
                st.caption(f"Last error: {err}")

            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Retry indexing", key=f"retry_{pid}_{i}"):
                    try:
                        p = Path(fname)
                        if not p.exists():
                            st.error("File not found on disk.")
                        else:
                            img = Image.open(p).convert("RGB")
                            img_bytes = pil_to_png_bytes(img)
                            _index_one(
                                qdrant_client,
                                img,
                                img_bytes,
                                fname,
                                caption,
                                tags,
                                source="pending_retry",
                            )
                            st.success("Indexed ✅")
                            append_history({"mode": "pending_retry", "status": "indexed", "id": str(pid)})
                            st.rerun()
                    except Exception as e:
                        st.error(f"Retry failed: {e}")
                        append_history(
                            {"mode": "pending_retry", "status": "failed", "id": str(pid), "error": str(e)[:300]}
                        )

            with c2:
                if st.button("Remove from pending", key=f"rm_{pid}_{i}"):
                    remove_pending_by_id(str(pid))
                    append_history({"mode": "pending", "status": "removed", "id": str(pid)})
                    st.rerun()
