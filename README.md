# AI Signal Radar

AI Signal Radar turns scattered AI news, research, repositories, and operator narratives into evidence-linked category abstractions.

The public site is designed for two readers: a technically curious person who wants a concise weekly brief, and an expert who wants to inspect the underlying claims, projects, sources, and scoring methodology.

## What is public

- Collection and scoring code
- Public-source metadata and links
- Sanitized AlphaSignal-derived records
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
data/public/          Sanitized frontend contract
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

- `collect-daily.yml` collects free public metadata from arXiv, Hugging Face, GitHub, and Hacker News.
- `synthesize-weekly.yml` classifies evidence, recalculates scores, and produces a weekly brief.
- `deploy-dashboard.yml` validates the public boundary and deploys the static site to GitHub Pages.

Gmail ingestion is intentionally local. `pipeline.collectors.email_import` accepts only a previously sanitized export.

## Current status

This scaffold establishes the contracts, privacy boundary, initial taxonomy, working dashboard, and automation entry points. The initial dashboard deliberately marks unobserved evidence as `N/O`; collectors add real observations over time.
