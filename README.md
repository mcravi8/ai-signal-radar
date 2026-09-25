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

Seven adjudicated cases in `config/evidence-policy-calibration.yml` test the rules against real Radar evidence. Run the calibration with:

```bash
python -m pipeline.cli calibrate-evidence
```

The current calibration rates the modular agent operating stack as `emerging`; evaluation/release gates, heterogeneous model routing, shared operational context, and simulation-first physical AI development as `experimental`; and AI-native GTM and bounded workflow ownership as `narrative`. The readable audit is in [reports/calibration/evidence-policy-2026-09-22.md](reports/calibration/evidence-policy-2026-09-22.md).

## Cross-source contract

`data/public/research.json` is the frontend's primary dataset. First-party lab publications, papers, repositories, community discussions, expert social observations, essays, AlphaSignal trend aggregates, and AlphaSignal project assessments all expose the same core fields:

- source and source type;
- evidence kind and publication date;
- canonical themes and stack layers;
- support count and monthly counts;
- derivation mode and provenance.

Theme scores use recurrence, acceleration, persistence, and source breadth. Raw source concentration is reported separately: a large volume from AlphaSignal or any other single source cannot masquerade as independent corroboration. Themes without evidence have a `null` score and appear as `N/O`.

The Early Signal Tracker is a separate inference layer. Each directional hypothesis requires an evidence record to connect at least two constituent themes. A reproducible lifecycle then distinguishes weak signals, emerging directions, corroborating directions, established patterns, and fading activity from independent source-family breadth, technical-family support, persistence, and recency inside a rolling 90-day window. Movement compares the latest 14 days with the preceding 14, while every direction retains its earliest observed source and a bounded set of diverse supporting records. These states describe observed attention; they are not forecasts of adoption, market size, or technical correctness.

Each retained evidence record also has an explicit disposition: `classified` when it maps to one or more canonical themes, `classification-review` when it may contain a relevant unresolved signal, or `out-of-scope` when a reviewed high-precision rule excludes it from the thematic taxonomy. Out-of-scope records are retained with a public reason; they are not deleted. The interface reports both raw coverage across the collected corpus and in-scope coverage across records eligible for classification. Coverage remains a quality metric, not a success score.

## Signal Discovery contract

`config/discovery.yml` defines the stage before the Early Signal Tracker. It distinguishes lightly supported `spark` records from review-ready `candidate` records, then preserves explicit `approved`, `merged`, `rejected`, and `dormant` decisions. Observation fields and inferred fields are kept separate, and no automatically generated candidate is presented as a finding.

The first eligibility rules admit only public-safe evidence that is new or materially changed inside a 35-day window. Repeated records and shared events are collapsed, primary technical sources are preferred over derivative roundups, and one source or publisher can contribute at most two retained records to a proposed cluster. The cap applies inside a cluster—not to the corpus.

Step 3 is also active. `pipeline.concepts` produces an internal `data/processed/discovery-concepts.json` catalog using the existing taxonomy, disclosed architectural primitives, recurring lexical phrases, project and technology metadata, and controlled actions. Relationship edges require same-sentence co-mention and never claim causality. No external model or paid API is used, and no title, summary, or source excerpt is copied into the concept document.

Steps 4 and 5 are active in `pipeline.discovery_cluster`. Recurring anchors are joined only when their evidence overlaps, then reduced to a cross-source coherent core using repeated themes, actions, or companion concepts. The cluster is compared with disclosed Early Signal anchors and recurrent canonical themes before it can enter the review queue. Explained clusters become merge suggestions. Unexplained clusters must contain new or materially changed evidence, meet source and publisher caps, and pass an anchor-support gate. Automatically extracted phrases need three sources to become a Spark and three source families plus technical support to become a Candidate; controlled structural concepts can enter with the base contract's lower Spark threshold. The bounded result is written to `data/processed/discovery-candidates.json` and remains explicitly labelled as review leads—not findings.

Validate all three contracts with:

```bash
python -m pipeline.cli validate-discovery
```

The weekly synthesis performs clustering, novelty comparison, and mechanical Spark/Candidate classification. Human decisions are recorded in `config/weekly-review.yml` and exposed through the Discovery and Weekly Review workspaces. Automation can propose and prioritize candidates, but it cannot approve a new Early Signal direction or Operating Model requirement.

## Engineering Atlas

The Engineering workspace connects canonical concepts to reviewed AlphaSignal projects and public repository discoveries. Its boundaries are deliberate:

- **Reviewed** means a project has a written assessment and opportunity score.
- **Queued** means a classified discovery is among the next 25 candidates for review, ranked by concept breadth, independent corroboration, and recency. Identical concept combinations are capped at three candidates so one activity burst cannot monopolize the queue.
- **Discovered** means the tool or repository is retained as evidence but has not received an analyst judgment.

The Atlas also reports source freshness from the newest dated evidence seen for each source. This is an evidence-recency signal, not a claim that every collector ran successfully. True collector uptime requires a separate run ledger.

The Expert Pulse analysis turns classified Bluesky observations into bounded findings with a stated interpretation, why it matters, a workflow opportunity, caveat, and inspectable supporting posts. Social engagement is never treated as corroboration.

The Engineering Atlas publishes the latest classification audit next to the registry. The September 25 pass inspected recurring unmatched clusters, added only precise regression-tested vocabulary, and introduced source-bounded exclusions for general community material, verification-only company and job records, and publisher housekeeping. Research, repositories, expert observations, and other plausible AI signals remain in `classification-review` when neither a precise theme nor a safe exclusion applies.

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

The unified dataset currently includes AlphaSignal, arXiv, Hugging Face Daily Papers, GitHub, Hacker News, nine first-party AI lab publication streams, nine expert newsletter and practitioner streams, a curated Bluesky expert list, official YC AI-company and startup-job records, and a narrative portfolio spanning Y Combinator, Sequoia, Menlo Ventures, Greylock, and Radical Ventures. Expert social observations are labeled separately from expert interpretation, curated roundups, and first-party claims. The interface provides nine direct workspaces: Overview, Weekly Review, Operating Model, Discovery, Analyses, Themes, Engineering, Evidence, and Method.

The Weekly Review is the controlled path from observation to judgment. It considers a 36-item pool made from seven Early Signal directions, three expert findings, six operator/investor narratives, and twenty cross-source themes. Only unresolved new or materially changed candidates can enter a ten-item assessment queue. Reviewed candidates retain an explicit adjudication explaining whether they created a conditional requirement, strengthened an existing requirement, or remained outside the model. Priority allocates reviewer attention; it cannot change requirement maturity. The public artifact lives at `data/public/weekly-review.json`.
