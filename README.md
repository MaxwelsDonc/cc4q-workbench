# CC4Q Workbench — Building and Analyzing Quantum Code Comment Corpora

[![CI](https://github.com/MaxwelsDonc/cc4q-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/MaxwelsDonc/cc4q-workbench/actions/workflows/ci.yml)

**Turn any Python-based quantum SDK repository into a labeled code-comment
corpus, then inspect and profile its quantum knowledge.**

CC4Q Workbench is the tool companion of *"Code Comments for Quantum Software
Development Kits: An Empirical Study on Qiskit"* (TOSEM, accepted). It
packages that study's methodology as a reusable tool:

- a **corpus-construction pipeline**: repository → code-comment pairs (CCPs)
  → sentence-level comment units (SCCUs);
- three released **fine-tuned BERT classifiers** (quantum-relatedness,
  developer intent, quantum-knowledge category);
- a four-page **web workbench**: live snippet labeling, repository
  dashboards, cross-SDK comparison, corpus exploration.

<p align="center">
  <img src="doc/screenshot_analyze_repo.png" alt="Analyze Repository dashboard" width="49%">
  <img src="doc/screenshot_analyze_code.png" alt="Analyze Code: live snippet labeling" width="49%">
</p>

## Try it

**Option 1 — Docker (easiest; nothing to install beyond Docker):**

```bash
docker build -t cc4q-workbench .
docker run -p 8501:8501 cc4q-workbench     # open http://localhost:8501
```

The image bundles the workbench, the pipeline, and precomputed results for
six Qiskit-ecosystem SDKs; classifier checkpoints are fetched at container
start (SHA256-verified). GPU hosts: build with
`docker build --build-arg TORCH_CHANNEL=cu126 -t cc4q-workbench:gpu .` and run
with `--gpus all`; the app auto-detects CUDA. (We develop on Apple Silicon,
so the GPU flavor is currently untested by us — feedback welcome.)

**Option 2 — pip install cc4q (CLI + library; requires Python ≥ 3.11):**

```bash
pip install git+https://github.com/MaxwelsDonc/cc4q-workbench
python -m spacy download en_core_web_sm
cc4q download-models          # ~1.2 GB checkpoints (SHA256-verified)
```

Then either launch the workbench:

```bash
cc4q demo                     # open http://localhost:8501
```

or run the corpus-building walkthrough (every step has `--help`):

```bash
cc4q build --repo https://github.com/Qiskit/qiskit-aer \
    --include-dir qiskit_aer --output-dir out/aer   # clone + extract + segment
cc4q predict --input out/aer/sccus_segmented.json \
    --output out/aer/labeled.jsonl                  # three-axis labels
cc4q sample --input out/aer/labeled.jsonl --by SDK --n 200 \
    --output out/aer/sample.jsonl                   # stratified spot-check
cc4q annotate --data out/aer/sample.jsonl \
    --labels quantum,non-quantum --mode adjudicate \
    --predictions out/aer/labeled.jsonl \
    --output-dir out/aer/ann                        # human spot-check UI
cc4q evaluate --annotations out/aer/ann/annotations.csv \
    --key out/aer/key.jsonl                         # agreement / P / R / CI
```

`examples/recipe_model_assisted_annotation.py` (in a source checkout) chains
the whole loop in one command (`run-all`), and `walk-spotcheck` replays the
paper's 385-item spot-check (predict -> sample -> annotate -> evaluate,
asserting 85.0% agreement).

**Option 3 — clone for development / paper reproduction:**

```bash
git clone https://github.com/MaxwelsDonc/cc4q-workbench.git
cd cc4q-workbench
conda create -n cc4q python=3.11 -y && conda activate cc4q
pip install -r requirements.txt -r demo/requirements-demo.txt
python -m spacy download en_core_web_sm
pip install -e .

pytest                        # 22 tests (model tests need the checkpoints)
python scripts/02_extract_code_comment_pairs.py config/examples.yaml
python scripts/03_segment_comments.py config/examples.yaml
streamlit run demo/app.py     # the workbench from the checkout
```

The `rqs/` and `exp/` trees hold the companion study's analysis scripts and
the tool-paper validation evidence (see their READMEs). Classifier
checkpoints: `python scripts/download_models.py` (same as `cc4q
download-models`).

## Python API & CLI

The pip-installed `cc4q` package is also a library; the CLI mirrors it 1:1
(`cc4q --help`):

```python
import cc4q

models = cc4q.load_models()                       # released checkpoints
labeled = cc4q.predict_corpus("sccus.jsonl", models=models)
sample = cc4q.sample(labeled, by=["SDK"], n=200, seed=42)
cc4q.annotate(sample, schema={"text_column": "comment_text",
                              "id_column": "id",
                              "labels": ["quantum", "non-quantum"]},
              mode="adjudicate", output_dir="ann/")
result = cc4q.evaluate_files(csv_path="ann/annotations.csv",
                             key_path="key.jsonl")
```

Full guides and the API reference: `docs/` (Sphinx; publishes to GitHub
Pages once the repo is public).

## Tests

One command runs the test suite (pytest is in `demo/requirements-demo.txt`):

```bash
pip install pytest   # plus: pip install -r demo/requirements-demo.txt for the app tests
pytest
```

Prerequisite: the spaCy English model (`python -m spacy download
en_core_web_sm`) — without it the segmenter tests are skipped, not failed.

- `tests/test_data.py` — demo-data integrity, packaging checks, and the
  snippet pipeline (no checkpoints needed; same checks CI runs via
  `python demo/smoke_test.py`).
- `tests/test_segmenters.py` — unit tests for the three comment segmenters.
- `tests/test_models_and_app.py` — three-axis classification and Streamlit
  page rendering; **skipped automatically** when `models_checkpoints/` is
  absent.

`demo/smoke_test.py` remains the CI entry point; `scripts/test_segment.py`
is a runnable usage example for the segmenters.

## Repository layout

```
cc4q/             the pip-installable library + CLI (pipeline, models, predict,
                  train, evaluate, sample, annotate, viz)
demo/           the web workbench (Streamlit) + precomputed dashboards
scripts/        pipeline entry points (download → extract → segment) + model download
parser_core/ segment_core/ utils/ config/   compatibility shims & per-SDK configs
model/          classifier training code, training data, label mappings
examples/       tiny sample sources + the model-assisted-annotation recipe
docs/           Sphinx documentation (guides, API reference, data contracts)
exp/            tool-paper validation evidence (see exp/README.md)
rqs/            companion study's analysis scripts and results
doc/            labeling guideline + workbench design document
```

## Documentation

- `doc/workbench_design.md` — the workbench's design specification
  (pages, analyses, acceptance criteria)
- `doc/Guideline_for_labelling_training.md` — the annotation guideline used
  in the companion study
- `exp/README.md` — the validation data behind the tool paper's numbers

## Companion corpus

The companion study's gold corpus (28,076 human-validated units from
`qiskit` 2.1.0, `qiskit-aer` 0.17.2, `qiskit-ibm-runtime` 0.45.1) is archived
separately (see the companion paper's artifact link; too large for git).
Each unit is a JSON object:

| Field | Description |
| --- | --- |
| `id` | unit id; the numeric prefix is the id of its parent comment pair |
| `SDK`, `version` | source library and pinned version |
| `dirPath`, `comment_line`, `code_line` | location in the upstream repository |
| `comment_type` | `docstring` / `block` / `inline` |
| `comment_text`, `code_snippet` | the comment text and its associated code |
| `code_entity_type` | `module` / `class` / `function` |
| `is_quantum_specific` | whether the unit is quantum related |
| `developer_intent_category` | `what` / `why` / `how-to-use` / `how-it-is-done` / `property` / `developer-others` |
| `quantum_specific_category` | one of six quantum-knowledge categories (quantum-specific units only) |

## Reproducing the analyses

Build a corpus for a new SDK: add an entry to `config/repo_list.yaml`
(`url` + pinned `ref`), run `scripts/01_download_repos.py`, then scripts
`02`/`03` with a per-SDK config (see `config/config_qiskit.yaml`), then label
with `exp/run_inference.py`. The companion study's RQ analyses live in
`rqs/`, and the tool paper's generalization/verification numbers in `exp/`;
both directories contain step-by-step notes.

## License & attribution

Code and annotations: MIT (see `LICENSE`). Comment/code content is extracted
from the Qiskit projects (Apache-2.0); the classifiers are derived from
`bert-base-uncased` (Apache-2.0). If you use this artifact, please cite the
companion paper.

## Citation

```bibtex
@article{cc4q2026tosem,
  author  = {Zhou, Zenghui and Li, Yuechen and Cai, Yi and Wen, Jinlong and Yu, Xiaohan and Zheng, Zheng and Yin, Beibei},
  title   = {Code Comments for Quantum Software Development Kits: An Empirical Study on Qiskit},
  journal = {ACM Transactions on Software Engineering and Methodology},
  year    = {2026},
  note    = {Accepted for publication}
}
```

