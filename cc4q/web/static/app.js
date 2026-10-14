/* CC4Q Workbench — Interactive Client Application */

const STATE = {
  activeTab: "explorer",
  overview: null,
  activeCorpusId: "qiskit",
  activeCorpusStats: null,
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

// ======================== INITIALIZATION & NAVIGATION ========================

async function initApp() {
  await refreshOverview();
  await selectCorpus(STATE.activeCorpusId);
  populateInspectorPresets();
  renderGuidelinesReference();
  setupKeyboardShortcuts();
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
  populateModelSelects();
}

function switchTab(tabId) {
  STATE.activeTab = tabId;
  document.querySelectorAll("#main-nav .nav-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tabId);
  });
  ["explorer", "inspector", "annotate", "models"].forEach((id) => {
    const sec = document.getElementById(`view-${id}`);
    if (sec) sec.classList.toggle("hidden", id !== tabId);
  });

  if (tabId === "explorer") {
    setTimeout(() => {
      Object.values(STATE.charts).forEach((c) => c && c.resize());
    }, 60);
  } else if (tabId === "inspector") {
    const unitsEl = document.getElementById("inspector-units-container");
    if (!unitsEl.innerHTML.trim()) {
      runLiveCodeInspect();
    }
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

  const infra = corpora.filter((c) => c.builtin && c.layer === "infrastructure");
  const appl = corpora.filter((c) => c.builtin && c.layer === "application");
  const custom = corpora.filter((c) => !c.builtin);

  const renderItem = (c) => {
    const key = c.sdk || c.id;
    const isActive = STATE.activeCorpusId === key || STATE.activeCorpusId === c.id;
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
  STATE.unitsOffset = 0;
  renderExplorerSidebar();
  await loadCorpusUnitsAndDashboard();
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

  document.getElementById("exp-download-link").href = `/api/corpora/${encodeURIComponent(asset.id)}/download`;

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

function renderRadarAndCategoryBars(stats) {
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
    const isSelected = activeCat === cat;
    return `
      <div onclick="filterByCategory('${esc(cat)}')"
        class="p-1.5 rounded-lg cursor-pointer transition border ${
          isSelected ? "bg-violet-50 border-violet-300" : "border-transparent hover:bg-slate-50"
        }">
        <div class="flex items-center justify-between text-xs mb-1">
          <span class="font-semibold text-slate-700 flex items-center gap-1.5">
            <span style="width:8px;height:8px;border-radius:2px;background:${meta.color};"></span>
            ${esc(meta.short)}
          </span>
          <span class="font-mono text-slate-600">${pct}% <span class="text-slate-400">(${cnt})</span></span>
        </div>
        <div class="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div style="width:${Math.min(100, pct)}%;background:${meta.color};" class="h-full rounded-full"></div>
        </div>
      </div>
    `;
  }).join("");
}

function filterByCategory(cat) {
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
  const stats = STATE.activeCorpusStats;
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

  chart.setOption({
    tooltip: {
      formatter: (p) => {
        const [, , val, ct, ent, raw] = p.data;
        return `<b>${ct} × ${ent}</b><br/>Count: ${raw.toLocaleString()} SCCUs${
          mode === "quantum_share" ? ` (${val}% of quantum)` : ""
        }<br/><span style="color:#A78BFA">Click to filter inspector</span>`;
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
          <div class="text-xs text-slate-800 font-medium line-clamp-2 leading-relaxed">${esc(u.comment_text)}</div>
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
        <p class="text-sm font-semibold text-slate-900 leading-relaxed">${esc(u.comment_text)}</p>
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
  switchInspectorSubtab("snippet");
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
  const presets = (STATE.overview && STATE.overview.presets) || [];
  const sel = document.getElementById("inspector-preset-select");
  if (!presets.length) return;
  sel.innerHTML = presets.map((p) => `<option value="${esc(p.id)}">${esc(p.title)}</option>`).join("");
  loadCodePreset(presets[0].id);
}

function loadCodePreset(presetId) {
  const presets = (STATE.overview && STATE.overview.presets) || [];
  const found = presets.find((p) => p.id === presetId) || presets[0];
  if (found) {
    document.getElementById("inspector-code-input").value = found.code;
  }
}

function populateModelSelects() {
  const models = (STATE.overview && STATE.overview.models) || {};
  const userModels = models.user_models || [];
  const opts = [
    `<option value="default">Active Default (${esc(models.active_name || "Released Checkpoints")})</option>`,
    `<option value="released">Released CC4Q Checkpoints (TOSEM)</option>`,
    ...userModels.map((m) => `<option value="${esc(m.id)}">Custom: ${esc(m.name)} (${esc((m.axes || []).join(", "))})</option>`),
  ].join("");

  const inspSel = document.getElementById("inspector-model-select");
  if (inspSel) inspSel.innerHTML = opts;

  const evalA = document.getElementById("eval-model-a");
  const evalB = document.getElementById("eval-model-b");
  if (evalA && evalB) {
    const evalOpts = [
      `<option value="released">Released CC4Q Checkpoints</option>`,
      ...userModels.map((m) => `<option value="${esc(m.id)}">${esc(m.name)}</option>`),
    ].join("");
    evalA.innerHTML = evalOpts;
    evalB.innerHTML = evalOpts;
    if (userModels.length > 0) {
      evalB.value = userModels[0].id;
    }
  }

  const corpora = (STATE.overview && STATE.overview.corpora) || [];
  const cOpts = corpora.map((c) => `<option value="${esc(c.id)}">${esc(c.name)}</option>`).join("");
  const annCorpus = document.getElementById("new-ann-corpus");
  if (annCorpus) annCorpus.innerHTML = cOpts;
  const evalCorpus = document.getElementById("eval-corpus");
  if (evalCorpus) evalCorpus.innerHTML = cOpts;
}

function switchInspectorSubtab(sub) {
  const isSnippet = sub === "snippet";
  document.getElementById("inspector-sub-snippet").classList.toggle("hidden", !isSnippet);
  document.getElementById("inspector-sub-repo").classList.toggle("hidden", isSnippet);
  document.getElementById("subtab-btn-snippet").className = isSnippet ? "btn-quantum text-xs" : "btn-outline text-xs";
  document.getElementById("subtab-btn-repo").className = !isSnippet ? "btn-quantum text-xs" : "btn-outline text-xs";
}

function openBuilderFromExplorer() {
  switchTab("inspector");
  switchInspectorSubtab("repo");
}

async function runLiveCodeInspect() {
  const code = document.getElementById("inspector-code-input").value;
  const modelId = document.getElementById("inspector-model-select").value;
  const btn = document.getElementById("btn-run-inspect");
  btn.disabled = true;
  btn.innerHTML = `<span>⏳ Analyzing AST &amp; Running Quantum BERT…</span>`;

  try {
    const res = await fetch("/api/inspect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, model_id: modelId }),
    });
    const data = await res.json();
    if (data.error) {
      document.getElementById("inspector-summary-panel").innerHTML = `<div class="text-xs text-rose-600">${esc(data.error)}</div>`;
      return;
    }
    renderInspectorResults(data);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<span>⚡ Extract, Segment &amp; Classify Quantum Comments</span>`;
  }
}

function renderInspectorResults(data) {
  const audit = data.audit || {};
  const units = data.units || [];
  document.getElementById("inspector-elapsed-badge").textContent = `${data.elapsed_ms || 0} ms · model: ${data.model_id}`;

  const findingsHtml = (audit.findings || [])
    .map((f) => {
      const isPass = f.severity === "pass";
      return `
        <div class="p-2.5 rounded-lg border text-xs flex items-start gap-2 ${
          isPass ? "bg-emerald-50/60 border-emerald-200 text-emerald-950" : "bg-amber-50/70 border-amber-200 text-amber-950"
        }">
          <span>${isPass ? "✅" : "⚠️"}</span>
          <div>
            <div class="font-bold">${esc(f.title)}</div>
            <div class="text-slate-600 mt-0.5">${esc(f.detail)}</div>
          </div>
        </div>
      `;
    })
    .join("");

  document.getElementById("inspector-summary-panel").innerHTML = `
    <div class="space-y-3">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-bold text-slate-900">Quantum Documentation Health Check (TOSEM Guidelines)</h3>
        <span class="badge badge-quantum">${audit.quantum_sccus || 0} / ${audit.total_sccus || 0} Quantum SCCUs (${((audit.quantum_ratio || 0) * 100).toFixed(0)}%)</span>
      </div>
      <div class="space-y-2">${findingsHtml}</div>
    </div>
  `;

  const container = document.getElementById("inspector-units-container");
  if (!units.length) {
    container.innerHTML = `<div class="text-xs text-slate-400 text-center py-8">No comments found in snippet.</div>`;
    return;
  }

  container.innerHTML = units
    .map((u, i) => {
      const qProb = u.quantum_prob !== undefined ? (u.quantum_prob * 100).toFixed(1) : u.quantum_related ? "95.0" : "5.0";
      const catProbs = u.category_probs || {};
      const topCats = Object.entries(catProbs)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3);

      const probBars = u.quantum_related && topCats.length
        ? `<div class="mt-2 pt-2 border-t border-slate-100 grid grid-cols-3 gap-2">
            ${topCats
              .map(([cname, p]) => {
                const m = CATEGORY_META[cname] || CATEGORY_META["Others"];
                return `<div class="text-[11px]">
                  <div class="flex justify-between text-slate-600"><span>${esc(m.short)}</span><span class="font-mono">${(p * 100).toFixed(0)}%</span></div>
                  <div class="w-full h-1 bg-slate-100 rounded-full mt-0.5"><div style="width:${(p * 100).toFixed(0)}%;background:${m.color};" class="h-full rounded-full"></div></div>
                </div>`;
              })
              .join("")}
          </div>`
        : "";

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
          <p class="text-xs font-semibold text-slate-900 leading-relaxed">${esc(u.text)}</p>
          ${probBars}
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
  const sel = document.getElementById("ann-session-select");
  if (!STATE.sessions.length) {
    sel.innerHTML = `<option value="">No sessions yet</option>`;
    return;
  }
  sel.innerHTML = STATE.sessions
    .map((s) => `<option value="${esc(s.id)}">${esc(s.name)} (${s.labeled_count || 0}/${s.total || 0})</option>`)
    .join("");

  const targetId = STATE.activeSession ? STATE.activeSession.id : STATE.sessions[0].id;
  sel.value = targetId;
  await loadAnnotationSession(targetId);
}

function toggleNewAnnotationModal() {
  document.getElementById("new-ann-drawer").classList.toggle("hidden");
}

function startAnnotationFromCurrentCorpus() {
  switchTab("annotate");
  setTimeout(() => {
    const drawer = document.getElementById("new-ann-drawer");
    drawer.classList.remove("hidden");
    const sel = document.getElementById("new-ann-corpus");
    if (sel) sel.value = STATE.activeCorpusId;
    document.getElementById("new-ann-name").value = `${STATE.activeCorpusId}-review`;
  }, 100);
}

async function createNewAnnotationSession() {
  const name = document.getElementById("new-ann-name").value.trim();
  const corpusId = document.getElementById("new-ann-corpus").value;
  const sampleSize = parseInt(document.getElementById("new-ann-size").value || "50", 10);
  const stratRaw = document.getElementById("new-ann-stratify").value;
  const stratifyBy = stratRaw ? stratRaw.split(",") : [];
  const mode = document.getElementById("new-ann-mode").value;

  const res = await fetch("/api/annotations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name,
      corpus_id: corpusId,
      sample_size: sampleSize,
      stratify_by: stratifyBy,
      mode,
    }),
  });
  const data = await res.json();
  if (data.error) {
    alert(data.error);
    return;
  }
  document.getElementById("new-ann-drawer").classList.add("hidden");
  STATE.activeSession = data.session;
  await initAnnotationStudio();
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

  document.getElementById("ann-kpi-agreement").textContent =
    m.agreement !== null && m.agreement !== undefined ? `${(m.agreement * 100).toFixed(1)}%` : "—";
  const ci = m.wilson95 || [null, null];
  document.getElementById("ann-kpi-ci").textContent =
    ci[0] !== null ? `95% CI: ${(ci[0] * 100).toFixed(1)}–${(ci[1] * 100).toFixed(1)}%` : "Wilson 95% CI: —";

  document.getElementById("ann-kpi-kappa").textContent =
    m.kappa !== null && m.kappa !== undefined ? m.kappa.toFixed(3) : "—";

  const p = m.precision !== null && m.precision !== undefined ? `${(m.precision * 100).toFixed(1)}%` : "—";
  const r = m.recall !== null && m.recall !== undefined ? `${(m.recall * 100).toFixed(1)}%` : "—";
  document.getElementById("ann-kpi-pr").textContent = `${p} / ${r}`;
  document.getElementById("ann-kpi-f1").textContent =
    m.f1 !== null && m.f1 !== undefined ? `F1: ${(m.f1 * 100).toFixed(1)}%` : "F1: —";

  const c = m.confusion || { tp: 0, fp: 0, fn: 0, tn: 0 };
  document.getElementById("ann-kpi-confusion").textContent = `TP:${c.tp} FP:${c.fp} FN:${c.fn} TN:${c.tn}`;

  document.getElementById("ann-kpi-cat-agree").textContent =
    m.category_agreement !== null && m.category_agreement !== undefined
      ? `${(m.category_agreement * 100).toFixed(1)}%`
      : "—";
  document.getElementById("ann-kpi-cat-n").textContent = `${m.category_compared || 0} quantum units`;
}

function renderAnnotationQueue() {
  const filter = document.getElementById("ann-item-filter").value;
  const indices = [];

  STATE.sessionItems.forEach((it, idx) => {
    const labeled = it.human_quantum_related !== null && it.human_quantum_related !== undefined;
    if (filter === "unlabeled" && labeled) return;
    if (filter === "labeled" && !labeled) return;
    if (filter === "disagree") {
      if (!labeled || Boolean(it.human_quantum_related) === Boolean(it.model_quantum_related)) return;
    }
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
      const disagree = isLabeled && Boolean(hq) !== Boolean(it.model_quantum_related);

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
              ${disagree ? `<span title="Human disagrees with Model" class="text-[10px] px-1.5 py-0.5 rounded bg-rose-100 text-rose-700 font-bold">≠ Model</span>` : ""}
              ${statusPill}
            </div>
          </div>
          <div class="text-xs text-slate-800 truncate">${esc(it.comment_text)}</div>
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
  document.getElementById("ann-curr-meta").textContent = `${it.comment_type || "—"} · ${it.code_entity_type || "—"}`;
  document.getElementById("ann-curr-file").textContent = it.file || "";
  document.getElementById("ann-curr-text").textContent = it.comment_text || "";
  document.getElementById("ann-item-note").value = it.notes || "";

  // Model Pre-label Banner (shown in adjudicate mode)
  const isBlind = STATE.activeSession && STATE.activeSession.mode === "blind";
  const banner = document.getElementById("ann-model-banner");
  if (isBlind) {
    banner.classList.add("hidden");
  } else {
    banner.classList.remove("hidden");
    document.getElementById("ann-model-pred-badges").innerHTML = `
      ${quantumBadge(it.model_quantum_related)}
      ${it.model_quantum_related ? catBadge(it.model_quantum_category) : ""}
    `;
  }

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

  if (document.getElementById("ann-auto-advance").checked) {
    if (STATE.activeAnnFilteredPos + 1 < STATE.filteredSessionIndices.length) {
      STATE.activeAnnFilteredPos += 1;
    }
  }
  renderAnnotationQueue();
}

function acceptModelPrediction() {
  const realIdx = STATE.filteredSessionIndices[STATE.activeAnnFilteredPos];
  const it = STATE.sessionItems[realIdx];
  if (!it) return;
  submitHumanLabel(Boolean(it.model_quantum_related), it.model_quantum_category);
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
    } else if (k === " ") {
      e.preventDefault();
      acceptModelPrediction();
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

function openTrainWithCurrentSession() {
  const sid = STATE.activeSession ? STATE.activeSession.id : null;
  switchTab("models");
  setTimeout(() => {
    document.getElementById("train-source-type").value = "session";
    toggleTrainSourceInputs();
    if (sid) {
      document.getElementById("train-session-select").value = sid;
    }
  }, 120);
}

// ======================== VIEW 4: MODEL TRAINER & REGISTRY ========================

async function loadModelsStudio() {
  await refreshOverview();
  const res = await fetch("/api/models");
  const data = await res.json();
  STATE.modelsInfo = data;

  renderModelRegistryCards();
  updateTrainSourceOptions();
}

function renderModelRegistryCards() {
  const models = (STATE.overview && STATE.overview.models) || {};
  const released = models.released || [];
  const userModels = models.user_models || [];
  const activeId = models.active_id || "released";

  document.getElementById("released-models-grid").innerHTML = released
    .map(
      (m) => `
      <div class="p-4 rounded-xl bg-slate-50 border ${
        activeId === "released" ? "border-violet-300 ring-1 ring-violet-200" : "border-slate-200"
      } flex flex-col justify-between space-y-2">
        <div>
          <div class="flex items-center justify-between">
            <span class="font-bold text-sm text-slate-900">${esc(m.name)}</span>
            <span class="badge ${m.ready ? "badge-quantum" : "badge-nonquantum"}">${
        m.ready ? "Ready on Disk" : "Missing Checkpoint"
      }</span>
          </div>
          <p class="text-xs text-slate-500 mt-1 leading-relaxed">${esc(m.desc)}</p>
        </div>
        <div class="pt-2 border-t border-slate-200/80 flex items-center justify-between text-xs font-mono text-slate-600">
          <span>Base: ${esc(m.base)}</span>
          <span>Held-out F1: <b>${(m.f1 * 100).toFixed(1)}%</b> · κ=${m.kappa}</span>
        </div>
      </div>
    `
    )
    .join("");

  const userGrid = document.getElementById("user-models-grid");
  if (!userModels.length) {
    userGrid.innerHTML = `
      <div class="col-span-3 p-6 rounded-xl bg-slate-50 border border-dashed border-slate-300 text-center text-xs text-slate-500">
        No custom fine-tuned models registered yet. Use the <b>Train Your Own Quantum Classifier</b> studio below to fine-tune a model on your labeled data!
      </div>
    `;
    return;
  }

  userGrid.innerHTML = userModels
    .map((m) => {
      const isDef = m.is_default;
      return `
        <div class="p-4 rounded-xl bg-white border ${
          isDef ? "border-violet-500 ring-1 ring-violet-400" : "border-slate-200"
        } flex flex-col justify-between space-y-3">
          <div>
            <div class="flex items-center justify-between">
              <span class="font-bold text-sm text-slate-900">${esc(m.name)}</span>
              <span class="badge ${isDef ? "badge-quantum" : "badge-nonquantum"}">${
        isDef ? "★ Active Default" : "Custom Model"
      }</span>
            </div>
            <div class="text-xs font-mono text-slate-500 mt-1">Task: ${esc((m.axes || []).join(", "))}</div>
            <div class="text-[11px] text-slate-400 mt-0.5">Created: ${esc(m.created || "")}</div>
          </div>
          <div class="flex items-center gap-2 pt-2 border-t border-slate-100">
            ${
              !isDef
                ? `<button onclick="setActiveModel('${esc(m.id)}')" class="btn-quantum text-xs py-1 px-2.5">★ Set Active</button>`
                : ""
            }
            <a href="/api/models/${encodeURIComponent(m.id)}/download" class="btn-outline text-xs py-1 px-2.5 no-underline">⬇ Zip</a>
            <button onclick="deleteUserModel('${esc(m.id)}')" class="btn-outline text-xs py-1 px-2.5 text-rose-600">Delete</button>
          </div>
        </div>
      `;
    })
    .join("");
}

async function setActiveModel(modelId) {
  await fetch("/api/models/default", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model_id: modelId }),
  });
  await loadModelsStudio();
}

async function deleteUserModel(modelId) {
  await fetch(`/api/models/${encodeURIComponent(modelId)}`, { method: "DELETE" });
  await loadModelsStudio();
}

function updateTrainSourceOptions() {
  if (!STATE.modelsInfo) return;
  const task = document.getElementById("train-task").value;
  document.getElementById("train-model-name").value =
    task === "quantum_related" ? "custom-quantum-related-v1" : "custom-quantum-category-v1";
  toggleTrainSourceInputs();
}

function toggleTrainSourceInputs() {
  if (!STATE.modelsInfo) return;
  const srcType = document.getElementById("train-source-type").value;
  const task = document.getElementById("train-task").value;
  const lbl = document.getElementById("train-source-detail-label");
  const sel = document.getElementById("train-session-select");
  const up = document.getElementById("train-upload-input");

  if (srcType === "session") {
    lbl.textContent = "Select Annotation Studio Session";
    sel.classList.remove("hidden");
    up.classList.add("hidden");
    const sessions = (STATE.modelsInfo.training_sources && STATE.modelsInfo.training_sources.sessions) || [];
    sel.innerHTML = sessions.length
      ? sessions.map((s) => `<option value="${esc(s.id)}">${esc(s.name)} (${s.labeled_count} labeled)</option>`).join("")
      : `<option value="">No labeled sessions available</option>`;
  } else if (srcType === "gold") {
    lbl.textContent = "Built-in Gold Benchmark Dataset";
    sel.classList.remove("hidden");
    up.classList.add("hidden");
    const gold = (STATE.modelsInfo.training_sources && STATE.modelsInfo.training_sources.gold && STATE.modelsInfo.training_sources.gold[task]) || {};
    sel.innerHTML = `<option value="gold">${esc(gold.name || task)} (${(gold.rows || 0).toLocaleString()} labeled units)</option>`;
  } else {
    lbl.textContent = "Upload Labeled JSONL File";
    sel.classList.add("hidden");
    up.classList.remove("hidden");
  }
}

async function startModelTraining() {
  const task = document.getElementById("train-task").value;
  const baseModel = document.getElementById("train-base-model").value;
  const sourceType = document.getElementById("train-source-type").value;
  const sessionId = document.getElementById("train-session-select").value;
  const modelName = document.getElementById("train-model-name").value.trim();
  const epochs = parseInt(document.getElementById("train-epochs").value || "2", 10);
  const batchSize = parseInt(document.getElementById("train-batch").value || "16", 10);
  const maxSamples = document.getElementById("train-max-samples").value.trim();

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
      base_model: baseModel,
      source_type: sourceType,
      session_id: sessionId,
      records: uploadedRecords,
      model_name: modelName,
      epochs,
      batch_size: batchSize,
      max_samples: maxSamples || null,
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
      <div class="flex flex-wrap items-center justify-between gap-2 text-xs">
        <span class="font-bold text-emerald-800">✅ Held-Out Test Split Results (${tr.test_rows || 0} units):</span>
        <div class="flex items-center gap-3 font-mono">
          <span>F1: <b>${((tr.f1 || 0) * 100).toFixed(1)}%</b></span>
          <span>Acc: <b>${((tr.accuracy || 0) * 100).toFixed(1)}%</b></span>
          <span>Prec: <b>${((tr.precision || 0) * 100).toFixed(1)}%</b></span>
          <span>Rec: <b>${((tr.recall || 0) * 100).toFixed(1)}%</b></span>
        </div>
      </div>
    `;
    await loadModelsStudio();
  } else if (job.status === "failed") {
    document.getElementById("train-stage-label").textContent = `Training Failed: ${job.error}`;
  }
}

async function runModelComparison() {
  const modelA = document.getElementById("eval-model-a").value;
  const modelB = document.getElementById("eval-model-b").value;
  const corpusId = document.getElementById("eval-corpus").value;
  const btn = document.getElementById("btn-run-eval");
  btn.disabled = true;
  btn.innerHTML = `<span>⏳ Comparing Models on Corpus…</span>`;

  try {
    const res = await fetch("/api/evaluations/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model_a: modelA, model_b: modelB, corpus_id: corpusId, max_units: 200 }),
    });
    const data = await res.json();
    const box = document.getElementById("eval-results-box");
    if (data.error) {
      box.innerHTML = `<div class="text-xs text-rose-600">${esc(data.error)}</div>`;
      return;
    }

    const ci = data.wilson95 || [0, 0];
    box.innerHTML = `
      <div class="grid grid-cols-3 gap-2.5 text-xs">
        <div class="p-3 rounded-lg bg-violet-50 border border-violet-200">
          <div class="text-violet-800">Binary Agreement</div>
          <div class="text-lg font-bold text-violet-700 font-mono">${((data.agreement || 0) * 100).toFixed(1)}%</div>
          <div class="text-[10px] text-violet-600 font-mono">CI: ${(ci[0] * 100).toFixed(1)}–${(ci[1] * 100).toFixed(1)}%</div>
        </div>
        <div class="p-3 rounded-lg bg-slate-50 border border-slate-200">
          <div class="text-slate-500">Cohen's Kappa (κ)</div>
          <div class="text-lg font-bold text-slate-900 font-mono">${data.kappa !== null ? data.kappa.toFixed(3) : "1.000"}</div>
          <div class="text-[10px] text-slate-400">n = ${data.n} units</div>
        </div>
        <div class="p-3 rounded-lg bg-slate-50 border border-slate-200">
          <div class="text-slate-500">Precision / Recall</div>
          <div class="text-sm font-bold text-slate-900 font-mono mt-1">${
            data.precision !== null ? (data.precision * 100).toFixed(0) : "100"
          }% / ${data.recall !== null ? (data.recall * 100).toFixed(0) : "100"}%</div>
          <div class="text-[10px] text-slate-400">${(data.disagreements || []).length} disagreements</div>
        </div>
      </div>
      ${
        (data.disagreements || []).length > 0
          ? `<div class="max-h-48 overflow-y-auto divide-y divide-slate-100 border border-slate-200 rounded-lg p-2 text-xs">
              ${data.disagreements
                .slice(0, 12)
                .map(
                  (d) => `<div class="py-1.5">
                  <div class="font-medium text-slate-800">${esc(d.comment_text)}</div>
                  <div class="text-[11px] font-mono text-slate-500">
                    A: <b>${d.a_quantum ? d.a_category || "Quantum" : "Non-Q"}</b> vs B: <b>${
                    d.b_quantum ? d.b_category || "Quantum" : "Non-Q"
                  }</b>
                  </div>
                </div>`
                )
                .join("")}
            </div>`
          : `<div class="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-medium">
              100% agreement across all ${data.n} evaluated comment units!
            </div>`
      }
    `;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<span>Run Agreement &amp; Profile Comparison</span>`;
  }
}

document.addEventListener("DOMContentLoaded", initApp);
