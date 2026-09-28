# CC4Q Generalization Experiment — New Qiskit-Ecosystem Repositories

Date: 2026-09-29
Pipeline: CC4Q workbench stages 01–03 (download → CCP extraction → SCCU segmentation)
Environment: Python 3.13.12 (miniconda-based venv, see `.venv/`; system Python 3.9.6 is too old for Sphinx 8.2.3), macOS.
Pinned release tags were resolved via `git ls-remote --tags` on 2026-09-29. All three repos have active releases; none are archived.

## Repositories

| Repository | Pinned tag |
|---|---|
| qiskit-community/qiskit-machine-learning | 0.9.1 |
| qiskit-community/qiskit-nature | 0.8 |
| qiskit-community/qiskit-algorithms | 0.4.0 |

## Corpus statistics

CCP = code–comment pair (stage-02 output). SCCU = sentence-level comment unit (stage-03 output).
Comment-type and code-entity breakdowns are over CCPs; the SCCU column shows the total segmented units.

| Repository | Version | .py files | CCPs | SCCUs | docstring | block | inline | module | class | function |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit-machine-learning | 0.9.1 | 123 | 1,663 | 3,140 | 740 | 779 | 144 | 270 | 201 | 1,192 |
| qiskit-nature | 0.8 | 175 | 2,037 | 4,842 | 1,077 | 801 | 159 | 401 | 211 | 1,425 |
| qiskit-algorithms | 0.4.0 | 152 | 1,802 | 3,535 | 899 | 715 | 188 | 318 | 213 | 1,271 |
| **Total** | — | **450** | **5,502** | **11,517** | **2,716** | **2,295** | **491** | **989** | **625** | **3,888** |

SCCU breakdown by parent comment type:

| Repository | docstring SCCUs | block SCCUs | inline SCCUs |
|---|---:|---:|---:|
| qiskit-machine-learning | 2,153 | 842 | 145 |
| qiskit-nature | 3,723 | 959 | 160 |
| qiskit-algorithms | 2,567 | 780 | 188 |
| **Total** | **8,443** | **2,581** | **493** |

## Wall-clock time per pipeline stage (single run, Apple-silicon Mac, 2026-09-29)

| Repository | Clone (stage 01) | Extraction (stage 02) | Segmentation (stage 03) | Total (02+03) |
|---|---:|---:|---:|---:|
| qiskit-machine-learning | ~3 s | 3.35 s | 6.93 s | 10.28 s |
| qiskit-nature | ~3 s | 2.72 s | 8.16 s | 10.88 s |
| qiskit-algorithms | ~3 s | 1.88 s | 6.71 s | 8.59 s |
| **Total (3 repos)** | **~9 s** | **7.95 s** | **21.80 s** | **29.75 s** |

Corpus construction for all three repositories (extraction + segmentation, excluding the one-time
dependency install of ~2 min and the ~9 s clone) took **under 30 seconds** in total.

## Notes

- `include_dirs` in each config scopes processing to the package source directory only
  (`qiskit_machine_learning/`, `qiskit_nature/`, `qiskit_algorithms/`); the `docs/` trees
  (`.rst` files) and `test/` directories are excluded, matching the original SDK configs.
- No extraction errors were logged (`Error processing` count = 0 across all repos).
- No pipeline bugs were hit; stages 02–03 ran unmodified.
- The stage-03 inline SCCU counts (145/160/188) slightly exceed the inline CCP counts
  (144/159/188) because the inline-comment segmenter occasionally splits one CCP into two
  sentence-level units.

## Reproduction

```bash
cd cc4q-workbench

# One-time environment setup (system python3 is 3.9.6, too old for Sphinx 8.2.3;
# use a newer interpreter, e.g. miniconda's python3.13)
/opt/homebrew/Caskroom/miniconda/base/bin/python3.13 -m venv .venv
source .venv/bin/activate
pip install libcst==1.8.2 PyYAML==6.0.2 loguru==0.7.3 "tqdm>=4.60" \
            docutils==0.21.2 Sphinx==8.2.3 spacy==3.8.7 nltk==3.9.1
python -m spacy download en_core_web_sm

# Stage 01: download (script 01 uses the default-branch HEAD and ignores tags, so clone
# pinned tags explicitly)
git clone --depth 1 --branch 0.9.1 https://github.com/qiskit-community/qiskit-machine-learning data/input/qiskit-machine-learning
git clone --depth 1 --branch 0.8     https://github.com/qiskit-community/qiskit-nature           data/input/qiskit-nature
git clone --depth 1 --branch 0.4.0   https://github.com/qiskit-community/qiskit-algorithms       data/input/qiskit-algorithms

# Stages 02 & 03: extraction and segmentation (repeat per repo)
for cfg in qiskit-machine-learning qiskit-nature qiskit-algorithms; do
  python scripts/02_extract_code_comment_pairs.py config/config_${cfg}.yaml
  python scripts/03_segment_comments.py          config/config_${cfg}.yaml
done

# Statistics
python exp/compute_stats.py
```
