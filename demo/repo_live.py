"""Live repository analysis for the demo: clone -> extract -> segment -> label.

Reuses the workbench pipeline scripts (02/03) and the shared three-axis
inference helpers from cc4q_analysis.py. Everything runs in a temp dir; the
repo is refused up front when it has more than MAX_PY_FILES Python files
(pointing big repos at the Docker route instead).
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pandas as pd
import yaml

DEMO_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DEMO_DIR)
if DEMO_DIR not in sys.path:
    sys.path.insert(0, DEMO_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cc4q_analysis import classify_sccu_records  # noqa: E402
from repo_metrics import compute_comment_density, quantum_residence  # noqa: E402

MAX_PY_FILES = 200
CLONE_TIMEOUT = 180
SCRIPT_TIMEOUT = 600

GITHUB_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/([^/\s]+)/([^/\s#?]+?)(?:\.git)?/?$"
)


class RepoRefusedError(Exception):
    """Raised when a repo falls outside the demo guardrails."""


def parse_github_url(url):
    match = GITHUB_RE.match(url.strip())
    if not match:
        raise RepoRefusedError(
            "That does not look like a GitHub repository URL. "
            "Expected something like https://github.com/owner/repo."
        )
    owner, repo = match.group(1), match.group(2)
    return f"{owner}/{repo}", f"https://github.com/{owner}/{repo}.git"


def _count_py_files(root):
    n = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in {".git", ".venv", "venv", "__pycache__"}]
        n += sum(1 for fn in filenames if fn.endswith(".py"))
    return n


def _run(cmd, cwd, stage, timeout):
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          timeout=timeout)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-8:]
        raise RuntimeError(
            f"{stage} failed (exit {proc.returncode}):\n" + "\n".join(tail)
        )
    return proc


def analyze_live_repo(url, models, progress=None):
    """Full live pipeline. ``progress(stage_name)`` is called between stages.

    Returns (stats_dict, units_df) with the same shapes the precomputed
    dashboard consumes.
    """
    repo_slug, clone_url = parse_github_url(url)
    repo_name = repo_slug.split("/")[-1]
    workdir = tempfile.mkdtemp(prefix="cc4q_live_")
    try:
        # Stage 1: Cloning
        if progress:
            progress("Cloning")
        _run(["git", "clone", "--depth", "1", clone_url, repo_name],
             cwd=workdir, stage="git clone", timeout=CLONE_TIMEOUT)
        repo_dir = os.path.join(workdir, repo_name)

        n_py = _count_py_files(repo_dir)
        if n_py > MAX_PY_FILES:
            raise RepoRefusedError(
                f"This repository has {n_py} Python files, which exceeds the "
                f"live-demo limit of {MAX_PY_FILES}. For large repositories, "
                f"run the full CC4Q pipeline with Docker — see the repository's "
                f"README — then point the workbench at its labeled output."
            )

        out_dir = os.path.join(workdir, "output")
        config_path = os.path.join(workdir, "config.yaml")
        config = {
            "clean_mode": "current_only",
            "project": repo_name,
            "version": "live",
            "language": "python",
            "input_dir": workdir,
            "output_dir": out_dir,
            "include_dirs": [repo_name],
            "pipeline": {"analyze": False, "segment": True},
        }
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f)

        # Stage 2: Extracting
        if progress:
            progress("Extracting")
        _run([sys.executable, os.path.join("scripts", "02_extract_code_comment_pairs.py"),
              config_path], cwd=PROJECT_ROOT, stage="extraction",
             timeout=SCRIPT_TIMEOUT)

        # Stage 3: Segmenting
        if progress:
            progress("Segmenting")
        _run([sys.executable, os.path.join("scripts", "03_segment_comments.py"),
              config_path], cwd=PROJECT_ROOT, stage="segmentation",
             timeout=SCRIPT_TIMEOUT)

        seg_path = os.path.join(out_dir, "segmented",
                                "comment_pairs_current_only_segmented.json")
        ccp_path = os.path.join(out_dir, "comment_pairs_current_only.json")
        with open(ccp_path, "r", encoding="utf-8") as f:
            n_ccps = len(json.load(f))
        with open(seg_path, "r", encoding="utf-8") as f:
            records = json.load(f)

        # Stage 4: Labeling
        if progress:
            progress("Labeling")
        if records:
            classify_sccu_records(records, models)
        density = compute_comment_density(repo_dir)  # whole cloned repo
        return _build_result(repo_name, n_py, n_ccps, records,
                             comment_density=density)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _build_result(repo_name, n_py, n_ccps, records, comment_density=None):
    rows = []
    for r in records:
        rows.append({
            "id": r.get("id", ""),
            "sdk": repo_name,
            "version": "live",
            "file": "/".join(r.get("dirPath") or []) or "(root)",
            "comment_type": r.get("comment_type", ""),
            "code_entity_type": r.get("code_entity_type", ""),
            "comment_text": r.get("comment_text", ""),
            "quantum_related": bool(r.get("quantum_related")),
            "developer_intent": r.get("developer_intent", "Others"),
            "quantum_category": r.get("quantum_category"),
        })
    df = pd.DataFrame(rows)
    n = len(df)
    n_quantum = int(df["quantum_related"].sum()) if n else 0
    ctype_by_entity = {}
    if n:
        for ctype, group in df.groupby("comment_type"):
            ctype_by_entity[ctype] = {
                ent: int(cnt) for ent, cnt in group["code_entity_type"].value_counts().items()
            }
    stats = {
        "sdk": repo_name,
        "version": "live",
        "source": "live",
        "sampled": False,
        "files": n_py,
        "ccps": n_ccps,
        "sccus": n,
        "quantum_sccus": n_quantum,
        "quantum_proportion": round(n_quantum / n, 4) if n else 0.0,
        "comment_density": comment_density or {"comment_lines": 0, "code_lines": 0, "value": 0.0},
        "intent_counts": (df["developer_intent"].value_counts().to_dict() if n else {}),
        "category_counts": (df[df["quantum_related"]]["quantum_category"]
                            .value_counts().to_dict() if n else {}),
        "ctype_by_entity": ctype_by_entity,
        "quantum_ctype_by_entity": quantum_residence(rows),
        "comment_type_counts": (df["comment_type"].value_counts().to_dict() if n else {}),
        "entity_type_counts": (df["code_entity_type"].value_counts().to_dict() if n else {}),
    }
    return stats, df
