const state = {
  research: null,
  alpha: null,
  operatingModel: null,
  route: "overview",
  selectedRequirement: "",
  selectedAnalysis: "cross-source-landscape",
  selectedTheme: "",
  themeSearch: "",
  themeStatus: "",
  projectSearch: "",
  projectReview: "reviewed",
  projectAction: "",
  projectSource: "",
  evidenceSearch: "",
  evidenceSource: "",
  evidenceTheme: "",
  sourceType: "",
};

const routes = new Set(["overview", "operating-model", "analyses", "themes", "projects", "evidence", "method"]);
const routeTitles = {
  overview: ["Research system", "Overview"],
  "operating-model": ["Evidence-backed practice", "Operating Model"],
  analyses: ["Research library", "Analyses"],
  themes: ["Cross-source dossiers", "Themes"],
  projects: ["Engineering registry", "Engineering Atlas"],
  evidence: ["Normalized corpus", "Evidence"],
  method: ["Trust and provenance", "Method"],
};

const sourceChannelOrder = [
  "first-party-lab",
  "paper",
  "paper-curation",
  "repository",
  "expert-newsletter",
  "curated-newsletter",
  "practitioner-blog",
  "expert-social",
  "operator-essay",
  "investor-essay",
  "newsletter",
  "community",
  "mixed",
];

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

function formatMonthDay(value) {
  if (!value) return "N/O";
  const date = new Date(value.length === 10 ? `${value}T12:00:00Z` : value);
  if (Number.isNaN(date.valueOf())) return value;
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", timeZone: "UTC" }).format(date);
}

function label(value) {
  return String(value || "N/O").replace(/[-_]/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function channelLabel(value) {
  return ({
    "first-party-lab": "Official lab",
    "expert-newsletter": "Expert newsletter",
    "curated-newsletter": "Curated newsletter",
    "practitioner-blog": "Practitioner blog",
  })[value] || label(value);
}

function compactAssessment(value) {
  return ({
    "broadly-corroborated": "Broadly corroborated",
    "corroborated-source-concentrated": "Source-concentrated",
    corroborated: "Corroborated",
    emerging: "Emerging",
    "source-specific": "Single-source",
    unobserved: "Unobserved",
  })[value] || label(value);
}

function sourceRecord(sourceId) {
  return state.research?.sources.find((source) => source.id === sourceId);
}

function sourceName(sourceId) {
  return sourceRecord(sourceId)?.name || sourceId;
}

function sourceIcon(source) {
  const icon = node("span", `source-icon source-icon-${source.id}`);
  icon.title = source?.name || "Source";
  icon.setAttribute("aria-hidden", "true");
  const fallback = node("span", "source-monogram", (source?.name || "Source").split(/\s+/).slice(0, 2).map((word) => word[0]).join("").toUpperCase());
  if (!source?.logo_url) {
    icon.append(fallback);
    return icon;
  }
  fallback.hidden = true;
  const image = node("img", "source-logo");
  image.src = source.logo_url;
  image.alt = "";
  image.decoding = "async";
  image.referrerPolicy = "no-referrer";
  image.addEventListener("error", () => {
    image.hidden = true;
    fallback.hidden = false;
  }, { once: true });
  icon.append(image, fallback);
  return icon;
}

function sourceIdentity(source) {
  const identity = node(source?.homepage_url ? "a" : "span", "source-identity");
  if (source?.homepage_url) {
    identity.href = source.homepage_url;
    identity.target = "_blank";
    identity.rel = "noreferrer";
  }
  identity.append(sourceIcon(source), node("strong", "", source?.name || "Unknown source"));
  return identity;
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

function maturityBadge(value) {
  return node("span", `maturity-badge maturity-${value}`, label(value));
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
  const structuralTrendCount = state.alpha?.trends.filter((trend) => trend.score?.tier === "Structural").length;
  const emergingCategoryCount = Math.min(3, themes.filter((theme) => ["source-specific", "emerging"].includes(theme.maturity)).length);
  $("#overview-metrics").replaceChildren(
    metric("Normalized evidence", formatNumber(meta.normalized_evidence_count), `${formatNumber(meta.public_record_count)} direct public records`),
    metric("Active sources", formatNumber(meta.active_source_count), "One shared evidence contract"),
    metric("Structural trends", structuralTrendCount === undefined ? "N/O" : formatNumber(structuralTrendCount), "Reviewed AlphaSignal corpus"),
    metric("Emerging categories", formatNumber(emergingCategoryCount), "Priority watchlist to validate"),
    metric("Reviewed projects", formatNumber(meta.reviewed_project_count), `${meta.queued_project_count} queued · ${meta.discovered_project_count} discovered`),
    metric("Analyses", formatNumber(state.research.analyses.length), "Cross-source and source-specific"),
  );

  $("#weekly-window").textContent = `${formatDate(weekly.window_start)} through ${formatDate(weekly.as_of)} versus the preceding seven days. Public date-level evidence only.`;
  const movementBody = $("#movement-body");
  movementBody.replaceChildren();
  for (const movement of weekly.movements.slice(0, 5)) {
    const row = node("tr");
    const theme = state.research.themes.find((item) => item.id === movement.theme_id);
    const themeCell = node("td");
    themeCell.append(themeButton(theme, true));
    const delta = movement.delta > 0 ? `+${movement.delta}` : String(movement.delta);
    row.append(
      themeCell,
      node("td", "number-cell tabular", String(movement.recent)),
      node("td", `number-cell tabular delta-${movement.delta > 0 ? "up" : movement.delta < 0 ? "down" : "flat"}`, delta),
      node("td", "number-cell tabular", String(theme.source_count)),
      node("td", "", compactAssessment(theme.maturity)),
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

  const analysisBody = $("#overview-analysis-body");
  analysisBody.replaceChildren();
  for (const analysis of state.research.analyses) {
    const row = node("tr");
    const titleCell = node("td", "analysis-summary-title");
    const link = node("a", "", analysis.title);
    link.href = `#analyses/${analysis.id}`;
    titleCell.append(link);
    row.append(
      titleCell,
      node("td", "analysis-question", analysis.question),
      node("td", "number-cell tabular", formatNumber(analysis.evidence_count)),
      node("td", "number-cell tabular", String(analysis.source_ids.length)),
      node("td", "", label(analysis.status)),
    );
    analysisBody.append(row);
  }

  const sourceGrid = $("#overview-sources");
  sourceGrid.replaceChildren();
  const filteredSources = sources.filter((source) => !state.sourceType || source.channel === state.sourceType);
  const activeCount = filteredSources.filter((source) => source.status === "active").length;
  $("#source-count").textContent = `${filteredSources.length} ${filteredSources.length === 1 ? "source" : "sources"} · ${activeCount} active`;

  const grouped = new Map();
  for (const source of filteredSources) {
    if (!grouped.has(source.channel)) grouped.set(source.channel, []);
    grouped.get(source.channel).push(source);
  }
  const channels = [...grouped.keys()].sort((left, right) => {
    const leftIndex = sourceChannelOrder.indexOf(left);
    const rightIndex = sourceChannelOrder.indexOf(right);
    return (leftIndex < 0 ? sourceChannelOrder.length : leftIndex) - (rightIndex < 0 ? sourceChannelOrder.length : rightIndex)
      || channelLabel(left).localeCompare(channelLabel(right));
  });
  for (const channel of channels) {
    const groupSources = grouped.get(channel).sort((left, right) => left.name.localeCompare(right.name));
    const group = node("section", "source-group");
    const head = node("header", "source-group-head");
    const recordCount = groupSources.reduce((total, source) => total + source.normalized_evidence_count, 0);
    head.append(
      node("h4", "", channelLabel(channel)),
      node("span", "tabular", `${groupSources.length} ${groupSources.length === 1 ? "source" : "sources"} · ${formatNumber(recordCount)} records`),
    );
    const grid = node("div", "source-grid");
    for (const source of groupSources) {
      const item = node("article", `source-item ${source.status === "configured" ? "source-muted" : ""}`);
      item.append(
        sourceIdentity(source),
        node("span", "source-record-count tabular", `${formatNumber(source.normalized_evidence_count)} records`),
        node("small", "", source.status === "active" ? `Active · ${label(source.freshness)} · latest ${formatDate(source.last_observed_at)}` : "Configured · no evidence observed"),
      );
      grid.append(item);
    }
    group.append(head, grid);
    sourceGrid.append(group);
  }
  if (!channels.length) {
    sourceGrid.append(node("p", "empty-state", "No sources match this type."));
  }
}

function relationshipLabel(value) {
  return ({
    "direct-support": "Qualifying support",
    "supporting-context": "Supporting context",
    counterevidence: "Counterevidence",
    "discovery-only": "Discovery only",
    excluded: "Excluded",
  })[value] || label(value);
}

function gateFailureLabel(value) {
  const match = String(value).match(/^(.+) is (.+); requires (.+)$/);
  if (!match) return label(value);
  const [, field, actual, required] = match;
  if (field === "counterevidence_reviewed") return "Counterevidence has not been explicitly reviewed.";
  return `${label(field)} is ${label(actual)}; ${label(required)} is required.`;
}

function renderOperatingModel() {
  const data = state.operatingModel;
  const metrics = $("#operating-metrics");
  const index = $("#requirement-index");
  const detail = $("#requirement-detail");
  const boundary = $("#operating-boundary");

  if (!data) {
    metrics.replaceChildren(metric("Operating requirements", "N/O", "Dataset unavailable"));
    boundary.replaceChildren();
    index.replaceChildren();
    const message = node("div", "empty-state");
    message.append(node("strong", "", "Operating model unavailable."), node("p", "", "The cross-source research loaded, but its requirement registry did not."));
    const retry = node("button", "inline-retry", "Retry loading");
    retry.type = "button";
    retry.addEventListener("click", load);
    message.append(retry);
    detail.replaceChildren(message);
    return;
  }

  const counts = data.meta.maturity_counts;
  const actionable = (counts.emerging || 0) + (counts.established || 0) + (counts.baseline || 0);
  const reviewedCounterevidence = data.requirements.filter((item) => item.gate_inputs.counterevidence_reviewed).length;
  metrics.replaceChildren(
    metric("Assessed requirements", formatNumber(data.meta.requirement_count), `Policy v${data.meta.policy_version}`),
    metric("Emerging or stronger", formatNumber(actionable), "Selective adoption supported"),
    metric("Experimental", formatNumber(counts.experimental), "Bounded testing only"),
    metric("Narrative", formatNumber(counts.narrative), "Watch; do not standardize"),
    metric("Counterevidence reviewed", formatNumber(reviewedCounterevidence), "Explicit opposing record required"),
  );
  boundary.replaceChildren(node("strong", "", "How to read this"), node("span", "", data.boundary));

  if (!state.selectedRequirement || !data.requirements.some((item) => item.id === state.selectedRequirement)) {
    state.selectedRequirement = data.requirements[0]?.id || "";
  }
  index.replaceChildren();
  for (const requirement of data.requirements) {
    const button = node("button", `requirement-item ${requirement.id === state.selectedRequirement ? "selected" : ""}`);
    button.type = "button";
    button.dataset.requirementId = requirement.id;
    button.setAttribute("aria-current", requirement.id === state.selectedRequirement ? "true" : "false");
    button.append(
      maturityBadge(requirement.maturity),
      node("strong", "", requirement.title),
      node("p", "", requirement.requirement),
      node("small", "tabular", `${label(requirement.confidence)} confidence · ${requirement.evidence.length} linked records`),
    );
    index.append(button);
  }

  const requirement = data.requirements.find((item) => item.id === state.selectedRequirement);
  if (!requirement) {
    detail.replaceChildren(node("p", "empty-state", "No operating requirements have been assessed yet."));
    return;
  }

  const definition = data.maturity_definitions[requirement.maturity];
  const head = node("header", "requirement-head");
  const headCopy = node("div", "requirement-head-copy");
  headCopy.append(
    node("span", "detail-kicker", `Operating requirement · ${label(requirement.confidence)} confidence`),
    node("h2", "", requirement.title),
    node("p", "requirement-statement", requirement.requirement),
  );
  const maturity = node("div", "requirement-maturity");
  maturity.append(maturityBadge(requirement.maturity), node("small", "", `Assessed ${formatDate(data.meta.as_of)}`));
  head.append(headCopy, maturity);

  const explanation = node("section", "requirement-explanation");
  explanation.append(node("h3", "", "What this means"), node("p", "", requirement.description));
  const posture = node("aside", "requirement-posture");
  posture.append(node("strong", "", `${label(requirement.maturity)} posture`), node("p", "", definition.recommended_posture));
  explanation.append(posture);

  const practice = node("section", "requirement-practice");
  const practiceList = node("ul", "practice-list");
  for (const item of requirement.what_it_looks_like) practiceList.append(node("li", "", item));
  const applicability = node("div", "applicability-note");
  applicability.append(node("strong", "", "Where it applies"), node("p", "", requirement.applicable_to));
  practice.append(node("h3", "", "What it looks like in a startup"), practiceList, applicability);

  const dimensions = node("section", "requirement-section");
  dimensions.append(node("h3", "", "Evidence assessment"));
  const dimensionGrid = node("div", "dimension-grid");
  const dimensionOrder = ["technical_reality", "operational_adoption", "market_pull", "evidence_independence"];
  for (const dimension of dimensionOrder) {
    const level = requirement.assessments[dimension];
    const item = node("article", `dimension-item evidence-level-${level}`);
    item.append(
      node("span", "dimension-label", label(dimension)),
      node("strong", "dimension-level", label(level)),
      node("p", "", data.dimension_rules[dimension][level]),
    );
    dimensionGrid.append(item);
  }
  dimensions.append(dimensionGrid);

  const judgment = node("section", "requirement-judgment");
  const assessment = node("div", "judgment-column");
  assessment.append(node("h3", "", "Why this maturity"), node("p", "", requirement.rationale));
  if (requirement.next_gate) {
    assessment.append(node("strong", "judgment-label", `Blocked at ${label(requirement.next_gate.maturity)}`));
    const failures = node("ul", "compact-list");
    for (const failure of requirement.next_gate.failures) failures.append(node("li", "", gateFailureLabel(failure)));
    assessment.append(failures);
  }
  const verification = node("div", "judgment-column");
  verification.append(node("h3", "", "What to verify next"));
  const gaps = node("ul", "compact-list");
  for (const gap of requirement.evidence_gaps) gaps.append(node("li", "", gap));
  verification.append(gaps);
  judgment.append(assessment, verification);

  const sourceAnalysis = requirement.source_analysis.split("/")[0];
  const analysisLink = node("a", "requirement-analysis-link", "Open the originating analysis →");
  analysisLink.href = `#analyses/${sourceAnalysis}`;

  const evidenceSection = node("section", "requirement-section");
  evidenceSection.append(node("h3", "", "Evidence map"));
  const evidenceBoundary = node("p", "section-note", "Qualifying support can promote maturity. Context and discovery records cannot. Counterevidence and exclusions stay visible.");
  const evidenceList = node("div", "requirement-evidence-list");
  for (const item of requirement.evidence) {
    const row = node("article", `requirement-evidence evidence-${item.relationship}`);
    const source = node("div", "requirement-evidence-source");
    const sourceInfo = sourceRecord(item.source_id);
    source.append(sourceIdentity(sourceInfo || { id: item.source_id, name: item.source_name }), node("small", "tabular", formatDate(item.published_at)));
    const copy = node("div", "requirement-evidence-copy");
    copy.append(linkOrText(item));
    if (item.exclusion_reason) copy.append(node("p", "evidence-reason", item.exclusion_reason));
    const disposition = node("div", "requirement-evidence-disposition");
    disposition.append(badge(relationshipLabel(item.relationship), item.relationship));
    if (item.dimensions.length) disposition.append(node("small", "", item.dimensions.map(label).join(" · ")));
    row.append(source, copy, disposition);
    evidenceList.append(row);
  }
  evidenceSection.append(evidenceBoundary, evidenceList, analysisLink);

  detail.replaceChildren(head, explanation, practice, dimensions, judgment, evidenceSection);
}

function renderAnalysisIndex() {
  const container = $("#analysis-index");
  container.replaceChildren();
  for (const analysis of state.research.analyses) {
    const button = node("button", `analysis-item ${analysis.id === state.selectedAnalysis ? "selected" : ""}`);
    button.type = "button";
    button.dataset.analysisId = analysis.id;
    const sourceCount = analysis.source_ids.length;
    button.append(node("span", "analysis-status", label(analysis.status)), node("strong", "", analysis.title), node("p", "", analysis.question), node("small", "tabular", `${formatNumber(analysis.evidence_count)} evidence records · ${sourceCount} ${sourceCount === 1 ? "source" : "sources"}`));
    container.append(button);
  }
}

function analysisFacts(analysis) {
  const facts = node("dl", "detail-facts");
  const factsList = [
    ["Evidence", formatNumber(analysis.evidence_count)],
    ["Sources", analysis.source_ids.map(sourceName).join(" · ")],
    ["Updated", formatDate(analysis.updated_at)],
  ];
  if (analysis.corpus_count !== undefined) factsList.splice(1, 0, ["Corpus items", formatNumber(analysis.corpus_count)]);
  for (const [term, value] of factsList) facts.append(node("dt", "", term), node("dd", "", value));
  return facts;
}

function analysisHeader(analysis, includeFacts = true) {
  const fragment = document.createDocumentFragment();
  fragment.append(node("span", "detail-kicker", label(analysis.status)), node("h2", "", analysis.title), node("p", "detail-question", analysis.question), node("p", "", analysis.summary));
  if (includeFacts) fragment.append(analysisFacts(analysis));
  return fragment;
}

function renderAnalysisDetail() {
  const analysis = state.research.analyses.find((item) => item.id === state.selectedAnalysis) || state.research.analyses[0];
  state.selectedAnalysis = analysis.id;
  const detail = $("#analysis-detail");
  detail.replaceChildren(analysisHeader(analysis, !["operator-narratives", "early-signal-tracker", "expert-pulse"].includes(analysis.id)));

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
      row.append(sourceIdentity(source), node("span", "", channelLabel(source.channel)), node("span", "tabular", formatNumber(source.normalized_evidence_count)));
      rows.append(row);
    }
    section.append(rows);
    detail.append(section);
  } else if (analysis.id === "early-signal-tracker") {
    const synthesis = node("section", "detail-section narrative-synthesis signal-synthesis");
    synthesis.append(node("h3", "", "Current directional read"), node("p", "synthesis-lead", analysis.executive_summary));
    if (analysis.interpretation_note) synthesis.append(node("p", "interpretation-note", analysis.interpretation_note));

    const signalMetrics = node("div", "metric-strip signal-metrics");
    const accelerating = (analysis.movement_counts?.accelerating || 0) + (analysis.movement_counts?.new || 0);
    const resurfacing = analysis.movement_counts?.resurfacing || 0;
    const established = analysis.stage_counts?.established || 0;
    const newestDate = (analysis.directions || []).map((item) => item.last_observed).filter(Boolean).sort().at(-1);
    signalMetrics.append(
      metric("Tracked directions", formatNumber(analysis.direction_count), "Explicit hypotheses, not generated topics"),
      metric("Established", formatNumber(established), "Meets breadth and persistence thresholds"),
      metric("Accelerating", formatNumber(accelerating), `${formatNumber(resurfacing)} resurfacing`),
      metric("Newest evidence", formatDate(newestDate), "Most recent supporting record"),
    );

    const changes = node("section", "detail-section signal-changes");
    changes.append(node("h3", "", "Important early changes"));
    const changeShell = node("div", "table-shell");
    const changeTable = node("table", "data-table signal-change-table");
    const changeHead = document.createElement("thead");
    const headRow = node("tr");
    for (const heading of ["Direction", "Lifecycle", "Movement", "14-day evidence", "Change", "Families"]) headRow.append(node("th", heading === "14-day evidence" || heading === "Change" || heading === "Families" ? "numeric-header" : "", heading));
    changeHead.append(headRow);
    const changeBody = document.createElement("tbody");
    const directionById = new Map((analysis.directions || []).map((item) => [item.id, item]));
    for (const id of analysis.important_changes || []) {
      const direction = directionById.get(id);
      if (!direction) continue;
      const row = node("tr");
      const titleCell = node("td", "signal-change-title");
      const jump = node("button", "signal-jump", direction.title);
      jump.type = "button";
      jump.dataset.signalId = direction.id;
      titleCell.append(jump, node("small", "", direction.movement_explanation));
      const delta = direction.evidence_change > 0 ? `+${direction.evidence_change}` : String(direction.evidence_change);
      row.append(
        titleCell,
        node("td", "", label(direction.stage)),
        node("td", `signal-movement signal-movement-${direction.movement}`, label(direction.movement)),
        node("td", "number-cell tabular", formatNumber(direction.current_evidence_count)),
        node("td", `number-cell tabular ${direction.evidence_change > 0 ? "delta-up" : direction.evidence_change < 0 ? "delta-down" : ""}`, delta),
        node("td", "number-cell tabular", formatNumber(direction.family_count)),
      );
      changeBody.append(row);
    }
    changeTable.append(changeHead, changeBody);
    changeShell.append(changeTable);
    changes.append(changeShell);

    const stages = node("section", "detail-section");
    stages.append(node("h3", "", "Lifecycle rules"));
    const stageGrid = node("div", "signal-stage-grid");
    for (const [stage, description] of Object.entries(analysis.method?.states || {})) {
      const item = node("div", "signal-stage-key");
      item.append(node("strong", `signal-stage signal-stage-${stage}`, label(stage)), node("span", "", description));
      stageGrid.append(item);
    }
    stages.append(stageGrid);

    const findings = node("section", "detail-section");
    findings.append(node("h3", "", "Directional hypotheses"));
    const directionList = node("div", "signal-directions");
    const evidenceById = new Map(state.research.evidence.map((item) => [item.id, item]));
    for (const [index, direction] of (analysis.directions || []).entries()) {
      const article = node("article", "signal-direction");
      article.id = `signal-${direction.id}`;
      article.tabIndex = -1;
      const head = node("div", "signal-direction-head");
      const title = node("div", "signal-direction-title");
      title.append(node("span", "finding-label", direction.domain), node("h4", "", direction.title));
      const status = node("div", "signal-direction-status");
      status.append(
        node("strong", `signal-stage signal-stage-${direction.stage}`, label(direction.stage)),
        node("span", `signal-movement signal-movement-${direction.movement}`, label(direction.movement)),
        node("span", "tabular", `${direction.source_count} ${direction.source_count === 1 ? "source" : "sources"} · ${direction.family_count} ${direction.family_count === 1 ? "family" : "families"}`),
      );
      head.append(node("span", "finding-index tabular", String(index + 1).padStart(2, "0")), title, status);

      const body = node("div", "signal-direction-body");
      body.append(node("p", "signal-hypothesis", direction.hypothesis));
      const stateRead = node("p", "signal-state-reason", direction.state_reason);
      if (direction.stage_changed) stateRead.append(node("strong", "", ` Changed from ${label(direction.previous_stage)} in the prior comparison snapshot.`));
      body.append(stateRead);
      const lifecycle = node("div", "signal-history");
      lifecycle.append(node("strong", "", "Eight-week path"));
      const history = direction.lifecycle_history || [];
      if (history.length) lifecycle.append(node("small", "", formatMonthDay(history[0].as_of)));
      for (const snapshot of history) {
        const point = node("span", `signal-history-point signal-history-${snapshot.stage}`, label(snapshot.stage));
        const recordWord = snapshot.evidence_count === 1 ? "record" : "records";
        const sourceWord = snapshot.source_count === 1 ? "source" : "sources";
        const familyWord = snapshot.family_count === 1 ? "family" : "families";
        point.title = `${formatDate(snapshot.as_of)} · ${snapshot.evidence_count} ${recordWord} · ${snapshot.source_count} ${sourceWord} · ${snapshot.family_count} ${familyWord}`;
        point.setAttribute("aria-label", point.title);
        lifecycle.append(point);
      }
      if (history.length) lifecycle.append(node("small", "", formatMonthDay(history.at(-1).as_of)));
      body.append(lifecycle);
      const reading = node("div", "signal-reading-grid");
      for (const [heading, copy] of [
        ["Interpretation", direction.interpretation],
        ["Why it matters", direction.why_it_matters],
        ["What would confirm it", direction.next_confirmation],
        ["Counter-signal", direction.counter_signal],
      ]) {
        const item = node("div", "finding-implication");
        item.append(node("strong", "", heading), node("p", "", copy));
        reading.append(item);
      }
      body.append(reading);

      const evidenceMap = node("div", "signal-evidence-map");
      evidenceMap.append(node("strong", "", "Observed across"));
      for (const family of direction.source_families || []) {
        evidenceMap.append(node("span", "signal-family", `${family.name} · ${family.source_count}`));
      }
      body.append(evidenceMap);

      if (direction.origin) {
        const origin = node("p", "signal-origin");
        origin.append(node("strong", "", "Earliest observed: "));
        const originEvidence = evidenceById.get(direction.origin.evidence_id) || direction.origin;
        origin.append(linkOrText(originEvidence), document.createTextNode(` · ${sourceName(direction.origin.source_id)} · ${formatDate(direction.origin.published_at)}`));
        body.append(origin);
      }

      const themes = node("div", "signal-theme-links");
      themes.append(node("strong", "", "Connected themes"));
      for (const themeId of direction.theme_ids || []) {
        const theme = state.research.themes.find((item) => item.id === themeId);
        if (theme) themes.append(themeButton(theme, true));
      }
      body.append(themes);

      const citedEvidence = (direction.evidence_ids || []).map((id) => evidenceById.get(id)).filter(Boolean);
      if (citedEvidence.length) {
        const details = node("details", "finding-evidence");
        details.append(node("summary", "", `${citedEvidence.length} diverse supporting records`));
        const rows = node("div", "evidence-list");
        for (const item of citedEvidence) {
          const row = node("article", "evidence-list-item");
          row.append(linkOrText(item), node("span", "", `${sourceName(item.source_id)} · ${formatDate(item.published_at)}`));
          rows.append(row);
        }
        details.append(rows);
        body.append(details);
      }
      const observed = node("p", "signal-observed tabular", `First observed ${formatDate(direction.first_observed)} · latest ${formatDate(direction.last_observed)} · ${direction.evidence_count} ${direction.evidence_count === 1 ? "record" : "records"} in the current ${direction.window_days}-day window`);
      body.append(observed);
      article.append(head, body);
      directionList.append(article);
    }
    if (!directionList.children.length) directionList.append(node("p", "empty-state", "No directional hypothesis has enough evidence to display yet."));
    findings.append(directionList);
    detail.append(synthesis, signalMetrics, changes, stages, findings);
  } else if (analysis.id === "expert-pulse") {
    const synthesis = node("section", "detail-section narrative-synthesis");
    synthesis.append(node("h3", "", "Executive synthesis"), node("p", "synthesis-lead", analysis.executive_summary || "No synthesis has been published yet."));
    if (analysis.interpretation_note) synthesis.append(node("p", "interpretation-note", analysis.interpretation_note));

    const findings = node("section", "detail-section");
    findings.append(node("h3", "", "Research findings"));
    const findingList = node("div", "research-findings");
    const evidenceById = new Map(state.research.evidence.map((item) => [item.id, item]));
    for (const [index, finding] of (analysis.findings || []).entries()) {
      const article = node("article", `research-finding finding-${finding.strength || "watch"}`);
      const head = node("div", "finding-head");
      head.append(node("span", "finding-index tabular", String(index + 1).padStart(2, "0")));
      const title = node("div", "finding-title");
      title.append(node("span", "finding-label", finding.label), node("h4", "", finding.title));
      head.append(title, node("span", "finding-metrics tabular", `${finding.metrics.posts} posts · ${finding.metrics.experts} ${finding.metrics.experts === 1 ? "expert" : "experts"}`));
      const body = node("div", "finding-body");
      body.append(node("p", "finding-analysis", finding.analysis));
      const implications = node("div", "finding-implications");
      for (const [heading, copy] of [["Why it matters", finding.why_it_matters], ["Workflow opportunity", finding.workflow_opportunity], ["Caveat", finding.caveat]]) {
        const item = node("div", "finding-implication");
        item.append(node("strong", "", heading), node("p", "", copy));
        implications.append(item);
      }
      body.append(implications);
      const citedEvidence = (finding.evidence_ids || []).map((id) => evidenceById.get(id)).filter(Boolean);
      if (citedEvidence.length) {
        const details = node("details", "finding-evidence");
        details.append(node("summary", "", `${citedEvidence.length} supporting posts`));
        const rows = node("div", "evidence-list");
        for (const post of citedEvidence) {
          const row = node("article", "evidence-list-item");
          const author = (post.authors || []).join(", ") || sourceName(post.source_id);
          row.append(linkOrText(post), node("span", "", `${author} · ${formatDate(post.published_at)}`));
          rows.append(row);
        }
        details.append(rows);
        body.append(details);
      }
      article.append(head, body);
      findingList.append(article);
    }
    if (!findingList.children.length) findingList.append(node("p", "empty-state", "No expert findings have enough classified evidence yet."));
    findings.append(findingList);

    const themes = node("section", "detail-section");
    themes.append(node("h3", "", "Category evidence counts"));
    const themeRows = node("div", "compact-rows");
    for (const summary of analysis.theme_summary || []) {
      const theme = state.research.themes.find((item) => item.id === summary.theme_id);
      if (!theme) continue;
      const row = node("div", "compact-row");
      row.append(themeButton(theme, true), node("span", "tabular", `${summary.evidence_count} posts`), node("span", "tabular", `${summary.source_count} experts`));
      themeRows.append(row);
    }
    if (!themeRows.children.length) themeRows.append(node("p", "empty-state", "No classified expert observations are available yet."));
    themes.append(themeRows);

    const recent = node("section", "detail-section");
    recent.append(node("h3", "", "Recent relevant posts"));
    const evidenceRows = node("div", "evidence-list");
    const evidenceIds = new Set(analysis.evidence_ids || []);
    const posts = state.research.evidence.filter((item) => evidenceIds.has(item.id)).slice(0, 30);
    for (const post of posts) {
      const row = node("article", "evidence-list-item");
      const author = (post.authors || []).join(", ") || sourceName(post.source_id);
      row.append(linkOrText(post), node("span", "", `${author} · ${formatDate(post.published_at)} · ${post.theme_ids.length} matched themes`));
      evidenceRows.append(row);
    }
    if (!evidenceRows.children.length) evidenceRows.append(node("p", "empty-state", "The weekly collector has not added any matching posts yet."));
    recent.append(evidenceRows);
    const scope = node("section", "detail-section analysis-scope");
    scope.append(node("h3", "", "Corpus scope"), analysisFacts(analysis));
    detail.append(synthesis, findings, scope, themes, recent);
  } else if (analysis.id === "operator-narratives") {
    const synthesis = node("section", "detail-section narrative-synthesis");
    synthesis.append(node("h3", "", "Executive synthesis"), node("p", "synthesis-lead", analysis.executive_summary || "No synthesis has been published yet."));
    if (analysis.interpretation_note) synthesis.append(node("p", "interpretation-note", analysis.interpretation_note));

    const findings = node("section", "detail-section");
    findings.append(node("h3", "", "Research findings"));
    const findingList = node("div", "research-findings");
    const evidenceById = new Map(state.research.evidence.map((item) => [item.id, item]));
    for (const [index, finding] of (analysis.findings || []).entries()) {
      const article = node("article", `research-finding finding-${finding.strength || "moderate"}`);
      const head = node("div", "finding-head");
      head.append(node("span", "finding-index tabular", String(index + 1).padStart(2, "0")));
      const title = node("div", "finding-title");
      title.append(node("span", "finding-label", finding.label), node("h4", "", finding.title));
      head.append(title, node("span", "finding-metrics tabular", `${finding.metrics.essays} essays · ${finding.metrics.publishers} ${finding.metrics.publishers === 1 ? "publisher" : "publishers"}`));

      const body = node("div", "finding-body");
      body.append(node("p", "finding-analysis", finding.analysis));
      const implications = node("div", "finding-implications");
      for (const [heading, copy] of [["Why it matters", finding.why_it_matters], ["Workflow opportunity", finding.workflow_opportunity], ["Caveat", finding.caveat]]) {
        const item = node("div", "finding-implication");
        item.append(node("strong", "", heading), node("p", "", copy));
        implications.append(item);
      }
      body.append(implications);

      const citedEvidence = (finding.evidence_ids || []).map((id) => evidenceById.get(id)).filter(Boolean);
      if (citedEvidence.length) {
        const details = node("details", "finding-evidence");
        details.append(node("summary", "", `${citedEvidence.length} supporting essays`));
        const rows = node("div", "evidence-list");
        for (const essay of citedEvidence) {
          const row = node("article", "evidence-list-item");
          row.append(linkOrText(essay), node("span", "", `${sourceName(essay.source_id)} · ${formatDate(essay.published_at)}`));
          rows.append(row);
        }
        details.append(rows);
        body.append(details);
      }
      article.append(head, body);
      findingList.append(article);
    }
    if (!findingList.children.length) findingList.append(node("p", "empty-state", "No narrative findings have been published yet."));
    findings.append(findingList);

    const scope = node("section", "detail-section analysis-scope");
    scope.append(node("h3", "", "Corpus scope"), analysisFacts(analysis));

    const categories = node("section", "detail-section");
    categories.append(node("h3", "", "Category evidence counts"));
    const categoryRows = node("div", "compact-rows");
    for (const summary of analysis.theme_summary || []) {
      const theme = state.research.themes.find((item) => item.id === summary.theme_id);
      if (!theme) continue;
      const row = node("div", "compact-row");
      row.append(themeButton(theme, true), node("span", "tabular", `${summary.evidence_count} essays`), node("span", "tabular", `${summary.source_count} sources`));
      categoryRows.append(row);
    }
    if (!categoryRows.children.length) categoryRows.append(node("p", "empty-state", "No narrative categories are classified yet."));
    categories.append(categoryRows);
    const section = node("section", "detail-section");
    section.append(node("h3", "", "Recent classified evidence"));
    const rows = node("div", "evidence-list");
    const narrativeEvidenceIds = new Set(analysis.evidence_ids || []);
    const essays = state.research.evidence.filter((item) => narrativeEvidenceIds.has(item.id)).slice(0, 20);
    for (const essay of essays) {
      const row = node("article", "evidence-list-item");
      row.append(linkOrText(essay), node("span", "", `${sourceName(essay.source_id)} · ${formatDate(essay.published_at)} · ${essay.theme_ids.length} matched themes`));
      rows.append(row);
    }
    section.append(rows);
    detail.append(synthesis, findings, scope, categories, section);
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
    metric("Sources", String(theme.source_count), "Distinct source streams observed"),
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
    const record = sourceRecord(source.source_id) || { name: sourceName(source.source_id), channel: "mixed" };
    row.append(sourceIdentity(record), node("span", "tabular", `${source.observations} records`), node("span", "tabular", `${formatNumber(source.support_units)} support`));
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
  const atlas = state.research.engineering_atlas;
  const quality = atlas.quality;
  $("#engineering-health").replaceChildren(
    metric("Classification", quality.classification_coverage === null ? "N/O" : `${Math.round(quality.classification_coverage * 100)}%`, `${formatNumber(quality.unclassified_public_records)} public records remain unclassified`),
    metric("Fresh sources", formatNumber(quality.recent_sources), `${quality.aging_sources} aging · ${quality.historical_sources} historical`),
    metric("Review queue", formatNumber(quality.queued_projects), "Bounded set selected from public discoveries"),
    metric("Reviewed tools", formatNumber(quality.reviewed_projects), `${quality.discovered_projects} additional discoveries`),
  );

  const auditRoot = $("#classification-audit");
  auditRoot.replaceChildren();
  const audit = atlas.classification_audit;
  if (audit) {
    const summary = node("div", "audit-summary");
    summary.append(
      metric("Sample", formatNumber(audit.sample_size), `${audit.sample_source_count} represented sources`),
      metric("Reclassified", formatNumber(audit.newly_classified_records), "Previously unresolved records"),
      metric("Coverage", `${Math.round(audit.post_audit_classification_coverage * 1000) / 10}%`, `from ${Math.round(audit.baseline_classification_coverage * 1000) / 10}%`),
      metric("After audit", formatNumber(audit.post_audit_unclassified_records), "Unresolved records at completion"),
    );
    const findings = node("div", "audit-findings");
    for (const finding of audit.findings || []) {
      const item = node("article", "audit-finding");
      item.append(node("strong", "", finding.title), node("p", "", finding.conclusion));
      findings.append(item);
    }
    const boundary = node("p", "audit-boundary", audit.limitation);
    auditRoot.append(summary, findings, boundary);
  } else {
    auditRoot.append(node("p", "empty-state", "No classification audit has been published yet."));
  }

  const conceptGrid = $("#engineering-concepts");
  conceptGrid.replaceChildren();
  for (const concept of atlas.concepts) {
    const card = node("article", "concept-card");
    const head = node("div", "concept-card-head");
    const theme = state.research.themes.find((item) => item.id === concept.id);
    if (theme) head.append(themeButton(theme, true));
    head.append(badge(compactAssessment(concept.maturity), concept.maturity));
    card.append(
      head,
      node("p", "", concept.definition),
      node("div", "concept-counts tabular", `${concept.project_count} tools · ${concept.reviewed_project_count} reviewed · ${concept.queued_project_count} queued`),
    );
    if (concept.project_names.length) card.append(node("small", "", concept.project_names.slice(0, 4).join(" · ")));
    conceptGrid.append(card);
  }
  if (!atlas.concepts.length) conceptGrid.append(node("p", "empty-state", "No concepts are connected to tools yet."));

  const query = state.projectSearch.trim().toLowerCase();
  const projects = state.research.projects.filter((project) => {
    const searchable = [project.name, project.category, project.why_it_matters, project.workflow_opportunity, ...(project.theme_ids || []).map(themeName)].join(" ").toLowerCase();
    const sourceMatch = !state.projectSource || (state.projectSource === "cross-source" ? project.cross_source : !project.cross_source);
    return (!query || searchable.includes(query)) && (!state.projectReview || project.review_status === state.projectReview) && (!state.projectAction || project.action === state.projectAction) && sourceMatch;
  });
  const reviewedCount = state.research.projects.filter((project) => project.review_status === "reviewed").length;
  const queuedCount = state.research.projects.filter((project) => project.review_status === "queued").length;
  const discoveryCount = state.research.projects.filter((project) => project.review_status === "discovered").length;
  $("#project-count").textContent = `${projects.length} shown · ${reviewedCount} reviewed / ${queuedCount} queued / ${discoveryCount} discovered`;
  const body = $("#project-body");
  body.replaceChildren();
  for (const project of projects) {
    const projectSlug = project.name.toLowerCase().replace(/[^a-z0-9]+/g, "-");
    const detailId = `project-detail-${project.review_status}-${project.rank ?? projectSlug}`;
    const row = node("tr", "primary-row");
    const rank = node("td", "rank-cell number-cell tabular", project.rank === null ? (project.review_status === "queued" ? "Q" : "—") : String(project.rank).padStart(2, "0"));
    const toggle = node("button", "detail-toggle", project.review_status === "reviewed" ? "Open assessment" : "Inspect evidence");
    toggle.type = "button";
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-controls", detailId);
    toggle.dataset.collapsedLabel = toggle.textContent;
    toggle.dataset.expandedLabel = "Close";
    const subject = node("td", "subject-cell");
    const link = node("a", "", project.name);
    link.href = project.official_url;
    link.target = "_blank";
    link.rel = "noreferrer";
    subject.append(link, node("small", "", project.category));
    const why = node("p", `project-why ${project.review_status === "reviewed" ? "" : "project-why-unreviewed"}`);
    const statusCopy = project.review_status === "queued" ? project.review_reason : "Not yet assessed; showing source facts only.";
    why.append(node("strong", "", project.review_status === "reviewed" ? "Why it matters: " : project.review_status === "queued" ? "Why queued: " : "Status: "), document.createTextNode(project.review_status === "reviewed" ? project.why_it_matters : statusCopy));
    subject.append(why, toggle);
    row.append(rank, subject, node("td", "score-cell tabular", project.opportunity_score === null ? "N/O" : String(project.opportunity_score)), node("td", "", project.action), node("td", "", project.hype_risk), node("td", "number-cell tabular", String(project.source_ids.length)), node("td", "", project.primary_layer));

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
    if (project.verification_level || project.reviewed_at) {
      const verification = node("div", "project-provenance");
      verification.append(
        node("strong", "detail-label", "Review status"),
        node("p", "", [project.verification_level, project.reviewed_at ? `completed ${formatDate(project.reviewed_at)}` : ""].filter(Boolean).join(" · ")),
      );
      if (project.review_basis?.length) {
        const basis = node("ul", "review-basis");
        for (const item of project.review_basis) basis.append(node("li", "", item));
        verification.append(basis);
      }
      panel.append(verification);
    }
    const concepts = node("div", "project-provenance");
    concepts.append(node("strong", "detail-label", "Engineering concepts"));
    const conceptLinks = node("div", "signal-theme-links");
    for (const themeId of project.theme_ids || []) {
      const theme = state.research.themes.find((item) => item.id === themeId);
      if (theme) conceptLinks.append(themeButton(theme, true));
    }
    if (!conceptLinks.children.length) conceptLinks.append(node("p", "", "Unclassified — no concept relationship assigned yet."));
    concepts.append(conceptLinks);
    panel.append(concepts);
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
    row.append(sourceIdentity(source), node("span", "", `${channelLabel(source.channel)} · ${source.source_quality || "unknown quality"}`), node("span", "tabular", `${formatNumber(source.normalized_evidence_count)} records`));
    sources.append(row);
  }
}

function populateFilters() {
  const sourceType = $("#source-type");
  const baseType = node("option", "", "All source types");
  baseType.value = "";
  sourceType.replaceChildren(baseType);
  const channels = [...new Set(state.research.sources.map((source) => source.channel))].sort((left, right) => {
    const leftIndex = sourceChannelOrder.indexOf(left);
    const rightIndex = sourceChannelOrder.indexOf(right);
    return (leftIndex < 0 ? sourceChannelOrder.length : leftIndex) - (rightIndex < 0 ? sourceChannelOrder.length : rightIndex)
      || channelLabel(left).localeCompare(channelLabel(right));
  });
  for (const channel of channels) {
    const option = node("option", "", channelLabel(channel));
    option.value = channel;
    sourceType.append(option);
  }
  if (channels.includes(state.sourceType)) sourceType.value = state.sourceType;
  else state.sourceType = "";

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
  renderOperatingModel();
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
  if (route === "operating-model" && parts[1]) state.selectedRequirement = parts[1];
  for (const view of document.querySelectorAll("[data-view]")) view.hidden = view.dataset.view !== route;
  for (const link of document.querySelectorAll("[data-route]")) link.setAttribute("aria-current", link.dataset.route === route ? "page" : "false");
  const [eyebrow, title] = routeTitles[route];
  $("#view-eyebrow").textContent = eyebrow;
  $("#view-title").textContent = title;
  if (state.research) {
    if (route === "themes") renderThemes();
    if (route === "analyses") renderAnalyses();
    if (route === "operating-model") renderOperatingModel();
  }
  window.scrollTo(0, 0);
}

function toggleDetail(button) {
  const target = document.getElementById(button.getAttribute("aria-controls"));
  if (!target) return;
  const expanded = button.getAttribute("aria-expanded") === "true";
  button.setAttribute("aria-expanded", String(!expanded));
  button.textContent = expanded ? button.dataset.collapsedLabel : button.dataset.expandedLabel;
  target.hidden = expanded;
}

function bindControls() {
  window.addEventListener("hashchange", routeFromHash);
  $("#theme-search").addEventListener("input", (event) => { state.themeSearch = event.target.value; renderThemes(); });
  $("#theme-status").addEventListener("change", (event) => { state.themeStatus = event.target.value; renderThemes(); });
  $("#project-search").addEventListener("input", (event) => { state.projectSearch = event.target.value; renderProjects(); });
  $("#project-review").addEventListener("change", (event) => { state.projectReview = event.target.value; renderProjects(); });
  $("#project-action").addEventListener("change", (event) => { state.projectAction = event.target.value; renderProjects(); });
  $("#project-source").addEventListener("change", (event) => { state.projectSource = event.target.value; renderProjects(); });
  $("#evidence-search").addEventListener("input", (event) => { state.evidenceSearch = event.target.value; renderEvidence(); });
  $("#evidence-source").addEventListener("change", (event) => { state.evidenceSource = event.target.value; renderEvidence(); });
  $("#evidence-theme").addEventListener("change", (event) => { state.evidenceTheme = event.target.value; renderEvidence(); });
  $("#source-type").addEventListener("change", (event) => { state.sourceType = event.target.value; renderOverview(); });
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
    const requirement = event.target.closest("[data-requirement-id]");
    if (requirement) {
      state.selectedRequirement = requirement.dataset.requirementId;
      history.replaceState(null, "", `#operating-model/${state.selectedRequirement}`);
      renderOperatingModel();
      $("#requirement-detail").focus({ preventScroll: true });
    }
    const toggle = event.target.closest(".detail-toggle");
    if (toggle) toggleDetail(toggle);
    const signalJump = event.target.closest("[data-signal-id]");
    if (signalJump) {
      const target = document.getElementById(`signal-${signalJump.dataset.signalId}`);
      if (target) {
        target.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
        target.focus({ preventScroll: true });
      }
    }
  });
}

async function load() {
  $("#load-failure").hidden = true;
  $("#sidebar-state").textContent = "Loading research";
  const [researchResult, alphaResult, operatingResult] = await Promise.allSettled([
    fetch("./data/research.json", { cache: "no-store" }).then((response) => {
      if (!response.ok) throw new Error(`Cross-source dataset returned ${response.status}.`);
      return response.json();
    }),
    fetch("./data/alphasignal-research.json", { cache: "no-store" }).then((response) => {
      if (!response.ok) throw new Error(`AlphaSignal detail returned ${response.status}.`);
      return response.json();
    }),
    fetch("./data/operating-model.json", { cache: "no-store" }).then((response) => {
      if (!response.ok) throw new Error(`Operating model returned ${response.status}.`);
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
  state.operatingModel = operatingResult.status === "fulfilled" ? operatingResult.value : null;
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
