/* CC4Q Workbench — Interactive Client Application */

const STATE = {
  activeTab: "explorer",
  overview: null,
  activeCorpusId: "qiskit",
  activeCorpusStats: null,
  explorerMode: "overview", // "overview" (benchmark landing) | "sdk" (single-corpus dashboard)
  units: [],
  unitsTotal: 0,
  unitsOffset: 0,
  unitsLimit: 40,
  selectedUnitIndex: 0,
  // Annotation Studio
  sessions: [],
  activeSession: null,
  sessionItems: [],
  filteredSessionIndices: [],
  activeAnnFilteredPos: 0,
  sessionMetrics: null,
  // Models & Training
  modelsInfo: null,
  charts: {},
};

const CATEGORY_META = {
  "Mathematics for quantum information": { short: "Mathematics", color: "#2563EB", bg: "#EFF6FF", border: "#BFDBFE", key: "1" },
  "Quantum algorithms": { short: "Algorithms", color: "#DC2626", bg: "#FEF2F2", border: "#FECACA", key: "2" },
  "Quantum circuit model": { short: "Circuit Model", color: "#7C3AED", bg: "#F5F3FF", border: "#DDD6FE", key: "3" },
  "Quantum hardware": { short: "Hardware", color: "#059669", bg: "#ECFDF5", border: "#A7F3D0", key: "4" },
  "Quantum software framework": { short: "Software Stack", color: "#D97706", bg: "#FFFBEB", border: "#FDE68A", key: "5" },
  "Others": { short: "Others", color: "#64748B", bg: "#F1F5F9", border: "#CBD5E1", key: "6" },
};

const CATEGORY_ORDER = [
  "Mathematics for quantum information",
  "Quantum algorithms",
  "Quantum circuit model",
  "Quantum hardware",
  "Quantum software framework",
  "Others",
];

function esc(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function catBadge(catName) {
  if (!catName) return "";
  const m = CATEGORY_META[catName] || CATEGORY_META["Others"];
  return `<span class="cat-pill" style="background:${m.bg};color:${m.color};border:1px solid ${m.border};">
    <span style="width:6px;height:6px;border-radius:999px;background:${m.color};"></span>
    ${esc(m.short)}
  </span>`;
}

function quantumBadge(isQ, prob) {
  if (isQ) {
    const pct = prob !== undefined && prob !== null ? ` · ${(prob * 100).toFixed(0)}%` : "";
    return `<span class="badge badge-quantum">⚛ Quantum${pct}</span>`;
  }
  return `<span class="badge badge-nonquantum">Non-Quantum</span>`;
}

function highlightCodeWithComment(codeSnippet, commentText) {
  if (!codeSnippet) {
    return `<span class="text-slate-500"># Source code snippet not available for this record</span>`;
  }
  const lines = codeSnippet.split("\n");
  const probe = (commentText || "").trim().slice(0, 32).toLowerCase();
  return lines
    .map((line) => {
      const isHit = probe && probe.length >= 4 && line.toLowerCase().includes(probe);
      if (isHit) {
        return `<span class="code-line-highlight">${esc(line)}</span>`;
      }
      return esc(line);
    })
    .join("\n");
}

function getChart(domId) {
  const el = document.getElementById(domId);
  if (!el) return null;
  if (STATE.charts[domId]) {
    STATE.charts[domId].resize();
    return STATE.charts[domId];
  }
  const chart = echarts.init(el);
  STATE.charts[domId] = chart;
  return chart;
}

window.addEventListener("resize", () => {
  Object.values(STATE.charts).forEach((c) => c && c.resize());
});

// Charts rendered inside a collapsed <details> (e.g. the Tab 1 radar toggle) have
// zero size until the fold opens — resize them when any disclosure toggles.
document.addEventListener("toggle", (e) => {
  if (e.target && e.target.tagName === "DETAILS") {
    setTimeout(() => {
      Object.values(STATE.charts).forEach((c) => c && c.resize());
    }, 60);
  }
}, true);

// ======================== INITIALIZATION & NAVIGATION ========================

async function initApp() {
  await refreshOverview();
  showBenchmarkOverview();
  populateInspectorPresets();
  renderGuidelinesReference();
  setupKeyboardShortcuts();
  setupAdvancedOptionsSummary();
}

async function refreshOverview() {
  const res = await fetch("/api/overview");
  const data = await res.json();
  STATE.overview = data;

  // Update header model & device indicator
  document.getElementById("header-active-model").textContent = data.models.active_name;
  document.getElementById("header-device-badge").textContent = (data.device || "cpu").toUpperCase();
  const dot = document.getElementById("model-status-dot");
  dot.className = data.models.checkpoints_ready
    ? "w-2 h-2 rounded-full bg-emerald-500"
    : "w-2 h-2 rounded-full bg-amber-500";

  renderExplorerSidebar();
  populateCompareSelects();
}

function switchTab(tabId) {
  STATE.activeTab = tabId;
  document.querySelectorAll("#main-nav .nav-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tabId);
  });
  ["explorer", "inspector", "builder", "annotate", "models"].forEach((id) => {
    const sec = document.getElementById(`view-${id}`);
    if (sec) sec.classList.toggle("hidden", id !== tabId);
  });

  if (tabId === "explorer") {
    setTimeout(() => {
      Object.values(STATE.charts).forEach((c) => c && c.resize());
    }, 60);
  } else if (tabId === "annotate") {
    initAnnotationStudio();
  } else if (tabId === "models") {
    loadModelsStudio();
  }
}

// ======================== VIEW 1: CORPUS EXPLORER ========================

function renderExplorerSidebar() {
  const corpora = (STATE.overview && STATE.overview.corpora) || [];
  const infraEl = document.getElementById("sidebar-infra-list");
  const appEl = document.getElementById("sidebar-app-list");
  const customGroup = document.getElementById("sidebar-custom-group");
  const customEl = document.getElementById("sidebar-custom-list");

  // Benchmark Overview item: active highlight (D1)
  const overviewItem = document.getElementById("sidebar-overview-item");
  if (overviewItem) {
    const isOverview = STATE.explorerMode === "overview";
    overviewItem.className = `px-3 py-2 rounded-lg cursor-pointer transition flex items-center justify-between border mb-3 ${
      isOverview
        ? "bg-violet-50 border-violet-300 text-violet-950 font-semibold"
        : "bg-white border-transparent hover:bg-slate-50 text-slate-700"
    }`;
  }

  const infra = corpora.filter((c) => c.builtin && c.layer === "infrastructure");
  const appl = corpora.filter((c) => c.builtin && c.layer === "application");
  const custom = corpora.filter((c) => !c.builtin);

  const renderItem = (c) => {
    const key = c.sdk || c.id;
    const isActive = STATE.explorerMode === "sdk" && (STATE.activeCorpusId === key || STATE.activeCorpusId === c.id);
    const qPct = c.quantum_pct !== null && c.quantum_pct !== undefined ? `${(c.quantum_pct * 100).toFixed(1)}%` : "unlabeled";
    return `
      <div onclick="selectCorpus('${esc(c.id)}')"
        class="px-3 py-2 rounded-lg cursor-pointer transition flex items-center justify-between border ${
          isActive
            ? "bg-violet-50 border-violet-300 text-violet-950 font-semibold"
            : "bg-white border-transparent hover:bg-slate-50 text-slate-700"
        }">
        <div class="truncate pr-2">
          <div class="text-xs truncate">${esc(c.sdk || c.name)}</div>
          <div class="text-[11px] text-slate-400 font-mono">${(c.sccus || 0).toLocaleString()} SCCUs</div>
        </div>
        <span class="text-xs font-mono px-2 py-0.5 rounded ${
          isActive ? "bg-violet-700 text-white font-bold" : "bg-slate-100 text-slate-600"
        }">${qPct}</span>
      </div>
    `;
  };

  infraEl.innerHTML = infra.map(renderItem).join("");
  appEl.innerHTML = appl.map(renderItem).join("");
  if (custom.length > 0) {
    customGroup.classList.remove("hidden");
    customEl.innerHTML = custom.map(renderItem).join("");
  } else {
    customGroup.classList.add("hidden");
  }
}

async function selectCorpus(corpusId) {
  STATE.activeCorpusId = corpusId;
  STATE.explorerMode = "sdk";
  STATE.unitsOffset = 0;
  updateExplorerModePanels();
  renderExplorerSidebar();
  await loadCorpusUnitsAndDashboard();
}

// ======================== BENCHMARK OVERVIEW (D1) ========================

function getManifestRepos() {
  return ((STATE.overview || {}).manifest || {}).repos || {};
}

// Pure-front-end aggregation over manifest repos of one architecture layer.
// Pass layer === null to aggregate across every repo (both layers).
function aggregateLayerStats(layer) {
  const repos = getManifestRepos();
  const agg = {
    layer: layer || "all",
    sdk: layer || "All SDKs",
    python_files: 0,
    ccps: 0,
    sccus: 0,
    quantum_sccus: 0,
    category_counts: {},
    ctype_by_entity: {},
    quantum_ctype_by_entity: {},
    comment_density: { comment_lines: 0, code_lines: 0, value: 0 },
  };
  const ctypes = ["docstring", "block", "inline"];
  const entities = ["module", "class", "function"];
  Object.values(repos).forEach((r) => {
    if (layer && r.layer !== layer) return;
    agg.python_files += r.python_files || r.files || 0;
    agg.ccps += r.ccps || 0;
    agg.sccus += r.sccus || 0;
    agg.quantum_sccus += r.quantum_sccus || 0;
    agg.comment_density.comment_lines += ((r.comment_density || {}).comment_lines) || 0;
    agg.comment_density.code_lines += ((r.comment_density || {}).code_lines) || 0;
    CATEGORY_ORDER.forEach((c) => {
      agg.category_counts[c] = (agg.category_counts[c] || 0) + ((r.category_counts || {})[c] || 0);
    });
    ctypes.forEach((ct) => {
      entities.forEach((en) => {
        agg.quantum_ctype_by_entity[ct] = agg.quantum_ctype_by_entity[ct] || {};
        agg.quantum_ctype_by_entity[ct][en] =
          (agg.quantum_ctype_by_entity[ct][en] || 0) + ((((r.quantum_ctype_by_entity || {})[ct]) || {})[en] || 0);
        agg.ctype_by_entity[ct] = agg.ctype_by_entity[ct] || {};
        agg.ctype_by_entity[ct][en] =
          (agg.ctype_by_entity[ct][en] || 0) + ((((r.ctype_by_entity || {})[ct]) || {})[en] || 0);
      });
    });
  });
  agg.quantum_proportion = agg.sccus > 0 ? agg.quantum_sccus / agg.sccus : 0;
  agg.comment_density.value =
    agg.comment_density.code_lines > 0 ? agg.comment_density.comment_lines / agg.comment_density.code_lines : 0;
  return agg;
}

// Aggregate across every manifest repo (infrastructure + application layers).
function aggregateAllStats() {
  return aggregateLayerStats(null);
}

function updateExplorerModePanels() {
  const isOverview = STATE.explorerMode === "overview";
  document.getElementById("explorer-inspector-panel").classList.toggle("hidden", isOverview);
  document.getElementById("explorer-overview-placeholder").classList.toggle("hidden", !isOverview);
  document.getElementById("overview-sdk-table-card").classList.toggle("hidden", !isOverview);
  // Compare SDKs is a benchmark-overview action only — hidden in single-SDK dashboards
  document.getElementById("btn-toggle-compare").classList.toggle("hidden", !isOverview);
}

function showBenchmarkOverview() {
  STATE.explorerMode = "overview";
  updateExplorerModePanels();
  renderExplorerSidebar();

  const all = aggregateAllStats();

  // Header
  document.getElementById("exp-corpus-title").textContent = "TOSEM Benchmark Overview";
  const badge = document.getElementById("exp-corpus-badge");
  badge.className = "badge badge-infra";
  badge.textContent = `${Object.keys(getManifestRepos()).length} SDKs`;
  document.getElementById("exp-corpus-source").textContent = "Aggregated from manifest";
  document.getElementById("exp-corpus-subtitle").textContent =
    "Collective results across all 6 SDKs — 3 infrastructure (TOSEM benchmark) + 3 application (analyzed with this workbench) · Pick an SDK below (or in the sidebar) to drill into its sentences.";

  // KPI cards (reuse the same slots as the single-SDK dashboard)
  document.getElementById("kpi-quantum-pct").textContent = `${(all.quantum_proportion * 100).toFixed(1)}%`;
  document.getElementById("kpi-quantum-count").textContent = `${all.quantum_sccus.toLocaleString()} quantum sentences`;
  document.getElementById("kpi-sccus").textContent = all.sccus.toLocaleString();
  document.getElementById("kpi-files").textContent = all.python_files.toLocaleString();
  document.getElementById("kpi-ccps").textContent = all.ccps.toLocaleString();

  // Third card slot: overall comment density across all repos (same metric as single-SDK dashboards)
  document.getElementById("kpi-density").textContent = all.comment_density.value.toFixed(3);
  document.getElementById("kpi-density-lines").textContent =
    all.comment_density.code_lines > 0
      ? `${all.comment_density.comment_lines.toLocaleString()} / ${all.comment_density.code_lines.toLocaleString()} LOC`
      : "comment / code lines";

  // Aggregate charts (reuses the single-SDK renderers)
  renderRadarAndCategoryBars(all, { clickable: false });
  renderResidenceChart();
  renderOverviewSdkTable();
}

function renderOverviewSdkTable() {
  const tbody = document.getElementById("overview-sdk-table");
  if (!tbody) return;
  const repos = getManifestRepos();
  const fmt = (n) => (n || 0).toLocaleString();

  const sdkRow = (r) => `
    <tr onclick="selectCorpus('${esc(r.sdk)}')" class="cursor-pointer hover:bg-violet-50/60 border-b border-slate-100 transition"
        title="Open ${esc(r.sdk)} dashboard">
      <td class="py-2 pr-3 font-semibold text-slate-800 font-mono">${esc(r.sdk)}</td>
      <td class="py-2 pr-3"><span class="badge ${r.layer === "infrastructure" ? "badge-infra" : "badge-app"}">${r.layer === "infrastructure" ? "Infrastructure" : "Application"}</span></td>
      <td class="py-2 pr-3 text-right font-mono text-slate-600">${fmt(r.python_files || r.files)}</td>
      <td class="py-2 pr-3 text-right font-mono text-slate-600">${fmt(r.ccps)}</td>
      <td class="py-2 pr-3 text-right font-mono text-slate-600">${fmt(r.sccus)}</td>
      <td class="py-2 pr-3 text-right font-mono font-semibold ${r.layer === "infrastructure" ? "text-blue-700" : "text-emerald-700"}">${((r.quantum_proportion || 0) * 100).toFixed(1)}%</td>
      <td class="py-2 text-right font-mono text-slate-600">${(((r.comment_density || {}).value) || 0).toFixed(3)}</td>
    </tr>`;

  const subtotalRow = (layer, agg, n) => `
    <tr class="border-b border-slate-200 bg-slate-50/80 font-bold text-slate-800">
      <td class="py-2 pr-3" colspan="2">${layer === "infrastructure" ? "Infrastructure subtotal" : "Application subtotal"} (${n} SDKs)</td>
      <td class="py-2 pr-3 text-right font-mono">${fmt(agg.python_files)}</td>
      <td class="py-2 pr-3 text-right font-mono">${fmt(agg.ccps)}</td>
      <td class="py-2 pr-3 text-right font-mono">${fmt(agg.sccus)}</td>
      <td class="py-2 pr-3 text-right font-mono text-violet-700">${(agg.quantum_proportion * 100).toFixed(1)}%</td>
      <td class="py-2 text-right font-mono">${agg.comment_density.value.toFixed(3)}</td>
    </tr>`;

  let html = "";
  ["infrastructure", "application"].forEach((layer) => {
    const items = Object.values(repos).filter((r) => r.layer === layer);
    items.forEach((r) => {
      html += sdkRow(r);
    });
    if (items.length) html += subtotalRow(layer, aggregateLayerStats(layer), items.length);
  });
  tbody.innerHTML = html;
}

async function loadCorpusUnitsAndDashboard() {
  const qFilter = document.getElementById("filter-quantum").value;
  const catFilter = document.getElementById("filter-category").value;
  const ctypeFilter = document.getElementById("filter-ctype").value;
  const etypeFilter = document.getElementById("filter-etype").value;
  const searchQ = document.getElementById("filter-search").value.trim();

  const params = new URLSearchParams({
    quantum: qFilter,
    category: catFilter,
    comment_type: ctypeFilter,
    entity_type: etypeFilter,
    q: searchQ,
    offset: String(STATE.unitsOffset),
    limit: String(STATE.unitsLimit),
  });

  const res = await fetch(`/api/corpora/${encodeURIComponent(STATE.activeCorpusId)}/units?${params}`);
  const data = await res.json();
  if (data.error) return;

  STATE.activeCorpusStats = data.stats;
  STATE.units = data.units || [];
  STATE.unitsTotal = data.total || 0;
  STATE.selectedUnitIndex = 0;

  renderCorpusKPIs(data.asset, data.stats);
  renderRadarAndCategoryBars(data.stats);
  renderResidenceChart();
  renderExplorerUnitsList();
  renderExplorerUnitDetail(0);
}

function renderCorpusKPIs(asset, stats) {
  const title = asset.name || `${stats.sdk} (${stats.version})`;
  document.getElementById("exp-corpus-title").textContent = title;
  const badge = document.getElementById("exp-corpus-badge");
  if (stats.layer === "infrastructure") {
    badge.className = "badge badge-infra";
    badge.textContent = "Infrastructure SDK";
  } else if (stats.layer === "application") {
    badge.className = "badge badge-app";
    badge.textContent = "Application SDK";
  } else {
    badge.className = "badge badge-quantum";
    badge.textContent = "Custom Corpus";
  }

  document.getElementById("exp-corpus-source").textContent =
    stats.source === "tosem-release"
      ? "TOSEM Gold Benchmark (full stats · 2,000-unit sample)"
      : stats.source === "cc4q-pipeline"
      ? "CC4Q Pipeline (full corpus)"
      : "User Workspace Corpus";
  // Subtitle is benchmark-overview copy only — don't leave it stale in single-SDK mode
  document.getElementById("exp-corpus-subtitle").textContent = "";

  document.getElementById("kpi-files").textContent = (stats.python_files || stats.files || 0).toLocaleString();
  document.getElementById("kpi-ccps").textContent = (stats.ccps || stats.sccus || 0).toLocaleString();
  document.getElementById("kpi-sccus").textContent = (stats.sccus || 0).toLocaleString();
  document.getElementById("kpi-quantum-pct").textContent = `${((stats.quantum_proportion || 0) * 100).toFixed(1)}%`;
  document.getElementById("kpi-quantum-count").textContent = `${(stats.quantum_sccus || 0).toLocaleString()} quantum SCCUs`;

  const dens = (stats.comment_density && stats.comment_density.value) || 0;
  document.getElementById("kpi-density").textContent = dens.toFixed(3);
  const cl = (stats.comment_density && stats.comment_density.comment_lines) || 0;
  const sl = (stats.comment_density && stats.comment_density.code_lines) || 0;
  document.getElementById("kpi-density-lines").textContent =
    sl > 0 ? `${cl.toLocaleString()} / ${sl.toLocaleString()} LOC` : "comment / code lines";
}

function renderRadarAndCategoryBars(stats, opts) {
  opts = opts || {};
  const clickable = opts.clickable !== false; // benchmark-overview bars are display-only
  const catCounts = stats.category_counts || {};
  const qTotal = Math.max(1, stats.quantum_sccus || 1);
  const shares = CATEGORY_ORDER.map((c) => ((catCounts[c] || 0) / qTotal) * 100);
  const maxShare = Math.max(35, ...shares.map((v) => Math.ceil(v / 5) * 5));

  const chart = getChart("chart-radar");
  if (chart) {
    chart.setOption({
      tooltip: { trigger: "item" },
      radar: {
        indicator: CATEGORY_ORDER.map((c) => ({
          name: CATEGORY_META[c].short,
          max: maxShare,
        })),
        radius: "66%",
        splitNumber: 4,
        axisName: { color: "#475569", fontSize: 11, fontWeight: 600 },
        splitArea: { areaStyle: { color: ["#FFFFFF", "#F8FAFC"] } },
      },
      series: [
        {
          type: "radar",
          data: [
            {
              value: shares.map((s) => Number(s.toFixed(1))),
              name: stats.sdk || "Corpus",
              areaStyle: { color: "rgba(109, 40, 217, 0.18)" },
              lineStyle: { color: "#6D28D9", width: 2.2 },
              itemStyle: { color: "#6D28D9" },
            },
          ],
        },
      ],
    });
  }

  // Clickable horizontal breakdown bars
  const activeCat = document.getElementById("filter-category").value;
  const barsEl = document.getElementById("category-breakdown-bars");
  barsEl.innerHTML = CATEGORY_ORDER.map((cat) => {
    const cnt = catCounts[cat] || 0;
    const pct = ((cnt / qTotal) * 100).toFixed(1);
    const meta = CATEGORY_META[cat];
    const isSelected = clickable && activeCat === cat;
    return `
      <div ${clickable ? `onclick="filterByCategory('${esc(cat)}')"` : ""}
        class="p-1.5 rounded-lg transition border ${
          clickable ? "cursor-pointer " : "cursor-default opacity-95 "
        }${
          isSelected ? "bg-violet-50 border-violet-300" : "border-transparent hover:bg-slate-50"
        }">
        <div class="flex items-center justify-between text-xs mb-1">
          <span class="font-semibold text-slate-700 flex items-center gap-1.5">
            <span style="width:8px;height:8px;border-radius:2px;background:${meta.color};"></span>
            ${esc(meta.short)}
          </span>
          <span class="font-mono text-slate-600">${pct}% <span class="text-slate-400">(${cnt.toLocaleString()})</span></span>
        </div>
        <div class="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div style="width:${Math.min(100, pct)}%;background:${meta.color};" class="h-full rounded-full"></div>
        </div>
      </div>
    `;
  }).join("");
}

function filterByCategory(cat) {
  if (STATE.explorerMode !== "sdk") return; // benchmark overview bars are display-only
  const sel = document.getElementById("filter-category");
  if (sel.value === cat) {
    sel.value = "";
  } else {
    sel.value = cat;
    document.getElementById("filter-quantum").value = "quantum";
  }
  resetAndLoadUnits();
}

function renderResidenceChart() {
  if (STATE.explorerMode === "overview") {
    renderResidenceChartForStats(aggregateAllStats(), false);
  } else {
    renderResidenceChartForStats(STATE.activeCorpusStats, true);
  }
}

function renderResidenceChartForStats(stats, interactive) {
  if (!stats) return;
  const mode = document.getElementById("heatmap-mode").value;
  const ctypes = ["docstring", "block", "inline"];
  const entities = ["module", "class", "function"];

  const sourceTable = mode === "all_count" ? stats.ctype_by_entity || {} : stats.quantum_ctype_by_entity || {};
  const denom = mode === "quantum_share" ? Math.max(1, stats.quantum_sccus || 1) : 1;

  const data = [];
  let maxVal = 1;
  ctypes.forEach((ct, yIdx) => {
    entities.forEach((ent, xIdx) => {
      const raw = (sourceTable[ct] && sourceTable[ct][ent]) || 0;
      const val = mode === "quantum_share" ? Number(((raw / denom) * 100).toFixed(1)) : raw;
      if (val > maxVal) maxVal = val;
      data.push([xIdx, yIdx, val, ct, ent, raw]);
    });
  });

  const chart = getChart("chart-residence");
  if (!chart) return;
  chart.off("click");
  if (interactive) {
    chart.on("click", (params) => {
      if (params && params.data) {
        const [, , , ct, ent] = params.data;
        document.getElementById("filter-ctype").value = ct;
        document.getElementById("filter-etype").value = ent;
        if (mode !== "all_count") {
          document.getElementById("filter-quantum").value = "quantum";
        }
        resetAndLoadUnits();
      }
    });
  }

  chart.setOption({
    tooltip: {
      formatter: (p) => {
        const [, , val, ct, ent, raw] = p.data;
        return `<b>${ct} × ${ent}</b><br/>Count: ${raw.toLocaleString()} SCCUs${
          mode === "quantum_share" ? ` (${val}% of quantum)` : ""
        }<br/><span style="color:#A78BFA">${interactive ? "Click to filter inspector" : "Select an SDK to enable filtering"}</span>`;
      },
    },
    grid: { left: 75, right: 20, top: 15, bottom: 32 },
    xAxis: {
      type: "category",
      data: ["Module", "Class", "Function"],
      splitArea: { show: true },
      axisLabel: { color: "#334155", fontWeight: 600, fontSize: 11 },
    },
    yAxis: {
      type: "category",
      data: ["Docstring", "Block (#)", "Inline (#)"],
      splitArea: { show: true },
      axisLabel: { color: "#334155", fontWeight: 600, fontSize: 11 },
    },
    visualMap: {
      min: 0,
      max: maxVal,
      show: false,
      inRange: {
        color: ["#F8FAFC", "#EDE9FE", "#C4B5FD", "#8B5CF6", "#5B21B6"],
      },
    },
    series: [
      {
        type: "heatmap",
        data: data,
        label: {
          show: true,
          formatter: (p) => (mode === "quantum_share" ? `${p.data[2]}%` : p.data[2].toLocaleString()),
          fontWeight: 600,
          fontSize: 11.5,
        },
        itemStyle: {
          borderColor: "#FFFFFF",
          borderWidth: 3,
          borderRadius: 6,
        },
      },
    ],
  });
}

function renderExplorerUnitsList() {
  const listEl = document.getElementById("explorer-units-list");
  const totalPages = Math.max(1, Math.ceil(STATE.unitsTotal / STATE.unitsLimit));
  const currPage = Math.floor(STATE.unitsOffset / STATE.unitsLimit) + 1;

  document.getElementById("units-count-label").textContent = `${STATE.unitsTotal.toLocaleString()} matching units`;
  document.getElementById("units-page-label").textContent = `${currPage} / ${totalPages}`;
  document.getElementById("btn-prev-page").disabled = STATE.unitsOffset <= 0;
  document.getElementById("btn-next-page").disabled = STATE.unitsOffset + STATE.unitsLimit >= STATE.unitsTotal;

  if (!STATE.units.length) {
    listEl.innerHTML = `<div class="p-8 text-center text-xs text-slate-400">No comment units match the current filters.</div>`;
    return;
  }

  listEl.innerHTML = STATE.units
    .map((u, idx) => {
      const isSel = idx === STATE.selectedUnitIndex;
      return `
        <div onclick="renderExplorerUnitDetail(${idx})" class="unit-row ${isSel ? "selected" : ""}">
          <div class="flex flex-wrap items-center justify-between gap-1.5 mb-1">
            <div class="flex items-center gap-1.5">
              ${quantumBadge(u.quantum_related)}
              ${u.quantum_related ? catBadge(u.quantum_category) : ""}
            </div>
            <span class="text-[11px] font-mono text-slate-400">${esc(u.comment_type)} · ${esc(u.code_entity_type)}</span>
          </div>
          <div class="text-[13px] text-slate-800 font-medium line-clamp-2 leading-relaxed">${esc(u.comment_text)}</div>
          <div class="text-[11px] font-mono text-slate-400 truncate mt-1">${esc(u.file)}</div>
        </div>
      `;
    })
    .join("");
}

function renderExplorerUnitDetail(idx) {
  STATE.selectedUnitIndex = idx;
  document.querySelectorAll("#explorer-units-list .unit-row").forEach((el, i) => {
    el.classList.toggle("selected", i === idx);
  });

  const detailEl = document.getElementById("explorer-unit-detail");
  const u = STATE.units[idx];
  if (!u) {
    detailEl.innerHTML = `<div class="text-center text-slate-400 my-auto py-16 text-xs">No unit selected.</div>`;
    return;
  }

  const cLines = u.comment_line && u.comment_line.length === 2 ? `Lines ${u.comment_line[0]}–${u.comment_line[1]}` : "";
  const sLines = u.code_line && u.code_line.length === 2 ? `Entity Scope Lines ${u.code_line[0]}–${u.code_line[1]}` : "";

  detailEl.innerHTML = `
    <div class="space-y-3.5">
      <!-- Top Metadata Strip -->
      <div class="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-slate-200">
        <div class="flex flex-wrap items-center gap-2">
          <span class="px-2 py-0.5 rounded bg-slate-900 text-white font-mono text-xs font-bold">#${esc(u.id)}</span>
          ${quantumBadge(u.quantum_related)}
          ${u.quantum_related ? catBadge(u.quantum_category) : ""}
        </div>
        <div class="text-xs font-mono text-slate-500">
          <span class="font-semibold text-slate-700">${esc(u.comment_type)}</span> on <span class="font-semibold text-slate-700">${esc(u.code_entity_type)}</span>
        </div>
      </div>

      <!-- Segmented Comment Sentence Card -->
      <div class="p-3.5 rounded-xl bg-white border border-violet-200 shadow-sm">
        <div class="flex items-center justify-between text-[11px] text-slate-400 font-mono mb-1">
          <span>SEGMENTED COMMENT UNIT (SCCU)</span>
          <span>${esc(cLines)}</span>
        </div>
        <p class="text-base font-medium text-slate-900 leading-relaxed">${esc(u.comment_text)}</p>
      </div>

      <!-- Enclosing Python Code Context -->
      <div>
        <div class="flex items-center justify-between text-xs mb-1.5">
          <span class="font-bold text-slate-700 font-mono truncate">${esc(u.file)}</span>
          <span class="text-[11px] font-mono text-slate-400">${esc(sLines)}</span>
        </div>
        <pre class="code-viewer max-h-[290px] overflow-y-auto"><code>${highlightCodeWithComment(u.code_snippet, u.comment_text)}</code></pre>
      </div>
    </div>

    <!-- Bottom Action Bar -->
    <div class="pt-3 mt-3 border-t border-slate-200 flex items-center justify-between">
      <span class="text-[11px] text-slate-400">SDK: <b>${esc(u.sdk)}</b> (${esc(u.version)})</span>
      <div class="flex items-center gap-2">
        <button onclick="sendUnitToLiveInspector(${idx})" class="btn-outline text-xs py-1 px-2.5">
          🔬 Open Snippet in Live Inspector →
        </button>
      </div>
    </div>
  `;
}

function sendUnitToLiveInspector(idx) {
  const u = STATE.units[idx];
  if (!u) return;
  const code = u.code_snippet || `# ${u.comment_text}\n`;
  document.getElementById("inspector-code-input").value = code;
  switchTab("inspector");
  runLiveCodeInspect();
}

function resetAndLoadUnits() {
  STATE.unitsOffset = 0;
  loadCorpusUnitsAndDashboard();
}

function clearExplorerFilters() {
  document.getElementById("filter-quantum").value = "all";
  document.getElementById("filter-category").value = "";
  document.getElementById("filter-ctype").value = "";
  document.getElementById("filter-etype").value = "";
  document.getElementById("filter-search").value = "";
  resetAndLoadUnits();
}

function pageUnits(dir) {
  const next = STATE.unitsOffset + dir * STATE.unitsLimit;
  if (next < 0 || next >= STATE.unitsTotal) return;
  STATE.unitsOffset = next;
  loadCorpusUnitsAndDashboard();
}

// ---------------- Cross-SDK Compare Drawer ----------------

function populateCompareSelects() {
  const repos = Object.keys((STATE.overview && STATE.overview.manifest && STATE.overview.manifest.repos) || {});
  if (!repos.length) return;
  const selA = document.getElementById("cmp-sdk-a");
  const selB = document.getElementById("cmp-sdk-b");
  const opts = repos.map((r) => `<option value="${esc(r)}">${esc(r)}</option>`).join("");
  selA.innerHTML = opts;
  selB.innerHTML = opts;
  selA.value = repos.includes("qiskit") ? "qiskit" : repos[0];
  selB.value = repos.includes("qiskit-nature") ? "qiskit-nature" : repos[Math.min(1, repos.length - 1)];
}

function toggleCompareDrawer() {
  const drawer = document.getElementById("compare-drawer");
  drawer.classList.toggle("hidden");
  if (!drawer.classList.contains("hidden")) {
    setTimeout(renderCompareChart, 50);
  }
}

function renderCompareChart() {
  const repos = (STATE.overview && STATE.overview.manifest && STATE.overview.manifest.repos) || {};
  const sdkA = document.getElementById("cmp-sdk-a").value;
  const sdkB = document.getElementById("cmp-sdk-b").value;
  const stA = repos[sdkA];
  const stB = repos[sdkB];
  if (!stA || !stB) return;

  const sharesOf = (st) => {
    const q = Math.max(1, st.quantum_sccus || 1);
    return CATEGORY_ORDER.map((c) => Number((((st.category_counts[c] || 0) / q) * 100).toFixed(1)));
  };
  const sA = sharesOf(stA);
  const sB = sharesOf(stB);
  const maxVal = Math.max(35, ...sA, ...sB);

  const chart = getChart("chart-compare-radar");
  if (chart) {
    chart.setOption({
      legend: { data: [sdkA, sdkB], bottom: 0 },
      tooltip: { trigger: "item" },
      radar: {
        indicator: CATEGORY_ORDER.map((c) => ({ name: CATEGORY_META[c].short, max: Math.ceil(maxVal / 5) * 5 })),
        radius: "64%",
      },
      series: [
        {
          type: "radar",
          data: [
            {
              value: sA,
              name: sdkA,
              areaStyle: { color: "rgba(109, 40, 217, 0.18)" },
              lineStyle: { color: "#6D28D9", width: 2 },
              itemStyle: { color: "#6D28D9" },
            },
            {
              value: sB,
              name: sdkB,
              areaStyle: { color: "rgba(5, 150, 105, 0.18)" },
              lineStyle: { color: "#059669", width: 2 },
              itemStyle: { color: "#059669" },
            },
          ],
        },
      ],
    });
  }

  const groups = (STATE.overview && STATE.overview.manifest && STATE.overview.manifest.groups) || {};
  const infra = groups.infrastructure || {};
  const app = groups.application || {};

  document.getElementById("compare-summary-cards").innerHTML = `
    <div class="grid grid-cols-2 gap-2.5 text-xs">
      <div class="p-3 rounded-lg bg-white border border-violet-200">
        <div class="font-bold text-violet-900 truncate">${esc(sdkA)}</div>
        <div class="text-xl font-bold text-violet-700 font-mono mt-0.5">${(stA.quantum_proportion * 100).toFixed(1)}%</div>
        <div class="text-[11px] text-slate-500">${stA.quantum_sccus.toLocaleString()} / ${stA.sccus.toLocaleString()} SCCUs</div>
      </div>
      <div class="p-3 rounded-lg bg-white border border-emerald-200">
        <div class="font-bold text-emerald-900 truncate">${esc(sdkB)}</div>
        <div class="text-xl font-bold text-emerald-700 font-mono mt-0.5">${(stB.quantum_proportion * 100).toFixed(1)}%</div>
        <div class="text-[11px] text-slate-500">${stB.quantum_sccus.toLocaleString()} / ${stB.sccus.toLocaleString()} SCCUs</div>
      </div>
    </div>
    <div class="p-3 rounded-lg bg-white border border-slate-200 text-xs space-y-1.5">
      <div class="font-bold text-slate-800">Layer Aggregate Comparison (6 SDKs)</div>
      <div class="flex items-center justify-between">
        <span class="text-slate-600">Infrastructure Layer (3 SDKs):</span>
        <span class="font-mono font-bold text-blue-700">${((infra.quantum_proportion || 0.343) * 100).toFixed(1)}% (${(infra.sccus || 28076).toLocaleString()} SCCUs)</span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-slate-600">Application Layer (3 SDKs):</span>
        <span class="font-mono font-bold text-emerald-700">${((app.quantum_proportion || 0.26) * 100).toFixed(1)}% (${(app.sccus || 11517).toLocaleString()} SCCUs)</span>
      </div>
    </div>
  `;
}

// ======================== VIEW 2: LIVE CODE INSPECTOR & BUILDER ========================

function populateInspectorPresets() {
  // The quick-preset pill buttons are static; we only preload the first preset's code.
  const presets = (STATE.overview && STATE.overview.presets) || [];
  if (presets.length) loadCodePreset(presets[0].id);
}

function loadCodePreset(presetId) {
  const presets = (STATE.overview && STATE.overview.presets) || [];
  const found = presets.find((p) => p.id === presetId) || presets[0];
  if (found) {
    document.getElementById("inspector-code-input").value = found.code;
  }
}

function openBuilderFromExplorer() {
  switchTab("builder");
}

async function runLiveCodeInspect() {
  const code = document.getElementById("inspector-code-input").value;
  const btn = document.getElementById("btn-run-inspect");
  btn.disabled = true;
  btn.innerHTML = `<span>⏳ Analyzing AST &amp; Running Quantum BERT…</span>`;

  // Explicit user action — swap the empty state for results (or an inline error bar).
  const emptyState = document.getElementById("inspector-empty-state");
  if (emptyState) emptyState.classList.add("hidden");

  try {
    const res = await fetch("/api/inspect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }), // server resolves the currently active classifier
    });
    const data = await res.json();
    if (data.error) {
      document.getElementById("inspector-units-container").innerHTML =
        `<div class="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">${esc(data.error)}</div>`;
      return;
    }
    renderInspectorResults(data);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<span>⚡ Extract, Segment &amp; Classify Quantum Comments</span>`;
  }
}

function renderInspectorResults(data) {
  const units = data.units || [];
  document.getElementById("inspector-elapsed-badge").textContent = `${data.elapsed_ms || 0} ms · model: ${data.model_id}`;

  const container = document.getElementById("inspector-units-container");
  if (!units.length) {
    container.innerHTML = `<div class="text-xs text-slate-400 text-center py-8">No comments found in snippet.</div>`;
    return;
  }

  container.innerHTML = units
    .map((u, i) => {
      const lineTag = u.comment_line && u.comment_line.length === 2 ? `L${u.comment_line[0]}–${u.comment_line[1]}` : "";

      return `
        <div class="p-3.5 rounded-xl border ${
          u.quantum_related ? "bg-white border-violet-200 shadow-sm" : "bg-slate-50/70 border-slate-200"
        }">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-1.5">
            <div class="flex items-center gap-1.5">
              <span class="text-xs font-mono font-bold text-slate-400">#${i + 1}</span>
              ${quantumBadge(u.quantum_related, u.quantum_prob)}
              ${u.quantum_related ? catBadge(u.quantum_category) : ""}
            </div>
            <span class="text-[11px] font-mono text-slate-500">${esc(u.comment_type)} · ${esc(u.entity_type)} ${esc(lineTag)}</span>
          </div>
          <p class="text-[14.5px] font-medium text-slate-900 leading-relaxed">${esc(u.text)}</p>
        </div>
      `;
    })
    .join("");
}

// ---------------- Pipeline Corpus Builder ----------------

function togglePipeSourceType() {
  const val = document.querySelector('input[name="pipe-source-type"]:checked').value;
  const lbl = document.getElementById("pipe-target-label");
  const inp = document.getElementById("pipe-target-input");
  if (val === "dir") {
    lbl.textContent = "Local Source Directory";
    inp.value = "examples/tiny_repo";
  } else {
    lbl.textContent = "GitHub Repository URL";
    inp.value = "https://github.com/qiskit-community/qiskit-algorithms";
  }
}

async function startPipelineBuild() {
  const sourceType = document.querySelector('input[name="pipe-source-type"]:checked').value;
  const target = document.getElementById("pipe-target-input").value.trim();
  const name = document.getElementById("pipe-name-input").value.trim();
  const ref = document.getElementById("pipe-ref-input").value.trim();
  const runPredict = document.getElementById("pipe-run-predict").checked;

  const box = document.getElementById("pipe-status-box");
  const actions = document.getElementById("pipe-result-actions");
  box.classList.remove("hidden");
  actions.classList.add("hidden");

  const res = await fetch("/api/pipeline/build", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source_type: sourceType,
      target,
      name,
      ref,
      run_predict: runPredict,
    }),
  });
  const job = await res.json();
  if (job.error) {
    document.getElementById("pipe-stage-text").textContent = `Error: ${job.error}`;
    return;
  }
  pollPipelineJob(job.job_id);
}

async function pollPipelineJob(jobId) {
  const res = await fetch(`/api/pipeline/jobs/${encodeURIComponent(jobId)}`);
  const job = await res.json();
  document.getElementById("pipe-stage-text").textContent = job.stage_name || job.status;
  const pct = Math.round((job.progress || 0) * 100);
  document.getElementById("pipe-pct-text").textContent = `${pct}%`;
  document.getElementById("pipe-progress-bar").style.width = `${pct}%`;

  if (job.status === "running") {
    setTimeout(() => pollPipelineJob(jobId), 800);
  } else if (job.status === "completed") {
    await refreshOverview();
    const actions = document.getElementById("pipe-result-actions");
    actions.classList.remove("hidden");
    document.getElementById("pipe-success-msg").textContent = `Built ${job.asset.name} (${job.asset.sccus} SCCUs)`;
    document.getElementById("btn-open-built-corpus").onclick = () => {
      switchTab("explorer");
      selectCorpus(job.asset.id);
    };
  } else if (job.status === "failed") {
    document.getElementById("pipe-stage-text").textContent = `Failed: ${job.error}`;
  }
}

// ======================== VIEW 3: ANNOTATION STUDIO ========================

async function initAnnotationStudio() {
  const res = await fetch("/api/annotations");
  const data = await res.json();
  STATE.sessions = data.sessions || [];

  // Reflect the seeded demo session size in the Load Demo button / empty-state card.
  const demo = STATE.sessions.find((s) => s.builtin_spotcheck || /Unseen SDKs/i.test(s.name || ""));
  const demoTotal = demo ? ` (${demo.total} units)` : "";
  const btn = document.getElementById("btn-load-demo");
  if (btn) btn.textContent = `📂 Load Demo Benchmark${demoTotal}`;
  const demoTitle = document.getElementById("ann-empty-demo-title");
  if (demoTitle) demoTitle.textContent = `Load Demo Benchmark${demoTotal}`;

  updateAnnotationEmptyState();
  // Data shows only after the user explicitly loads the demo or uploads a file;
  // if a session is already active in this visit, just re-render its workspace.
  if (STATE.activeSession && STATE.sessionItems.length) {
    renderAnnotationMetrics();
    renderAnnotationQueue();
  }
}

// D3: the Studio is a two-card landing (Load Demo / Upload JSONL) until a session is loaded.
function updateAnnotationEmptyState() {
  const empty = document.getElementById("ann-empty-state");
  const workspace = document.getElementById("ann-workspace");
  const loaded = !!(STATE.activeSession && STATE.sessionItems.length);
  if (empty) empty.classList.toggle("hidden", loaded);
  if (workspace) workspace.classList.toggle("hidden", !loaded);
}

// D3: open (or re-seed and open) the pre-built labeling demo session — unlabeled items
// carrying model predictions, so the human can verify/adjudicate from scratch.
async function loadDemoBenchmarkSession() {
  const res = await fetch("/api/annotations"); // the server re-seeds the demo session when missing
  const data = await res.json();
  STATE.sessions = data.sessions || [];
  const demo = STATE.sessions.find((s) => s.builtin_spotcheck || /Unseen SDKs/i.test(s.name || ""));
  if (!demo) {
    alert('Demo benchmark session not found. Make sure the server can access exp/spotcheck_annotation.csv, then retry.');
    return;
  }
  await loadAnnotationSession(demo.id);
}

function uploadJsonlToLabel() {
  document.getElementById("ann-upload-input").click();
}

// D3: parse a user-provided .jsonl / .json file and create a labeling session from it.
async function handleAnnotationUpload(input) {
  const file = input.files && input.files[0];
  input.value = ""; // allow re-picking the same file later
  if (!file) return;
  try {
    const text = await file.text();
    const trimmed = text.trim();
    if (!trimmed) throw new Error("The file is empty.");

    let records;
    if (file.name.toLowerCase().endsWith(".json")) {
      const parsed = JSON.parse(trimmed);
      if (!Array.isArray(parsed)) throw new Error("A .json file must contain an array of record objects.");
      records = parsed;
    } else {
      records = [];
      const lines = trimmed.split("\n");
      for (let i = 0; i < lines.length; i++) {
        if (!lines[i].trim()) continue;
        try {
          records.push(JSON.parse(lines[i]));
        } catch (e) {
          throw new Error(`Line ${i + 1} is not valid JSON.`);
        }
      }
    }
    if (!records.length) throw new Error("No records found in the file.");

    const MAX_RECORDS = 1000;
    const totalCount = records.length;
    let truncatedNote = "";
    if (records.length > MAX_RECORDS) {
      records = records.slice(0, MAX_RECORDS);
      truncatedNote = `\n(Truncated to the first ${MAX_RECORDS} of ${totalCount} records.)`;
    }

    // Records carrying model labels → adjudicate (review predictions); otherwise blind labeling.
    const mode = records.some((r) => r && typeof r === "object" && "quantum_related" in r) ? "adjudicate" : "blind";

    const res = await fetch("/api/annotations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: file.name.replace(/\.(jsonl|json)$/i, ""),
        sample_size: records.length,
        mode,
        records,
      }),
    });
    const data = await res.json();
    if (data.error) {
      alert(`Could not create session: ${data.error}`);
      return;
    }
    if (truncatedNote) alert(`Session created with ${records.length} records.${truncatedNote}`);
    STATE.activeSession = data.session;
    await loadAnnotationSession(data.session.id);
  } catch (err) {
    alert(`Upload failed: ${err.message || err}`);
  }
}

async function loadAnnotationSession(sessionId) {
  if (!sessionId) return;
  const res = await fetch(`/api/annotations/${encodeURIComponent(sessionId)}`);
  const data = await res.json();
  if (data.error) return;

  STATE.activeSession = data.session;
  STATE.sessionItems = data.items || [];
  STATE.sessionMetrics = data.metrics || {};
  STATE.activeAnnFilteredPos = 0;

  document.getElementById("ann-export-link").href = `/api/annotations/${encodeURIComponent(sessionId)}/export?task=full`;
  updateAnnotationEmptyState();
  renderAnnotationMetrics();
  renderAnnotationQueue();
}

function renderAnnotationMetrics() {
  const m = STATE.sessionMetrics || {};
  const done = m.labeled_count || 0;
  const total = m.total || 0;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  document.getElementById("ann-kpi-progress").textContent = `${done} / ${total} (${pct}%)`;
  document.getElementById("ann-progress-bar").style.width = `${pct}%`;
}

function renderAnnotationQueue() {
  const filter = document.getElementById("ann-item-filter").value;
  const indices = [];

  STATE.sessionItems.forEach((it, idx) => {
    const labeled = it.human_quantum_related !== null && it.human_quantum_related !== undefined;
    if (filter === "unlabeled" && labeled) return;
    if (filter === "labeled" && !labeled) return;
    if (filter === "quantum" && it.human_quantum_related !== true) return;
    indices.push(idx);
  });

  STATE.filteredSessionIndices = indices;
  if (STATE.activeAnnFilteredPos >= indices.length) {
    STATE.activeAnnFilteredPos = Math.max(0, indices.length - 1);
  }

  document.getElementById("ann-filter-count").textContent = `${indices.length} items`;
  const listEl = document.getElementById("ann-queue-list");

  if (!indices.length) {
    listEl.innerHTML = `<div class="p-6 text-center text-xs text-slate-400">No items match this filter.</div>`;
    return;
  }

  const activeRealIdx = indices[STATE.activeAnnFilteredPos];
  listEl.innerHTML = indices
    .map((realIdx, pos) => {
      const it = STATE.sessionItems[realIdx];
      const hq = it.human_quantum_related;
      const isLabeled = hq !== null && hq !== undefined;

      let statusPill = `<span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">Unlabeled</span>`;
      if (isLabeled) {
        statusPill = hq
          ? `<span class="text-[10px] px-1.5 py-0.5 rounded bg-violet-100 text-violet-800 font-semibold">⚛ Quantum</span>`
          : `<span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-200 text-slate-700 font-semibold">Non-Q</span>`;
      }

      return `
        <div onclick="selectAnnotationPos(${pos})" class="unit-row ${realIdx === activeRealIdx ? "selected" : ""}">
          <div class="flex items-center justify-between text-xs mb-1">
            <span class="font-mono font-bold text-slate-600">#${realIdx + 1} · ${esc(it.sdk)}</span>
            <div class="flex items-center gap-1">
              ${statusPill}
            </div>
          </div>
          <div class="text-[13px] text-slate-800 line-clamp-2 leading-relaxed">${esc(it.comment_text)}</div>
        </div>
      `;
    })
    .join("");

  renderActiveAnnotationItem();
}

function selectAnnotationPos(pos) {
  STATE.activeAnnFilteredPos = pos;
  renderAnnotationQueue();
}

function renderActiveAnnotationItem() {
  const realIdx = STATE.filteredSessionIndices[STATE.activeAnnFilteredPos];
  const it = STATE.sessionItems[realIdx];
  if (!it) return;

  document.getElementById("ann-curr-index").textContent = `#${realIdx + 1} of ${STATE.sessionItems.length}`;
  document.getElementById("ann-curr-sdk").textContent = it.sdk || "corpus";
  document.getElementById("ann-curr-file").textContent = it.file || "";
  document.getElementById("ann-curr-text").textContent = it.comment_text || "";
  document.getElementById("ann-item-note").value = it.notes || "";

  // Code snippet
  const codeEl = document.getElementById("ann-curr-code");
  codeEl.innerHTML = `<code>${highlightCodeWithComment(it.code_snippet, it.comment_text)}</code>`;

  // Highlight active buttons
  const hq = it.human_quantum_related;
  const btnQ = document.getElementById("btn-label-quantum");
  const btnN = document.getElementById("btn-label-nonquantum");
  btnQ.className = `p-3 rounded-xl border-2 text-left transition flex flex-col justify-between ${
    hq === true ? "bg-violet-100 border-violet-600 shadow-sm" : "bg-white border-slate-200 hover:border-violet-400"
  }`;
  btnN.className = `p-3 rounded-xl border-2 text-left transition flex flex-col justify-between ${
    hq === false ? "bg-slate-200 border-slate-700 shadow-sm" : "bg-white border-slate-200 hover:border-slate-400"
  }`;

  // Render 6-Category buttons
  const activeCat = it.human_quantum_category || (hq === true ? it.model_quantum_category : null);
  const catContainer = document.getElementById("ann-category-buttons");
  catContainer.innerHTML = CATEGORY_ORDER.map((cat) => {
    const m = CATEGORY_META[cat];
    const isSel = hq === true && activeCat === cat;
    return `
      <button onclick="submitHumanLabel(true, '${esc(cat)}')"
        class="w-full p-2.5 rounded-lg border text-left transition flex items-center justify-between ${
          isSel ? "bg-violet-50 border-violet-600 ring-1 ring-violet-500" : "bg-white border-slate-200 hover:bg-slate-50"
        }">
        <div class="flex items-center gap-2">
          <span class="w-3 h-3 rounded-sm" style="background:${m.color};"></span>
          <span class="text-xs font-semibold text-slate-800">${esc(cat)}</span>
        </div>
        <span class="kbd-key">${m.key}</span>
      </button>
    `;
  }).join("");
}

async function submitHumanLabel(isQuantum, category) {
  if (!STATE.activeSession) return;
  const realIdx = STATE.filteredSessionIndices[STATE.activeAnnFilteredPos];
  const it = STATE.sessionItems[realIdx];
  if (!it) return;

  const chosenCat = isQuantum
    ? category || it.human_quantum_category || it.model_quantum_category || "Quantum circuit model"
    : null;
  const notes = document.getElementById("ann-item-note").value;

  const res = await fetch(`/api/annotations/${encodeURIComponent(STATE.activeSession.id)}/label`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      index: realIdx,
      item_id: it.item_id,
      human_quantum_related: isQuantum,
      human_quantum_category: chosenCat,
      notes,
    }),
  });
  const data = await res.json();
  if (data.error) return;

  STATE.sessionItems[realIdx] = data.item;
  STATE.sessionMetrics = data.metrics;
  renderAnnotationMetrics();

  // Stay on the current item so both step results remain visible — the user
  // moves on explicitly via Prev / Next (← / →).
  renderAnnotationQueue();
}

async function saveItemNote(noteText) {
  if (!STATE.activeSession) return;
  const realIdx = STATE.filteredSessionIndices[STATE.activeAnnFilteredPos];
  const it = STATE.sessionItems[realIdx];
  if (!it) return;
  await fetch(`/api/annotations/${encodeURIComponent(STATE.activeSession.id)}/label`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      index: realIdx,
      item_id: it.item_id,
      human_quantum_related: it.human_quantum_related,
      human_quantum_category: it.human_quantum_category,
      notes: noteText,
    }),
  });
}

function stepAnnotationItem(delta) {
  const next = STATE.activeAnnFilteredPos + delta;
  if (next < 0 || next >= STATE.filteredSessionIndices.length) return;
  STATE.activeAnnFilteredPos = next;
  renderAnnotationQueue();
}

function renderGuidelinesReference() {
  const tax = (STATE.overview && STATE.overview.taxonomy) || { binary_criteria: [], categories: [] };
  const el = document.getElementById("ann-guideline-content");
  if (!el) return;

  el.innerHTML = `
    <div class="font-semibold text-slate-800">Task 1 · Three Criteria for Quantum-Specific (All 3 required):</div>
    <ul class="list-disc pl-4 space-y-1">
      ${(tax.binary_criteria || []).map((c) => `<li><b>${esc(c.name)}:</b> ${esc(c.desc)}</li>`).join("")}
    </ul>
    <div class="font-semibold text-slate-800 pt-1">Task 2 · Six Quantum Knowledge Categories:</div>
    <div class="space-y-1">
      ${(tax.categories || [])
        .map(
          (c) => `<div><b style="color:${c.color}">[${c.key}] ${esc(c.short)}:</b> ${esc(c.desc)}</div>`
        )
        .join("")}
    </div>
  `;
}

function setupKeyboardShortcuts() {
  window.addEventListener("keydown", (e) => {
    if (STATE.activeTab !== "annotate") return;
    const tag = (e.target && e.target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

    const k = e.key.toLowerCase();
    if (k === "q") {
      e.preventDefault();
      submitHumanLabel(true, null);
    } else if (k === "n") {
      e.preventDefault();
      submitHumanLabel(false, null);
    } else if (["1", "2", "3", "4", "5", "6"].includes(k)) {
      e.preventDefault();
      const cat = CATEGORY_ORDER[parseInt(k, 10) - 1];
      if (cat) submitHumanLabel(true, cat);
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      stepAnnotationItem(1);
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      stepAnnotationItem(-1);
    }
  });
}

// ======================== VIEW 4: MODEL TRAINER & REGISTRY ========================

async function loadModelsStudio() {
  await refreshOverview();
  const res = await fetch("/api/models");
  const data = await res.json();
  STATE.modelsInfo = data;

  updateTrainSourceOptions();
}

function updateTrainSourceOptions() {
  if (!STATE.modelsInfo) return;
  const task = document.getElementById("train-task").value;
  document.getElementById("train-model-name").value =
    task === "quantum_related" ? "custom-quantum-related-v1" : "custom-quantum-category-v1";
  toggleTrainSourceInputs();
}

// Keep the collapsed ⚙️ Training Parameters summary in sync with the folded controls (spec §2.4.2)
function updateAdvancedOptionsSummary() {
  const summaryEl = document.getElementById("train-advanced-summary");
  if (!summaryEl) return;
  const epochs = document.getElementById("train-epochs").value || "2";
  const batch = document.getElementById("train-batch").value || "16";
  summaryEl.textContent = `⚙️ Training Parameters (${epochs} Epochs · Batch ${batch})`;
}

function setupAdvancedOptionsSummary() {
  ["train-epochs", "train-batch"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("change", updateAdvancedOptionsSummary);
  });
  updateAdvancedOptionsSummary();
}

function toggleTrainSourceInputs() {
  if (!STATE.modelsInfo) return;
  const srcType = document.getElementById("train-source-type").value;
  const task = document.getElementById("train-task").value;
  const up = document.getElementById("train-upload-input");

  // Reflect the built-in demo dataset size in the gold option label.
  const gold = (STATE.modelsInfo.training_sources && STATE.modelsInfo.training_sources.gold && STATE.modelsInfo.training_sources.gold[task]) || {};
  const goldOpt = document.querySelector('#train-source-type option[value="gold"]');
  if (goldOpt) goldOpt.textContent = `Demo Dataset (${(gold.rows || 0).toLocaleString()} units)`;

  if (srcType === "upload") {
    up.classList.remove("hidden");
  } else {
    up.classList.add("hidden");
  }
}

async function startModelTraining() {
  const task = document.getElementById("train-task").value;
  const sourceType = document.getElementById("train-source-type").value;
  const modelName = document.getElementById("train-model-name").value.trim();
  const epochs = parseInt(document.getElementById("train-epochs").value || "2", 10);
  const batchSize = parseInt(document.getElementById("train-batch").value || "16", 10);

  let uploadedRecords = null;
  if (sourceType === "upload") {
    const fileInp = document.getElementById("train-upload-input");
    if (!fileInp.files || !fileInp.files[0]) {
      alert("Please select a JSONL file to upload.");
      return;
    }
    const text = await fileInp.files[0].text();
    uploadedRecords = text
      .split("\n")
      .filter((l) => l.trim())
      .map((l) => JSON.parse(l));
  }

  const monitor = document.getElementById("train-monitor-box");
  monitor.classList.remove("hidden");
  document.getElementById("train-test-results").classList.add("hidden");

  const res = await fetch("/api/models/train", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      task,
      source_type: sourceType,
      records: uploadedRecords,
      model_name: modelName,
      epochs,
      batch_size: batchSize,
    }),
  });
  const job = await res.json();
  if (job.error) {
    document.getElementById("train-stage-label").textContent = `Error: ${job.error}`;
    return;
  }
  pollTrainJob(job.job_id);
}

async function pollTrainJob(jobId) {
  const res = await fetch(`/api/models/train/${encodeURIComponent(jobId)}`);
  const job = await res.json();

  document.getElementById("train-stage-label").textContent = job.stage || job.status;
  const pct = Math.round((job.progress || 0) * 100);
  document.getElementById("train-step-label").textContent = `Step ${job.step || 0}/${job.total_steps || 1} (${pct}%)`;
  document.getElementById("train-progress-bar").style.width = `${pct}%`;

  if (job.history && job.history.length > 0) {
    const chartBox = document.getElementById("chart-train-history");
    chartBox.classList.remove("hidden");
    const chart = getChart("chart-train-history");
    if (chart) {
      const steps = job.history.map((h) => `Step ${h.step}`);
      const losses = job.history.map((h) => h.loss ?? null);
      const f1s = job.history.map((h) => (h.eval_f1 !== undefined ? Number((h.eval_f1 * 100).toFixed(1)) : null));
      chart.setOption({
        tooltip: { trigger: "axis" },
        legend: { data: ["Train Loss", "Val F1 (%)"], bottom: 0 },
        grid: { left: 45, right: 45, top: 15, bottom: 35 },
        xAxis: { type: "category", data: steps },
        yAxis: [
          { type: "value", name: "Loss" },
          { type: "value", name: "F1 %", min: 0, max: 100 },
        ],
        series: [
          { name: "Train Loss", type: "line", data: losses, smooth: true, connectNulls: true, itemStyle: { color: "#6D28D9" } },
          { name: "Val F1 (%)", type: "line", yAxisIndex: 1, data: f1s, smooth: true, connectNulls: true, itemStyle: { color: "#059669" } },
        ],
      });
    }
  }

  if (job.status === "running") {
    setTimeout(() => pollTrainJob(jobId), 1000);
  } else if (job.status === "completed") {
    const tr = job.test_results || {};
    const resEl = document.getElementById("train-test-results");
    resEl.classList.remove("hidden");
    resEl.innerHTML = `
      <div class="space-y-1.5 text-xs">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="font-bold text-emerald-800">✅ Held-Out Test Split Results (${tr.test_rows || 0} units):</span>
          <div class="flex items-center gap-3 font-mono">
            <span>F1: <b>${((tr.f1 || 0) * 100).toFixed(1)}%</b></span>
            <span>Acc: <b>${((tr.accuracy || 0) * 100).toFixed(1)}%</b></span>
            <span>Prec: <b>${((tr.precision || 0) * 100).toFixed(1)}%</b></span>
            <span>Rec: <b>${((tr.recall || 0) * 100).toFixed(1)}%</b></span>
          </div>
        </div>
        <div class="font-mono text-[11px] text-slate-500 break-all">
          💾 Model saved to: <b>${esc(job.saved_to || "")}</b>
        </div>
      </div>
    `;
  } else if (job.status === "failed") {
    document.getElementById("train-stage-label").textContent = `Training Failed: ${job.error}`;
  }
}

document.addEventListener("DOMContentLoaded", initApp);
