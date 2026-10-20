# CC4Q Workbench

Build sentence-level comment corpora from Python quantum SDKs and label them with a two-stage taxonomy. Inspect, annotate, evaluate, or fine-tune the resulting models through a web workbench, CLI, or Python API.

CC4Q Workbench accompanies our study in ACM Transactions on Software Engineering and Methodology (TOSEM), *Code Comments for Quantum Software Development Kits: An Empirical Study on Qiskit*. It ships six precomputed Qiskit-ecosystem corpora and a 361-unit unseen-SDK demo, so you can explore the workbench without downloading model checkpoints.

[![CI](https://github.com/MaxwelsDonc/cc4q-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/MaxwelsDonc/cc4q-workbench/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-violet.svg)](LICENSE)
[![Companion Paper: TOSEM](https://img.shields.io/badge/Companion%20Paper-ACM%20TOSEM%202026-6D28D9.svg)](#citation)

## Documentation

- [API reference](https://zhouzenghui.site/cc4q-workbench/api.html): public functions grouped by workflow.
- [Python API](https://zhouzenghui.site/cc4q-workbench/api/python.html), [HTTP API](https://zhouzenghui.site/cc4q-workbench/api/web.html), and [CLI reference](https://zhouzenghui.site/cc4q-workbench/api/cli.html).
- [Module index](https://zhouzenghui.site/cc4q-workbench/api/modules.html): every public module and its role.

## What you can do

- **Build a corpus** from a GitHub repository or a local Python checkout. The pipeline extracts comment/code pairs (CCPs) and segments them into sentence-level code comment units (SCCUs).
- **Inspect a snippet** and see each SCCU with its predicted quantum label and confidence, next to the enclosing source code.
- **Browse six bundled SDK corpora** by label, category, comment type, and entity type.
- **Label a sample** in the Annotation Studio, either blind or with model suggestions, then export a training-ready JSONL file.
- **Measure agreement** between human labels and model labels, with Cohen's kappa, precision, recall, F1, and a Wilson 95% confidence interval.
- **Fine-tune Task 1 or Task 2** on your own annotations and use the resulting model package in the workbench.

## Requirements

- Python 3.11 or newer.
- Git, if you build a corpus from a GitHub URL.
- Several GB of free disk for PyTorch and the optional checkpoints. The bundled corpora are about 23 MB; the two checkpoints are about 835 MB.
- CPU is enough. A CUDA GPU speeds up classification and training.
- Network access for the first dependency install and the optional checkpoint download.

## Quick start

This quick start is the shortest path for artifact reviewers. It uses the bundled corpora and does not download model checkpoints. The install still pulls PyTorch and the rest of the Python stack, so the first run can take several minutes.

### Windows

```bash
git clone https://github.com/MaxwelsDonc/cc4q-workbench.git
cd cc4q-workbench

# Create environment and install package
py -3.11 -m venv .venv
# Activate the virtual environment
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r demo/requirements-demo.txt
pip install -e .

# Launch the Starlette/Uvicorn Web Workbench at http://127.0.0.1:8501
cc4q demo
```

### macOS / Linux

```bash
git clone https://github.com/MaxwelsDonc/cc4q-workbench.git
cd cc4q-workbench

# Create environment and install package
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r demo/requirements-demo.txt
pip install -e .

# Launch the Starlette/Uvicorn Web Workbench at http://127.0.0.1:8501
cc4q demo
```

Open `http://127.0.0.1:8501`. The landing page aggregates the six bundled SDK corpora. The Annotation Studio contains the 361-unit unseen-SDK demo. Press `Ctrl+C` in the terminal to stop the server.

## Optional: live classification and training

The quick start can browse and annotate bundled data. To classify new code, build corpora from new repositories, or fine-tune the classifiers, download the two BERT checkpoints and the spaCy English model. The checkpoints are about 835 MB in total; `--check` verifies them without downloading.

```bash
python -m spacy download en_core_web_sm
cc4q download-models          # Downloads & SHA256-verifies released BERT checkpoints
cc4q download-models --check  # Verifies checkpoint integrity on disk
cc4q demo                     # Launch full interactive workbench at http://127.0.0.1:8501
```

If the server is already running, stop it and start `cc4q demo` again after the download.

## Docker

The Docker image is CPU-based. It downloads checkpoints at container start unless `CC4Q_SKIP_MODEL_DOWNLOAD=1` is set; with that flag, the bundled demo data still works.

```bash
# Build & run (exposes the Web Workbench on http://localhost:8501)
docker build -t cc4q-workbench .
docker run --rm -p 8501:8501 cc4q-workbench
```

## How it works

1. **Extract.** LibCST walks a Python file and records each docstring, inline comment, and contiguous block comment as a comment/code pair. Each record keeps its enclosing scope, line ranges, and code context.
2. **Segment.** A Sphinx/reST-aware parser splits docstrings into semantic blocks; spaCy splits inline and block comments into sentences. Each result is an SCCU.
3. **Classify.** Task 1 decides whether an SCCU is quantum-specific. Task 2 assigns one of six categories to quantum SCCUs.
4. **Use.** Browse the result in the web workbench, run the CLI, or call the Python API to sample, annotate, evaluate, or fine-tune a model.

## What the workbench does

| Task | Where to do it | Input | Output |
| :--- | :--- | :--- | :--- |
| Build a corpus | Corpus Builder, `cc4q build` | GitHub URL or local Python checkout | `comment_pairs.json` and `sccus_segmented.json` |
| Label SCCUs | `cc4q predict`, Python API | Segmented SCCUs with `comment_text` | Records with `quantum_related`, `quantum_prob`, `quantum_category`, and `category_confidence` |
| Inspect code | Live Inspector, HTTP API | Python snippet | SCCUs, two-stage labels, confidence, documentation audit |
| Draw a sample | Annotation Studio, `cc4q sample` | Labeled corpus | Random, stratified, or quota sample |
| Annotate | Annotation Studio, `cc4q annotate` | Sample JSONL; the CLI accepts a schema | `annotations.jsonl`, CSV and JSONL exports |
| Evaluate | `cc4q evaluate`, Python API | Annotation file and answer key | Agreement, kappa, precision/recall/F1, Wilson CI |
| Train | Model Trainer, `cc4q train` | Labeled JSONL | Fine-tuned model package |
| Manage assets | Workbench workspace | Corpora, sessions, evaluations | JSON index plus per-asset payload files |

## The five workbench tabs

| Tab | What it shows | What to try |
| :--- | :--- | :--- |
| Corpus Explorer | Six SDK dashboards, an aggregate overview, category profiles, and a source context viewer | Filter by quantum label, category, comment type, or entity type; click a unit to read its enclosing code |
| Live Inspector | A snippet editor with three quantum presets | Paste code, run the pipeline, and inspect each SCCU, label, category, and confidence |
| Corpus Builder | A four-stage repository pipeline | Use the prefilled `examples/tiny_repo` or a GitHub URL; open the result in Corpus Explorer |
| Annotation Studio | A blind labeling session for the 361-unit demo, or your own JSONL upload | Label with hotkeys, resume later, and export the session |
| Model Trainer | Task 1 and Task 2 fine-tuning from the bundled training data or an upload | Warm-start from the released checkpoints, set epochs and batch size, watch validation F1, then use the saved model |

## Core concepts

**CCP.** A comment/code pair extracted from the Python abstract syntax tree (AST). One docstring, one inline comment, or one contiguous block comment produces one CCP.

**SCCU.** A sentence-level code comment unit produced by segmenting a CCP. The pipeline keeps the comment type, enclosing entity, file path, line numbers, and source context.

**Two-stage taxonomy.** Task 1 decides whether an SCCU is quantum-specific. Task 2 assigns one of six categories to quantum SCCUs:

| Category | Typical content |
| :--- | :--- |
| Mathematics for quantum information | Hilbert spaces, operators, eigenstates, tensor products, amplitudes |
| Quantum algorithms | VQE, QAOA, Grover, Shor, QPE, amplitude estimation, quantum kernels |
| Quantum circuit model | Qubits, registers, gates, state preparation, circuit composition, measurement |
| Quantum hardware | Coupling maps, connectivity, T1/T2 relaxation times, gate and readout errors, pulse control |
| Quantum software framework | Compilers, transpilers, simulators, primitives, OpenQASM, cloud backends |
| Others | Quantum-specific comments that span several domains |

## Command line

| Command | What it does | Main output |
| :--- | :--- | :--- |
| `cc4q download-models` | Download and SHA256-verify the released checkpoints | Checkpoint directories |
| `cc4q build` | Clone or scan a repository and run extraction plus segmentation | `comment_pairs.json`, `sccus_segmented.json` |
| `cc4q predict` | Label segmented SCCUs on both quantum axes | Labeled JSONL |
| `cc4q sample` | Draw a random, stratified, or quota sample | Sampled JSONL |
| `cc4q annotate` | Prepare or launch an annotation session | Session directory; `annotations.jsonl` after labeling |
| `cc4q train` | Fine-tune one classifier | Model directory |
| `cc4q evaluate` | Compare human labels with a model answer key | Agreement and classification metrics |
| `cc4q demo` | Launch the workbench with reviewer defaults | Web server on `127.0.0.1:8501` |
| `cc4q serve` | Serve the workbench on a chosen host and port | Web server |

The `predict` command requires the checkpoints from the optional step. `annotate --dry-run` and `train --dry-run` validate their inputs without launching the UI or starting training.

Command-specific behavior:

- `build --clean-mode current_only|full|none` controls how much code context is kept in each SCCU. The CLI default is `current_only`.
- `annotate --mode blind|adjudicate` chooses whether the UI hides model labels or shows them for confirmation. A schema names the text column, id column, and label vocabulary.
- `evaluate --contaminated id1,id2,...` excludes ids that appeared in training from the agreement calculation.

### End-to-end CLI example

The block uses POSIX shell syntax (`\` for line continuation and `/tmp` paths). On Windows, use a local output directory and keep each command on one line.

```bash
# 1. Build a segmented comment corpus (CCPs -> SCCUs) from a local dir or GitHub URL
cc4q build --repo examples/tiny_repo --output-dir /tmp/cc4q_out

# 2. Predict two-stage quantum labels (quantum_related & quantum_category)
cc4q predict --input /tmp/cc4q_out/sccus_segmented.json \
             --output /tmp/cc4q_out/labeled.jsonl

# 3. Draw a stratified or random sample for human verification
cc4q sample --input /tmp/cc4q_out/labeled.jsonl --by comment_type \
            --n 50 --output /tmp/cc4q_out/sample.jsonl

# 4. Prepare or run an interactive annotation session
cc4q annotate --data /tmp/cc4q_out/sample.jsonl \
              --labels quantum,non-quantum --mode adjudicate \
              --predictions /tmp/cc4q_out/labeled.jsonl \
              --output-dir /tmp/cc4q_out/ann --dry-run

# 5. Fine-tune a custom Task 1 (quantum_related) or Task 2 (quantum_category) classifier
cc4q train --task quantum_related --data examples/tiny_labels.jsonl \
           --output-dir /tmp/cc4q_out/clf --dry-run

# 6. Compute human-vs-model agreement, Cohen's kappa, Precision/Recall, and Wilson 95% CI
cc4q evaluate --annotations exp/spotcheck_annotation.csv \
              --key exp/spotcheck_answer_key.jsonl \
              --contaminated 1,8,16,25,62,132

# 7. Launch the Web Workbench (Starlette/Uvicorn)
cc4q demo --host 127.0.0.1 --port 8501
```

## Python API

The top-level package exposes the common entry points as lazy aliases. The paths are illustrative; point them at your segmented corpus.

```python
import cc4q

models = cc4q.load_models()
labeled = cc4q.predict_corpus("out/algorithms/sccus_segmented.json", models=models)
quantum_units = [r for r in labeled if r["quantum_related"]]
```

The [Python API reference](https://zhouzenghui.site/cc4q-workbench/api/python.html) lists every public function, including `sample`, `annotate`, `evaluate`, and `train`.

## Data and benchmark

The repository includes six precomputed corpora under `cc4q/web/data/`, plus a 361-unit unseen-SDK demo. The table reports the corpus construction results used in the TOSEM study.

| SDK repository | Pinned release | Stack layer | Python files | CCPs | SCCUs | Quantum SCCUs | Quantum share | Comment density |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `qiskit` | `2.1.0` | Infrastructure | 1,038 | 9,677 | 21,970 | 7,778 | 35.4% | 0.126 |
| `qiskit-aer` | `0.17.2` | Infrastructure | 109 | 1,153 | 2,368 | 961 | 40.6% | 0.114 |
| `qiskit-ibm-runtime` | `0.45.1` | Infrastructure | 280 | 1,982 | 3,738 | 878 | 23.5% | 0.210 |
| **Infrastructure subtotal** | n/a | Infrastructure | 1,427 | 12,812 | 28,076 | 9,617 | 34.3% | n/a |
| `qiskit-machine-learning` | `0.9.1` | Application | 132 | 1,663 | 3,140 | 704 | 22.4% | 0.172 |
| `qiskit-nature` | `0.8` | Application | 246 | 2,037 | 4,842 | 1,379 | 28.5% | 0.127 |
| `qiskit-algorithms` | `0.4.0` | Application | 175 | 1,802 | 3,535 | 915 | 25.9% | 0.155 |
| **Application subtotal** | n/a | Application | 553 | 5,502 | 11,517 | 2,998 | 26.0% | n/a |
| **Total across six SDKs** | n/a | All layers | 1,980 | 18,314 | 39,593 | 12,615 | 31.9% | n/a |

Column definitions:

- **CCP**: comment/code pair extracted from the AST.
- **SCCU**: sentence-level unit after comment segmentation.
- **Quantum SCCUs**: SCCUs labeled quantum-specific.
- **Quantum share**: quantum SCCUs divided by all SCCUs.
- **Comment density**: comment lines divided by code lines in the repository checkout.

## Data locations

- Bundled corpora: `cc4q/web/data/` contains `manifest.json` and the per-SDK `units/*.jsonl` files.
- Workspace: `.cc4q_workspace/` in a source checkout, or the directory in `$CC4Q_WORKSPACE`.
- User models: `user_models/` in a source checkout, or the directory in `$CC4Q_USER_MODELS`.
- Checkpoints: `models_checkpoints/` in a source checkout, or the directory in `$CC4Q_MODEL_DIR`.

The workspace stores corpora, annotation sessions, and evaluation reports. Models are stored in the separate registry and referenced by id.

## Troubleshooting

**`cc4q: command not found`.** The virtual environment is not active, or the package was not installed. Activate the environment and run `pip install -e .` again. On Windows, the script is in `.venv\Scripts`; on macOS and Linux, in `.venv/bin`.

**spaCy model missing.** Run `python -m spacy download en_core_web_sm`.

**Checkpoint download is slow or fails.** Run `cc4q download-models --check` to see what is missing, then retry `cc4q download-models`. Browsing bundled data and the 361-unit demo do not need the checkpoints.

**Port 8501 is already in use.** Start the server on another port with `cc4q demo --port 8502`.

**The Annotation Studio does not open.** The standalone UI needs Streamlit and pandas from `demo/requirements-demo.txt`.

**Training is slow on CPU.** Lower the number of epochs or the batch size. GPU acceleration is optional.

## Repository layout

| Path | Contents |
| :--- | :--- |
| `cc4q/pipeline/` | LibCST extraction, Sphinx-aware segmentation, cleaning, and repository metrics |
| `cc4q/models/` | Checkpoint download, SHA256 verification, device resolution, and model loading |
| `cc4q/web/` | Starlette server, single-page UI, and bundled demo corpora |
| `cc4q/predict.py` | Two-stage inference and confidence scores |
| `cc4q/train.py` | Hugging Face Trainer wrapper, warm start, and schema normalization |
| `cc4q/evaluate.py` | Agreement, kappa, precision/recall/F1, and Wilson CI |
| `cc4q/sample.py` | Random, stratified, and quota sampling |
| `cc4q/workspace.py`, `cc4q/registry.py` | Asset persistence and user model registry |
| `cc4q/cli.py` | Typer command-line entry point |
| `config/` | Pinned repository configurations |
| `exp/`, `model/` | Unseen-SDK results, the human verification benchmark, and gold training data |
| `tests/` | Pytest suite |
| `Dockerfile`, `pyproject.toml` | Container image and package metadata |

## Citation

If you use CC4Q Workbench, the released classifiers, or the labeled corpora in your research, cite the companion study:

```bibtex
@article{cc4q2026tosem,
  author  = {Zhou, Zenghui and Li, Yuechen and Cai, Yi and Wen, Jinlong and Yu, Xiaohan and Zheng, Zheng and Yin, Beibei},
  title   = {Code Comments for Quantum Software Development Kits: An Empirical Study on Qiskit},
  journal = {ACM Transactions on Software Engineering and Methodology (TOSEM)},
  year    = {2026},
  note    = {Accepted for publication}
}
```

## License

Code, workbench UI, and annotations are released under the [MIT License](LICENSE). Extracted code and comment snippets remain under the Apache-2.0 license of their upstream Qiskit repositories; fine-tuned checkpoints derive from `bert-base-uncased` (Apache-2.0).
