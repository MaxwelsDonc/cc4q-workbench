# CC4Q Workbench — Quantum Code Comment Corpus Construction, Labeling & Model Adaptation Studio

[![CI](https://github.com/MaxwelsDonc/cc4q-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/MaxwelsDonc/cc4q-workbench/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-violet.svg)](LICENSE)
[![Companion Paper: TOSEM](https://img.shields.io/badge/Companion%20Paper-ACM%20TOSEM%202026-6D28D9.svg)](#citation)

**CC4Q Workbench** is an open-source, end-to-end experimentation and curation workbench for **Quantum Software Engineering (QSE)** code documentation research and practice. It operationalizes and extends the methodology of our ACM TOSEM companion study (*"Code Comments for Quantum Software Development Kits: An Empirical Study on Qiskit"*), turning any Python-based quantum SDK repository into a structured, sentence-level comment corpus labeled across our **Two-Stage Quantum-Specific Taxonomy**, while providing an interactive **Web Studio** and **CLI/Python API** for human-in-the-loop data labeling, custom BERT fine-tuning, and cross-SDK evaluation.

---

## ⚡ Reviewer Quick-Start (Zero-Friction Evaluation)

For ICSE Tool Demonstration & Artifact Reviewers, CC4Q Workbench supports three evaluation tiers depending on your available time and hardware:

### Tier 1 · 30-Second Instant Exploration (No Model Download Required)

All precomputed corpora across **6 Qiskit-ecosystem SDKs (39,593 labeled sentence units)** and the **379-unit human-verified unseen-SDK transfer benchmark** are bundled directly in the repository (`cc4q/web/data/`, ~23 MB) with full Python source-code context (`code_snippet` + line numbers).

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

Open **`http://127.0.0.1:8501`** in your browser to immediately explore the 6 SDK dashboards, inspect source-linked comment units, and audit the 379-unit human verification session.

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
# CPU build & run (exposes Web Workbench on http://localhost:8501)
docker build -t cc4q-workbench .
docker run --rm -p 8501:8501 cc4q-workbench

# Optional GPU build & run (CUDA 12.6)
docker build --build-arg TORCH_CHANNEL=cu126 -t cc4q-workbench:gpu .
docker run --rm --gpus all -p 8501:8501 cc4q-workbench:gpu
```

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
│  ┌────────────────────┐ ┌────────────────────┐ ┌──────────────┐ ┌──────────────┐  │
│  │ 1. Corpus Explorer │ │ 2. Live Inspector  │ │ 3. Annotation│ │ 4. Model     │  │
│  │    & SDK Compare   │ │    & Repo Builder  │ │    Studio    │ │    Trainer   │  │
│  └────────────────────┘ └────────────────────┘ └──────────────┘ └──────────────┘  │
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

Once `cc4q demo` is running at **`http://127.0.0.1:8501`**, the top navigation bar guides you through four integrated studios:

### 1. Corpus Explorer & Cross-SDK Compare (`Tab 1`)
* **Infrastructure vs. Application Layer Discovery**: Switch between the 3 infrastructure SDKs (`qiskit`, `qiskit-aer`, `qiskit-ibm-runtime`) and 3 application SDKs (`qiskit-nature`, `qiskit-algorithms`, `qiskit-machine-learning`). Click **`⇄ Compare SDKs`** to overlay any two SDKs on a dual radar chart and inspect our central empirical finding: **infrastructure SDKs carry 34.3% quantum-specific comments vs. 26.0% in application SDKs**.
* **Chart-to-Code Bidirectional Filtering**: Click any bar in the **Six-Category Quantum Knowledge Profile** (e.g., *Mathematics* at 28.9% in `qiskit-nature`) or any cell in the **Quantum Residence Heatmap (`Form × Entity`)** to filter the unit list below.
* **IDE-Style Source Context Viewer**: Click any comment unit on the left to inspect its exact enclosing Python source code (`code_snippet`), file path, and highlighted comment line on the right.

### 2. Live Code Inspector & Repository Builder (`Tab 2`)
* **Live Code Snippet Inspector**: Load one of the 3 curated quantum presets (*Bell State & Entanglement Circuit*, *Variational Quantum Eigensolver (VQE)*, *Hardware Noise & Coupling-Map Transpiler*) or paste custom Python code. Click **`⚡ Extract, Segment & Classify Quantum Comments`** to inspect:
  * An automated **Quantum Documentation Health Check** based on our TOSEM guidelines (checking structured docstring coverage, quantum domain signal, and inline point-of-use comments).
  * Every segmented SCCU with its **Quantum Confidence (%)** and **Top-3 Category Probability Bars**.
* **4-Stage Repository Corpus Builder**: Switch to **`🏗️ Build Corpus from Repository`**, keep the pre-filled local path `examples/tiny_repo` (or paste any GitHub URL), and click **`🚀 Build & Label Corpus`**. Watch the 4 stages execute live and open the newly built corpus directly in the Explorer.

### 3. Annotation Studio — Human-in-the-Loop Data Labeling (`Tab 3`)
* **Inspect the 379-Unit Unseen-SDK Verification Benchmark**: By default, the studio opens the preloaded **`Unseen SDKs Human Verification (379 units)`** session, displaying live **85.0% Human–Model Agreement** (Wilson 95% CI: `81.0%–88.2%`, Cohen's $\kappa = 0.699$, Precision `83.0%`, Recall `86.2%`). Use the left filter dropdown to select **`⚠️ Disagreements (Human ≠ Model)`** and inspect the exact 57 disagreement cases alongside their Python source code.
* **Create Your Own Labeling Session**: Click **`+ New Labeling Session`**, choose any corpus, set a sample size (or click the **`385`** button for Cochran's 95% CI formula), choose **Stratified (`Form × Entity`)** sampling, and pick **`Adjudicate (Show Model)`** or **`Blind (Hide Model)`** mode.
* **Ergonomic Keyboard-Driven Labeling**: Use hotkeys **`Q`** (Quantum-Specific), **`N`** (Non-Quantum), **`1`–`6`** (Six Quantum Categories), **`Space`** (Accept Model Pre-label), and **`←`/`→`** to label units rapidly while referencing the collapsible **TOSEM Annotation Guidelines** card.

### 4. Model Trainer, Registry & Side-by-Side Evaluator (`Tab 4`)
* **Train Your Own Quantum Classifier in the Browser**:
  1. Select **Task 1 (`quantum_related`, 2 classes)** or **Task 2 (`quantum_category`, 6 classes)**.
  2. Choose your **Starting Checkpoint**: *Warm-Start from Released CC4Q Checkpoint* (recommended for fast domain adaptation) or *Train from Scratch (`bert-base-uncased`)*.
  3. Select a **Training Data Source**: pick any **Annotation Studio Session** you labeled in Tab 3, the **Built-in TOSEM Gold Training Dataset** (2,802 binary / 1,800 balanced 6-class records), or **Upload a Custom JSONL File**.
  4. Click **`🚀 Start Fine-Tuning`** to watch the asynchronous progress bar and real-time **Train Loss & Validation F1 ECharts Curve**, followed by held-out test split metrics (`F1`, `Accuracy`, `Precision`, `Recall`).
* **One-Click Model Activation & Comparison**: Click **`★ Set Active`** on any newly trained model to make it the default classifier across the workbench, or run **Side-by-Side Model Evaluation** on the right panel to measure agreement, $\kappa$, and category shifts between two models on any corpus.

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
├── Dockerfile             # Self-contained CPU/GPU container image
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
