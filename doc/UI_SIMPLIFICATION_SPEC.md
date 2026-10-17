# CC4Q Workbench — Frontend Simplification & Readability Specification (v2.5)

**v2.5 changes (owner acceptance round, round 4)**:
1. **Tab 1 Benchmark Overview aggregates all 6 SDKs**: headline KPIs now show the full-benchmark totals (39,593 SCCUs · 31.9% quantum · 6 SDKs); the per-SDK table still breaks down infrastructure (28,076 @ 34.3%) vs. application (11,517 @ 26.0%) subtotals. The sidebar overview entry loses its SCCU-count badge.
2. **Annotation Studio is fully blind**: the demo session is re-seeded as *Unseen SDKs Labeling Demo (361 units)* — 361 unlabeled items (18 docutils-noise rows dropped) with recovered Python source context, no human labels pre-filled. The model pre-label banner, session dropdown, "+ New Labeling Session" drawer, auto-advance, "≠ Model" pills, and all model-comparison metrics (agreement/κ/P-R, statistical-breakdown drawer, disagreement filter) are removed; only Progress remains. Labeling stays on the item; Prev/Next is manual.
3. **Model Trainer is a pure train-and-save flow**: registry strip and "Your Custom Fine-Tuned Models" list removed (APIs retained). Training always warm-starts from the released checkpoints; data source = Demo Dataset or upload only; parameters = Epochs/Batch only (Max Samples and Starting Checkpoint selects removed). On completion the monitor shows held-out metrics **and the save path** (`user_models/<name>/`). Concurrent training jobs are refused (409) — simultaneous Trainer instances abort the MPS backend.
4. **Maintenance**: `/static` responses carry `Cache-Control: no-cache` (+`app.js` version query) so UI iterations are not defeated by browser caching; `accelerate>=1.1.0` added for transformers 5.x; `TrainingArguments(logging_dir=…)` dropped (removed in transformers 5.x).

**v2.4 changes (owner feedback, round 3)**:
1. **Tab 1 header actions pruned**: `⇄ Compare SDKs` is now shown **only on the Benchmark Overview** (hidden on per-SDK dashboards); the `🏷️ Label Sample in Studio` and `⬇ Export JSONL` buttons are removed (corpus download remains available via API/CLI; studio sessions are created inside the Studio).
2. **Live Inspector de-duplicated**: the preset dropdown is gone (one-click pills are the only preset entry), and so is the per-page classifier dropdown — inspection always uses the active model (set in the Model Trainer).
3. **Results render on demand only**: entering the Inspector no longer auto-runs classification; the right pane shows an empty state until the user clicks ⚡, so results always match the code on the left. (Cross-tab "inspect this unit" jumps still run immediately, since that is an explicit action.)
4. **Result cards trimmed**: the summary banner + Documentation Health Check panel and the per-card Top-3 category probability bars are removed; each card keeps the quantum-confidence badge, the knowledge-category badge, and the sentence.

**v2.3 changes (interaction pass, owner feedback)**:
1. **Tab 1 gains a Benchmark Overview landing (default view)** — a pinned `📊 Benchmark Overview` sidebar entry shows the TOSEM trio's collective results (aggregate KPIs, aggregate category bars + residence heatmap, per-SDK comparison table with drill-down), so the Explorer presents the study's results first and single-SDK dashboards second.
2. **Tab 2 split into two top-level tabs (5 total)**: `2 Live Inspector` (snippet only) and `3 Corpus Builder` (the 4-stage repository pipeline) — the old in-tab switcher is gone.
3. **Annotation Studio gets task-first entries**: prominent `📂 Load Demo Benchmark (379 units)` and `⬆ Upload JSONL to Label` buttons (upload is pure frontend — `POST /api/annotations` accepts a `records` array); session management stays one level down.
4. **Model Trainer simplified**: the Side-by-Side Model Evaluation panel is removed (API retained), the registry cards collapse into a slim `Active: Released CC4Q Checkpoints ★ (F1 chips)` strip, and the training monitor moves beside the 3-step form.

**v2.2 changes (design-review pass)**:
1. **Tab 3 keeps Precision/Recall always visible** — `doc/VERIFICATION.md` Part 3.1 lists P/R as header metrics, so hiding them in `<details>` would fail verification; only F1, the confusion matrix, and 6-category agreement move into the drawer.
2. **Radar chart stays inside the category card as a collapsible toggle** — the v2.1 Tab-1 wireframe ("Radar moved into Compare SDKs drawer") contradicted Concrete Change #2; the in-card collapse is the adopted design.
3. **Sampling/heatmap labels keep the `Form × Entity` token** — verifiers match on it (VERIFICATION.md Part 3.5); plain-English renames must keep the original token in parentheses.
4. **Corrected the "keep ids for tests" rationale** — the 51-check pytest suite is API-level only (TestClient + HTTP-200 static checks; it never touches the DOM). Ids are load-bearing because `app.js` binds handlers/state to them, and `doc/VERIFICATION.md` is the behavioral gate.
5. **Tab 1 header actions explicitly preserved** (⇄ Compare SDKs / 🏷️ Label Sample in Studio / ⬇ Export JSONL) — the Explorer→Studio hand-off is part of the workflow story.
6. **Queue/list rows are exempted from the 16px upgrade** (13–14px + 2-line clamp); only focused reading surfaces scale up.
7. **Shared `<details>` interaction conventions** added (§2.4).
8. **Sign-off checklist gains a screenshot-refresh step and a phased rollout** (§4).

**Target Files**:
- `cc4q/web/static/index.html`
- `cc4q/web/static/styles.css`
- `cc4q/web/static/app.js`

**Hard Constraints (Zero Backend / Test Breakage)**:
1. **Do NOT modify `cc4q/web/server.py` or any backend Python modules** (`cc4q/predict.py`, `cc4q/train.py`, `cc4q/evaluate.py`, `cc4q/workspace.py`).
2. **Preserve all existing DOM element `id="..."` attributes** in `index.html` and `app.js`. The pytest suite is API-level only (Starlette TestClient + HTTP-200 static checks; it never touches the DOM), so ids are **not** protected by tests — they are load-bearing because `app.js` binds event handlers and state to them (e.g. `loadCodePreset` on `#inspector-preset-select`, `startAnnotationFromCurrentCorpus` on the Tab-1 header button). Removing or renaming an id breaks the wiring silently while pytest stays green; the behavioral gate is the manual browser checklist in `doc/VERIFICATION.md` (Parts 1–4), which must pass unmodified.
3. **Scope of changes**: Purely visual hierarchy, typography scaling, progressive disclosure (`<details>` / collapsible drawers), and plain-English labeling.

---

## 1. Root Cause Diagnosis: Why the Current UI Feels Complex & Hard to Read

1. **Dashboard Overload (Too Many Competing Regions per Screen)**:
   - **Tab 1 (`Corpus Explorer`)** currently renders ~15 distinct visual blocks simultaneously (left sidebar + 5 KPI cards + radar chart + 6 progress bars + 3×3 heatmap + 4 filter `<select>` dropdowns + search bar + unit list + code viewer). The user's eye has no clear entry point.
2. **Internal Research Jargon Used as Primary UI Labels**:
   - Terms such as `CCPs`, `SCCUs`, `Quantum Residence (Form × Entity)`, `Adjudicate`, `Wilson 95% CI`, and `TP/FP/FN/TN` appear as top-level headers without plain-language context.
3. **Small Typography & Box-in-Box Clutter**:
   - Heavy reliance on `11px`–`12px` (`text-xs` / `text-[11px]`) even for the primary comment sentence being inspected or annotated, combined with nested bordered boxes.
4. **Secondary/Advanced Controls Mixed with Primary Workflows**:
   - In **Tab 3 (`Annotation Studio`)**, 6 statistical evaluation cards sit above a cramped 3-column workspace.
   - In **Tab 4 (`Model Trainer`)**, low-level hyperparameters (`Batch Size`, `Max Samples`, `Starting Checkpoint`) and the `Side-by-Side Model Evaluation` panel compete visually with the core 3-step training flow.

---

## 2. Global Visual & Typography Upgrades (`styles.css` + `index.html`)

### 2.1 Typography Scale Upgrade
- **Primary comment sentence (`#explorer-unit-detail p`, `#ann-curr-text`, `.unit-row` main text)**:
  - Increase from `text-xs` (`12px`) / `text-sm` (`14px`) to **`15px–16px` (`text-base font-medium leading-relaxed`)**.
- **Section titles & card headers**:
  - Use `15px` (`text-[15px] font-bold text-slate-900`) with a concise 1-line subtitle (`12.5px text-slate-500`).
- **Code viewer (`.code-viewer`)**:
  - Increase font size from `12.5px` to `13px`, line-height `1.65`, with generous padding (`16px 18px`).
- **Queue/list-row exception**: the 15–16px upgrade applies only to *focused reading surfaces* (the sentence being inspected or annotated). Dense queues — `.unit-row` rows in the Tab 1 inspector list and the Tab 3 session item list — stay at `13px–14px` with a 2-line clamp (`display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden`), otherwise a 3-column queue shows only 1–2 long sentences per viewport.

### 2.2 Jargon-to-Plain-English Mapping Table

Replace cryptic labels in `index.html` with self-explanatory labels. **Rule: keep the original token in parentheses** — `doc/VERIFICATION.md` items and the paper match on these tokens (`CCPs`, `SCCUs`, `Adjudicate`, `Blind`, `Form × Entity`), so plain English must wrap, not replace, them:

| Current Label | New Self-Explanatory Label |
| :--- | :--- |
| `Code–Comment Pairs` / `CCPs` | `Code–Comment Blocks (CCPs)` |
| `Sentence Units (SCCUs)` / `SCCUs` | `Comment Sentences (SCCUs)` |
| `Quantum Comment Residence (Form × Entity)` | `Where Quantum Comments Live (Form × Entity)` |
| `Six-Category Quantum Knowledge Profile` | `What Quantum Topics They Cover (6 Categories)` |
| `Adjudicate (Show Model)` | `Review Model Predictions (Adjudicate)` |
| `Blind (Hide Model)` | `Label from Scratch (Blind)` |
| `Stratify By: Form × Entity` | `Balanced Sampling (Form × Entity)` |

### 2.3 Fix Known Cosmetic Issue (`doc/VERIFICATION.md` Part 7.1)
- In `index.html` sidebar group headers (`Infrastructure Layer` and `Application Layer`), add `gap-2` and `pr-1` between the group title `<span>` and the percentage `<span>` so `APPLICATION LAYER (NEW SDKS)` and `26.0% Q` never collide. (VERIFICATION.md Part 7.1 has been updated to treat any recurrence as a defect.)

### 2.4 Shared `<details>` Interaction Conventions

All progressive-disclosure blocks introduced by this spec (Tab 2 health check, Tab 3 statistics drawer, Tab 4 advanced options, Tab 1 more-filters/radar toggles) follow one convention:

1. **Default state: collapsed**, with the `<summary>` line showing the live value or count (e.g. `📋 Documentation Health Check (3 guidelines)`, `⚙️ Advanced Options (Warm-start · 2 Epochs · Batch 16 · Max 120)`), so the collapsed state is still informative.
2. **Summary stays in sync**: when the user changes a folded control, the summary line re-renders to reflect the new values.
3. **Bounded growth**: expanded content gets `max-height: 60vh; overflow-y: auto` so opening a fold never pushes the primary workflow off-screen.
4. **Verifiability**: folded controls keep their existing ids and remain in the DOM (no lazy mounting), so VERIFICATION.md steps that touch them only require one extra click to expand.

---

## 3. Page-by-Page Simplification Blueprint

### Page 1: `Corpus Explorer` (`#view-explorer`)

**Goal**: Let a user immediately understand *"How much quantum knowledge does this SDK carry, what topics dominate, and what does the actual commented code look like?"*

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ [Left Sidebar: 3 cols]          │ [Main Content: 9 cols]                     │
│ • Infrastructure SDKs (34.3% Q) │ 1. Header + 3 Hero KPIs (instead of 5):    │
│   - qiskit (2.1.0)              │    [Comment Sentences] [Quantum %] [Density]│
│   - qiskit-aer (0.17.2)         │    (Files & CCPs shown in subtitle line)   │
│   - qiskit-ibm-runtime (0.45.1) │ 2. Two Clear Charts Side-by-Side:          │
│ • Application SDKs (26.0% Q)    │    Left: 6-Category Horizontal Bars        │
│   - qiskit-machine-learning     │    Right: 3×3 Scope Heatmap                │
│   - qiskit-nature               │    (Radar collapsed into ▾ toggle in-card) │
│   - qiskit-algorithms           │ 3. Code–Comment Inspector:                 │
│ • [+ Build New Corpus]          │    Filter bar: [All | ⚛ Quantum | Non-Q]   │
│                                 │    + Search input + Active chart chip      │
│                                 │    Split Pane: Sentence List | Code Context│
└──────────────────────────────────────────────────────────────────────────────┘
```

**Concrete Changes**:
0. **Preserve the dashboard header actions as-is**: `⇄ Compare SDKs` (`#btn-toggle-compare`), `🏷️ Label Sample in Studio` (`startAnnotationFromCurrentCorpus()`), and `⬇ Export JSONL` (`#exp-download-link`) stay visible and unchanged — the Explorer→Studio hand-off and JSONL export are part of the documented workflow and must survive the refactor.
1. **Streamline the Top KPI Strip (from 5 small boxes to 3 prominent cards)**:
   - Card 1 (Highlighted Violet): **Quantum-Specific Share** (`#kpi-quantum-pct`, `#kpi-quantum-count`).
   - Card 2: **Comment Sentences (SCCUs)** (`#kpi-sccus`), with subtitle showing `<span id="kpi-files"></span> Python files · <span id="kpi-ccps"></span> comment blocks`.
   - Card 3: **Comment Density** (`#kpi-density`, `#kpi-density-lines`).
2. **De-clutter the Left Chart Card (`What Quantum Topics They Cover`)**:
   - On the main dashboard, give 100% width of the left chart card to the **6 clickable horizontal category bars** (`#category-breakdown-bars`) with larger labels and clear percentages (`Mathematics 28.9% (398)`).
   - Keep `#chart-radar` inside a collapsible toggle **within the same card** (per §2.4 conventions: collapsed by default, summary `📊 Show Radar View ▾`) so it does not squeeze the category bars into a narrow 50% column. Do **not** move it into the Compare drawer — the radar is the single-SDK knowledge-profile overview; the Compare drawer keeps its own dual-trace radar.

---

### Page 2: `Live Inspector & Builder` (`#view-inspector`)

**Goal**: A clean, zero-distraction **"Paste Python Code on the Left → See Extracted Quantum Comments on the Right"** experience.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Top Switcher: [🔬 Analyze Code Snippet (Default)]  [🏗️ Import Repository]    │
├───────────────────────────────────────┬──────────────────────────────────────┤
│ Left: Python Code Input (6 cols)      │ Right: Classification Results (6 cols)│
│ • Quick Presets (1-click pills):      │ • One-Line Summary Banner:           │
│   [Bell Circuit] [VQE] [Transpiler]   │   "10 sentences · 10 Quantum (100%)" │
│ • Dark Code Editor (13px mono)        │   + Collapsible <details> Audit      │
│ • [⚡ Classify Quantum Comments]       │ • Clean Sentence Result Cards        │
└───────────────────────────────────────┴──────────────────────────────────────┘
```

**Concrete Changes**:
1. **Replace Preset Dropdown with 3 One-Click Pill Buttons**:
   - Render 3 visible pill buttons above the code editor (`Bell State Circuit`, `VQE Algorithm`, `Hardware Transpiler`) that trigger `loadCodePreset(...)` on click. Keep `#inspector-preset-select` in the DOM and synced (visually de-emphasized, e.g. a small fallback dropdown beside the pills) — `loadCodePreset` is bound to it and it is the keyboard/assistive fallback; pytest does not touch the DOM either way.
2. **Collapse Verbose Documentation Health Check Details**:
   - In `#inspector-summary-panel`, show a single high-contrast summary bar: **`Extracted 10 Comment Sentences · 10 Quantum-Specific (100%)`** alongside a `<details>` toggle: **`📋 View Documentation Health Check (3 guidelines)`**. This prevents 3 multi-line alert boxes from pushing the actual comment classification cards down the page.
3. **Clean Up Individual SCCU Result Cards**:
   - Increase the sentence text to `14.5px font-medium`.
   - Show the two primary badges prominently (`[⚛ Quantum · 98%]` + `[Circuit Model]`), and render the Top-3 category probability bars in a subtle, compact single row at the bottom of the card.

---

### Page 3: `Annotation Studio` (`#view-annotate`)

**Goal**: Turn a crowded 3-column statistical dashboard into a **focused, spacious labeling card** (like Anki / Prodigy).

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Compact Top Bar: Session Select | Progress: 379/379 | Agreement: 85.0%     │
│   (CI 81.0–88.2 · κ=.70) | P 83.0 / R 86.2  [📊 Detailed Metrics ▾]        │
│                  [+ New Session]  [⬇ Export]                               │
├────────────────────────┬─────────────────────────────────────────────────────┤
│ Left Queue (3 cols)    │ Right: Focused Labeling Card (9 cols)               │
│ • Filter:              │ 1. Target Comment Sentence (16px bold, spacious)    │
│   [All / ≠ Disagrees]  │    + Model Pre-Label pill & [Accept (Space)]        │
│ • Compact Item List    │ 2. Direct 2-Step Action Buttons:                    │
│   #1 qiskit-nature     │    Step 1: [⚛ Quantum-Specific (Q)] [Non-Quantum(N)]│
│   #8 qiskit-nature ≠   │    Step 2: 2×3 Grid of 6 Quantum Categories (1–6)   │
│   ...                  │ 3. Enclosing Python Code Context + Guidelines       │
└────────────────────────┴─────────────────────────────────────────────────────┘
```

**Concrete Changes**:
1. **Condense the 6-Card Statistical Header into a 1-Line Summary Bar + Expandable Drawer**:
   - Always visible in the header: Session selector (`#ann-session-select`), Progress (`#ann-kpi-progress`: `379 / 379 (100%)`), **Human–Model Agreement** (`#ann-kpi-agreement`: `85.0%`, `#ann-kpi-ci`: `95% CI: 81.0–88.2%`, `#ann-kpi-kappa`: `κ = 0.699`), **and Precision/Recall** (`#ann-kpi-pr`: `P 83.0% / R 86.2%`) — VERIFICATION.md Part 3.1 lists agreement, CI, κ, Precision, and Recall as header metrics, so all five stay in the always-visible bar (rendered as one compact inline strip, not six cards).
   - Put only the deeper diagnostics (`F1 #ann-kpi-f1`, `Confusion TP/FP/FN/TN #ann-kpi-confusion`, `6-Category Agreement #ann-kpi-cat-agree`) inside a collapsible `<details>` panel labeled **`📊 View Detailed Statistical Breakdown (F1, Confusion Matrix, Category Agreement)`**, following §2.4 conventions.
2. **Merge the Center (5 cols) & Right (4 cols) Panes into a Single 9-Column Focus Card**:
   - Instead of splitting the sentence/code (center column) from the labeling buttons (right column), stack them naturally inside one spacious 9-column card:
     - **Top**: Target Comment Sentence (`16px font-semibold`) + Model Pre-label banner (`#ann-model-banner`).
     - **Middle**: Step 1 Binary buttons (`[Q] Quantum-Specific` / `[N] Non-Quantum`) + Step 2 Category buttons (`#ann-category-buttons` arranged in a clean **2×3 grid** instead of a tall vertical stack of 6 rows).
     - **Bottom**: Enclosing Python Source Context (`#ann-curr-code`) + Collapsible TOSEM Annotation Guidelines (`<details>`) + Prev/Next navigation bar.

---

### Page 4: `Model Trainer & Registry` (`#view-models`)

**Goal**: Separate **"Using/Training a Model"** from **"Comparing Two Models"** and hide low-level hyperparameters by default.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Active Model Registry Strip:                                                 │
│ [Task 1 Binary BERT · F1 93.6%] [Task 2 6-Class BERT · F1 84.0%] + Custom    │
├───────────────────────────────────────┬──────────────────────────────────────┤
│ Left: Simple 3-Step Trainer (7 cols)  │ Right: Model Comparison (5 cols)     │
│ Step 1: Choose Task (Task 1 / Task 2) │ • Compare Model A vs. Model B        │
│ Step 2: Choose Data Source            │   on any SDK Corpus                  │
│ Step 3: Name & [🚀 Start Fine-Tuning] │ • Agreement %, κ, and Disagreements  │
│ (⚙️ Advanced Hyperparameters folded)  │                                      │
└───────────────────────────────────────┴──────────────────────────────────────┘
```

**Concrete Changes**:
1. **Simplify the Training Form to 3 Primary Inputs**:
   - Keep **1. Classification Task** (`#train-task`), **2. Labeled Training Data Source** (`#train-source-type` + `#train-session-select`), and **3. New Model Name** (`#train-model-name`) visible by default.
2. **Fold Hyperparameters into `<details> ⚙️ Advanced Training Options`**:
   - Move `Starting Checkpoint (#train-base-model)`, `Epochs (#train-epochs)`, `Batch Size (#train-batch)`, and `Max Samples (#train-max-samples)` inside a collapsible `<details>` block showing their sensible defaults in the summary line: `⚙️ Advanced Options (Warm-start from Released Checkpoint · 2 Epochs · Batch 16 · Max 120 samples)`. The summary must re-render when any folded value changes (§2.4.2). Note VERIFICATION.md Part 4.2 now tells verifiers to expand this panel before choosing the warm-start option.

---

## 4. Verification Sign-Off Checklist (After Implementation)

**Rollout strategy (recommended)**: land in four small, separately verifiable commits rather than one big-bang change — (a) global typography + sidebar fix (§2), (b) Tab 1, (c) Tab 2, (d) Tab 3 + Tab 4. After *each* commit run the pytest suite and the corresponding VERIFICATION.md part; a pure-visual refactor's main risk is silently dropping an id or button that `app.js` binds to, and small diffs make that class of regression trivial to locate.

After applying the layout changes in `cc4q/web/static/`, run:

1. **Automated Test Suite**:
   ```bash
   .venv/bin/pytest
   ```
   Must report **51 passed** (or 49 passed, 2 skipped if checkpoints are not downloaded).
2. **Manual Browser Check (`cc4q demo` at `http://127.0.0.1:8501`)**:
   - Verify all items in `doc/VERIFICATION.md` (Parts 1–4).
   - Confirm that `doc/VERIFICATION.md` Part 7.1 (`APPLICATION LAYER (NEW SDKS) 26.0%` spacing) is resolved.
3. **Screenshot refresh**: every image that documents the UI (`doc/screenshot_*.png` and any README-embedded figures) goes stale the moment labels change — re-capture them after the refactor lands, and re-capture the four `Tool paper/figures/tab*.png` paper figures so the paper matches the shipped UI.
