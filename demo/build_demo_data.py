"""Build the committed demo dataset under cc4q/web/data/.

Sources
-------
* New SDKs (3): the release-quality labeled corpora produced by the CC4Q
  pipeline itself, ``data/output/<repo>/labeled/sccus_labeled.json``.
  All SCCUs are kept.
* Original SDKs (3): the TOSEM release gold corpus
  ``CCPs_final_modified_r2_cleaned_validated.jsonl`` (SCCU-level records).
  Per-SDK statistics are computed over the FULL corpus, while the demo keeps
  a 2,000-row random sample (seed 42) per SDK.
* Comment density: recomputed at build time from the pinned repo checkouts
  under ``data/input/``.

Each unit includes a compact source-code context window (`code_snippet`,
`comment_line`, `code_line`) and focuses exclusively on Quantum-Specific
analysis (`quantum_related` and `quantum_category`).
"""

import json
import os
import random
import subprocess
import sys
from collections import Counter

DEMO_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DEMO_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cc4q.web import DATA_DIR  # noqa: E402

UNITS_DIR = os.path.join(DATA_DIR, "units")

SAMPLE_SIZE = 2000
SAMPLE_SEED = 42

REPO_SOURCES = {
    "qiskit": ("https://github.com/Qiskit/qiskit", "2.1.0", ["qiskit"]),
    "qiskit-aer": ("https://github.com/Qiskit/qiskit-aer", "0.17.2", ["qiskit_aer"]),
    "qiskit-ibm-runtime": ("https://github.com/Qiskit/qiskit-ibm-runtime",
                           "0.45.1", ["qiskit_ibm_runtime"]),
    "qiskit-machine-learning": ("https://github.com/qiskit-community/qiskit-machine-learning",
                                "0.9.1", ["qiskit_machine_learning"]),
    "qiskit-nature": ("https://github.com/qiskit-community/qiskit-nature",
                      "0.8", ["qiskit_nature"]),
    "qiskit-algorithms": ("https://github.com/qiskit-community/qiskit-algorithms",
                          "0.4.0", ["qiskit_algorithms"]),
}

NEW_SDKS = ["qiskit-machine-learning", "qiskit-nature", "qiskit-algorithms"]
ORIGINAL_SDKS = ["qiskit", "qiskit-aer", "qiskit-ibm-runtime"]

ORIGINAL_GOLD = os.path.join(
    PROJECT_ROOT, "..", "TOSEM paper", "CC4Q_release", "data", "final_data",
    "CCPs_final_modified_r2_cleaned_validated.jsonl",
)

CATEGORY_CANON = {
    "mathematics-for-quantum": "Mathematics for quantum information",
    "quantum-algorithm": "Quantum algorithms",
    "quantum-circuit-model": "Quantum circuit model",
    "quantum-hardware": "Quantum hardware",
    "quantum-software-stack": "Quantum software framework",
    "quantum-others": "Others",
}
CATEGORY_ORDER = [
    "Mathematics for quantum information", "Quantum algorithms",
    "Quantum circuit model", "Quantum hardware",
    "Quantum software framework", "Others",
]


def _file_of(unit):
    dp = unit.get("dirPath")
    if isinstance(dp, list):
        return "/".join(dp) or "(root)"
    if isinstance(dp, str) and dp:
        return dp
    return unit.get("file", "(root)")


from cc4q.predict import compact_snippet as _compact_snippet


def _lean_unit(unit, sdk, version):
    comment_text = unit.get("comment_text", "")
    raw_snippet = unit.get("code_snippet", "")
    return {
        "id": unit.get("id", ""),
        "sdk": sdk,
        "version": version,
        "file": _file_of(unit),
        "comment_type": unit.get("comment_type", ""),
        "code_entity_type": unit.get("code_entity_type", ""),
        "comment_text": comment_text,
        "code_snippet": _compact_snippet(raw_snippet, comment_text),
        "comment_line": unit.get("comment_line") or [],
        "code_line": unit.get("code_line") or [],
        "quantum_related": bool(unit.get("quantum_related")),
        "quantum_category": unit.get("quantum_category") if unit.get("quantum_related") else None,
    }


def _quantum_residence(units):
    """Quantum SCCU counts per (comment_type, entity_level), quantum only."""
    table = {}
    for u in units:
        if not u["quantum_related"]:
            continue
        table.setdefault(u["comment_type"], Counter())[u["code_entity_type"]] += 1
    return {c: dict(sorted(e.items())) for c, e in sorted(table.items())}


def _stats(sdk, version, units, sampled, comment_density=None, python_files=None):
    """Aggregate stats + distributions over a list of units."""
    n = len(units)
    n_quantum = sum(1 for u in units if u["quantum_related"])
    category_counts = Counter(
        u["quantum_category"] for u in units if u["quantum_related"] and u["quantum_category"]
    )
    ctype_by_entity = {}
    for u in units:
        ctype_by_entity.setdefault(u["comment_type"], Counter())[u["code_entity_type"]] += 1
    return {
        "sdk": sdk,
        "version": version,
        "layer": "infrastructure" if sdk in ORIGINAL_SDKS else "application",
        "source": "cc4q-pipeline" if not sampled else "tosem-release",
        "sampled": sampled,
        "python_files": python_files,
        "files": len({u["file"] for u in units}),
        "ccps": n if sampled else None,
        "sccps": n,
        "sccus": n,
        "quantum_sccus": n_quantum,
        "quantum_proportion": round(n_quantum / n, 4) if n else 0.0,
        "comment_density": comment_density or {"comment_lines": 0, "code_lines": 0, "value": 0.0},
        "category_counts": {k: category_counts.get(k, 0) for k in CATEGORY_ORDER},
        "ctype_by_entity": {
            ctype: dict(sorted(entities.items()))
            for ctype, entities in sorted(ctype_by_entity.items())
        },
        "quantum_ctype_by_entity": _quantum_residence(units),
        "comment_type_counts": dict(sorted(Counter(u["comment_type"] for u in units).items())),
        "entity_type_counts": dict(sorted(Counter(u["code_entity_type"] for u in units).items())),
    }


def ensure_clone(sdk):
    url, tag, include_dirs = REPO_SOURCES[sdk]
    path = os.path.join(PROJECT_ROOT, "data", "input", sdk)
    current = None
    if os.path.isdir(os.path.join(path, ".git")):
        try:
            current = subprocess.run(
                ["git", "-C", path, "describe", "--tags", "--exact-match"],
                capture_output=True, text=True, timeout=30).stdout.strip()
        except Exception:
            current = None
    if current == tag:
        return path
    if os.path.exists(path):
        print(f"  re-cloning {sdk}: found tag {current!r}, need {tag}")
        subprocess.run(["rm", "-rf", path], check=True)
    print(f"  cloning {sdk} @ {tag} …")
    subprocess.run(["git", "clone", "--depth", "1", "--branch", tag, url, path],
                   check=True)
    return path


def density_for(sdk):
    from cc4q.pipeline.metrics import compute_comment_density

    _, _, include_dirs = REPO_SOURCES[sdk]
    path = ensure_clone(sdk)
    return compute_comment_density(path, include_dirs)


def python_file_count(sdk):
    from cc4q.pipeline.metrics import iter_py_files

    _, _, include_dirs = REPO_SOURCES[sdk]
    path = ensure_clone(sdk)
    return sum(1 for _ in iter_py_files(path, include_dirs))


def build_new_sdk(sdk):
    version = REPO_SOURCES[sdk][1]
    labeled = os.path.join(PROJECT_ROOT, "data", "output", sdk, "labeled",
                           "sccus_labeled.json")
    ccp_file = os.path.join(PROJECT_ROOT, "data", "output", sdk,
                            "comment_pairs_current_only.json")
    with open(labeled, "r", encoding="utf-8") as f:
        raw = json.load(f)
    units = [_lean_unit(u, sdk, version) for u in raw]
    stats = _stats(sdk, version, units, sampled=False,
                   comment_density=density_for(sdk),
                   python_files=python_file_count(sdk))
    if os.path.exists(ccp_file):
        with open(ccp_file, "r", encoding="utf-8") as f:
            stats["ccps"] = len(json.load(f))
    else:
        stats["ccps"] = stats["sccus"]
    return stats, units


def _canon_original(record):
    cat_raw = record.get("quantum_specific_category")
    is_q = bool(record.get("is_quantum_specific"))
    category = CATEGORY_CANON.get(cat_raw) if (is_q and cat_raw) else None
    comment_text = record.get("comment_text", "")
    raw_snippet = record.get("code_snippet", "")
    return {
        "id": record.get("id", ""),
        "sdk": record.get("SDK", ""),
        "version": record.get("version", ""),
        "file": _file_of(record),
        "comment_type": record.get("comment_type", ""),
        "code_entity_type": record.get("code_entity_type", ""),
        "comment_text": comment_text,
        "code_snippet": _compact_snippet(raw_snippet, comment_text),
        "comment_line": record.get("comment_line") or [],
        "code_line": record.get("code_line") or [],
        "quantum_related": is_q,
        "quantum_category": category,
    }


def build_original_sdks():
    """One streaming pass: full-corpus stats + seeded reservoir sampling."""
    if not os.path.exists(ORIGINAL_GOLD):
        sys.exit(f"Gold corpus not found: {ORIGINAL_GOLD}")

    target_sdks = set(ORIGINAL_SDKS)
    versions = {}
    files = {s: set() for s in target_sdks}
    n_total = Counter()
    n_quantum = Counter()
    max_pair_id = Counter()
    category_counts = {s: Counter() for s in target_sdks}
    ctype_by_entity = {s: {} for s in target_sdks}
    quantum_ctype = {s: {} for s in target_sdks}
    ctype_counts = {s: Counter() for s in target_sdks}
    entity_counts = {s: Counter() for s in target_sdks}
    reservoirs = {s: [] for s in target_sdks}
    rng = random.Random(SAMPLE_SEED)

    with open(ORIGINAL_GOLD, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            sdk = record.get("SDK")
            if sdk not in target_sdks:
                continue
            unit = _canon_original(record)
            versions.setdefault(sdk, record.get("version", ""))
            n_total[sdk] += 1
            try:
                pair_id = int(str(record.get("id", "")).split("-", 1)[0])
                max_pair_id[sdk] = max(max_pair_id[sdk], pair_id)
            except ValueError:
                pass
            if unit["quantum_related"]:
                n_quantum[sdk] += 1
            files[sdk].add(unit["file"])
            if unit["quantum_related"] and unit["quantum_category"]:
                category_counts[sdk][unit["quantum_category"]] += 1
            ctype_by_entity[sdk].setdefault(unit["comment_type"], Counter())[unit["code_entity_type"]] += 1
            if unit["quantum_related"]:
                quantum_ctype[sdk].setdefault(unit["comment_type"], Counter())[unit["code_entity_type"]] += 1
            ctype_counts[sdk][unit["comment_type"]] += 1
            entity_counts[sdk][unit["code_entity_type"]] += 1
            reservoir = reservoirs[sdk]
            if len(reservoir) < SAMPLE_SIZE:
                reservoir.append(unit)
            else:
                j = rng.randrange(n_total[sdk])
                if j < SAMPLE_SIZE:
                    reservoir[j] = unit

    stats_map, units_map = {}, {}
    for sdk in sorted(target_sdks):
        units = reservoirs[sdk]
        n = n_total[sdk]
        stats = {
            "sdk": sdk,
            "version": versions.get(sdk, ""),
            "layer": "infrastructure",
            "source": "tosem-release",
            "sampled": True,
            "sample_size": SAMPLE_SIZE,
            "sample_seed": SAMPLE_SEED,
            "python_files": python_file_count(sdk),
            "files": len(files[sdk]),
            "ccps": max_pair_id[sdk],
            "sccus": n,
            "quantum_sccus": n_quantum[sdk],
            "quantum_proportion": round(n_quantum[sdk] / n, 4) if n else 0.0,
            "comment_density": density_for(sdk),
            "category_counts": {k: category_counts[sdk].get(k, 0) for k in CATEGORY_ORDER},
            "ctype_by_entity": {
                c: dict(sorted(e.items()))
                for c, e in sorted(ctype_by_entity[sdk].items())
            },
            "quantum_ctype_by_entity": {
                c: dict(sorted(e.items()))
                for c, e in sorted(quantum_ctype[sdk].items())
            },
            "comment_type_counts": dict(sorted(ctype_counts[sdk].items())),
            "entity_type_counts": dict(sorted(entity_counts[sdk].items())),
        }
        stats_map[sdk] = stats
        units_map[sdk] = units
    return stats_map, units_map


def write_units(sdk, units):
    path = os.path.join(UNITS_DIR, f"{sdk}.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for u in units:
            f.write(json.dumps(u, ensure_ascii=False) + "\n")
    return path


def _group_aggregate(manifest, members):
    sccus = sum(manifest["repos"][s]["sccus"] for s in members)
    quantum = sum(manifest["repos"][s]["quantum_sccus"] for s in members)
    cat_totals = Counter()
    for s in members:
        for k, v in manifest["repos"][s]["category_counts"].items():
            cat_totals[k] += v
    return {
        "sdks": list(members),
        "sccus": sccus,
        "quantum_sccus": quantum,
        "quantum_proportion": round(quantum / sccus, 4) if sccus else 0.0,
        "category_counts": {k: cat_totals.get(k, 0) for k in CATEGORY_ORDER},
    }


def main():
    os.makedirs(UNITS_DIR, exist_ok=True)
    manifest = {"generated_by": "demo/build_demo_data.py",
                "sample_seed": SAMPLE_SEED, "repos": {}}
    total_units = 0

    for sdk in NEW_SDKS:
        stats, units = build_new_sdk(sdk)
        manifest["repos"][sdk] = stats
        write_units(sdk, units)
        total_units += len(units)
        print(f"[new]      {sdk:28s} files={stats['files']:5d} "
              f"ccps={stats['ccps']:6d} sccus={len(units):6d} "
              f"quantum={stats['quantum_sccus']:5d} "
              f"density={stats['comment_density']['value']:.4f}")

    stats_map, units_map = build_original_sdks()
    for sdk in sorted(stats_map):
        stats = stats_map[sdk]
        units = units_map[sdk]
        manifest["repos"][sdk] = stats
        write_units(sdk, units)
        total_units += len(units)
        print(f"[original] {sdk:28s} files={stats['files']:5d} "
              f"ccps={stats['ccps']:6d} sampled={len(units):6d} "
              f"quantum={stats['quantum_sccus']:5d} "
              f"density={stats['comment_density']['value']:.4f}")

    manifest["groups"] = {
        "infrastructure": _group_aggregate(manifest, ORIGINAL_SDKS),
        "application": _group_aggregate(manifest, NEW_SDKS),
    }
    manifest["total_demo_units"] = total_units
    with open(os.path.join(DATA_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    size = sum(os.path.getsize(os.path.join(dp, fn))
               for dp, _, fns in os.walk(DATA_DIR) for fn in fns)
    print(f"\nWrote {total_units} demo units, "
          f"{len(manifest['repos'])} repos, total {size / 1e6:.1f} MB "
          f"-> {DATA_DIR}")


if __name__ == "__main__":
    main()
