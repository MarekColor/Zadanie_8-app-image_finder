from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.services.qdrant_service import ensure_collection_exists, get_qdrant_client
from src.ui.tab_add import render_add
from src.ui.tab_gallery import render_gallery
from src.ui.tab_history import render_history
from src.ui.tab_search import render_search

IMAGES_DIR = Path("data/images")


@st.cache_resource
def get_qdrant_cached():
    return get_qdrant_client()


def main() -> None:
    st.set_page_config(page_title="Image Finder", page_icon="🖼️", layout="wide")
    st.title("🖼️ Image Finder")

    qdrant = get_qdrant_cached()
    ensure_collection_exists(qdrant)

    options = ["Gallery", "Add photo", "Search", "History"]
    default_tab = st.session_state.get("menu", "Gallery")
    if default_tab not in options:
        default_tab = "Gallery"
    tab = st.radio("Menu", options, horizontal=True, index=options.index(default_tab), key="menu")

    if tab == "Gallery":
        render_gallery(qdrant)
    elif tab == "Add photo":
        render_add(qdrant, IMAGES_DIR)
    elif tab == "Search":
        render_search(qdrant)
    else:
        render_history()


if __name__ == "__main__":
    main()
