# Architecture

## Data flow

```text
free public collectors + local sanitized email import
                         ↓
                 normalized source items
                         ↓
        claims, projects, aliases, and theme evidence
                         ↓
       trend / opportunity / confidence / hype signals
                         ↓
             allowlisted public dashboard JSON
                         ↓
                  static GitHub Pages site
```

## Internal entities

- `Source`: publisher, author, channel, expertise, quality, and commercial bias.
- `SourceItem`: one email, paper, repository, essay, post, job, or transcript.
- `Claim`: a concise proposition attributed to a source item.
- `Project`: a company, tool, model, paper, repository, or infrastructure project.
- `Theme`: a canonical abstraction with aliases, definition, layer, and maturity.
- `Evidence`: a typed relationship from a source item to a theme, claim, or project.
- `ScoreSnapshot`: dated, reproducible score components.

JSONL is used for transparent early-stage storage. The contracts are intentionally compatible with a later move to SQLite or DuckDB.

## Abstraction promotion rule

A candidate theme is promoted when it has either:

1. evidence from at least three independent credible sources; or
2. one strong thesis source and at least three concrete projects.

Promotion is never based on engagement alone.

## Compute boundary

GitHub-hosted runners collect public metadata, compute deterministic scores, build the site, and publish sanitized results. Mailbox access and optional local-model enrichment stay on the owner's machine.
