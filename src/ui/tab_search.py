from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

import streamlit as st
from PIL import Image

from src.config import settings
from src.features.embedding import embed_text
from src.features.vision import describe_image, pil_to_png_bytes
from src.services.qdrant_service import search, build_source_filter
from src.utils.history import append_history
from src.utils.saved_searches import load_saved


def _tokenize(text: str) -> List[str]:
    toks = re.findall(r"[a-zA-Z0-9]+", (text or "").lower())
    return [t for t in toks if len(t) >= 3]


def _tag_overlap_score(query: str, tags: List[str]) -> float:
    q = set(_tokenize(query))
    t = set([x.lower() for x in (tags or [])])
    if not q or not t:
        return float("nan")
    return len(q & t) / max(1, len(t))


def render_search(qdrant_client):
    st.subheader("Search")

    # Optional prefill from History → "Re-run"
    prefill = st.session_state.get("prefill_search") or {}
    prefill_mode = prefill.get("search_mode") or "Text → Image"
    prefill_query = prefill.get("query_text") or prefill.get("query_label") or ""
    prefill_source = prefill.get("source_filter") or prefill.get("source_choice") or "All"
    prefill_top_k = int(prefill.get("top_k") or settings.top_k)


    with st.expander("Search settings", expanded=True):
        # Load from saved searches (optional)
        saved_items = load_saved()
        if saved_items:
            names = [it.get('name') or it.get('id') for it in saved_items]
            pick = st.selectbox('Load saved search', ['(none)'] + names, index=0)
            if pick != '(none)':
                chosen = next((it for it in saved_items if (it.get('name')==pick) or (it.get('id')==pick)), None)
                if chosen and isinstance(chosen.get('params'), dict):
                    st.session_state['prefill_search'] = chosen['params']
                    st.session_state['run_search_once'] = False
                    st.rerun()

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            top_k = st.slider("Top-K", min_value=3, max_value=50, value=prefill_top_k, step=1)
        with col2:
            grid_cols = st.slider("Grid columns", min_value=2, max_value=6, value=3, step=1)
        with col3:
            source_opts = ["All", "Stock", "User uploads"]
            source_choice = st.selectbox("Filter", source_opts, index=source_opts.index(prefill_source) if prefill_source in source_opts else 0)

    mode_opts = ["Text → Image", "Image → Image"]
    mode = st.radio("Search mode", mode_opts, horizontal=True, index=mode_opts.index(prefill_mode) if prefill_mode in mode_opts else 0)

    query_vector: Optional[List[float]] = None
    query_label: str = ""

    if mode == "Text → Image":
        q = st.text_input("Describe what you are looking for", value=prefill_query if mode == "Text → Image" else "", placeholder="e.g. forest in fog, morning light")
        auto_run = bool(st.session_state.pop("run_search_once", False))
        if (auto_run and q) or st.button("Search", type="primary", disabled=not q):
            query_vector = embed_text(q)
            query_label = q
    else:
        up = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])
        if up is not None:
            img = Image.open(up).convert("RGB")
            st.image(img, caption="Query image", use_container_width=True)
            if st.button("Search", type="primary"):
                img_bytes = pil_to_png_bytes(img)
                caption = describe_image(img_bytes)
                query_vector = embed_text(caption)
                query_label = caption

    if query_vector is None:
        return

    st.caption(f"Query used for embedding: {query_label}")

    qfilter = build_source_filter(source_choice)
    results = search(qdrant_client, query_vector, top_k=top_k, qfilter=qfilter)

    # Save to local history
    try:
        append_history({
            "mode": "search",
            "search_mode": mode,
            "source_filter": source_choice,
            "top_k": top_k,
            "query_label": query_label[:500],
            "query_text": query_label[:500],
            "results": [
                {
                    "id": str(getattr(r, "id", "")),
                    "score": float(getattr(r, "score", 0.0)),
                    "filename": (getattr(r, "payload", {}) or {}).get("filename"),
                    "caption": (getattr(r, "payload", {}) or {}).get("caption"),
                }
                for r in results
            ],
        })
    except Exception:
        pass


    if not results:
        st.info("No results found.")
        return

    scores = [getattr(r, "score", None) for r in results if getattr(r, "score", None) is not None]
    if scores:
        st.write(
            f"Results: **{len(results)}** | similarity score (cosine): mean **{sum(scores)/len(scores):.4f}** | max **{max(scores):.4f}**"
        )

    # Pagination (client-side)
    page_size = grid_cols * 4
    total = len(results)
    pages = max(1, (total + page_size - 1) // page_size)
    page = st.number_input("Page", min_value=1, max_value=pages, value=1, step=1)
    start = (page - 1) * page_size
    end = min(total, start + page_size)
    view = results[start:end]

    cols = st.columns(grid_cols)
    for idx, r in enumerate(view):
        payload = r.payload or {}
        filename = payload.get("filename")
        caption = payload.get("caption", "")
        tags = payload.get("tags") or []
        score = getattr(r, "score", None)

        with cols[idx % grid_cols]:
            if filename and Path(str(filename)).exists():
                st.image(str(filename), use_container_width=True)
            else:
                st.write("(missing file)")
            cap_short = caption[:110] + ("..." if len(caption) > 110 else "")
            st.caption(cap_short)

            if tags:
                st.caption("#" + "  #".join(tags[:6]))
            if score is not None:
                st.caption(f"score: {score:.4f}")
            ov = _tag_overlap_score(query_label, tags) if tags else float("nan")
            if ov == ov:  # not NaN
                st.caption(f"tag overlap: {ov:.2f}")