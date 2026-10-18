# CC4Q Workbench — Quantum Code Comment Corpus Construction, Labeling & Model Adaptation Studio

[![CI](https://github.com/MaxwelsDonc/cc4q-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/MaxwelsDonc/cc4q-workbench/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-violet.svg)](LICENSE)
[![Companion Paper: TOSEM](https://img.shields.io/badge/Companion%20Paper-ACM%20TOSEM%202026-6D28D9.svg)](#citation)

**CC4Q Workbench** is an open-source, end-to-end experimentation and curation workbench for **Quantum Software Engineering (QSE)** code documentation research and practice. It operationalizes and extends the methodology of our ACM TOSEM companion study (*"Code Comments for Quantum Software Development Kits: An Empirical Study on Qiskit"*), turning any Python-based quantum SDK repository into a structured, sentence-level comment corpus labeled across our **Two-Stage Quantum-Specific Taxonomy**, while providing an interactive **Web Studio** and **CLI/Python API** for human-in-the-loop data labeling, custom BERT fine-tuning, and cross-SDK evaluation.

---

## 📚 Documentation

- **API reference:** [zhouzenghui.site/cc4q-workbench/api.html](https://zhouzenghui.site/cc4q-workbench/api.html) — grouped by workflow (pipeline, models, inference, training/evaluation, annotation, workspace, HTTP, CLI).
- **Python API:** [top-level API](https://zhouzenghui.site/cc4q-workbench/api/python.html) · **HTTP API:** [Workbench routes](https://zhouzenghui.site/cc4q-workbench/api/web.html) · **CLI:** [commands](https://zhouzenghui.site/cc4q-workbench/api/cli.html)
- **Module index:** [all public modules](https://zhouzenghui.site/cc4q-workbench/api/modules.html)

---

## ⚡ Reviewer Quick-Start (Zero-Friction Evaluation)

For ICSE Tool Demonstration & Artifact Reviewers, CC4Q Workbench supports three evaluation tiers depending on your available time and hardware:

### Tier 1 · 30-Second Instant Exploration (No Model Download Required)

All precomputed corpora across **6 Qiskit-ecosystem SDKs (39,593 labeled sentence units)** and a **361-unit unseen-SDK labeling demo** (derived from our human-verified spot-check benchmark) are bundled directly in the repository (`cc4q/web/data/`, ~23 MB) with full Python source-code context (`code_snippet` + line numbers).

#### Windows

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

#### macOS / Linux

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

Open **`http://127.0.0.1:8501`** in your browser to immediately explore the 6 SDK dashboards, inspect source-linked comment units, and label the 361-unit unseen-SDK demo session.

### Tier 2 · Full Live Inference, Repository Building & In-Tool Model Training

To enable **live code snippet classification**, **building corpora for new GitHub repositories**, and **warm-start BERT fine-tuning** in the browser or CLI, download the SHA256-verified released checkpoints (~835 MB for the two quantum classifiers) and the spaCy English sentence model:

```bash
python -m spacy download en_core_web_sm
cc4q download-models          # Downloads & SHA256-verifies released BERT checkpoints
cc4q download-models --check  # Verifies checkpoint integrity on disk
cc4q demo                     # Launch full interactive workbench at http://127.0.0.1:8501
```

### Tier 3 · All-in-One Docker Container

```bash
# Build & run (exposes the Web Workbench on http://localhost:8501)
docker build -t cc4q-workbench .
docker run --rm -p 8501:8501 cc4q-workbench
```

(The image is single-flavor and CPU-based; every push is build- and
run-verified by CI, so no manual Docker verification is needed.)

---

## 🧭 System Architecture & Two-Stage Quantum Taxonomy

Unlike classical software comment tools that target generic Java API docstrings, **CC4Q Workbench** is purpose-built for Python quantum SDKs where domain semantics (superposition, entanglement, Hamiltonians, qubit topology, and decoherence constraints) are carried in complex Sphinx/reStructuredText/LaTeX docstrings and inline gate comments.

```text
┌───────────────────────────────────────────────────────────────────────────────────┐
│                         CC4Q WORKBENCH ARCHITECTURE (v2.0)                        │
├───────────────────────────────────────────────────────────────────────────────────┤
│  STAGE 1: CORPUS CONSTRUCTION PIPELINE (cc4q.pipeline)                            │
│  [GitHub Repo / Local Dir] ──► LibCST AST Scope Parser (CCPs)                     │
│                            ──► ~30 Sphinx-Directive Shims + spaCy (SCCUs)         │
├───────────────────────────────────────────────────────────────────────────────────┤
│  STAGE 2: TWO-STAGE QUANTUM-SPECIFIC CLASSIFICATION (cc4q.models / cc4q.predict)  │
│  [Task 1 · Binary BERT]    ──► Quantum-Specific vs. Non-Quantum (Held-out F1 .936)│
│  [Task 2 · 6-Class BERT]   ──► Mathematics | Algorithms | Circuit Model |         │
│                                Hardware | Software Framework | Others (F1 .840)   │
├───────────────────────────────────────────────────────────────────────────────────┤
│  STAGE 3: INTERACTIVE WEB WORKBENCH (Starlette/Uvicorn + ECharts SPA) & CLI       │
│  Tabs: 1. Corpus Explorer (Benchmark Overview + per-SDK dashboards & Compare) ·   │
│        2. Live Inspector (snippet labeling) · 3. Corpus Builder (4-stage repo     │
│        pipeline) · 4. Annotation Studio (labeling & verification) ·               │
│        5. Model Trainer (warm-start fine-tuning)                                  │
└───────────────────────────────────────────────────────────────────────────────────┘
```

### Two-Stage Quantum-Specific Taxonomy

Every **Sentence-level Code Comment Unit (SCCU)** is linked to its enclosing AST entity (`module`, `class`, `function`) and comment form (`docstring`, `block`, `inline`), and labeled across two hierarchical quantum stages:

| Stage & Task | Category | Definition & Representative Quantum Scope |
| :--- | :--- | :--- |
| **Task 1 · Binary**<br>(`quantum_related`) | **Quantum-Specific (`1`)**<br>vs. **Non-Quantum (`0`)** | An SCCU is marked **Quantum-Specific** iff it satisfies *(1) Domain Relevance* (quantum physics/computing concepts), *(2) Exclusivity* (not shared with classical computing), and *(3) Explicitness* (direct mention in the sentence). |
| **Task 2 · 6-Class**<br>(`quantum_category`)<br>*(Applied to Quantum SCCUs)* | **1. Mathematics for quantum info** | Hilbert spaces, unitary/Hermitian operators, Pauli/fermionic matrices, eigenstates, tensor products, and probability amplitudes. |
| | **2. Quantum algorithms** | High-level quantum/variational algorithms and problem mappings: VQE, QAOA, Grover, Shor, QPE, amplitude estimation, quantum kernels. |
| | **3. Quantum circuit model** | Qubits, quantum/classical registers, logic gates (`H`, `CX`, `RZ`), state preparation, circuit composition, and projective measurements. |
| | **4. Quantum hardware** | Physical QPU constraints: coupling maps, qubit connectivity, $T_1/T_2$ thermal relaxation/dephasing, gate/readout error rates, pulse control. |
| | **5. Quantum software framework** | Compilers, transpiler passes, simulators, runtime primitives (`Estimator`/`Sampler`), OpenQASM intermediate representations, cloud backends. |
| | **6. Others** | Quantum-specific comments spanning multiple domains or conveying general quantum context not attributable to a single primary class above. |

---

## 🖥️ 5-Minute Reviewer Walkthrough (Web Workbench)

Once `cc4q demo` is running at **`http://127.0.0.1:8501`**, the top navigation bar guides you through five integrated studios:

### 1. Corpus Explorer & Cross-SDK Compare (`Tab 1`)
* **TOSEM Benchmark Overview (landing)**: the default view aggregates **all six repositories** into collective headline metrics (**39,593 comment sentences · 31.9% quantum-specific · 6 SDKs** — 3 TOSEM-infrastructure + 3 application SDKs we analyzed with this workbench), an aggregate knowledge profile and residence heatmap, and a per-SDK breakdown table (infrastructure subtotal **28,076 @ 34.3%**, application subtotal **11,517 @ 26.0%**) — click any row to drill into that SDK.
* **Infrastructure vs. Application Layer Discovery**: Switch between the 3 infrastructure SDKs (`qiskit`, `qiskit-aer`, `qiskit-ibm-runtime`) and 3 application SDKs (`qiskit-nature`, `qiskit-algorithms`, `qiskit-machine-learning`). Click **`⇄ Compare SDKs`** to overlay any two SDKs on a dual radar chart and inspect our central empirical finding: **infrastructure SDKs carry 34.3% quantum-specific comments vs. 26.0% in application SDKs**.
* **Chart-to-Code Bidirectional Filtering**: Click any bar in **What Quantum Topics They Cover (6 Categories)** (e.g., *Mathematics* at 28.9% in `qiskit-nature`) or any cell in **Where Quantum Comments Live (`Form × Entity`)** to filter the unit list below.
* **IDE-Style Source Context Viewer**: Click any comment unit on the left to inspect its exact enclosing Python source code (`code_snippet`), file path, and highlighted comment line on the right.

### 2. Live Code Inspector (`Tab 2`)
* **Live Code Snippet Inspector**: Load one of the 3 one-click quantum presets (*Bell State Circuit*, *VQE Algorithm*, *Hardware Transpiler*) or paste custom Python code. Click **`⚡ Extract, Segment & Classify Quantum Comments`** to inspect:
  * Every segmented SCCU with its **Quantum Confidence badge (%)** and its **quantum-knowledge category badge** — results render only after you click, so what you see always matches the code on the left.

### 3. Corpus Builder (`Tab 3`)
* **4-Stage Repository Corpus Builder**: Keep the pre-filled local path `examples/tiny_repo` (or paste any GitHub URL), and click **`🚀 Build & Label Corpus`**. Watch the 4 stages execute live (acquire → LibCST extraction → Sphinx segmentation → quantum labeling) and open the newly built corpus directly in the Explorer.

### 4. Annotation Studio — Human-in-the-Loop Data Labeling (`Tab 4`)
* **Blind Labeling Demo**: the studio opens as a two-card landing — **`📂 Load Demo Benchmark (361 units)`** loads the pre-built *Unseen SDKs Labeling Demo* (361 unlabeled comment sentences from the 3 application-layer SDKs, each with its enclosing Python source context), and **`⬆ Upload JSONL to Label`** accepts your own `.jsonl`/`.json` (up to 1,000 records). Nothing is shown until you load a session.
* **Purely Manual, No Model Leakage**: the interface deliberately shows only a **Progress** counter — no model pre-labels, no agreement/κ/P-R metrics, no disagreement filters — so your labels are never biased by model predictions (the human-vs-model agreement study behind this benchmark lives in `exp/` and the CLI).
* **Ergonomic Keyboard-Driven Labeling**: Use hotkeys **`Q`** (Quantum-Specific), **`N`** (Non-Quantum), **`1`–`6`** (Six Quantum Categories), and **`←`/`→`** to move between items manually — labeling stays on the current item so both step choices remain visible. **`⬇ Export Labeled JSONL`** downloads the session with your labels.

### 5. Model Trainer (`Tab 5`)
* **Train Your Own Quantum Classifier in the Browser** (fine-tuning always warm-starts from the released CC4Q BERT checkpoints):
  1. Select **Task 1 (`quantum_related`, 2 classes)** or **Task 2 (`quantum_category`, 6 classes)**.
  2. Select a **Training Data Source**: the built-in **Demo Dataset** (TOSEM gold training data — 2,802 binary / 1,800 balanced 6-class records) or **Upload Your Own JSONL**.
  3. Name the model, tune **⚙️ Training Parameters** (Epochs · Batch Size), and click **`🚀 Start Fine-Tuning`** to watch the asynchronous progress bar and real-time **Train Loss & Validation F1 ECharts Curve** in the Live Training Monitor.
* **Saved Where You Can See It**: on completion the monitor reports the held-out test split metrics (`F1`, `Accuracy`, `Precision`, `Recall`) **and the exact save path** (a self-contained model package under `user_models/<model-name>/`). The trained model automatically becomes the active classifier across the workbench (see the page header); delete its folder under `user_models/` to revert to the released checkpoints. Only one training job runs at a time — starting a second is politely refused.

---

## 🛠️ Command-Line Interface (`cc4q`) Reference

Every workflow in the Web Workbench has a 1:1 standalone CLI command for headless execution, CI pipelines, and batch reproduction:

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

---

## 📊 Empirical Benchmark Summary (6 Quantum SDKs)

All six corpora below are pre-indexed in the workbench (`cc4q/web/data/`) and reproducible from pinned release tags (`config/*.yaml`):

| SDK Repository | Pinned Release | Stack Layer | Python Files | Extracted CCPs | Segmented SCCUs | Quantum SCCUs | Quantum Share (%) | Comment Density |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `qiskit` | `2.1.0` | Infrastructure | 1,038 | 9,677 | 21,970 | 7,778 | **35.4%** | 0.126 |
| `qiskit-aer` | `0.17.2` | Infrastructure | 109 | 1,153 | 2,368 | 961 | **40.6%** | 0.114 |
| `qiskit-ibm-runtime` | `0.45.1` | Infrastructure | 280 | 1,982 | 3,738 | 878 | **23.5%** | 0.210 |
| **Infrastructure Subtotal** | — | **Infrastructure** | **1,427** | **12,812** | **28,076** | **9,617** | **34.3%** | — |
| `qiskit-machine-learning` | `0.9.1` | Application | 132 | 1,663 | 3,140 | 704 | **22.4%** | 0.172 |
| `qiskit-nature` | `0.8` | Application | 246 | 2,037 | 4,842 | 1,379 | **28.5%** | 0.127 |
| `qiskit-algorithms` | `0.4.0` | Application | 175 | 1,802 | 3,535 | 915 | **25.9%** | 0.155 |
| **Application Subtotal** | — | **Application** | **553** | **5,502** | **11,517** | **2,998** | **26.0%** | — |
| **Total Across 6 SDKs** | — | **All Layers** | **1,980** | **18,314** | **39,593** | **12,615** | **31.9%** | — |

---

## 📁 Repository Structure

```text
cc4q-workbench/
├── cc4q/
│   ├── pipeline/          # Stage 1–3: LibCST AST extraction, ~30 Sphinx-directive shims, spaCy segmentation
│   ├── models/            # SHA256-verified checkpoint downloader & lazy BERT ModelHandle loader
│   ├── web/               # Starlette/Uvicorn REST API (server.py) + Modern SPA Frontend (static/)
│   ├── web/data/          # Precomputed manifest.json + source-enriched unit corpora (units/*.jsonl)
│   ├── predict.py         # Two-stage quantum inference with softmax confidence probabilities
│   ├── train.py           # HuggingFace Trainer wrapper with warm-start & automatic schema normalization
│   ├── evaluate.py        # Agreement, Cohen's kappa, Precision/Recall/F1, Wilson 95% CI, confusion matrix
│   ├── sample.py          # Random, stratified, and quota sampling
│   ├── workspace.py       # Atomic JSON persistence for user corpora, annotation sessions & evaluations
│   └── cli.py             # Typer CLI entry point (`cc4q <command>`)
├── config/                # Pinned repository configurations (URL, release tag, include_dirs)
├── exp/                   # Unseen-SDK generalization results & 379-unit human verification benchmark
├── model/                 # TOSEM gold training datasets for Task 1 (quantum_related) & Task 2 (quantum_category)
├── tests/                 # Automated pytest suite (pipeline, workspace, registry, sampling, models)
├── Dockerfile             # Self-contained container image (build/run-verified by CI)
└── pyproject.toml         # Package metadata and dependencies
```

---

## 📖 Citation

If you use **CC4Q Workbench**, the released BERT classifiers, or the labeled quantum code-comment corpora in your research, please cite our companion paper:

```bibtex
@article{cc4q2026tosem,
  author  = {Zhou, Zenghui and Li, Yuechen and Cai, Yi and Wen, Jinlong and Yu, Xiaohan and Zheng, Zheng and Yin, Beibei},
  title   = {Code Comments for Quantum Software Development Kits: An Empirical Study on Qiskit},
  journal = {ACM Transactions on Software Engineering and Methodology (TOSEM)},
  year    = {2026},
  note    = {Accepted for publication}
}
```

## 📄 License

Code, workbench UI, and annotations are released under the [MIT License](LICENSE). Extracted code and comment snippets remain under the Apache-2.0 license of their upstream Qiskit repositories; fine-tuned model checkpoints derive from `bert-base-uncased` (Apache-2.0).
