const state = {
  alpha: null,
  public: null,
  trendSearch: "",
  trendLayer: "",
  trendSort: "score",
  projectSearch: "",
  projectAction: "",
  projectRisk: "",
};

const $ = (selector) => document.querySelector(selector);

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function formatNumber(value) {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatDate(value, includeTime = false) {
  if (!value) return "N/O";
  const date = new Date(value.length === 10 ? `${value}T12:00:00Z` : value);
  if (Number.isNaN(date.valueOf())) return value;
  return new Intl.DateTimeFormat("en", includeTime ? { dateStyle: "medium", timeStyle: "short" } : { dateStyle: "medium", timeZone: "UTC" }).format(date);
}

function shortMonth(value) {
  return new Intl.DateTimeFormat("en", { month: "short", timeZone: "UTC" }).format(new Date(`${value}-15T12:00:00Z`));
}

function slug(value) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function makeBadge(text, tone = "neutral") {
  const badge = node("span", `badge badge-${tone}`, text);
  return badge;
}

function metric(label, value, note = "") {
  const item = node("div", "metric");
  item.append(node("span", "metric-label", label), node("strong", "metric-value", value));
  if (note) item.append(node("small", "metric-note", note));
  return item;
}

function renderCorpus() {
  const { meta } = state.alpha;
  const coverage = $("#coverage");
  coverage.replaceChildren();
  for (const [term, description] of [
    ["Coverage", `${formatDate(meta.coverage_start)} — ${formatDate(meta.coverage_end)}`],
    ["Source", meta.source],
    ["Analysis", formatDate(meta.analysis_date)],
  ]) {
    const row = node("div");
    row.append(node("dt", "", term), node("dd", "", description));
    coverage.append(row);
  }

  const metrics = $("#corpus-metrics");
  metrics.replaceChildren(
    metric("Emails received", formatNumber(meta.email_count), `${meta.substantive_email_count} substantive`),
    metric("Extracted signals", formatNumber(meta.raw_signal_records), "Before exact deduplication"),
    metric("Unique records", formatNumber(meta.unique_catalog_records), "Research catalog"),
    metric("Sponsored records", formatNumber(meta.sponsored_records), "Excluded from interpretation"),
    metric("Analyzed trends", formatNumber(meta.trend_count), "Two or more dimensions"),
    metric("Ranked projects", formatNumber(meta.project_count), "Official links retained"),
  );
  $("#boundary-note span").textContent = meta.publication_boundary;
}

function renderLayers() {
  const container = $("#layer-table");
  container.replaceChildren();
  const max = Math.max(...state.alpha.layers.map((layer) => layer.catalog_records));
  for (const [index, layer] of state.alpha.layers.entries()) {
    const row = node("article", "layer-row");
    const label = node("div", "layer-name");
    label.append(node("span", "layer-index", String(index + 1).padStart(2, "0")), node("strong", "", layer.name));
    const measure = node("div", "layer-measure");
    const track = node("span", "measure-track");
    const fill = node("span", "measure-fill");
    fill.style.width = `${(layer.catalog_records / max) * 100}%`;
    track.append(fill);
    measure.append(track, node("strong", "tabular", formatNumber(layer.catalog_records)));
    row.append(label, node("p", "", layer.definition), measure);
    container.append(row);
  }
}

function renderFindings() {
  const list = $("#finding-list");
  list.replaceChildren();
  for (const [index, finding] of state.alpha.findings.entries()) {
    const item = node("li");
    item.append(
      node("span", "finding-index tabular", String(index + 1).padStart(2, "0")),
      node("strong", "", finding.finding),
      node("p", "", finding.evidence),
    );
    list.append(item);
  }
}

function scoreComponent(label, value) {
  const item = node("div", "score-component");
  const head = node("div", "component-head");
  head.append(node("span", "", label), node("strong", "tabular", `${value}/25`));
  const track = node("span", "component-track");
  const fill = node("span", "component-fill");
  fill.style.width = `${value * 4}%`;
  track.append(fill);
  item.append(head, track);
  return item;
}

function monthlySeries(months) {
  const wrapper = node("div", "monthly-series");
  const max = Math.max(1, ...Object.values(months));
  for (const [month, value] of Object.entries(months)) {
    const item = node("div", "month-item");
    const bar = node("span", "month-bar");
    const fill = node("span", "month-fill");
    fill.style.height = `${Math.max(3, (value / max) * 100)}%`;
    bar.append(fill);
    item.append(node("strong", "tabular", String(value)), bar, node("span", "", shortMonth(month)));
    wrapper.append(item);
  }
  return wrapper;
}

function detailButton(id, label) {
  const button = node("button", "detail-toggle", label);
  button.type = "button";
  button.setAttribute("aria-expanded", "false");
  button.setAttribute("aria-controls", id);
  return button;
}

function renderTrends() {
  if (!state.alpha) return;
  const query = state.trendSearch.trim().toLowerCase();
  const ranked = new Map(state.alpha.trends.map((trend, index) => [trend.name, index + 1]));
  const trends = state.alpha.trends.filter((trend) => {
    const searchText = [trend.name, trend.finding, trend.direction, trend.primary_layer, trend.secondary_layer, ...trend.examples].join(" ").toLowerCase();
    return (!query || searchText.includes(query)) && (!state.trendLayer || trend.primary_layer === state.trendLayer || trend.secondary_layer === state.trendLayer);
  });
  trends.sort((a, b) => {
    if (state.trendSort === "mentions") return b.mentions - a.mentions;
    if (state.trendSort === "acceleration") return b.score.acceleration - a.score.acceleration || b.score.total - a.score.total;
    if (state.trendSort === "name") return a.name.localeCompare(b.name);
    return b.score.total - a.score.total;
  });

  $("#trend-count").textContent = `${trends.length} of ${state.alpha.trends.length} trends`;
  const body = $("#trend-body");
  body.replaceChildren();
  if (!trends.length) {
    const row = node("tr");
    const cell = node("td", "table-message", "No trends match these filters.");
    cell.colSpan = 7;
    row.append(cell);
    body.append(row);
    return;
  }

  for (const trend of trends) {
    const id = `trend-${slug(trend.name)}`;
    const main = node("tr", "primary-row");
    const rank = node("td", "rank-cell tabular");
    rank.append(detailButton(id, "+"), document.createTextNode(String(ranked.get(trend.name)).padStart(2, "0")));
    const trendCell = node("td", "subject-cell");
    trendCell.append(node("strong", "", trend.name), node("small", "", trend.finding));
    main.append(
      rank,
      trendCell,
      node("td", "number-cell tabular", formatNumber(trend.mentions)),
      node("td", "direction-cell", trend.direction),
      node("td", "", trend.primary_layer),
      node("td", "score-cell tabular", String(trend.score.total)),
      node("td", "", trend.score.tier),
    );

    const detail = node("tr", "detail-row");
    detail.id = id;
    detail.hidden = true;
    const detailCell = node("td");
    detailCell.colSpan = 7;
    const panel = node("div", "trend-detail-grid");
    const examples = node("div", "detail-copy");
    examples.append(node("span", "detail-label", "Representative examples"), node("p", "", trend.examples.join(" · ")));
    if (trend.secondary_layer) examples.append(node("span", "detail-note", `Secondary layer: ${trend.secondary_layer}${trend.cross_layer ? " · Cross-layer" : ""}`));
    const components = node("div", "component-grid");
    for (const key of ["recurrence", "acceleration", "persistence", "breadth"]) components.append(scoreComponent(key, trend.score[key]));
    const time = node("div", "series-wrap");
    time.append(node("span", "detail-label", "Matched non-sponsored records by month"), monthlySeries(trend.monthly_mentions));
    panel.append(examples, components, time);
    detailCell.append(panel);
    detail.append(detailCell);
    body.append(main, detail);
  }
}

function ratingItem(label, value) {
  const item = node("div", "rating-item");
  item.append(node("span", "", label), node("strong", "tabular", `${value}/5`));
  return item;
}

function renderProjects() {
  if (!state.alpha) return;
  const query = state.projectSearch.trim().toLowerCase();
  const projects = state.alpha.projects.filter((project) => {
    const searchText = [project.name, project.category, project.why_it_matters, project.workflow_opportunity, project.primary_layer, project.secondary_layer].join(" ").toLowerCase();
    return (!query || searchText.includes(query)) && (!state.projectAction || project.action === state.projectAction) && (!state.projectRisk || project.hype_risk === state.projectRisk);
  });
  $("#project-count").textContent = `${projects.length} of ${state.alpha.projects.length} projects`;
  const body = $("#project-body");
  body.replaceChildren();
  if (!projects.length) {
    const row = node("tr");
    const cell = node("td", "table-message", "No projects match these filters.");
    cell.colSpan = 7;
    row.append(cell);
    body.append(row);
    return;
  }

  for (const project of projects) {
    const id = `project-${slug(project.name)}`;
    const main = node("tr", "primary-row");
    const rank = node("td", "rank-cell tabular");
    rank.append(detailButton(id, "+"), document.createTextNode(String(project.rank).padStart(2, "0")));
    const projectCell = node("td", "subject-cell");
    const link = node("a", "project-link", project.name);
    link.href = project.official_url;
    link.target = "_blank";
    link.rel = "noreferrer";
    projectCell.append(link, node("small", "", project.category));
    main.append(
      rank,
      projectCell,
      node("td", "score-cell tabular", String(project.opportunity_score)),
      node("td", "", project.action),
      node("td", "", ""),
      node("td", "", project.primary_layer),
      node("td", "date-cell tabular", formatDate(project.source_date)),
    );
    main.children[4].append(makeBadge(project.hype_risk, project.hype_risk.toLowerCase()));

    const detail = node("tr", "detail-row");
    detail.id = id;
    detail.hidden = true;
    const detailCell = node("td");
    detailCell.colSpan = 7;
    const panel = node("div", "project-detail-grid");
    for (const [label, value] of [
      ["Why it matters", project.why_it_matters],
      ["Workflow opportunity", project.workflow_opportunity],
      ["Maturity / caveat", project.caveat],
    ]) {
      const block = node("div", "detail-copy");
      block.append(node("span", "detail-label", label), node("p", "", value));
      panel.append(block);
    }
    const ratings = node("div", "ratings-grid");
    for (const [key, value] of Object.entries(project.ratings)) ratings.append(ratingItem(key.replace("_", " "), value));
    const layer = node("div", "project-provenance");
    layer.append(node("strong", "", "Classification"), node("span", "", `${project.primary_layer}${project.secondary_layer ? ` → ${project.secondary_layer}` : ""}${project.cross_layer ? " · cross-layer" : ""}`));
    panel.append(ratings, layer);
    detailCell.append(panel);
    detail.append(detailCell);
    body.append(main, detail);
  }
}

function renderLive() {
  if (!state.public) return;
  const { meta } = state.public;
  const summary = $("#live-summary");
  summary.replaceChildren(
    metric("Public records", formatNumber(meta.evidence_count ?? 0)),
    metric("Independent sources", formatNumber(meta.source_count ?? 0)),
    metric("Snapshot", formatDate(meta.generated_at, true)),
    metric("Collection status", meta.status || "unknown"),
  );

  const themes = $("#live-theme-body");
  themes.replaceChildren();
  for (const theme of state.public.themes || []) {
    const row = node("tr");
    row.append(
      node("td", "", theme.name),
      node("td", "number-cell tabular", formatNumber(theme.evidence_count || 0)),
      node("td", "number-cell tabular", formatNumber((theme.source_types || []).length)),
      node("td", "score-cell tabular", theme.score?.total === undefined ? "N/O" : String(theme.score.total)),
    );
    themes.append(row);
  }

  const records = [...(state.public.evidence || [])].sort((a, b) => String(b.published_at).localeCompare(String(a.published_at))).slice(0, 12);
  const list = $("#record-list");
  list.replaceChildren();
  for (const record of records) {
    const item = node("li");
    const link = node("a", "", record.title);
    link.href = record.url;
    link.target = "_blank";
    link.rel = "noreferrer";
    item.append(link, node("span", "", `${record.source_id} · ${formatDate(record.published_at)}`));
    list.append(item);
  }
}

function renderMethod() {
  if (!state.alpha) return;
  const method = state.alpha.methodology;
  $("#trend-purpose").textContent = method.trend_score.purpose;
  const trendList = $("#trend-method");
  trendList.replaceChildren();
  for (const [term, description] of Object.entries(method.trend_score.components)) trendList.append(node("dt", "", term), node("dd", "", description));

  $("#opportunity-purpose").textContent = method.opportunity_score.purpose;
  const opportunityList = $("#opportunity-method");
  opportunityList.replaceChildren();
  for (const [term, value] of Object.entries(method.opportunity_score.weights)) opportunityList.append(node("dt", "", term.replace("_", " ")), node("dd", "tabular", `${value}%`));
  opportunityList.append(node("dt", "", "Rating scale"), node("dd", "", method.opportunity_score.scale));

  const limitations = $("#limitations");
  limitations.replaceChildren();
  for (const limit of method.limitations) limitations.append(node("li", "", limit));
}

function populateFilters() {
  const layerSelect = $("#trend-layer");
  const allLayers = node("option", "", "All layers");
  allLayers.value = "";
  layerSelect.replaceChildren(allLayers);
  const layers = [...new Set(state.alpha.layers.map((layer) => layer.name))];
  for (const layer of layers) {
    const option = node("option", "", layer);
    option.value = layer;
    layerSelect.append(option);
  }
  const actionSelect = $("#project-action");
  const allActions = node("option", "", "All actions");
  allActions.value = "";
  actionSelect.replaceChildren(allActions);
  const actions = [...new Set(state.alpha.projects.map((project) => project.action))];
  for (const action of actions) {
    const option = node("option", "", action);
    option.value = action;
    actionSelect.append(option);
  }
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
  $("#trend-search").addEventListener("input", (event) => { state.trendSearch = event.target.value; renderTrends(); });
  $("#trend-layer").addEventListener("change", (event) => { state.trendLayer = event.target.value; renderTrends(); });
  $("#trend-sort").addEventListener("change", (event) => { state.trendSort = event.target.value; renderTrends(); });
  $("#project-search").addEventListener("input", (event) => { state.projectSearch = event.target.value; renderProjects(); });
  $("#project-action").addEventListener("change", (event) => { state.projectAction = event.target.value; renderProjects(); });
  $("#project-risk").addEventListener("change", (event) => { state.projectRisk = event.target.value; renderProjects(); });
  document.addEventListener("click", (event) => {
    const button = event.target.closest(".detail-toggle");
    if (button) toggleDetail(button);
  });
  $("#retry-load").addEventListener("click", load);
}

function showFailure(messages) {
  const failure = $("#load-failure");
  failure.hidden = false;
  $("#failure-detail").textContent = messages.join(" ");
}

async function load() {
  $("#load-failure").hidden = true;
  $("#dataset-state").textContent = "Loading datasets";
  const [alphaResult, publicResult] = await Promise.allSettled([
    fetch("./data/alphasignal-research.json", { cache: "no-store" }).then((response) => {
      if (!response.ok) throw new Error(`AlphaSignal dataset returned ${response.status}.`);
      return response.json();
    }),
    fetch("./data/dashboard.json", { cache: "no-store" }).then((response) => {
      if (!response.ok) throw new Error(`Public evidence returned ${response.status}.`);
      return response.json();
    }),
  ]);

  const failures = [];
  if (alphaResult.status === "fulfilled") {
    state.alpha = alphaResult.value;
    renderCorpus();
    renderFindings();
    renderLayers();
    populateFilters();
    renderTrends();
    renderProjects();
    renderMethod();
  } else {
    failures.push(alphaResult.reason.message);
    $("#trend-body").innerHTML = '<tr><td colspan="7" class="table-message error-message">AlphaSignal research is unavailable.</td></tr>';
    $("#project-body").innerHTML = '<tr><td colspan="7" class="table-message error-message">Project research is unavailable.</td></tr>';
  }

  if (publicResult.status === "fulfilled") {
    state.public = publicResult.value;
    renderLive();
  } else {
    failures.push(publicResult.reason.message);
    $("#live-theme-body").innerHTML = '<tr><td colspan="4" class="table-message error-message">Public evidence is unavailable.</td></tr>';
    $("#record-list").replaceChildren(node("li", "table-message error-message", "Recent public records are unavailable."));
  }

  if (failures.length) showFailure(failures);
  $("#dataset-state").textContent = failures.length ? "Partial data" : `${state.alpha.meta.email_count} emails · ${state.public.meta.evidence_count} public records`;
}

bindControls();
load();
