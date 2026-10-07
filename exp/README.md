# exp/ — Tool-paper validation artifacts

Evidence behind the ICSE 2027 tool-demonstration paper *"CC4Q Workbench:
Building and Analyzing Quantum Code Comment Corpora"*.

| File | Content |
|---|---|
| `generalization_results.md` / `generalization_table.tex` | Corpus-construction stats for the three additional SDKs (qiskit-machine-learning 0.9.1, qiskit-nature 0.8, qiskit-algorithms 0.4.0), timings, reproduction commands |
| `labeling_summary.json` / `label_distribution_table.tex` | Three-axis label distributions on the new corpora |
| `run_inference.py` | Driver that produced the labels with the released checkpoints |
| `compute_stats.py` | Recomputes the corpus stats from pipeline outputs |
| `spotcheck_annotation.csv` | 385-unit stratified sample with author-verified labels (379 valid) |
| `spotcheck_answer_key.jsonl` | Model predictions for the sample |
| `score_spotcheck.py` | Recomputes agreement / precision / recall / Wilson CI (85.0% overall) |
| `disagreement_analysis.md` | Error-pattern analysis of the 57 disagreements |

The internal annotation UI used during the spot-check is not part of this
release.
