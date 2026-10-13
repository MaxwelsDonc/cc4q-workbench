# CC4Q Workbench — Design Document

Version 1.0 · 2026-10-07 · Status: approved for implementation

## 1. Product Positioning

**One-liner**: *From quantum code to labeled comment corpora: build, inspect, profile.*

CC4Q Workbench turns any Python-based quantum SDK repository into a labeled
code-comment corpus (CCPs → SCCUs with three-axis labels), then provides
quantum-centric analyses of that corpus. It is the tool companion of the TOSEM
paper *"Code Comments for Quantum Software Development Kits: An Empirical Study
on Qiskit"* (the "companion paper"), which introduced the CC4Q dataset and the
quantum-specific comment taxonomy.

**User priority**: (1) ICSE tool-demo reviewers — 90-second wow loop;
(2) QSE researchers — build corpora for their own SDKs;
(3) quantum developers — audit comment practices.

## 2. Design Principles

1. **Quantum-centric.** The quantum axis (binary quantum-relatedness + the
   six-category quantum-knowledge taxonomy) is the protagonist of every page.
   The pipeline still labels every unit on three axes (quantum-relatedness,
   quantum category, developer intent), but the UI shows only the two
   quantum axes: developer intent lives exclusively in the data layer
   (units JSONL, manifest, downloads) and is never rendered.
2. **One workflow, three verbs.** Every page and every paper scenario maps to
   *Build → Inspect → Profile*:
   - **Build**: repo → labeled corpus (pipeline).
   - **Inspect**: quantum-density health check (how much quantum knowledge,
     where it lives).
   - **Profile**: six-category quantum-knowledge distribution (what kind of
     quantum knowledge), comparable across SDKs.
3. **Zero setup for reviewers.** Precomputed results for the six studied SDKs
   render instantly; Docker for full reproduction; live mode for new repos
   with guardrails.
4. **Honest output.** Model-labeled corpora are always marked as such; the
   human-verification summary (n=379, agreement 85.0%) is visible in-app.

## 3. Information Architecture

Workspace IA: a flat six-page navigation, no sections. Every artifact the
user creates is a **workspace asset** (`cc4q/workspace.py`); pages are
views over assets.

| Page | Purpose |
|---|---|
| 1. Workspace | Overview: per-type asset counts, recent activity, quick-create shortcuts, metrics, 8-primitive strip |
| 2. Corpora | Corpus assets (six built-in precomputed SDK corpora + user-created); New corpus flow (URL clone+build with >200-file guardrail / local dir / upload; optional predict → labeled asset); Open → three-section dashboard + filter table |
| 3. Annotate | Annotation session assets (resume at current progress, export, delete); New annotation wizard (corpus asset / upload / predict output → sampling → embedded annotation UI blind/adjudicate → session asset) |
| 4. Models | Released checkpoints section + user model registry (default star, upload zip, download, delete) + inline Train-new-model flow |
| 5. Evaluate | Evaluation assets (open report with radar overlay, delete); New evaluation (two models + corpus asset → agreement/P/R/Wilson → saved report) |
| 6. Playground | Snippet analysis + live-repository try-out — scratch space, nothing is saved |

Model resolution: registry default (★) → released checkpoints; single-axis
custom packages compose with the released fallback. A compact model
indicator sits in the header row of every page.

### Workspace model and asset schemas

Workspace dir: `$CC4Q_WORKSPACE` > `.cc4q_workspace/` beside a source
checkout (pyproject.toml detection) > `~/.cache/cc4q/workspace/`. An
`index.json` (atomic tmp+rename writes; corrupted → `index.json.bak` +
rebuild) lists assets; payloads live under `assets/<type>/<id>/`.

- `corpus`: {id, name, source: url|dir|upload|precomputed, sccus,
  quantum_pct?, labeled, files: {corpus, labeled?}, created_at}
- `annotation_session`: {id, name, schema, mode, total, labeled_count,
  export_path?, created_at, updated_at}
- `evaluation`: {id, name, pair: [model_a, model_b], corpus,
  metrics: {n, agreement, precision, recall, wilson95}, report_path,
  created_at}
- `model`: not duplicated in the workspace index — delegated to
  `cc4q.app.registry`; the workspace references model ids only.





## 4. Analysis Specifications

All analyses operate on SCCU-level labeled records with fields:
`id, sdk, comment_text, comment_type (docstring|block|inline), entity_level
(module|class|function), is_quantum (bool), quantum_category (6|None),
developer_intent (6)`.

| Analysis | Definition | Chart |
|---|---|---|
| Corpus stats | counts of files, CCPs, SCCUs | metric cards |
| Type × entity | SCCU counts per (comment_type, entity_level) | grouped bars |
| Quantum % | quantum SCCUs / all SCCUs | big number |
| Comment density | comment lines / total code lines (LOC from repo checkout) | small metric |
| Quantum residence | share of quantum SCCUs per (entity_level, comment_type) | heatmap |
| Category profile | category counts / quantum SCCU count, 6 categories | radar |
| Compare | two SDKs' radar traces + Quantum % | overlaid radar |

## 5. Data Layer

- `cc4q/app/data/manifest.json` — per-SDK stats + all distributions needed by §1–§3
  (computed at build time by `demo/build_demo_data.py`).
- `cc4q/app/data/units/<sdk>.jsonl` — lean SCCU records for Explore (full for the
  three new SDKs; 2,000-row seed-42 samples for the original three; code
  snippets dropped).
- Live mode computes the same manifest structure in-session and caches it in
  `st.session_state`.
- Total precomputed-data budget: ≤ 25 MB (currently ~6.6 MB).

## 6. Visual Design

Kimi-style minimal product language (kimi.com aesthetics), light mode only:

- **Surfaces**: white / very light neutral — app background `#FBFBFC`,
  cards `#FFFFFF` with a 1px `#E5E7EB` hairline border, border-radius 12px,
  no shadows. Generous whitespace.
- **Text**: near-black `#1A1A1A` primary, muted gray `#6B7280` secondary.
  Headings weight 700 (h1/h2) / 650 (h3); Streamlit default sans font.
- **Primary buttons**: Kimi signature black — `#1A1A1A` background, white
  text, ~10px radius, no shadow; hover `#000000`. Secondary/outline buttons:
  white background, dark text, 1px `#E5E7EB` border.
- **Accent**: quantum purple `#6C3FC5` is used *sparingly* — only quantum
  badges/chips, the summary strip, small highlights (hero accent line,
  unit-card left border), and the quantum charts (residence heatmap, radar).
  All other UI chrome (links, tabs, checkboxes, toggle, §1 corpus bars) is
  neutral black/gray.
- **Hero (Home)**: clean typography — large black title, gray subtitle, a
  thin purple accent line; no gradient bands.
- **Category chip palette (fixed, colorblind-aware)**: Mathematics `#1f77b4`,
  Algorithms `#d62728`, Circuit model `#6C3FC5`, Hardware `#2ca02c`,
  Software stack `#ff7f0e`, Others `#7f7f7f`.
- **Charts**: plotly only (no `st.bar_chart`); consistent axis titles; English UI
  throughout; neutral gridlines `#ECECEF`.
- **Navigation**: top navigation bar (`st.navigation(position="top")`), no
  sidebar; brand "⚛ CC4Q Workbench" top-left with the one-liner.
- **Design tokens** (WP1B, exported from `cc4q/app/ui.py`): spacing scale
  4/8/12/16/24/32 (`SPACING`), radius 10/12 (`RADIUS`), a type scale
  (`TYPE_SCALE`, caption→h1), and `BADGE_TONES`
  (neutral/quantum/success/warn); mirrored as `--cc4q-*` CSS variables.
- **Component library** (WP1B, all in `cc4q/app/ui.py`, Streamlit-native
  widgets for anything interactive so AppTest can drive pages by label):
  - `page_header(title, description, action_label=None, action_help=None)`
    — page title + one-liner + right-aligned black primary action;
    returns the click.
  - `section_divider(title, description=None)` — subsection heading with a
    hairline underneath.
  - `status_badge(text, tone="neutral")` — pill badge, returns HTML for
    composition into cards.
  - `asset_card_grid(items, key_prefix=..., columns=3)` — responsive
    HTML/CSS card grid (title + badge + meta lines); actions are native
    buttons/download-buttons rendered in a matching column row beneath each
    card row. An action is `{"label", "on_click"}` or
    `{"label", "download": {data, file_name}}`.
  - `empty_state(title, hint, action_label=None)` — centered glyph block +
    one big primary CTA; returns the click.
- Theme delivery is dual, so the palette holds no matter where the app is
  launched from: `.streamlit/config.toml` at the repo root (picked up when
  `streamlit run` is invoked from the repo root) **plus** CSS-variable and
  component overrides injected by `cc4q/app/ui.py` (covers launches from any
  other working directory, where Streamlit does not discover the project
  config and would otherwise fall back to the default red #FF4B4B).

## 7. Technical Architecture

```
demo/
├── app.py              # st.navigation entry
├── pages/              # p_home / p_analyze_code / p_analyze_repo / p_explore
├── cc4q_analysis.py    # snippet pipeline: extract → segment → classify
├── repo_live.py        # live repo pipeline + guardrails + density computation
├── dashboard.py        # §1–§3 sections + compare mode (quantum-centric)
├── data_io.py          # manifest/units loading (cached)
├── model_cache.py      # lazy model loading + missing-checkpoint warning
├── ui.py               # theme CSS, cards, chips, plotly layout helpers
├── demo/build_demo_data.py  # regenerates cc4q/app/data/
└── smoke_test.py       # data checks + AppTest page tests
```

Rules: CPU-only inference; models load lazily; no torch import at page load;
missing checkpoints disable Analyze buttons with instructions, never crash.

## 8. Acceptance Criteria

1. `python demo/smoke_test.py --app` passes; headless run returns HTTP 200 on
   all six pages.
2. Precomputed dashboards for all six SDKs render §1–§3 + compare without
   model checkpoints installed.
3. Live mode: a small public repo (e.g. this workbench repo) completes all
   four stages and renders the dashboard; a >200-file repo is refused with
   the Docker hint.
4. Density values in §2 match a direct recomputation on the cloned repos
   (spot-check one SDK).
5. Compare mode visually reproduces the infra-vs-application gap
   (Quantum % 34.3 vs 26.0 aggregate).
6. All six pages render under AppTest. Workspace assets persist across
   sessions (restart test); the Corpora page seeds six built-in SDK assets
   and its Open action renders the §1–§3 dashboard; Annotate resumes a
   session at current progress; Evaluate reopens a saved report; the
   Models page rejects contract violations with its example-row error;
   the header model indicator defaults to the released checkpoints.
7. No developer-intent UI anywhere — no intent charts, badges, filters, or
   table columns; intent appears only in the data layer (units JSONL,
   manifest, downloads). The third classifier still runs at inference time.

## 9. Out of Scope (v1.0)

User accounts; annotation UI (internal tooling, not shipped); non-Python
languages; sentence-embedding analyses (RQ8-style); multi-language UI;
public hosting (HF Spaces) — local/Docker only for v1.0.
