# AI Signal Radar

AI Signal Radar is one cross-source research system for AI newsletters, papers, repositories, public essays, and technical discussion.

Every source enters the same evidence contract. The public site is organized around analyses, theme dossiers, project opportunities, and inspectable evidence—not around a privileged newsletter or a blog feed.

## What is public

- Collection and scoring code
- Public-source metadata and links
- Sanitized AlphaSignal-derived trend and project research
- Official YC and Sequoia essay feeds
- Themes, aliases, projects, claims, and evidence relationships
- Weekly reports and historical scores
- The static dashboard

## What never enters Git

- Gmail credentials, cookies, OAuth tokens, or account-specific links
- Raw MIME messages, full newsletter HTML, or private headers
- Personal email addresses
- Full copyrighted source text
- Local model caches and private notes

The exporter uses an allowlist and fails when blocked keys or sensitive-looking strings appear in public output. See [docs/privacy.md](docs/privacy.md).

## Repository map

```text
.github/workflows/    Scheduled collection, weekly synthesis, Pages deployment
config/               Sources, taxonomy, keywords, and repository searches
pipeline/             Collection, normalization, classification, scoring, export
data/private/         Local-only inputs; ignored by Git
data/manual/          Reviewed public URLs without an automated collector
data/snapshots/       Compact public-source observations
data/processed/       Normalized public-source records
data/public/          Sanitized source-specific and unified frontend contracts
reports/weekly/       Human-readable weekly briefs
site/                 Zero-dependency static frontend
scripts/              Build and safety utilities
tests/                Privacy, scoring, and build tests
schemas/              Public frontend data contracts
```

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
make test
make build
make preview
```

Open `http://localhost:8000`.

## Automation

- `collect-daily.yml` collects free public metadata from arXiv, Hugging Face, GitHub, Hacker News, YC, and Sequoia.
- `synthesize-weekly.yml` normalizes every source, classifies evidence, recalculates cross-source scores, and produces a weekly brief.
- `deploy-dashboard.yml` validates the public boundary and deploys the static site to GitHub Pages.

Gmail ingestion is intentionally local. `pipeline.collectors.email_import` accepts only a previously sanitized export.

## Cross-source contract

`data/public/research.json` is the frontend's primary dataset. Papers, repositories, community discussions, essays, AlphaSignal trend aggregates, and AlphaSignal project assessments all expose the same core fields:

- source and source type;
- evidence kind and publication date;
- canonical themes and stack layers;
- support count and monthly counts;
- derivation mode and provenance.

Theme scores use recurrence, acceleration, persistence, and source breadth. Raw source concentration is reported separately: a large volume from AlphaSignal or any other single source cannot masquerade as independent corroboration. Themes without evidence have a `null` score and appear as `N/O`.

## AlphaSignal research

The tracked `data/public/alphasignal-research.json` is a derivative, public-safe research artifact built from the private local corpus. It currently covers 129 received emails, 128 substantive issues, 901 extracted signal records, 888 unique catalog records, 15 analyzed trends, and 20 ranked projects from April 14 through September 20, 2026.

It publishes aggregate counts, analyst findings, monthly theme frequencies, the four-layer stack classification, score components, project assessments, and official project URLs. It does **not** publish raw email bodies, Gmail links, message IDs, account addresses, private headers, or the newsletter's full text.

To refresh the public derivative from a private local analysis file:

```bash
python scripts/export_alphasignal_research.py /path/to/private/alpha_analysis_data.json
python -m pipeline.cli validate-public
```

Trend score and opportunity score remain separate: the first measures persistence inside the newsletter corpus; the second measures whether a specific project appears worth testing for workflow automation. See [docs/alphasignal-methodology.md](docs/alphasignal-methodology.md).

## Current status

The unified dataset currently includes AlphaSignal, arXiv, Hugging Face Daily Papers, GitHub, Hacker News, Y Combinator essays, and Sequoia essays. The interface provides six direct workspaces: Overview, Analyses, Themes, Projects, Evidence, and Method.
