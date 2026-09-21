# Architecture

## Data flow

```text
official public collectors + weekly sanitized newsletter ingestion
                         ↓
           common normalized evidence contract
                         ↓
        themes, projects, provenance, and source mix
                         ↓
 cross-source trend score + separate opportunity score
                         ↓
       allowlisted unified research JSON + weekly brief
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

## Compute boundary

GitHub-hosted runners collect public metadata, first-party AI lab publications, and official essay feeds, then retrieve subscribed newsletters from a dedicated AgentMail inbox once per week. Newsletter bodies are reduced to allowlisted derivative records in memory and are never committed or uploaded as artifacts. Gmail access and optional local-model enrichment stay on the owner's machine.
