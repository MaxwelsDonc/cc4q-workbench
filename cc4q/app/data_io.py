"""Loading and aggregation for the committed precomputed demo dataset
(cc4q/app/data/, shipped as package data).

The app reads ONLY from that directory for precomputed content; nothing
here touches data/output/ or the TOSEM release at runtime.
"""

import json
import os

import pandas as pd
import streamlit as st

from cc4q.app import DATA_DIR as _PKG_DATA  # package data dir

DATA_DIR = _PKG_DATA
UNITS_DIR = os.path.join(DATA_DIR, "units")
MANIFEST_PATH = os.path.join(DATA_DIR, "manifest.json")

INTENT_ORDER = ["What", "How-to-use", "How-it-is-done", "Property", "Why", "Others"]
CATEGORY_ORDER = [
    "Mathematics for quantum information", "Quantum algorithms",
    "Quantum circuit model", "Quantum hardware",
    "Quantum software framework", "Others",
]
CATEGORY_SHORT = {
    "Mathematics for quantum information": "Mathematics",
    "Quantum algorithms": "Algorithms",
    "Quantum circuit model": "Circuit model",
    "Quantum hardware": "Hardware",
    "Quantum software framework": "Software stack",
    "Others": "Others",
}
ENTITY_ORDER = ["module", "class", "function"]
CTYPE_ORDER = ["docstring", "block", "inline"]


@st.cache_data(show_spinner=False)
def load_manifest():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def load_units_df(sdk):
    """Labeled units for one SDK as a DataFrame."""
    path = os.path.join(UNITS_DIR, f"{sdk}.jsonl")
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    df["quantum_related"] = df["quantum_related"].astype(bool)
    return df


@st.cache_data(show_spinner=False)
def load_all_units():
    """Every labeled unit across all 6 SDKs (for Explore)."""
    manifest = load_manifest()
    frames = [load_units_df(sdk) for sdk in sorted(manifest["repos"])]
    return pd.concat(frames, ignore_index=True)


def repo_options(manifest):
    """Ordered [(sdk, 'sdk (version)')] for selectboxes."""
    return [(sdk, f"{sdk} ({info['version']})")
            for sdk, info in sorted(manifest["repos"].items())]


def units_to_jsonl_bytes(df):
    return "\n".join(
        json.dumps(record, ensure_ascii=False)
        for record in df.to_dict(orient="records")
    ).encode("utf-8")


def distribution_frame(stats_list, key, order):
    """Build a {label: sdk -> count} long/wide frame for grouped bars."""
    return pd.DataFrame(
        {s["sdk"]: pd.Series(s[key]).reindex(order).fillna(0)
         for s in stats_list}
    ).fillna(0)


def ctype_entity_frame(stats):
    """comment_type x entity_level counts -> DataFrame (ctypes x entities)."""
    frame = pd.DataFrame(
        {ctype: pd.Series(entities) for ctype, entities in stats["ctype_by_entity"].items()}
    ).fillna(0).astype(int)
    frame = frame.reindex(index=ENTITY_ORDER)
    return frame.reindex(columns=CTYPE_ORDER).dropna(axis=1, how="all").fillna(0).astype(int)


def quantum_residence_frame(stats):
    """Quantum SCCU *share* per (entity_level, comment_type).

    Rows = entity levels, columns = comment forms, values = share of all
    quantum SCCUs (0..1). NaN where the corpus has no such cell.
    """
    table = stats.get("quantum_ctype_by_entity", {})
    counts = pd.DataFrame(
        {ctype: pd.Series(entities) for ctype, entities in table.items()}
    )
    counts = counts.reindex(index=ENTITY_ORDER, columns=CTYPE_ORDER)
    total = counts.sum().sum()
    shares = counts / total if total else counts * float("nan")
    return shares


def radar_shares(stats):
    """Six category shares of quantum SCCUs, in CATEGORY_ORDER."""
    n_quantum = stats.get("quantum_sccus", 0)
    counts = stats.get("category_counts", {})
    if not n_quantum:
        return [0.0] * len(CATEGORY_ORDER)
    return [counts.get(k, 0) / n_quantum for k in CATEGORY_ORDER]


def radar_labels():
    return [CATEGORY_SHORT[k] for k in CATEGORY_ORDER]
