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

---

# Three-Axis BERT Labeling (generalization corpora)

Date: 2026-09-29. Classifiers: release checkpoints (BERT-base, `models_checkpoints/`, copied unmodified from the TOSEM release), run on CPU (`CC4Q_DEVICE=cpu`; the MPS path hung on this machine with torch 2.14.0), batch size 32, max length 512. torch 2.14.0, transformers 5.17.0. Driver: `exp/run_inference.py`; machine-readable summary: `exp/labeling_summary.json`; per-unit labels: `data/output/<repo>/labeled/sccus_labeled.json`.

Workflow (mirrors the release inference scripts): (1) binary quantum-related classifier on **all** SCCUs; (2) 6-class quantum-category classifier on the quantum-related SCCUs only; (3) 6-class developer-intent classifier on **all** SCCUs.

## Axis 1 — quantum-related SCCUs

| Repository | SCCUs | Quantum SCCUs | Proportion |
|---|---:|---:|---:|
| qiskit-machine-learning | 3,140 | 704 | 22.4% |
| qiskit-nature | 4,842 | 1,379 | 28.5% |
| qiskit-algorithms | 3,535 | 915 | 25.9% |
| **Overall** | **11,517** | **2,998** | **26.0%** |

The overall quantum proportion (26.0%) is below the ~34% reported for the original three core SDKs — expected: these ecosystem packages wrap classical ML/optimization/chemistry workflows and reference quantum concepts less densely than the core SDKs. (Original-SDK comparison numbers to be inserted from the TOSEM paper camera-ready.)

## Axis 2 — developer intent (all SCCUs, row %)

| Repository | What | How-to-use | How-it-is-done | Property | Why | Others |
|---|---:|---:|---:|---:|---:|---:|
| qiskit-machine-learning | 55.3% | 5.3% | 12.1% | 9.5% | 3.9% | 14.0% |
| qiskit-nature | 54.5% | 6.4% | 10.1% | 11.6% | 4.4% | 12.9% |
| qiskit-algorithms | 55.0% | 4.4% | 12.1% | 9.6% | 5.0% | 13.9% |

## Axis 3 — quantum category (quantum SCCUs only, row %)

| Repository | Math for QI | Quantum algorithms | Quantum circuit model | Quantum hardware | Quantum software framework | Others |
|---|---:|---:|---:|---:|---:|---:|
| qiskit-machine-learning | 11.4% | 8.1% | 28.4% | 11.4% | 37.5% | 3.3% |
| qiskit-nature | 28.9% | 2.9% | 16.4% | 11.7% | 32.9% | 7.3% |
| qiskit-algorithms | 11.3% | 11.0% | 29.4% | 8.9% | 33.3% | 6.1% |

qiskit-nature skews toward *Mathematics for quantum information* (second-quantized operators, tensors) and away from *Quantum algorithms*, consistent with its domain; the other two repos are dominated by *Quantum software framework* and *Quantum circuit model*.

## Inference wall-clock (seconds, prediction only, CPU)

| Classifier | qiskit-machine-learning | qiskit-nature | qiskit-algorithms | Total |
|---|---:|---:|---:|---:|
| quantum_related (all SCCUs) | 152.2 | 220.1 | 181.6 | 553.8 |
| quantum_category (quantum SCCUs) | 62.5 | 105.5 | 102.4 | 270.4 |
| developer_intent (all SCCUs) | 169.5 | 235.6 | 342.9 | 747.9 |
| **Per-repo total** | **384.1** | **561.1** | **626.9** | **1,572.1 (~26 min)** |

## Sanity check — 10 random units per repo (seed 42)

| Repo | SCCU text (truncated) | Quantum | Category | Intent |
|---|---|---|---|---|
| q-ml | Neural networks may be used, for example, with the ~qiskit_machine_learning.algorithms. | no | – | How-to-use |
| q-ml | Returns: | no | – | What |
| q-ml | pylint: disable=arguments-differ Disable Lint warnings caused by different number of parameters… | no | – | Others |
| q-ml | This code is part of a Qiskit project. (C) Copyright IBM 2022, 2026… | no | – | Others |
| q-ml | training loop | no | – | What |
| q-ml | Returns the used feature map. | no | – | What |
| q-ml | List of truncated fidelities. | yes | Math for QI | What |
| nature | The terms to be summed are encoded in a dictionary, where each operator product is identified by its key… | yes | Math for QI | How-it-is-done |
| nature | pylint: disable=broad-except | no | – | Others |
| nature | No need to multiply the coefficient by -1 due to commutation relations | no | – | Why |
| nature | Sample a random two-body tensor with real-valued orbitals. | yes | Math for QI | What |
| nature | FCIDump (qiskit_nature.second_q.formats.fcidump) | no | – | Others |
| alg | Run the single job with all circuits. | yes | Quantum software framework | What |
| alg | Some amplitude estimators, such as .AmplitudeEstimation do not support a custom implementation of the is_good_state function… | yes | Quantum software framework | Property |
| alg | product_formula: A Lie-Trotter-Suzuki product formula. If None provided (default), the ~qiskit.synthesis.LieTrotter… | yes | Quantum software framework | What |
| alg | scaling_factor: The scaling factor in [0, 1]. | no | – | What |
| alg | perform optimization | no | – | What |
| alg | type: ignore[arg-type] | no | – | Others |

Assessment: labels are plausible. Boilerplate (copyright headers, pylint disables) is consistently non-quantum / Others; API-description fragments ("Returns the used feature map.") are What; genuinely quantum units receive sensible categories and intents. Two soft spots, both inherited from the SCCU granularity rather than the classifier: bare docstring headers like "Returns:" get What, and fragment units (".unfold_s8_to_s1.") are noisy input.

## Reproduction (labeling)

```bash
cd cc4q-workbench && source .venv/bin/activate

# one-time: inference deps (CPU-only torch is fine; ~1.3 GB wheel on macOS)
pip install torch transformers datasets scikit-learn

# checkpoints: copy the three release model dirs (unmodified) to models_checkpoints/
#   models_checkpoints/quantum_related   <- .../BERT_QR_classifier/saved_model
#   models_checkpoints/quantum_category  <- .../BERT_QC_classifier/saved_best_model
#   models_checkpoints/developer_intent  <- .../BERT_DI_classifier/saved_best_model

# label all three corpora (CPU; set CC4Q_DEVICE to override device selection)
CC4Q_DEVICE=cpu python exp/run_inference.py
```
