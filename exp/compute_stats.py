"""Compute per-repo statistics for the CC4Q generalization experiment.

Reads the stage-02 (CCP) and stage-03 (SCCU) outputs produced by
scripts/02_extract_code_comment_pairs.py and scripts/03_segment_comments.py,
and prints a JSON summary used to build exp/generalization_results.md and
exp/generalization_table.tex.

Usage (from the workbench root, with .venv activated):
    python exp/compute_stats.py
"""

import json
import os
import sys
from collections import Counter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import yaml
from utils.get_files_from_dir import get_files_from_dir

REPOS = [
    ("qiskit-machine-learning", "0.9.1"),
    ("qiskit-nature", "0.8"),
    ("qiskit-algorithms", "0.4.0"),
]
CLEAN_MODE = "current_only"

MISSING_HINT = """\
[✗] Required pipeline output not found: {path}

This script reads the stage-02/03 outputs of the generalization experiment,
which are not part of the git checkout. To reproduce them:

  1. Clone the pinned repos:   python scripts/01_download_repos.py config/repo_list_generalization.yaml
  2. For each repo config in config/config_qiskit-*.yaml:
       python scripts/02_extract_code_comment_pairs.py <config>
       python scripts/03_segment_comments.py <config>
  3. Label the SCCUs:          python exp/run_inference.py   (needs the checkpoints)

See exp/generalization_results.md for the full reproduction walkthrough.
"""


def require(path):
    if not os.path.isfile(path):
        sys.exit(MISSING_HINT.format(path=path))


def load_config(project):
    cfg_path = os.path.join(PROJECT_ROOT, "config", f"config_{project}.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    stats = {}
    for project, version in REPOS:
        cfg = load_config(project)
        base_dir = os.path.join(PROJECT_ROOT, cfg["input_dir"])
        output_dir = os.path.join(PROJECT_ROOT, cfg["output_dir"])

        py_files = get_files_from_dir(base_dir, cfg.get("include_dirs", []))

        ccp_file = os.path.join(output_dir, f"comment_pairs_{CLEAN_MODE}.json")
        require(ccp_file)
        with open(ccp_file, "r", encoding="utf-8") as f:
            ccps = json.load(f)

        sccu_file = os.path.join(
            output_dir, "segmented", f"comment_pairs_{CLEAN_MODE}_segmented.json"
        )
        require(sccu_file)
        with open(sccu_file, "r", encoding="utf-8") as f:
            sccus = json.load(f)

        by_type = Counter(r.get("comment_type", "unknown") for r in ccps)
        by_entity = Counter(r.get("code_entity_type", "unknown") for r in ccps)

        # SCCU breakdown by the parent CCP's comment type
        ccp_type_by_id = {r["id"]: r.get("comment_type", "unknown") for r in ccps}
        sccu_by_type = Counter()
        for s in sccus:
            parent_id = s.get("id", "").rsplit("-", 1)[0]
            sccu_by_type[ccp_type_by_id.get(parent_id, "unknown")] += 1

        stats[project] = {
            "version": version,
            "py_files": len(py_files),
            "ccps": len(ccps),
            "sccus": len(sccus),
            "ccp_by_type": dict(by_type),
            "ccp_by_entity": dict(by_entity),
            "sccu_by_type": dict(sccu_by_type),
        }

    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
