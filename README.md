# CC4Q Workbench — Building and Analyzing Quantum Code Comment Corpora

[![CI](https://github.com/MaxwelsDonc/cc4q-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/MaxwelsDonc/cc4q-workbench/actions/workflows/ci.yml)

**Point CC4Q at any Python quantum-SDK repository and get a corpus of comments, each labeled by how much quantum knowledge it carries — ready to study, extend, or retrain.**

<p align="center">
  <img src="doc/screenshot_analyze_repo.png" alt="Analyze Repository dashboard" width="49%">
  <img src="doc/screenshot_analyze_code.png" alt="Analyze Code: live snippet labeling" width="49%">
</p>

## Installation

**pip (CLI + library; Python ≥ 3.11):**

```bash
pip install git+https://github.com/MaxwelsDonc/cc4q-workbench
python -m spacy download en_core_web_sm
cc4q download-models   # ~1.2 GB classifier checkpoints (SHA256-verified)
```

**Docker (all-in-one image with the web workbench):**

```bash
docker build -t cc4q-workbench . && docker run -p 8501:8501 cc4q-workbench
```

(GPU hosts: `docker build --build-arg TORCH_CHANNEL=cu126 -t cc4q-workbench:gpu .`, then `docker run --gpus all -p 8501:8501 cc4q-workbench:gpu`.)

**For development / paper reproduction:**

```bash
git clone https://github.com/MaxwelsDonc/cc4q-workbench.git && cd cc4q-workbench
conda create -n cc4q python=3.11 -y && conda activate cc4q
pip install -r requirements.txt -r demo/requirements-demo.txt && pip install -e .
pytest    # 22 tests; the model tests need cc4q download-models first
```

## Features

Eight standalone-first primitives — every command works on its own
(`cc4q <command> --help`). The snippets below run from a source checkout
(fixtures live in `examples/`); from a pip install, point `--repo` at any
GitHub URL instead. Snippets marked ⚡ require the checkpoints
(`cc4q download-models`).

**Build** — turn a repository's comments into small, labeled-ready text units (one JSON file you can search and filter):

```bash
cc4q build --repo examples/tiny_repo --output-dir /tmp/cc4q_out
```

**Analyze** — count and break down what's in a corpus (how many comments, what kinds, where they live) with a few lines of Python:

```bash
python -c "
import json, collections
recs = json.load(open('/tmp/cc4q_out/sccus_segmented.json'))
print(len(recs), 'SCCUs;', collections.Counter(r['comment_type'] for r in recs))"
```

**Predict ⚡** — have the trained models read every comment and answer: is it about quantum? what kind of quantum knowledge? what was the author trying to say?

```bash
cc4q predict --input /tmp/cc4q_out/sccus_segmented.json \
    --output /tmp/cc4q_out/labeled.jsonl
```

**Sample** — pick a fair subset for human review (random, or balanced so every project/label is represented):

```bash
cc4q sample --input /tmp/cc4q_out/labeled.jsonl --by SDK --n 2 \
    --output /tmp/cc4q_out/sample.jsonl
```

**Annotate** — review model labels in a click-through web UI: confirm, fix, or skip each item; your answers save as you go and export as a ready-to-train file. `--dry-run` checks the setup without opening the UI:

```bash
cc4q annotate --data /tmp/cc4q_out/sample.jsonl \
    --labels quantum,non-quantum --mode adjudicate \
    --predictions /tmp/cc4q_out/labeled.jsonl \
    --output-dir /tmp/cc4q_out/ann --dry-run
```

**Train** — teach the models your own labeling decisions, starting from the released classifiers or plain BERT (drop `--dry-run` to train for real):

```bash
cc4q train --task quantum_related --data examples/tiny_labels.jsonl \
    --output-dir /tmp/cc4q_out/clf --dry-run
```

**Evaluate** — score how much a human agrees with the model (percent agreement, precision/recall, and a confidence interval), the same statistics reported in the paper:

```bash
cc4q evaluate --annotations examples/tiny_spotcheck/annotations.csv \
    --key examples/tiny_spotcheck/key.jsonl
```

**Visualize** — turn label counts into charts you can embed anywhere — Jupyter notebooks, HTML pages, or figures for a paper:

```bash
python -c "
import json, cc4q.viz as viz
recs = [json.loads(l) for l in open('/tmp/cc4q_out/labeled.jsonl')]
q = [r for r in recs if r['quantum_related']]
stats = {'quantum_sccus': len(q),
         'category_counts': dict(__import__('collections').Counter(r['quantum_category'] for r in q))}
viz.radar_figure([('corpus', stats)], 'Knowledge profile').write_html('/tmp/cc4q_out/radar.html')"
```

**Web workbench** — a browser app that ties it all together: label a pasted snippet, explore ready-made dashboards for six quantum SDKs, and compare projects side by side (precomputed dashboards work without the model checkpoints):

```bash
cc4q demo   # open http://localhost:8501
```

Full documentation (API reference + guides): https://maxwelsdonc.github.io/cc4q-workbench/ (after the repository is made public; build locally with `sphinx-build -b html docs docs/_build` meanwhile).

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

## License

Code and annotations: MIT (see `LICENSE`). Comment/code content is extracted
from the Qiskit projects (Apache-2.0); the classifiers are derived from
`bert-base-uncased` (Apache-2.0). If you use this artifact, please cite the
companion paper.
