# RQ analyses (`rqs/`)

Scripts, results, generated tables, and figures behind the empirical
analyses (RQs) of the companion paper. Two families:

- `distribution_based/` — corpus statistics over the annotated gold corpus:
  comment-type/entity distributions (RQ1), comment density (RQ2), docstring
  coverage (RQ3), and the quantum proportion of comments (RQ4).
- `quantum_specific/` — analyses restricted to quantum-specific comments:
  category distribution (RQ8), category co-occurrence / relations (RQ9),
  semantic similarity between categories (RQ10), and keyword/class coverage
  (RQ11). Each `analysis/` script has a matching `visualization/` script
  that renders the published figures (PDFs under `*/visualization/`).

## Input corpus

Every analysis expects the **annotated CC4Q gold corpus**, one
SCCU-level JSON record per line:

```
CCPs_final_modified_r2_cleaned_validated.jsonl
```

This file ships in the CC4Q dataset archive (Zenodo, linked from the
repository README); in that archive it lives at
`data/final_data/CCPs_final_modified_r2_cleaned_validated.jsonl`, which is
the default path for the `distribution_based` scripts. The
`quantum_specific` scripts take the corpus path as a required positional
argument, so they work no matter where you unpacked the archive.

## How to run

From the workbench root, with the full `requirements.txt` installed:

```bash
# distribution-based RQs (default data path; override with argv[1])
python rqs/distribution_based/analysis/rq1_distributions.py
python rqs/distribution_based/analysis/rq2_comment_density.py
python rqs/distribution_based/analysis/rq3_docstring_coverage.py
python rqs/distribution_based/analysis/rq4_quantum_proportion.py

# quantum-specific RQs (corpus path required)
GOLD=/path/to/CCPs_final_modified_r2_cleaned_validated.jsonl
python rqs/quantum_specific/analysis/rq8_quantum_distribution.py  $GOLD
python rqs/quantum_specific/analysis/rq9_relation.py              $GOLD
python rqs/quantum_specific/analysis/rq10_semantic_similarity.py  $GOLD
python rqs/quantum_specific/analysis/rq11_keywords_matching.py    $GOLD

# figures (read the JSON results, write PDFs)
python rqs/distribution_based/visualization/rq3.py
python rqs/quantum_specific/analysis/rq8_visualization.py
python rqs/quantum_specific/analysis/rq9_visualization.py
python rqs/quantum_specific/analysis/rq10_visualization.py
python rqs/quantum_specific/analysis/rq11_visualization.py
```

## Outputs

- `*/results/*.json` — numeric results (already committed; re-running the
  analyses reproduces them).
- `*/visualization/*.pdf`, `distribution_based/visualization/img/*.pdf` —
  the paper's figures (regenerate with the visualization scripts).
- `distribution_based/table/` — LaTeX table generators for the paper.

Rerunning an analysis overwrites its `results/*.json`; the committed values
are the ones reported in the paper.
