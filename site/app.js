const state = {
  research: null,
  alpha: null,
  route: "overview",
  selectedAnalysis: "cross-source-landscape",
  selectedTheme: "",
  themeSearch: "",
  themeStatus: "",
  projectSearch: "",
  projectAction: "",
  projectSource: "",
  evidenceSearch: "",
  evidenceSource: "",
  evidenceTheme: "",
};

const routes = new Set(["overview", "analyses", "themes", "projects", "evidence", "method"]);
const routeTitles = {
  overview: ["Research system", "Overview"],
  analyses: ["Research library", "Analyses"],
  themes: ["Cross-source dossiers", "Themes"],
  projects: ["Practical assessment", "Projects"],
  evidence: ["Normalized corpus", "Evidence"],
  method: ["Trust and provenance", "Method"],
};

const $ = (selector) => document.querySelector(selector);

function node(tag, className = "", text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function formatNumber(value) {
  return new Intl.NumberFormat("en-US").format(value ?? 0);
}

function formatDate(value, time = false) {
  if (!value) return "N/O";
  const date = new Date(value.length === 10 ? `${value}T12:00:00Z` : value);
  if (Number.isNaN(date.valueOf())) return value;
  return new Intl.DateTimeFormat("en", time ? { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" } : { dateStyle: "medium", timeZone: "UTC" }).format(date);
}

function label(value) {
  return String(value || "N/O").replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function sourceName(sourceId) {
  return state.research?.sources.find((source) => source.id === sourceId)?.name || sourceId;
}

function themeName(themeId) {
  return state.research?.themes.find((theme) => theme.id === themeId)?.name || themeId;
}

function metric(title, value, note = "") {
  const item = node("div", "metric");
  item.append(node("span", "metric-label", title), node("strong", "metric-value tabular", value));
  if (note) item.append(node("small", "metric-note", note));
  return item;
}

function badge(text, tone = "") {
  return node("span", `badge ${tone ? `badge-${tone}` : ""}`, text);
}

function linkOrText(item) {
  if (!item.url) return node("strong", "evidence-title", item.title);
  const link = node("a", "evidence-title", item.title);
  link.href = item.url;
  link.target = "_blank";
  link.rel = "noreferrer";
  return link;
}

function scoreBar(labelText, value, maximum = 25) {
  const item = node("div", "score-item");
  const head = node("div", "score-head");
  head.append(node("span", "", label(labelText)), node("strong", "tabular", `${value}/${maximum}`));
  const track = node("span", "score-track");
  const fill = node("span", "score-fill");
  fill.style.width = `${Math.min(100, (value / maximum) * 100)}%`;
  track.append(fill);
  item.append(head, track);
  return item;
}

function themeButton(theme, compact = false) {
  const button = node("button", compact ? "theme-link compact" : "theme-link");
  button.type = "button";
  button.dataset.themeId = theme.id;
  button.append(node("strong", "", theme.name));
  if (!compact) button.append(node("span", "", theme.score ? String(theme.score.total) : "N/O"));
  return button;
}

function renderOverview() {
  const { meta, weekly, themes, sources } = state.research;
  $("#overview-metrics").replaceChildren(
    metric("Normalized evidence", formatNumber(meta.normalized_evidence_count), `${formatNumber(meta.public_record_count)} direct public records`),
    metric("Active sources", formatNumber(meta.active_source_count), "One shared evidence contract"),
    metric("Observed themes", `${meta.observed_theme_count}/${meta.theme_count}`, `${meta.theme_count - meta.observed_theme_count} explicitly unobserved`),
    metric("Project catalog", formatNumber(meta.project_count), `${meta.reviewed_project_count} reviewed · ${meta.discovered_project_count} discovered`),
  );

  $("#weekly-window").textContent = `${formatDate(weekly.window_start)} through ${formatDate(weekly.as_of)} versus the preceding seven days. ${weekly.note}`;
  const movementBody = $("#movement-body");
  movementBody.replaceChildren();
  for (const movement of weekly.movements) {
    const row = node("tr");
    const theme = state.research.themes.find((item) => item.id === movement.theme_id);
    const themeCell = node("td");
    themeCell.append(themeButton(theme, true));
    const delta = movement.delta > 0 ? `+${movement.delta}` : String(movement.delta);
    row.append(
      themeCell,
      node("td", "number-cell tabular", String(movement.recent)),
      node("td", "number-cell tabular", String(movement.prior)),
      node("td", `number-cell tabular delta-${movement.delta > 0 ? "up" : movement.delta < 0 ? "down" : "flat"}`, delta),
      node("td", "", label(movement.direction)),
    );
    movementBody.append(row);
  }
  if (!weekly.movements.length) {
    const row = node("tr");
    const cell = node("td", "table-message", "No classified movement in this window.");
    cell.colSpan = 5;
    row.append(cell);
    movementBody.append(row);
  }

  const themeBody = $("#overview-theme-body");
  themeBody.replaceChildren();
  for (const theme of themes.slice(0, 10)) {
    const row = node("tr");
    const themeCell = node("td");
    themeCell.append(themeButton(theme, true));
    row.append(
      themeCell,
      node("td", "score-cell tabular", theme.score ? String(theme.score.total) : "N/O"),
      node("td", "number-cell tabular", String(theme.source_count)),
      node("td", "number-cell tabular", formatNumber(theme.support_units)),
      node("td", "number-cell tabular", theme.source_concentration === null ? "N/O" : `${Math.round(theme.source_concentration * 100)}%`),
      node("td", "", label(theme.maturity)),
    );
    themeBody.append(row);
  }

  const sourceGrid = $("#overview-sources");
  sourceGrid.replaceChildren();
  for (const source of sources) {
    const item = node("article", `source-item ${source.status === "configured" ? "source-muted" : ""}`);
    item.append(node("span", "source-channel", source.channel), node("strong", "", source.name), node("span", "tabular", formatNumber(source.normalized_evidence_count)), node("small", "", source.status));
    sourceGrid.append(item);
  }
}

function renderAnalysisIndex() {
  const container = $("#analysis-index");
  container.replaceChildren();
  for (const analysis of state.research.analyses) {
    const button = node("button", `analysis-item ${analysis.id === state.selectedAnalysis ? "selected" : ""}`);
    button.type = "button";
    button.dataset.analysisId = analysis.id;
    button.append(node("span", "analysis-status", label(analysis.status)), node("strong", "", analysis.title), node("p", "", analysis.question), node("small", "tabular", `${formatNumber(analysis.evidence_count)} evidence records · ${analysis.source_ids.length} sources`));
    container.append(button);
  }
}

function analysisHeader(analysis) {
  const fragment = document.createDocumentFragment();
  fragment.append(node("span", "detail-kicker", label(analysis.status)), node("h2", "", analysis.title), node("p", "detail-question", analysis.question), node("p", "", analysis.summary));
  const facts = node("dl", "detail-facts");
  for (const [term, value] of [
    ["Evidence", formatNumber(analysis.evidence_count)],
    ["Sources", analysis.source_ids.map(sourceName).join(" · ")],
    ["Updated", formatDate(analysis.updated_at)],
  ]) {
    facts.append(node("dt", "", term), node("dd", "", value));
  }
  fragment.append(facts);
  return fragment;
}

function renderAnalysisDetail() {
  const analysis = state.research.analyses.find((item) => item.id === state.selectedAnalysis) || state.research.analyses[0];
  state.selectedAnalysis = analysis.id;
  const detail = $("#analysis-detail");
  detail.replaceChildren(analysisHeader(analysis));

  if (analysis.id === "alphasignal-corpus") {
    if (!state.alpha) {
      detail.append(node("p", "inline-notice", "The cross-source aggregate is available, but the expanded AlphaSignal research file did not load."));
      return;
    }
    const findings = node("section", "detail-section");
    findings.append(node("h3", "", "Executive findings"));
    const list = node("ol", "finding-list");
    for (const finding of state.alpha.findings) {
      const item = node("li");
      item.append(node("strong", "", finding.finding), node("p", "", finding.evidence));
      list.append(item);
    }
    findings.append(list);
    const trends = node("section", "detail-section");
    trends.append(node("h3", "", "Reviewed trend analysis"));
    const rows = node("div", "compact-rows");
    for (const trend of state.alpha.trends) {
      const row = node("div", "compact-row");
      row.append(node("strong", "", trend.name), node("span", "tabular", `${trend.mentions} mentions`), node("span", "tabular", `score ${trend.score.total}`));
      rows.append(row);
    }
    trends.append(rows);
    detail.append(findings, trends);
  } else if (analysis.id === "cross-source-landscape") {
    const section = node("section", "detail-section");
    section.append(node("h3", "", "Leading assessments"));
    const rows = node("div", "compact-rows");
    for (const theme of state.research.themes.slice(0, 10)) {
      const row = node("div", "compact-row");
      row.append(themeButton(theme, true), node("span", "tabular", `${theme.source_count} sources`), node("span", "", label(theme.maturity)));
      rows.append(row);
    }
    section.append(rows);
    detail.append(section);
  } else if (analysis.id === "public-signal-monitor") {
    const section = node("section", "detail-section");
    section.append(node("h3", "", "Public source coverage"));
    const rows = node("div", "compact-rows");
    for (const source of state.research.sources.filter((item) => item.id !== "alphasignal")) {
      const row = node("div", "compact-row");
      row.append(node("strong", "", source.name), node("span", "", source.channel), node("span", "tabular", formatNumber(source.normalized_evidence_count)));
      rows.append(row);
    }
    section.append(rows);
    detail.append(section);
  } else if (analysis.id === "operator-narratives") {
    const section = node("section", "detail-section");
    section.append(node("h3", "", "Recent public essays"));
    const rows = node("div", "evidence-list");
    const essays = state.research.evidence.filter((item) => analysis.source_ids.includes(item.source_id)).slice(0, 20);
    for (const essay of essays) {
      const row = node("article", "evidence-list-item");
      row.append(linkOrText(essay), node("span", "", `${sourceName(essay.source_id)} · ${formatDate(essay.published_at)} · ${essay.theme_ids.length} matched themes`));
      rows.append(row);
    }
    section.append(rows);
    detail.append(section);
  } else {
    const section = node("section", "detail-section");
    section.append(node("h3", "", "Highest-priority projects"));
    const rows = node("div", "compact-rows");
    for (const project of state.research.projects.slice(0, 10)) {
      const row = node("div", "compact-row");
      const link = node("a", "", project.name);
      link.href = project.official_url;
      link.target = "_blank";
      link.rel = "noreferrer";
      row.append(link, node("span", "", project.action), node("span", "tabular", String(project.opportunity_score)));
      rows.append(row);
    }
    section.append(rows);
    detail.append(section);
  }
}

function renderAnalyses() {
  renderAnalysisIndex();
  renderAnalysisDetail();
}

function renderThemeIndex() {
  const query = state.themeSearch.trim().toLowerCase();
  const filtered = state.research.themes.filter((theme) => {
    const searchable = [theme.name, theme.definition, ...(theme.aliases || [])].join(" ").toLowerCase();
    return (!query || searchable.includes(query)) && (!state.themeStatus || theme.maturity === state.themeStatus);
  });
  $("#theme-count").textContent = `${filtered.length} of ${state.research.themes.length}`;
  if (!filtered.some((theme) => theme.id === state.selectedTheme)) state.selectedTheme = filtered[0]?.id || "";
  const container = $("#theme-index");
  container.replaceChildren();
  for (const theme of filtered) {
    const button = node("button", `theme-index-item ${theme.id === state.selectedTheme ? "selected" : ""}`);
    button.type = "button";
    button.dataset.selectTheme = theme.id;
    button.append(node("strong", "", theme.name), node("span", "tabular", theme.score ? String(theme.score.total) : "N/O"), node("small", "", `${theme.source_count} sources · ${label(theme.maturity)}`));
    container.append(button);
  }
  if (!filtered.length) container.append(node("p", "empty-state", "No themes match these filters."));
}

function monthlySeries(counts) {
  const wrapper = node("div", "monthly-series");
  const values = Object.values(counts);
  const max = Math.max(1, ...values);
  for (const [month, value] of Object.entries(counts)) {
    const item = node("div", "month-item");
    const bar = node("span", "month-bar");
    const fill = node("span", "month-fill");
    fill.style.height = `${Math.max(value ? 4 : 0, (value / max) * 100)}%`;
    bar.append(fill);
    item.append(node("strong", "tabular", String(value)), bar, node("span", "", month.slice(5)));
    wrapper.append(item);
  }
  return wrapper;
}

function renderThemeDossier() {
  const dossier = $("#theme-dossier");
  dossier.replaceChildren();
  const theme = state.research.themes.find((item) => item.id === state.selectedTheme);
  if (!theme) {
    dossier.append(node("p", "empty-state", "Select a theme to inspect its evidence."));
    return;
  }
  const head = node("header", "dossier-head");
  const title = node("div");
  title.append(badge(label(theme.maturity), theme.maturity), node("h2", "", theme.name), node("p", "", theme.definition || "Seed theme; definition will be refined from evidence."));
  const score = node("div", "dossier-score");
  score.append(node("span", "", "Cross-source score"), node("strong", "tabular", theme.score ? String(theme.score.total) : "N/O"));
  head.append(title, score);
  dossier.append(head);

  const metrics = node("div", "dossier-metrics");
  metrics.append(
    metric("Sources", String(theme.source_count), "Independent channels observed"),
    metric("Evidence records", formatNumber(theme.evidence_count), "Normalized observations"),
    metric("Support units", formatNumber(theme.support_units), "Source attention, not adoption"),
    metric("Largest-source share", theme.source_concentration === null ? "N/O" : `${Math.round(theme.source_concentration * 100)}%`, "Reported outside the score"),
  );
  dossier.append(metrics);

  const grid = node("div", "dossier-grid");
  const time = node("section");
  time.append(node("h3", "", "Six-month evidence"), monthlySeries(theme.monthly_counts));
  const components = node("section");
  components.append(node("h3", "", "Score components"));
  const scoreGrid = node("div", "score-grid");
  if (theme.score) {
    for (const key of ["recurrence", "acceleration", "persistence", "breadth"]) scoreGrid.append(scoreBar(key, theme.score[key]));
  } else {
    scoreGrid.append(node("p", "empty-state", "N/O — no observed evidence, so no points are awarded."));
  }
  components.append(scoreGrid);
  grid.append(time, components);
  dossier.append(grid);

  const sources = node("section", "dossier-section");
  sources.append(node("h3", "", "Source contribution"));
  const sourceRows = node("div", "compact-rows");
  for (const source of theme.source_breakdown) {
    const row = node("div", "compact-row");
    row.append(node("strong", "", sourceName(source.source_id)), node("span", "tabular", `${source.observations} records`), node("span", "tabular", `${formatNumber(source.support_units)} support`));
    sourceRows.append(row);
  }
  if (!theme.source_breakdown.length) sourceRows.append(node("p", "empty-state", "No source currently supports this theme."));
  sources.append(sourceRows);
  dossier.append(sources);

  const evidenceSection = node("section", "dossier-section");
  evidenceSection.append(node("h3", "", "Underlying evidence"));
  const records = theme.evidence_ids.map((id) => state.research.evidence.find((item) => item.id === id)).filter(Boolean).slice(0, 15);
  const list = node("div", "evidence-list");
  for (const record of records) {
    const item = node("article", "evidence-list-item");
    item.append(linkOrText(record), node("span", "", `${sourceName(record.source_id)} · ${formatDate(record.published_at)} · ${label(record.evidence_kind)}`));
    list.append(item);
  }
  evidenceSection.append(list);
  dossier.append(evidenceSection);
}

function renderThemes() {
  renderThemeIndex();
  renderThemeDossier();
}

function renderProjects() {
  const query = state.projectSearch.trim().toLowerCase();
  const projects = state.research.projects.filter((project) => {
    const searchable = [project.name, project.category, project.why_it_matters, project.workflow_opportunity].join(" ").toLowerCase();
    const sourceMatch = !state.projectSource || (state.projectSource === "cross-source" ? project.cross_source : !project.cross_source);
    return (!query || searchable.includes(query)) && (!state.projectAction || project.action === state.projectAction) && sourceMatch;
  });
  $("#project-count").textContent = `${projects.length} of ${state.research.projects.length}`;
  const body = $("#project-body");
  body.replaceChildren();
  for (const project of projects) {
    const projectSlug = project.name.toLowerCase().replace(/[^a-z0-9]+/g, "-");
    const detailId = `project-detail-${project.review_status}-${project.rank ?? projectSlug}`;
    const row = node("tr", "primary-row");
    const rank = node("td", "rank-cell tabular");
    const toggle = node("button", "detail-toggle", "+");
    toggle.type = "button";
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-controls", detailId);
    rank.append(toggle, document.createTextNode(project.rank === null ? "—" : String(project.rank).padStart(2, "0")));
    const subject = node("td", "subject-cell");
    const link = node("a", "", project.name);
    link.href = project.official_url;
    link.target = "_blank";
    link.rel = "noreferrer";
    subject.append(link, node("small", "", project.category));
    row.append(rank, subject, node("td", "score-cell tabular", project.opportunity_score === null ? "N/O" : String(project.opportunity_score)), node("td", "", project.action), node("td", "", project.hype_risk), node("td", "tabular", String(project.source_ids.length)), node("td", "", project.primary_layer));

    const detailRow = node("tr", "detail-row");
    detailRow.id = detailId;
    detailRow.hidden = true;
    const cell = node("td");
    cell.colSpan = 7;
    const panel = node("div", "project-detail");
    for (const [heading, copy] of [["Why it matters", project.why_it_matters], ["Workflow opportunity", project.workflow_opportunity], ["Caveat", project.caveat]]) {
      const block = node("div");
      block.append(node("strong", "detail-label", heading), node("p", "", copy));
      panel.append(block);
    }
    const provenance = node("div", "project-provenance");
    provenance.append(node("strong", "detail-label", "Evidence sources"), node("p", "", project.source_ids.map(sourceName).join(" · ")));
    panel.append(provenance);
    cell.append(panel);
    detailRow.append(cell);
    body.append(row, detailRow);
  }
  if (!projects.length) {
    const row = node("tr");
    const cell = node("td", "table-message", "No projects match these filters.");
    cell.colSpan = 7;
    row.append(cell);
    body.append(row);
  }
}

function renderEvidence() {
  const query = state.evidenceSearch.trim().toLowerCase();
  const records = state.research.evidence.filter((item) => {
    const searchable = [item.title, item.summary, ...(item.projects || []), ...(item.authors || [])].join(" ").toLowerCase();
    return (!query || searchable.includes(query)) && (!state.evidenceSource || item.source_id === state.evidenceSource) && (!state.evidenceTheme || item.theme_ids.includes(state.evidenceTheme));
  });
  $("#evidence-count").textContent = `${formatNumber(records.length)} of ${formatNumber(state.research.evidence.length)}`;
  const shown = records.slice(0, 100);
  $("#evidence-limit").textContent = records.length > shown.length ? `Showing the first ${shown.length} records. Narrow the filters to inspect the rest.` : `Showing all ${shown.length} matching records.`;
  const body = $("#evidence-body");
  body.replaceChildren();
  for (const item of shown) {
    const row = node("tr");
    const subject = node("td", "subject-cell");
    subject.append(linkOrText(item));
    if (item.summary) subject.append(node("small", "", item.summary));
    const themes = node("td", "theme-chip-cell");
    for (const themeId of item.theme_ids.slice(0, 3)) {
      const button = node("button", "theme-chip", themeName(themeId));
      button.type = "button";
      button.dataset.themeId = themeId;
      themes.append(button);
    }
    row.append(node("td", "date-cell tabular", formatDate(item.published_at)), node("td", "", sourceName(item.source_id)), subject, node("td", "", label(item.evidence_kind)), node("td", "number-cell tabular", formatNumber(item.support_count)), themes);
    body.append(row);
  }
  if (!shown.length) {
    const row = node("tr");
    const cell = node("td", "table-message", "No evidence matches these filters.");
    cell.colSpan = 6;
    row.append(cell);
    body.append(row);
  }
}

function renderMethod() {
  const method = state.research.methodology;
  $("#method-normalization").textContent = method.normalization;
  const score = $("#method-score");
  score.replaceChildren();
  for (const [term, description] of Object.entries(method.trend_score)) score.append(node("dt", "", label(term)), node("dd", "", description));
  const limits = $("#method-limits");
  limits.replaceChildren();
  for (const limit of method.limits) limits.append(node("li", "", limit));
  const sources = $("#method-sources");
  sources.replaceChildren();
  for (const source of state.research.sources) {
    const row = node("div", "method-source");
    row.append(node("strong", "", source.name), node("span", "", `${source.channel} · ${source.source_quality || "unknown quality"}`), node("span", "tabular", `${formatNumber(source.normalized_evidence_count)} records`));
    sources.append(row);
  }
}

function populateFilters() {
  const projectAction = $("#project-action");
  const baseAction = node("option", "", "All actions");
  baseAction.value = "";
  projectAction.replaceChildren(baseAction);
  for (const action of [...new Set(state.research.projects.map((project) => project.action))]) {
    const option = node("option", "", action);
    option.value = action;
    projectAction.append(option);
  }

  const sourceSelect = $("#evidence-source");
  const baseSource = node("option", "", "All sources");
  baseSource.value = "";
  sourceSelect.replaceChildren(baseSource);
  for (const source of state.research.sources.filter((item) => item.status === "active")) {
    const option = node("option", "", source.name);
    option.value = source.id;
    sourceSelect.append(option);
  }

  const themeSelect = $("#evidence-theme");
  const baseTheme = node("option", "", "All themes");
  baseTheme.value = "";
  themeSelect.replaceChildren(baseTheme);
  for (const theme of state.research.themes) {
    const option = node("option", "", theme.name);
    option.value = theme.id;
    themeSelect.append(option);
  }
}

function renderAll() {
  renderOverview();
  renderAnalyses();
  if (!state.selectedTheme) state.selectedTheme = state.research.themes[0]?.id || "";
  renderThemes();
  renderProjects();
  renderEvidence();
  renderMethod();
}

function routeFromHash() {
  const parts = location.hash.replace(/^#/, "").split("/").filter(Boolean);
  const route = routes.has(parts[0]) ? parts[0] : "overview";
  state.route = route;
  if (route === "themes" && parts[1]) state.selectedTheme = parts[1];
  if (route === "analyses" && parts[1]) state.selectedAnalysis = parts[1];
  for (const view of document.querySelectorAll("[data-view]")) view.hidden = view.dataset.view !== route;
  for (const link of document.querySelectorAll("[data-route]")) link.setAttribute("aria-current", link.dataset.route === route ? "page" : "false");
  const [eyebrow, title] = routeTitles[route];
  $("#view-eyebrow").textContent = eyebrow;
  $("#view-title").textContent = title;
  if (state.research) {
    if (route === "themes") renderThemes();
    if (route === "analyses") renderAnalyses();
  }
  window.scrollTo(0, 0);
}

function toggleDetail(button) {
  const target = document.getElementById(button.getAttribute("aria-controls"));
  if (!target) return;
  const expanded = button.getAttribute("aria-expanded") === "true";
  button.setAttribute("aria-expanded", String(!expanded));
  button.textContent = expanded ? "+" : "−";
  target.hidden = expanded;
}

function bindControls() {
  window.addEventListener("hashchange", routeFromHash);
  $("#theme-search").addEventListener("input", (event) => { state.themeSearch = event.target.value; renderThemes(); });
  $("#theme-status").addEventListener("change", (event) => { state.themeStatus = event.target.value; renderThemes(); });
  $("#project-search").addEventListener("input", (event) => { state.projectSearch = event.target.value; renderProjects(); });
  $("#project-action").addEventListener("change", (event) => { state.projectAction = event.target.value; renderProjects(); });
  $("#project-source").addEventListener("change", (event) => { state.projectSource = event.target.value; renderProjects(); });
  $("#evidence-search").addEventListener("input", (event) => { state.evidenceSearch = event.target.value; renderEvidence(); });
  $("#evidence-source").addEventListener("change", (event) => { state.evidenceSource = event.target.value; renderEvidence(); });
  $("#evidence-theme").addEventListener("change", (event) => { state.evidenceTheme = event.target.value; renderEvidence(); });
  $("#retry-load").addEventListener("click", load);
  document.addEventListener("click", (event) => {
    const theme = event.target.closest("[data-theme-id]");
    if (theme) location.hash = `themes/${theme.dataset.themeId}`;
    const selectedTheme = event.target.closest("[data-select-theme]");
    if (selectedTheme) {
      state.selectedTheme = selectedTheme.dataset.selectTheme;
      history.replaceState(null, "", `#themes/${state.selectedTheme}`);
      renderThemes();
      $("#theme-dossier").focus({ preventScroll: true });
    }
    const analysis = event.target.closest("[data-analysis-id]");
    if (analysis) {
      state.selectedAnalysis = analysis.dataset.analysisId;
      history.replaceState(null, "", `#analyses/${state.selectedAnalysis}`);
      renderAnalyses();
      $("#analysis-detail").focus({ preventScroll: true });
    }
    const toggle = event.target.closest(".detail-toggle");
    if (toggle) toggleDetail(toggle);
  });
}

async function load() {
  $("#load-failure").hidden = true;
  $("#sidebar-state").textContent = "Loading research";
  const [researchResult, alphaResult] = await Promise.allSettled([
    fetch("./data/research.json", { cache: "no-store" }).then((response) => {
      if (!response.ok) throw new Error(`Cross-source dataset returned ${response.status}.`);
      return response.json();
    }),
    fetch("./data/alphasignal-research.json", { cache: "no-store" }).then((response) => {
      if (!response.ok) throw new Error(`AlphaSignal detail returned ${response.status}.`);
      return response.json();
    }),
  ]);

  if (researchResult.status === "rejected") {
    $("#load-failure").hidden = false;
    $("#failure-detail").textContent = researchResult.reason.message;
    $("#sidebar-state").textContent = "Dataset unavailable";
    return;
  }
  state.research = researchResult.value;
  state.alpha = alphaResult.status === "fulfilled" ? alphaResult.value : null;
  populateFilters();
  renderAll();
  routeFromHash();
  const { meta } = state.research;
  $("#sidebar-state").textContent = `${meta.active_source_count} active sources`;
  $("#sidebar-updated").textContent = `Updated ${formatDate(meta.generated_at)}`;
  $("#header-coverage").textContent = `${formatNumber(meta.normalized_evidence_count)} normalized records · ${meta.observed_theme_count} observed themes`;
  $("#header-date").textContent = formatDate(meta.generated_at, true);
  if (alphaResult.status === "rejected") {
    $("#load-failure").hidden = false;
    $("#failure-detail").textContent = "Cross-source research loaded, but the expanded AlphaSignal analysis is unavailable.";
  }
}

bindControls();
routeFromHash();
load();
