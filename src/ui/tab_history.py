from __future__ import annotations

import csv
import datetime
import io
import json
from typing import Any, Dict, List, Tuple

import streamlit as st

from src.utils.history import load_history, clear_history
from src.utils.saved_searches import load_saved, add_saved, delete_saved


def _fmt_ts(ts: int) -> str:
    try:
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)


def _to_csv(items: List[Dict[str, Any]]) -> bytes:
    out = io.StringIO()
    fieldnames = [
        "ts",
        "mode",
        "search_mode",
        "query_text",
        "source_filter",
        "top_k",
        "results_filenames",
        "results_scores",
    ]
    w = csv.DictWriter(out, fieldnames=fieldnames)
    w.writeheader()
    for it in items:
        results = it.get("results") or []
        filenames = [str((r or {}).get("filename") or "") for r in results]
        scores = [str((r or {}).get("score") or "") for r in results]
        w.writerow(
            {
                "ts": it.get("ts"),
                "mode": it.get("mode"),
                "search_mode": it.get("search_mode"),
                "query_text": it.get("query_text") or it.get("query_label") or "",
                "source_filter": it.get("source_filter"),
                "top_k": it.get("top_k"),
                "results_filenames": "|".join(filenames),
                "results_scores": "|".join(scores),
            }
        )
    return out.getvalue().encode("utf-8")


def _history_key(it: Dict[str, Any]) -> str:
    ts = int(it.get("ts") or 0)
    q = (it.get("query_text") or it.get("query_label") or "")[:80]
    mode = it.get("search_mode") or it.get("mode") or ""
    return f"{_fmt_ts(ts)} • {mode} • {q}"


def _extract_params_from_history(it: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "search_mode": it.get("search_mode") or "Text → Image",
        "source_filter": it.get("source_filter") or "All",
        "top_k": int(it.get("top_k") or 10),
        "query_text": (it.get("query_text") or it.get("query_label") or "")[:500],
    }


def _run_search_from_params(params: Dict[str, Any]) -> None:
    st.session_state["prefill_search"] = dict(params)
    st.session_state["menu"] = "Search"
    st.session_state["run_search_once"] = True
    st.rerun()


def _render_timeline(items: List[Dict[str, Any]]) -> None:
    st.caption("Tip: click **Re-run** to open Search with the same parameters and run it automatically.")

    for it in reversed(items):
        ts = _fmt_ts(int(it.get("ts", 0)))
        mode = it.get("mode", "event")
        search_mode = it.get("search_mode", "")
        src = it.get("source_filter", "")
        q = it.get("query_text") or it.get("query_label") or ""

        title = f"{ts} • {mode}"
        if search_mode:
            title += f" • {search_mode}"
        if src:
            title += f" • {src}"

        with st.expander(title, expanded=False):
            cols = st.columns([1, 1, 2, 2])
            with cols[0]:
                if st.button("Re-run", key=f"rerun_{it.get('ts')}_{hash(q)}"):
                    _run_search_from_params(_extract_params_from_history(it))
            with cols[1]:
                st.write("**Query**")
                st.write(q if q else "(none)")
            with cols[2]:
                results = it.get("results") or []
                if results:
                    st.write("**Top results**")
                    for r in results[:10]:
                        fn = (r or {}).get("filename", "")
                        score = (r or {}).get("score", "")
                        st.write(f"- {fn} (score: {score})")
                else:
                    st.write("")
            with cols[3]:
                # Save search shortcut (works best for text queries)
                st.write("**Save**")
                default_name = (q[:40] + ("…" if len(q) > 40 else "")) if q else "saved search"
                name = st.text_input("Name", value=default_name, key=f"save_name_{it.get('ts')}_{hash(q)}")
                if st.button("Add to saved", key=f"save_btn_{it.get('ts')}_{hash(q)}"):
                    try:
                        add_saved(name=name, params=_extract_params_from_history(it))
                        st.success("Saved.")
                    except Exception as e:
                        st.error(str(e))

            with st.expander("Raw record", expanded=False):
                st.json(it, expanded=False)


def _render_saved() -> None:
    items = load_saved()
    if not items:
        st.info("No saved searches yet. Save one from Timeline.")
        return

    st.write(f"Saved searches: **{len(items)}**")

    for it in reversed(items):
        sid = str(it.get("id"))
        name = it.get("name") or sid
        created = _fmt_ts(int(it.get("created_ts") or 0))
        params = it.get("params") or {}
        subtitle = f"{created} • {params.get('search_mode','')} • {params.get('source_filter','')} • Top-{params.get('top_k','')}"

        with st.expander(f"{name}  —  {subtitle}", expanded=False):
            st.write("**Query**")
            st.write(params.get("query_text") or "(none)")

            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                if st.button("Run", key=f"run_saved_{sid}"):
                    _run_search_from_params(params)
            with c2:
                if st.button("Delete", key=f"del_saved_{sid}"):
                    delete_saved(sid)
                    st.success("Deleted.")
                    st.rerun()
            with c3:
                st.json(params, expanded=False)


def _pick_two_history(items: List[Dict[str, Any]]) -> Tuple[Dict[str, Any] | None, Dict[str, Any] | None]:
    if len(items) < 2:
        return None, None
    options = [(idx, _history_key(it)) for idx, it in enumerate(items)]
    labels = [lab for _, lab in options]
    i1 = st.selectbox("Pick first search", list(range(len(labels))), format_func=lambda i: labels[i], index=0)
    i2 = st.selectbox("Pick second search", list(range(len(labels))), format_func=lambda i: labels[i], index=min(1, len(labels)-1))
    if i1 == i2 and len(labels) > 1:
        i2 = (i1 + 1) % len(labels)
    return items[i1], items[i2]


def _render_compare(items: List[Dict[str, Any]]) -> None:
    st.caption("Compare two past searches side-by-side (Top results + scores).")

    a, b = _pick_two_history(items)
    if not a or not b:
        st.info("Need at least two searches in history.")
        return

    pa = _extract_params_from_history(a)
    pb = _extract_params_from_history(b)

    colA, colB = st.columns(2)
    for col, rec, params, label in [(colA, a, pa, "A"), (colB, b, pb, "B")]:
        with col:
            st.markdown(f"### {label}")
            st.write(f"**Mode:** {params.get('search_mode')}  |  **Filter:** {params.get('source_filter')}  |  **Top-K:** {params.get('top_k')}")
            st.write("**Query:**")
            st.write(params.get("query_text") or "(none)")
            if st.button(f"Re-run {label}", key=f"rerun_cmp_{label}_{rec.get('ts')}"):
                _run_search_from_params(params)

            results = rec.get("results") or []
            if not results:
                st.info("No results saved for this record.")
                continue

            # show top 8 as a simple list (no heavy grid here)
            for r in results[:8]:
                fn = (r or {}).get("filename")
                cap = (r or {}).get("caption") or ""
                score = (r or {}).get("score")
                if fn:
                    st.write(f"- **{fn}** (score: {score})")
                if cap:
                    st.caption(cap[:120] + ("…" if len(cap) > 120 else ""))


def _render_dashboard(items: List[Dict[str, Any]]) -> None:
    searches = [it for it in items if it.get("mode") == "search" or it.get("search_mode")]
    if not searches:
        st.info("No search events in history yet.")
        return

    total = len(searches)
    modes = {}
    filters = {}
    top1_scores = []
    mean_scores = []

    for it in searches:
        m = it.get("search_mode") or "unknown"
        f = it.get("source_filter") or "unknown"
        modes[m] = modes.get(m, 0) + 1
        filters[f] = filters.get(f, 0) + 1
        results = it.get("results") or []
        scores = [float((r or {}).get("score") or 0.0) for r in results if (r or {}).get("score") is not None]
        if scores:
            top1_scores.append(scores[0])
            mean_scores.append(sum(scores) / len(scores))

    st.metric("Total searches", total)
    if top1_scores:
        st.metric("Avg Top-1 score", f"{sum(top1_scores)/len(top1_scores):.4f}")
    if mean_scores:
        st.metric("Avg mean Top-K score", f"{sum(mean_scores)/len(mean_scores):.4f}")

    st.write("### Breakdown")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**By mode**")
        st.json(modes, expanded=False)
    with c2:
        st.write("**By filter**")
        st.json(filters, expanded=False)

    # Quick table: last 20 searches
    st.write("### Recent searches (last 20)")
    rows = []
    for it in searches[:20]:
        q = (it.get("query_text") or it.get("query_label") or "")[:80]
        results = it.get("results") or []
        top1 = None
        if results:
            top1 = float((results[0] or {}).get("score") or 0.0)
        rows.append(
            {
                "time": _fmt_ts(int(it.get("ts") or 0)),
                "mode": it.get("search_mode"),
                "filter": it.get("source_filter"),
                "top_k": it.get("top_k"),
                "top1_score": top1,
                "query": q,
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_history() -> None:
    st.subheader("History")

    colA, colB, colC, colD = st.columns([1, 1, 1, 2])
    with colA:
        limit = st.number_input("Show last N", min_value=10, max_value=500, value=150, step=10)
    with colB:
        if st.button("Clear history"):
            clear_history()
            st.success("History cleared.")
            st.rerun()

    items = load_history(limit=int(limit))

    # Export (history only)
    with colC:
        if items:
            st.download_button(
                "Export JSON",
                data=json.dumps(items, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name="history.json",
                mime="application/json",
            )
    with colD:
        if items:
            st.download_button(
                "Export CSV",
                data=_to_csv(items),
                file_name="history.csv",
                mime="text/csv",
            )

    if not items:
        st.info("No history yet.")
        return

    t1, t2, t3, t4 = st.tabs(["Timeline", "Saved searches", "Compare", "Dashboard"])
    with t1:
        _render_timeline(items)
    with t2:
        _render_saved()
    with t3:
        _render_compare(items)
    with t4:
        _render_dashboard(items)
