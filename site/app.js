const state = {
  data: null,
  filter: "",
};

const $ = (selector) => document.querySelector(selector);

function formatDate(value) {
  if (!value) return "Initial watchlist";
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function label(value) {
  return String(value || "")
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function renderStatus(meta) {
  const status = $("#status-row");
  status.replaceChildren();
  const facts = [
    ["Snapshot", meta.status || "unknown"],
    ["Sources", meta.source_count ?? "N/O"],
    ["Evidence items", meta.evidence_count ?? "N/O"],
  ];
  for (const [name, value] of facts) {
    const item = document.createElement("span");
    item.className = "status-pill";
    item.innerHTML = `<small>${name}</small><strong>${value}</strong>`;
    status.append(item);
  }
  for (const warning of meta.warnings || []) {
    const item = document.createElement("p");
    item.className = "warning";
    item.textContent = warning;
    status.append(item);
  }
}

function renderThemes() {
  const container = $("#theme-list");
  const query = state.filter.trim().toLowerCase();
  const themes = (state.data?.themes || []).filter((theme) => {
    const searchable = [theme.name, theme.definition, ...(theme.aliases || [])].join(" ").toLowerCase();
    return !query || searchable.includes(query);
  });
  container.replaceChildren();

  if (!themes.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.innerHTML = `<strong>No matching categories</strong><p>Try another term or clear the filter. Your current query is preserved.</p>`;
    container.append(empty);
    return;
  }

  for (const theme of themes) {
    const card = $("#theme-template").content.cloneNode(true);
    card.querySelector("h3").textContent = theme.name;
    card.querySelector(".definition").textContent = theme.definition;
    card.querySelector(".aliases").textContent = `Also tracked as: ${(theme.aliases || []).join(" · ") || "No aliases yet"}`;
    card.querySelector(".maturity").textContent = label(theme.maturity);
    card.querySelector(".layer").textContent = label(theme.primary_layer);
    card.querySelector(".theme-score strong").textContent = theme.score?.total ?? "N/O";
    card.querySelector(".theme-evidence").textContent = `${theme.evidence_count || 0} evidence items · ${(theme.source_types || []).length || 0} source types`;
    container.append(card);
  }
}

function renderEvidence(items) {
  const container = $("#evidence-list");
  container.replaceChildren();
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state evidence-empty";
    empty.innerHTML = `<strong>No evidence collected yet</strong><p>The first daily run will add papers, repositories, and discussions here. Seed themes remain clearly marked as unobserved.</p>`;
    container.append(empty);
    return;
  }

  const list = document.createElement("ol");
  list.className = "evidence-list";
  for (const item of items.slice(0, 30)) {
    const row = document.createElement("li");
    const title = document.createElement("a");
    title.href = item.url;
    title.target = "_blank";
    title.rel = "noreferrer";
    title.textContent = item.title;
    const meta = document.createElement("span");
    meta.textContent = `${label(item.source_type)} · ${formatDate(item.published_at)}`;
    row.append(title, meta);
    list.append(row);
  }
  container.append(list);
}

function render(data) {
  state.data = data;
  $("#weekly-title").textContent = data.weekly?.title || "Weekly AI signal brief";
  $("#weekly-summary").textContent = data.weekly?.summary || "No synthesis is available yet.";
  $("#edition").textContent = formatDate(data.meta?.generated_at);
  renderStatus(data.meta || {});
  renderThemes();
  renderEvidence(data.evidence || []);
}

async function load() {
  try {
    const response = await fetch("./data/dashboard.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`Snapshot request returned ${response.status}`);
    render(await response.json());
  } catch (error) {
    $("#weekly-title").textContent = "The latest snapshot could not be opened";
    $("#weekly-summary").textContent = "The dashboard kept its structure, but the data file is unavailable. Rebuild the site or try again.";
    const status = $("#status-row");
    status.innerHTML = `<button class="retry" type="button">Retry loading</button><span class="error-detail"></span>`;
    status.querySelector(".error-detail").textContent = error.message;
    status.querySelector(".retry").addEventListener("click", load);
  }
}

$("#theme-filter").addEventListener("input", (event) => {
  state.filter = event.target.value;
  renderThemes();
});

load();
