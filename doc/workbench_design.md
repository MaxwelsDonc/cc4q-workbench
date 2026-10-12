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

Four pages, reachable via the top navigation (`st.navigation`):

| Page | Workflow stage | Purpose |
|---|---|---|
| 1. Home | — | Positioning, numbers, entry points |
| 2. Analyze Code | Inspect (unit level) | Paste snippet → real-time three-axis labels |
| 3. Analyze Repository | Build → Inspect → Profile | The hero page |
| 4. Explore Corpus | Inspect (browse) | Filter/search labeled SCCUs |

### 3.1 Home

- Hero band (purple gradient): name, one-liner, buttons to GitHub repo,
  companion paper (citation text), demo video (placeholder URL until recorded).
- Three metric cards: **6 SDKs** · **39,593 SCCUs** · **2 quantum label axes**.
- Workflow strip: three cards *Build* / *Inspect* / *Profile*, each with a
  one-line description and a `st.page_link` to the relevant page.
- Footer: Beihang University, MIT license note, artifact links.

### 3.2 Analyze Code

- Left column: code textarea pre-filled with a Bell-state example (verified
  clean labels; no `(|00>+|11>)/sqrt(2)` line). Button: **Analyze**.
- Right column, on result:
  - Summary strip: `N units · M quantum-related (P%)` — intent is NOT in the
    summary strip.
  - One card per SCCU. Badge hierarchy (visual weight in this order):
    1. **quantum badge** — solid purple `✓ quantum` / gray outline
       `✗ non-quantum` (largest);
    2. **quantum category badge** — colored chip (quantum units only).
  - Card caption: `DOCSTRING · FUNCTION` style entity/type info.
  - Developer intent is not shown anywhere on this page (data layer only).
- Model loading: lazy via `st.cache_resource` on first Analyze click; spinner
  text "Loading classifiers (first run takes a few seconds)". CPU only.
- Edge states: empty input → info message; non-parseable Python → warning +
  automatic line-by-line fallback (no manual raw-text mode); missing
  checkpoints → warning with
  `python scripts/download_models.py` instructions and disabled button.

### 3.3 Analyze Repository

Top: two tabs — **Precomputed SDKs** (instant) and **Live repository**.

**Precomputed tab**: dropdown with the six SDKs (qiskit 2.1.0, qiskit-aer
0.17.2, qiskit-ibm-runtime 0.45.1, qiskit-machine-learning 0.9.1,
qiskit-nature 0.8, qiskit-algorithms 0.4.0). Selecting one renders the
three-section dashboard below.

**Live tab**: GitHub URL input. Four-stage progress via `st.status`:
Cloning → Extracting → Segmenting → Labeling. Guardrail: if the cloned repo
contains > 200 `.py` files, refuse politely and point to the Docker image for
large repos. On success, render the same three-section dashboard and mark it
"model-labeled, unverified".

**Result dashboard — three sections, in order:**

**§1 Corpus Built** *(Build)*
- Metric cards: Python files / CCPs / SCCUs.
- Chart: comment type (docstring/block/inline) × entity level
  (module/class/function) grouped bar chart (plotly).
- Download button: labeled corpus JSONL.

**§2 Quantum Density Check** *(Inspect)* — mirroring RQ2/RQ3 of the companion
paper
- Big-number card: **Quantum %** of SCCUs.
- Comment density: comment lines / code lines (live mode computes it from the
  cloned repo; precomputed mode shows the value computed at build time).
- Heatmap: quantum SCCU share by entity level × comment form.

**§3 Knowledge Profile** *(Profile)* — mirroring RQ6 of the companion paper
- Radar chart (plotly `Scatterpolar`) over the six quantum categories:
  Mathematics / Algorithms / Circuit model / Hardware / Software stack /
  Others, values = share of quantum SCCUs.
- One-line interpretation hint, e.g. "This SDK's quantum comments concentrate
  on the circuit model."

**Compare mode** (below the dashboard, both tabs feed it):
- Select two SDKs (default: qiskit vs qiskit-machine-learning).
- Overlaid radar charts (two traces, one figure) + Quantum % side-by-side
  cards. This is the figure that supports the paper's infrastructure-vs-
  application-layer finding.

### 3.4 Explore Corpus

- Default view: **quantum units only** (toggle to include non-quantum).
- Filter bar order: quantum category → entity level → comment form → SDK →
  keyword search. No developer-intent filter (intent is data-layer only, §2).
- Paginated dataframe (rows-per-page selector), download-filtered-JSONL
  button.

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

- `demo/data/manifest.json` — per-SDK stats + all distributions needed by §1–§3
  (computed at build time by `demo/build_demo_data.py`).
- `demo/data/units/<sdk>.jsonl` — lean SCCU records for Explore (full for the
  three new SDKs; 2,000-row seed-42 samples for the original three; code
  snippets dropped).
- Live mode computes the same manifest structure in-session and caches it in
  `st.session_state`.
- Total `demo/data/` budget: ≤ 25 MB (currently ~6.6 MB).

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
- Theme delivery is dual, so the palette holds no matter where the app is
  launched from: `.streamlit/config.toml` at the repo root (picked up when
  `streamlit run` is invoked from the repo root) **plus** CSS-variable and
  component overrides injected by `demo/ui.py` (covers launches from any
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
├── build_demo_data.py  # regenerates demo/data/
└── smoke_test.py       # data checks + AppTest page tests
```

Rules: CPU-only inference; models load lazily; no torch import at page load;
missing checkpoints disable Analyze buttons with instructions, never crash.

## 8. Acceptance Criteria

1. `python demo/smoke_test.py --app` passes; headless run returns HTTP 200 on
   all four pages.
2. Precomputed dashboards for all six SDKs render §1–§3 + compare without
   model checkpoints installed.
3. Live mode: a small public repo (e.g. this workbench repo) completes all
   four stages and renders the dashboard; a >200-file repo is refused with
   the Docker hint.
4. Density values in §2 match a direct recomputation on the cloned repos
   (spot-check one SDK).
5. Compare mode visually reproduces the infra-vs-application gap
   (Quantum % 34.3 vs 26.0 aggregate).
6. No developer-intent UI anywhere — no intent charts, badges, filters, or
   table columns; intent appears only in the data layer (units JSONL,
   manifest, downloads). The third classifier still runs at inference time.

## 9. Out of Scope (v1.0)

User accounts; annotation UI (internal tooling, not shipped); non-Python
languages; sentence-embedding analyses (RQ8-style); multi-language UI;
public hosting (HF Spaces) — local/Docker only for v1.0.
