"""Page — Explore Corpus: filters + paginated table over labeled SCCUs."""

import streamlit as st

from cc4q.app import data_io  # noqa: E402
from cc4q.app.ui import footer  # noqa: E402


def _filter_frame(df):
    include_nonquantum = st.toggle("Include non-quantum units", value=False)
    with st.expander("Filters", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            cats = st.multiselect("Quantum category", data_io.CATEGORY_ORDER,
                                  default=[])
            entity_choices = [e for e in data_io.ENTITY_ORDER
                              if e in set(df["code_entity_type"])] or \
                             sorted(df["code_entity_type"].unique())
            entities = st.multiselect("Code entity level", entity_choices,
                                      default=[])
        with c2:
            ctype_choices = [c for c in data_io.CTYPE_ORDER
                             if c in set(df["comment_type"])] or \
                            sorted(df["comment_type"].unique())
            ctypes = st.multiselect("Comment form", ctype_choices, default=[])
            sdks = st.multiselect("SDK", sorted(df["sdk"].unique()),
                                  default=sorted(df["sdk"].unique()))
            st.caption("No SDK selection = all SDKs.")
        with c3:
            keyword = st.text_input("Keyword search (comment text)",
                                    placeholder="e.g. entangle, backend, VQE "
                                                "(press Enter to apply)")

    # developer intent stays in the data layer (units JSONL, downloads) —
    # it is not an Explore filter (design doc §2, quantum-centric)
    out = df if include_nonquantum else df[df["quantum_related"]]
    if cats:
        out = out[out["quantum_category"].isin(cats)]
    if entities:
        out = out[out["code_entity_type"].isin(entities)]
    if ctypes:
        out = out[out["comment_type"].isin(ctypes)]
    if sdks:
        out = out[out["sdk"].isin(sdks)]
    if keyword.strip():
        out = out[out["comment_text"].str.contains(keyword.strip(),
                                                    case=False, na=False)]
    return out


def _display(out):
    c1, c2, _ = st.columns([1, 1, 4])
    with c1:
        page_size = st.selectbox("Rows per page", [25, 50, 100, 250], index=1)
    total = len(out)
    max_page = max(1, (total - 1) // page_size + 1)
    with c2:
        page = st.number_input("Page", min_value=1, max_value=max_page,
                               value=1, step=1)
    page = min(int(page), max_page)
    start = (page - 1) * page_size
    chunk = out.iloc[start:start + page_size]

    if total:
        st.caption(f"{total:,} units match — showing rows {start + 1:,}–"
                   f"{min(start + page_size, total):,}.")
    else:
        st.caption("0 units match — adjust or clear the filters.")
    st.dataframe(
        chunk[["sdk", "file", "comment_type", "code_entity_type",
               "comment_text", "quantum_related", "quantum_category"]],
        width="stretch",
        hide_index=True,
        column_config={
            "sdk": "SDK",
            "file": "File",
            "comment_type": "Comment form",
            "code_entity_type": "Entity level",
            "comment_text": st.column_config.TextColumn("Comment text",
                                                        width="large"),
            "quantum_related": st.column_config.CheckboxColumn("Quantum?"),
            "quantum_category": "Quantum category",
        },
    )


def render():
    st.header("Explore Corpus")
    st.write(
        "Browse the labeled SCCUs behind the workbench: the full corpora of "
        "the three newest SDKs (qiskit-machine-learning, qiskit-nature, "
        "qiskit-algorithms) plus 2,000-row seeded samples from each of the "
        "three original SDKs (qiskit, qiskit-aer, qiskit-ibm-runtime). "
        "The default view shows quantum units only."
    )

    df = data_io.load_all_units()
    out = _filter_frame(df)
    _display(out)

    st.download_button(
        "Download filtered units (JSONL)",
        data=data_io.units_to_jsonl_bytes(out),
        file_name="cc4q_explore_filtered.jsonl",
        mime="application/x-jsonlines",
        disabled=len(out) == 0,
    )

    footer()


render()
