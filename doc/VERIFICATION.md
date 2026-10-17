# CC4Q Workbench — Step-by-Step Verification Report

**Purpose**: an independent verifier follows this document top to bottom, runs every
command, compares every observed value with the **Expected** value, and ticks the
boxes. Any mismatch = a defect: please note it in §8 (Sign-off) with the observed value.

**Reference document**: `README.md` (all claims verified here map to README sections).

---

**Verifier**: ______________________  **Date**: ____________
**OS**: ____________  **Python version**: ____________  **Machine**: ____________

---

## Part 0 — Setup (README: Reviewer Quick-Start, Tier 1)

- [ ] **0.1** Clone and enter the repository
```bash
git clone https://github.com/MaxwelsDonc/cc4q-workbench.git
cd cc4q-workbench
```

- [ ] **0.2** Create an isolated environment and install (requires **Python ≥ 3.11**)
```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt -r demo/requirements-demo.txt
pip install -e .
```
**Expected**: install completes with no errors; `cc4q --help` prints the command list
(`build / predict / sample / annotate / train / evaluate / download-models / demo / serve`).

- [ ] **0.3** Launch the workbench
```bash
ccq demo        # note: the command is `cc4q demo`
```
**Expected**: server starts; opening `http://127.0.0.1:8501` shows the workbench with a
top navigation bar of **five tabs** (Corpus Explorer · Live Inspector · Corpus Builder ·
Annotation Studio · Model Trainer).

---

## Part 1 — Corpus Explorer & Cross-SDK Compare (README §Tab 1, Empirical Table)

*No model download required for this part.*

- [ ] **1.1** Tab 1 lands on the **📊 Benchmark Overview** (default view): aggregate cards
for **all 6 repositories** (**39,593 Comment Sentences · 31.9% Quantum-Specific ·
6 SDKs** — 3 TOSEM infrastructure + 3 application), an aggregate knowledge profile and
residence heatmap, and a per-SDK breakdown table listing **6 SDK corpora** with the
infrastructure subtotal (28,076 @ 34.3%) and application subtotal (11,517 @ 26.0%).
For each SDK, the row shows SCCU counts matching the Empirical Benchmark table:

| SDK | Expected SCCUs | Expected Quantum share |
|---|---|---|
| qiskit 2.1.0 | 21,970 | 35.4% |
| qiskit-aer 0.17.2 | 2,368 | 40.6% |
| qiskit-ibm-runtime 0.45.1 | 3,738 | 23.5% |
| qiskit-machine-learning 0.9.1 | 3,140 | 22.4% |
| qiskit-nature 0.8 | 4,842 | 28.5% |
| qiskit-algorithms 0.4.0 | 3,535 | 25.9% |

**Expected totals** (shown in the UI or via API below): **39,593 SCCUs**, 12,615
quantum, overall 31.9%; infrastructure subtotal 28,076 SCCUs @ **34.3%**; application
subtotal 11,517 SCCUs @ **26.0%**.

- [ ] **1.2** API cross-check (no browser needed):
```bash
curl -s http://127.0.0.1:8501/api/overview | python3 -m json.tool | head -40
```
**Expected**: JSON reports 6 repos and the corpus/asset counts consistent with 1.1.

- [ ] **1.3** **Compare SDKs**: from the Benchmark Overview, click `⇄ Compare SDKs`
(the button is only shown on the Overview), choose `qiskit` vs
`qiskit-machine-learning`. **Expected**: dual radar chart renders; the comparison shows
35.4% vs 22.4% quantum share (the infra-vs-application finding).

- [ ] **1.4** **Chart-to-code filtering**: click the *Mathematics* bar of
`qiskit-nature`. **Expected**: the unit list below filters to mathematics-category units;
the header indicates the active filter.

- [ ] **1.5** **Source viewer**: click any unit. **Expected**: right pane shows the
unit's `code_snippet` with file path and line numbers.

---

## Part 2 — Live Inspector & Repository Builder (README §Tab 2)

*Requires Tier 2 setup first:*

- [ ] **2.0** Download the language model and checkpoints (README Tier 2):
```bash
python -m spacy download en_core_web_sm
cc4q download-models
cc4q download-models --check
```
**Expected**: download of **two** checkpoints (~835 MB total, SHA256-verified);
`--check` prints OK. An optional third asset (`bert-base-uncased.tar.gz`, for
from-scratch fine-tuning) is fetched with `python scripts/download_models.py --with-base`.

- [ ] **2.1** Tab 2 → load preset **“Bell State & Entanglement Circuit”** (one-click preset
pill above the editor) and click `⚡ Extract, Segment & Classify Quantum Comments`.
**Expected**: the right pane starts as an empty placeholder and results render **only
after the click**; every SCCU shows a **Quantum Confidence badge (%)** and a
knowledge-category badge; Bell-state units are classified quantum with high confidence.

- [ ] **2.2** Paste non-Python text (e.g. plain English). **Expected**: graceful
fallback (line-by-line mode or a clear "not parseable" message) — no crash.

- [ ] **2.3** Open Tab 3 (**Corpus Builder**), keep the pre-filled
`examples/tiny_repo`, click `🚀 Build & Label Corpus`.
**Expected**: four stages execute (clone/verify → extract → segment → label); a new
corpus opens in the Explorer. CLI equivalent:
```bash
cc4q build --repo examples/tiny_repo --output-dir /tmp/cc4q_out
```
**Expected CLI output**: `[build] 2 CCPs -> 2 SCCUs`.

- [ ] **2.4** (Optional) Guardrail: build from a GitHub URL of a repo with >200 Python
files. **Expected**: a polite refusal suggesting Docker/local CLI.

---

## Part 3 — Annotation Studio (README §Tab 4)

- [ ] **3.1** Tab 4 opens as a two-card landing (**Load Demo Benchmark** /
**Upload JSONL**) with no session preloaded. Click **`📂 Load Demo Benchmark (361 units)`**.
**Expected**: the *Unseen SDKs Labeling Demo (361 units)* session opens with
**Progress `0 / 361`**, every item marked `Unlabeled`, each item showing its target
comment sentence and the enclosing Python source context (file path + code viewer).
The only header metric is Progress — the UI intentionally shows no model pre-labels
and no agreement/κ/P-R metrics (blind labeling).

- [ ] **3.2** Filter dropdown → `Unlabeled Only`. **Expected**: 361 items; after
labeling one item and re-filtering, `Labeled Only` shows it with its Quantum/Non-Q
pill.

- [ ] **3.3** Keyboard labeling: focus an item, press `Q` or `N`, then a category
key `1`–`6`. **Expected**: the label is applied and persisted; the view **stays on
the same item** (both step choices remain highlighted); Progress increments; `←`/`→`
move between items manually.

- [ ] **3.4** CLI cross-check of the human-vs-model study behind the demo benchmark
(UI deliberately hides these numbers to keep labeling blind — README CLI §6):
```bash
cc4q evaluate --annotations exp/spotcheck_annotation.csv \
              --key exp/spotcheck_answer_key.jsonl \
              --contaminated 1,8,16,25,62,132
```
**Expected**: `n=379  agreement=85.0%  (95% CI 81.0–88.2)  precision=83.0%  recall=86.2%`.

- [ ] **3.5** `⬇ Export Labeled JSONL`. **Expected**: downloads the current session
including your human labels.

- [ ] **3.6** `⬆ Upload JSONL to Label`: upload any `.jsonl` file of comment records.
**Expected**: a new session opens directly with your records ready to label (up to
1,000 records).

---

## Part 4 — Model Trainer (README §Tab 5)

- [ ] **4.1** Dry-run validation (no training yet):
```bash
cc4q train --task quantum_related --data examples/tiny_labels.jsonl \
           --output-dir /tmp/cc4q_out/clf --dry-run
```
**Expected**: `[train] dry-run OK: quantum_related data honors the contract`.

- [ ] **4.2** Tab 5 → Task 1 (`quantum_related`) → data source **Demo Dataset
(2,802 units)** (or upload `examples/tiny_labels.jsonl`) → `🚀 Start Fine-Tuning`.
**Expected**: asynchronous progress + live Train-Loss / Validation-F1 curve in the
**Live Training Monitor**; on completion, held-out metrics (F1/Accuracy/Precision/Recall)
are reported together with the save path (`💾 Model saved to: …/user_models/<name>`).
Starting a second job while one is running is rejected with a clear message.

- [ ] **4.3** On completion the trained model automatically becomes the active/default
classifier. **Expected**: the page-header indicator (Active Model: ...) switches to the
new model; Tab 2 classification now uses it. Restore the released checkpoints by
deleting the folder under `user_models/` (or
`curl -X POST /api/models/default -d '{"model_id":"released"}'`).

- [ ] **4.4** The tab shows only the 3-step training form and the **Live Training
Monitor**. **Expected**: no model-registry strip, no Set-Active buttons, no
side-by-side evaluation panel (the JSON APIs remain available).

- [ ] **4.5** README classifier-quality claims (architecture diagram): Task 1 held-out
**F1 = 0.936**, Task 2 held-out **F1 = 0.840**. **Expected**: these figures are the
companion-study training results; the trainer's final validation F1 should be in the
same range for Task 1 on gold data.

---

## Part 5 — Full CLI walkthrough (README CLI Reference)

Run each; all should succeed end-to-end:

- [ ] **5.1** `cc4q build --repo examples/tiny_repo --output-dir /tmp/cc4q_out` → 2 CCPs / 2 SCCUs
- [ ] **5.2** `cc4q predict --input /tmp/cc4q_out/sccus_segmented.json --output /tmp/cc4q_out/labeled.jsonl` → every record gains `quantum_related` (0/1) and, for quantum units, `quantum_category`
- [ ] **5.3** `cc4q sample --input /tmp/cc4q_out/labeled.jsonl --by comment_type --n 50 --output /tmp/cc4q_out/sample.jsonl` → ≤50 records, stratified by `comment_type`
- [ ] **5.4** `cc4q annotate --data /tmp/cc4q_out/sample.jsonl --labels quantum,non-quantum --mode adjudicate --predictions /tmp/cc4q_out/labeled.jsonl --output-dir /tmp/cc4q_out/ann --dry-run` → dry-run OK
- [ ] **5.5** `cc4q train ... --dry-run` → contract OK (see 4.1)
- [ ] **5.6** `cc4q evaluate ...` → 85.0% (see 3.4)
- [ ] **5.7** `cc4q demo --host 127.0.0.1 --port 8501` → web workbench

---

## Part 6 — Automated test suite

- [ ] **6.1**
```bash
pytest
```
**Expected**: **51 passed** in under ~2 minutes (model-dependent tests self-skip if
checkpoints are absent: then 49 passed / 2 skipped is also correct).

- [ ] **6.2** (Optional, needs Docker) README Tier 3:
```bash
docker build -t cc4q-workbench . && docker run --rm -p 8501:8501 cc4q-workbench
```
**Expected**: workbench on `http://localhost:8501` without any local install.

---

## Part 7 — Known cosmetic issues (not defects)

The verifier should NOT fail the verification for these (already tracked):

1. ~~Corpus Explorer group labels render tight, e.g. `APPLICATION LAYER (NEW SDKS)26.0%`
   (missing space)~~ — **fixed in the v2.2 UI pass** (spacing added between the group title
   and percentage spans). If you still see the collision, record it as a defect.
2. The legacy `v0.1.0` release is retained for provenance; the tool uses `v0.2.0`
   (two-stage checkpoints + optional bert-base). Do not verify against v0.1.0.

---

## Part 8 — Sign-off

| README claim | Verified? | Observed value (if different) |
|---|---|---|
| 6 SDKs / 39,593 SCCUs / 12,615 quantum / 31.9% | ☐ | |
| Infra 34.3% vs Application 26.0% | ☐ | |
| 379-unit benchmark: 85.0% (81.0–88.2), κ 0.699, P 83.0, R 86.2, 57 disagreements | ☐ | |
| Two-stage taxonomy (quantum_related → 6-class quantum_category) | ☐ | |
| Checkpoints download (~835 MB) + SHA256 verify | ☐ | |
| Live inspector: presets, confidence, health check | ☐ | |
| 4-stage repo builder (2 CCPs → 2 SCCUs on tiny_repo) | ☐ | |
| Annotation studio: sessions, sampling, keyboard labels, export | ☐ | |
| Trainer: dry-run, warm-start, live curves, active-model strip, set-active | ☐ | |
| Benchmark Overview landing (28,076 @ 34.3%) + Upload-JSONL labeling | ☐ | |
| CLI: 7 commands end-to-end | ☐ | |
| pytest 51 passed | ☐ | |
| Docker all-in-one (optional) | ☐ | |

**Verifier signature**: ______________________  **Result**: ☐ PASS / ☐ FAIL
**Notes**:
