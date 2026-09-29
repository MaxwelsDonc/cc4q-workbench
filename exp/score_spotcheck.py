"""Score the human spot-check of model-labeled quantum-axis labels.

Usage (from the workbench root):
    python exp/score_spotcheck.py

Reads exp/spotcheck_annotation.csv (preferred; fill the `human_label` column
with "quantum" or "non-quantum" in Excel/Numbers — blank rows are skipped) or
exp/spotcheck_annotation.jsonl, plus exp/spotcheck_answer_key.jsonl, then
prints per-repo and overall agreement, precision/recall for the quantum axis,
and a Wilson 95% CI for the pooled agreement estimate.
"""

import csv
import json
import math
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_annotations():
    csv_path = os.path.join(ROOT, "exp", "spotcheck_annotation.csv")
    jsonl_path = os.path.join(ROOT, "exp", "spotcheck_annotation.jsonl")
    if os.path.exists(csv_path):
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    with open(jsonl_path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - half, center + half


def report(name, pairs):
    n = len(pairs)
    agree = sum(1 for h, m in pairs if h == m)
    tp = sum(1 for h, m in pairs if m == "quantum" and h == "quantum")
    fp = sum(1 for h, m in pairs if m == "quantum" and h != "quantum")
    fn = sum(1 for h, m in pairs if m != "quantum" and h == "quantum")
    prec = tp / (tp + fp) if (tp + fp) else float("nan")
    rec = tp / (tp + fn) if (tp + fn) else float("nan")
    lo, hi = wilson_ci(agree, n)
    print(f"{name}: n={n} agreement={100*agree/n:.1f}% "
          f"(95% CI {100*lo:.1f}-{100*hi:.1f}) "
          f"precision={100*prec:.1f}% recall={100*rec:.1f}%")


def main():
    ann = load_annotations()
    key = {r["no"]: r["model_label"] for r in load("exp/spotcheck_answer_key.jsonl")}

    pairs_by_repo = defaultdict(list)
    skipped = 0
    for r in ann:
        h = r.get("human_label", "").strip().lower()
        if h not in ("quantum", "non-quantum"):
            skipped += 1
            continue
        pairs_by_repo[r["repo"]].append((h, key[r["no"]]))

    if skipped:
        print(f"skipped {skipped} unlabeled entries\n")
    all_pairs = []
    for repo, pairs in sorted(pairs_by_repo.items()):
        report(repo, pairs)
        all_pairs.extend(pairs)
    if not all_pairs:
        print("no labeled entries yet - fill the human_label column in "
              "exp/spotcheck_annotation.csv first")
        return
    report("OVERALL", all_pairs)


if __name__ == "__main__":
    main()
