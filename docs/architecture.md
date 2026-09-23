# Architecture

## Data flow

```text
official public collectors + weekly expert/social + newsletter ingestion
                         ↓
           common normalized evidence contract
                         ↓
        themes, projects, provenance, and source mix
                         ↓
 cross-source trend score + separate opportunity score
                         ↓
 candidate selection + formal evidence-policy review boundary
                         ↓
 unified research, weekly review, operating model + briefs
                         ↓
                  static GitHub Pages site
```

## Internal entities

- `Source`: publisher, author, channel, expertise, quality, and commercial bias.
- `SourceItem`: one public paper, repository, essay, post, job, or transcript.
- `Claim`: a concise proposition attributed to a source item.
- `Project`: a company, tool, model, paper, repository, or infrastructure project.
- `Theme`: a canonical abstraction with aliases, definition, layer, and maturity.
- `Evidence`: a typed relationship from a source item to a theme, claim, or project.
- `ScoreSnapshot`: dated, reproducible score components.

JSONL is used for transparent early-stage storage. The contracts are intentionally compatible with a later move to SQLite or DuckDB.

AlphaSignal is normalized at the public boundary as aggregate trend evidence, project assessments, and sanitized records from new AgentMail issues. Its historical private catalog remains local. Aggregate records and direct public records share source, date, theme, stack-layer, support, and provenance fields, while `evidence_kind` and `provenance.mode` preserve their differences.

## Cross-source scoring

- Recurrence uses log-normalized support per source so one large corpus cannot dominate linearly.
- Acceleration compares the most recent two months with the preceding two months.
- Persistence counts active months in a six-month window.
- Breadth rewards contributing source channels.
- Source concentration is reported outside the score and changes the maturity label when one source supplies at least 75% of support.
- Unobserved themes receive no score rather than a zero presented as evidence.

## Abstraction promotion rule

A candidate theme is promoted when it has either:

1. evidence from at least three independent credible sources; or
2. one strong thesis source and at least three concrete projects.

Promotion is never based on engagement alone.

## Signal Discovery boundary

Signal Discovery is the pre-analysis layer for patterns that are not yet represented by a canonical theme or Early Signal direction. Its first contract is defined in `config/discovery.yml` and enforced by `pipeline.discovery`.

The contract separates machine-observed fields—evidence, sources, families, concepts, dates, and counts—from inferred fields such as a provisional title, hypothesis, novelty explanation, alternatives, and confirmation tests. A discovery record is always a lead rather than a finding. Its lifecycle is `spark → candidate → approved`, with explicit `merged`, `rejected`, and reversible `dormant` dispositions. Only a human `track` decision can create an approved direction, and approval does not assign an Early Signal lifecycle state.

The eligibility window is 35 days. Inputs must be new or materially changed, attributable to an enabled source, public-safe, dated, and non-empty. Exact records and shared events are collapsed before discovery. Direct papers and repositories are preferred over derivative roundups when the same event appears more than once. Per-candidate contribution caps allow at most two records from one source or publisher; these caps never remove records from the global corpus.

A Spark requires either two records from two sources or one technical seed that receives a manual novelty review. A Candidate requires at least three independent events from three sources and two source families, with no publisher supplying more than half of the retained evidence. These are admission rules for review, not evidence that the proposed hypothesis is true.

Eligible records are converted into an internal concept catalog by the deterministic rules in `config/discovery-concepts.yml`. Extraction combines canonical theme vocabulary, a small disclosed set of architectural primitives, recurring two-to-four-token phrases, project and technology metadata, and controlled action verbs. A relationship is retained only when two controlled concepts or entities and one action occur in the same sentence. The catalog stores no source excerpt and describes co-mention rather than causality. It is written to `data/processed/discovery-concepts.json`; unchanged documents remain available for corpus context while `changed_document_ids` bounds the next clustering step.

`config/discovery-clustering.yml` and `pipeline.discovery_cluster` implement the next two stages. Anchor overlap proposes clusters, while a recurring-context graph removes records that merely reuse the same phrase with a different meaning. Known-direction comparison uses only explicit anchor IDs, disclosed exact phrases, or at least two recurrent constituent themes; one-off theme unions cannot trigger a merge. Dominant canonical-theme coverage is evaluated separately. Only coherent, materially changed, unexplained clusters can produce `spark` or `candidate` records in `data/processed/discovery-candidates.json`. Product/version phrases, generic language, source concentration, and entity-only clusters are bounded before state assignment. Every retained lead includes alternatives, confirmation tests, invalidation tests, evidence IDs, and a pending human-review status.

## Compute boundary

GitHub-hosted runners collect public metadata, first-party AI lab publications, and official essay feeds, then retrieve subscribed newsletters from a dedicated AgentMail inbox once per week. Newsletter bodies are reduced to allowlisted derivative records in memory and are never committed or uploaded as artifacts. Gmail access and optional local-model enrichment stay on the owner's machine.

The weekly runner also reads public author feeds from Bluesky's unauthenticated AppView API. Accounts are pinned by DID so a changed or reused handle cannot silently redirect collection. Replies, repost-only activity, off-topic posts, and engagement counters are excluded. Simon Willison and swyx reuse their existing publisher IDs so cross-posting across social, blog, and newsletter channels cannot inflate source breadth.

The same runner collects two official YC public surfaces without authentication: the AI company directory and recent startup jobs. Company formation and hiring intent are supporting verification signals only. GitHub popularity, funding announcements, case studies, and architecture reports are likewise kept inside their stated proof boundaries.

## Weekly decision path

The current Weekly Review candidate pool remains separate from Signal Discovery. It considers approved analytical surfaces only; Sparks and unreviewed Candidates cannot become Operating Model evidence. A transparent priority score ranks material changes using momentum, source breadth, technical support, new evidence, and Operating Model relevance. At most ten candidates enter the weekly assessment queue.

The score never changes requirement maturity. Promotion or demotion requires an explicit edit to the calibrated case record followed by the formal evidence-policy gates. Same-day synthesis reruns preserve the already-published review when no evidence changed, avoiding an empty or unstable report caused by deployment regeneration.
