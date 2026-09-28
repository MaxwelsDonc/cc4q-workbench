# CC4Q — A Dataset of Code Comments in Quantum Software Development Kits

Data, models, and analysis scripts for the paper:

> **Code Comments for Quantum Software Development Kits: An Empirical Study on Qiskit**
> (accepted for publication)

The dataset contains **28,076 annotated code-comment units** collected from
three popular Qiskit-family libraries (`qiskit` 2.1.0, `qiskit-aer` 0.17.2,
`qiskit-ibm-runtime` 0.45.1). Each unit is labeled with whether it is
quantum-specific, its developer-intent category, and (for quantum-specific
units) its quantum-knowledge category. This archive also ships the comment
extraction/segmentation pipeline, the three BERT classifiers used for
model-assisted annotation, and the scripts behind the paper's empirical
analyses.

```
data/final_data/                the annotated dataset (JSONL, one unit per line)
scripts/                        pipeline: download repos → extract pairs → segment units
parser_core/ segment_core/ utils/ config/   pipeline libraries & configurations
examples/                       tiny sample sources for a quick run
model/                            three BERT classifiers: training code, data, label mappings
rqs/                            analysis scripts, results, tables and figures
doc/                            labeling guideline
```

## Quick start

```bash
# Python >= 3.9
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# run the pipeline on the bundled example files
python scripts/02_extract_code_comment_pairs.py config/examples.yaml
python scripts/03_segment_comments.py config/examples.yaml
```

Outputs are written to `examples/output/`.

## Using the dataset

```python
import pandas as pd

df = pd.read_json(
    "data/final_data/CCPs_final_modified_r2_cleaned_validated.jsonl",
    lines=True,
)
print(df.shape)          # (28076, 14)
```

Each line is one comment unit with the following fields:

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
| `quantum_specific_category` | for quantum-specific units: one of six quantum-knowledge categories (see the labeling guideline in `doc/`), else `null` |

## Reproducing the full pipeline

The upstream source code is not redistributed; download the pinned versions
with the helper script, then run the extraction steps:

```bash
python scripts/01_download_repos.py
python scripts/02_extract_code_comment_pairs.py config/config_qiskit.yaml
python scripts/02_extract_code_comment_pairs.py config/config_qiskit-aer.yaml
python scripts/02_extract_code_comment_pairs.py config/config_qiskit-ibm-runtime.yaml
python scripts/03_segment_comments.py config/config_qiskit.yaml
python scripts/03_segment_comments.py config/config_qiskit-aer.yaml
python scripts/03_segment_comments.py config/config_qiskit-ibm-runtime.yaml
```

The annotation workflow (human labeling + model-assisted labeling) is
described in the labeling guideline; the released file contains the final
agreed labels.

## Models

Training code, training data, and label mappings for the three
`bert-base-uncased` classifiers used for model-assisted annotation live under
`model/<name>/`:

| Model | Task |
| --- | --- |
| `quantum_related_classifier` | binary: is the comment quantum related? |
| `quantum_category_classifier` | 6-way quantum-knowledge category |
| `developer_intent_classifier` | 6-way developer intent |

```bash
# fine-tune from scratch (downloads bert-base-uncased from the Hugging Face Hub)
python model/quantum_related_classifier/src/01_build_model.py
python model/quantum_category_classifier/src/01_build_model.py
python model/developer_intent_classifier/src/01_build_model.py
```

The inference entrypoints (`src/02_infer_label.py`) batch-classify a
JSON/JSONL input file with a trained checkpoint; point the path constants at
the bottom of each script at your model directory and input file.

## Empirical analyses (RQ scripts)

`rqs/` contains the analysis scripts, results, generated tables, and figures
reported in the paper:

```bash
# comment distribution, comment density, quantum proportions
python rqs/distribution_based/analysis/rq1_distributions.py
python rqs/distribution_based/analysis/rq2_comment_density.py
python rqs/distribution_based/analysis/rq4_quantum_proportion.py

# quantum-specific analyses (category distribution, relations, similarity)
python rqs/quantum_specific/analysis/rq8_quantum_distribution.py data/final_data/CCPs_final_modified_r2_cleaned_validated.jsonl
python rqs/quantum_specific/analysis/rq9_relation.py data/final_data/CCPs_final_modified_r2_cleaned_validated.jsonl
```

## License & attribution

This archive (code and annotations) is released under the MIT license — see
`LICENSE`. The comment/code content of the dataset is extracted from the Qiskit
projects listed above, which are licensed under the Apache License 2.0, and the
fine-tuned models are derived from `bert-base-uncased` (Hugging Face,
Apache-2.0). Please attribute the respective upstream projects when using the
data. If you use this artifact, please cite the paper.
