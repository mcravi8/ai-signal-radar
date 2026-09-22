# AI Signal Radar

AI Signal Radar is one cross-source research system for first-party AI labs, newsletters, papers, repositories, public essays, expert social observations, and technical discussion.

Every source enters the same evidence contract. The public site is organized around analyses, theme dossiers, an engineering atlas, and inspectable evidence—not around a privileged newsletter or a blog feed.

## What is public

- Collection and scoring code
- Public-source metadata and links
- Sanitized AlphaSignal-derived trend and project research
- Official AI lab, operator, and investor publication feeds
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
reports/calibration/  Evidence-policy calibration reports
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

- `collect-daily.yml` collects free public metadata from first-party AI labs, expert newsletters, practitioner blogs, arXiv, Hugging Face, GitHub, Hacker News, and official operator/investor feeds.
- `synthesize-weekly.yml` retrieves relevant posts from a curated Bluesky expert list and new AgentMail newsletters, reduces them to sanitized evidence, normalizes every source, recalculates cross-source scores, and produces a weekly brief.
- `deploy-dashboard.yml` validates the public boundary and deploys the static site to GitHub Pages.

Gmail ingestion remains local. Future subscribed newsletters arrive in the dedicated AgentMail inbox and are ingested weekly with a read-only API key. Raw bodies exist only in AgentMail and runner memory; only allowlisted derivative records enter Git. `pipeline.collectors.email_import` still accepts previously sanitized local exports.

The weekly job requires an `AGENTMAIL_API_KEY` repository secret with read-only inbox and message permissions. The public cursor in `data/state/agentmail.json` stores only the last processed timestamp—never mailbox or message identifiers.

## Operating-model evidence policy

`config/evidence-policy.yml` defines the formal evidence contract used to decide whether a proposed startup operating requirement is merely a `narrative`, is `experimental`, or has matured to `emerging`, `established`, or `baseline`. Each judgment reports technical reality, operational adoption, market pull, and evidence independence as `N/O`, `Low`, `Moderate`, or `Strong`. Maturity is gate-based: attention or a weighted score cannot compensate for missing operational proof.

The Operating Model workspace renders the public `data/public/operating-model.json` registry. Each requirement explains the concept, what it looks like in a startup, where it applies, its recommended posture, evidence dimensions, promotion blockers, verification gaps, and the disposition of every linked record.

Six adjudicated cases in `config/evidence-policy-calibration.yml` test the rules against real Radar evidence. Run the calibration with:

```bash
python -m pipeline.cli calibrate-evidence
```

The current calibration rates the modular agent operating stack as `emerging`; evaluation/release gates, heterogeneous model routing, and shared operational context as `experimental`; and AI-native GTM and bounded workflow ownership as `narrative`. The readable audit is in [reports/calibration/evidence-policy-2026-09-22.md](reports/calibration/evidence-policy-2026-09-22.md).

## Cross-source contract

`data/public/research.json` is the frontend's primary dataset. First-party lab publications, papers, repositories, community discussions, expert social observations, essays, AlphaSignal trend aggregates, and AlphaSignal project assessments all expose the same core fields:

- source and source type;
- evidence kind and publication date;
- canonical themes and stack layers;
- support count and monthly counts;
- derivation mode and provenance.

Theme scores use recurrence, acceleration, persistence, and source breadth. Raw source concentration is reported separately: a large volume from AlphaSignal or any other single source cannot masquerade as independent corroboration. Themes without evidence have a `null` score and appear as `N/O`.

The Early Signal Tracker is a separate inference layer. Each directional hypothesis requires an evidence record to connect at least two constituent themes. A reproducible lifecycle then distinguishes weak signals, emerging directions, corroborating directions, established patterns, and fading activity from independent source-family breadth, technical-family support, persistence, and recency inside a rolling 90-day window. Movement compares the latest 14 days with the preceding 14, while every direction retains its earliest observed source and a bounded set of diverse supporting records. These states describe observed attention; they are not forecasts of adoption, market size, or technical correctness.

Each retained evidence record also has an explicit disposition: `classified` when it maps to one or more canonical themes, or `classification-review` when it remains in the visible taxonomy backlog. This prevents unclassified records from silently disappearing. Classification coverage is reported as a quality metric, not a success score.

## Engineering Atlas

The Engineering workspace connects canonical concepts to reviewed AlphaSignal projects and public repository discoveries. Its boundaries are deliberate:

- **Reviewed** means a project has a written assessment and opportunity score.
- **Queued** means a classified discovery is among the next 25 candidates for review, ranked by concept breadth, independent corroboration, and recency. Identical concept combinations are capped at three candidates so one activity burst cannot monopolize the queue.
- **Discovered** means the tool or repository is retained as evidence but has not received an analyst judgment.

The Atlas also reports source freshness from the newest dated evidence seen for each source. This is an evidence-recency signal, not a claim that every collector ran successfully. True collector uptime requires a separate run ledger.

The Expert Pulse analysis turns classified Bluesky observations into bounded findings with a stated interpretation, why it matters, a workflow opportunity, caveat, and inspectable supporting posts. Social engagement is never treated as corroboration.

The Engineering Atlas publishes the latest classification audit next to the registry. The September 21 audit sampled 120 records across 35 sources, added precise missing vocabulary, replaced substring matching with term boundaries, and moved 110 records from `classification-review` into supported themes. Unresolved records remain visible rather than being assigned a convenient category.

## AlphaSignal research

The tracked `data/public/alphasignal-research.json` is a derivative, public-safe research artifact built from the private local corpus. It currently covers 130 received emails, 129 substantive issues, 912 extracted signal records, 899 unique catalog records, 15 analyzed trends, and 20 ranked projects from April 14 through September 21, 2026.

It publishes aggregate counts, analyst findings, monthly theme frequencies, the four-layer stack classification, score components, project assessments, and official project URLs. It does **not** publish raw email bodies, Gmail links, message IDs, account addresses, private headers, or the newsletter's full text.

To refresh the public derivative from a private local analysis file:

```bash
python scripts/export_alphasignal_research.py /path/to/private/alpha_analysis_data.json
python -m pipeline.cli validate-public
```

Trend score and opportunity score remain separate: the first measures persistence inside the newsletter corpus; the second measures whether a specific project appears worth testing for workflow automation. See [docs/alphasignal-methodology.md](docs/alphasignal-methodology.md).

## Current status

The unified dataset currently includes AlphaSignal, arXiv, Hugging Face Daily Papers, GitHub, Hacker News, nine first-party AI lab publication streams, nine expert newsletter and practitioner streams, a curated Bluesky expert list, and an official narrative portfolio spanning Y Combinator, Sequoia, Menlo Ventures, Greylock, and Radical Ventures. Expert social observations are labeled separately from expert interpretation, curated roundups, and first-party claims. The interface provides seven direct workspaces: Overview, Operating Model, Analyses, Themes, Engineering, Evidence, and Method.
