from __future__ import annotations

from pathlib import Path
import streamlit as st

from src.services.qdrant_service import list_points


def render_gallery(qdrant_client):
    st.subheader("Gallery")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        grid_cols = st.slider("Grid columns", 2, 6, 4, 1)
    with col2:
        source_choice = st.selectbox("Filter", ["All", "Stock", "User uploads"], index=0)
    with col3:
        page_size = st.selectbox("Page size", [12, 24, 36, 48], index=1)

    items = list_points(qdrant_client, limit=500)
    if not items:
        st.info("No images indexed yet. Use 'Add photo' or run seed script.")
        return

    if source_choice == "Stock":
        items = [it for it in items if (it.get("payload", {}) or {}).get("stock") is True]
    elif source_choice == "User uploads":
        items = [it for it in items if (it.get("payload", {}) or {}).get("stock") is False]

    total = len(items)
    pages = max(1, (total + page_size - 1) // page_size)
    page = st.number_input("Page", min_value=1, max_value=pages, value=1, step=1)
    start = (page - 1) * page_size
    end = min(total, start + page_size)
    view = items[start:end]

    cols = st.columns(grid_cols)
    for i, it in enumerate(view):
        payload = it.get("payload") or {}
        fn = payload.get("filename")
        cap = payload.get("caption", "")
        tags = payload.get("tags") or []
        with cols[i % grid_cols]:
            if fn and Path(str(fn)).exists():
                st.image(str(fn), use_container_width=True)
            else:
                st.write("(missing file)")
            st.caption(cap[:110] + ("..." if len(cap) > 110 else ""))
            if tags:
                st.caption("#" + "  #".join(tags[:6]))
