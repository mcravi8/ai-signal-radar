# AlphaSignal research methodology

## Corpus

The analysis covers 129 emails received between April 14 and September 20, 2026. One email was a verification message, leaving 128 substantive issues. Extraction produced 901 signal records; exact deduplication produced 888 unique catalog records. Sixty-two sponsored records are retained in corpus metadata but excluded from trend interpretation and project ranking.

This newsletter corpus is a discovery source, not a complete measurement of the AI market. Counts measure AlphaSignal editorial attention. They do not establish adoption, quality, revenue, or technical superiority.

## Four-layer stack

Each unique catalog record has one primary layer:

1. **Models & capabilities** — foundation and specialized models, multimodal capabilities, and local inference. 213 records.
2. **Harness & orchestration** — agent loops, state, memory, routing, sandboxes, and execution control. 299 records.
3. **Tools, skills & integrations** — reusable capabilities, data access, application connectors, and workflow components. 185 records.
4. **Assurance layer** — evaluation, validation, security, governance, and observability. 191 records.

Trend and project records may also identify a secondary layer when the signal crosses stack boundaries.

## Trend score

The trend score measures whether a capability is a durable pattern in the AlphaSignal corpus. It is the sum of four 25-point components:

- **Recurrence:** log-scaled number of AlphaSignal mentions.
- **Acceleration:** August–September monthly rate compared with April–July.
- **Persistence:** number of active months in the six-month observation window.
- **Breadth:** log-scaled count of distinct lead entities among non-sponsored records.

Scores of 80–100 are labeled structural, 65–79 strong, 50–64 emerging, and below 50 niche or uncertain. Theme matching is keyword-based and overlapping: one catalog record can inform more than one trend.

## Opportunity score

The opportunity score is independent from the trend score. It asks whether a specific project appears worth testing for workflow automation. Analysts rate six components from one to five:

| Component | Weight |
| --- | ---: |
| Leverage | 25% |
| Composability | 20% |
| Maturity | 15% |
| Cost and accessibility | 15% |
| Ease of testing | 15% |
| Relevance | 10% |

Hype risk is reported separately so it cannot be hidden inside a composite. Opportunity scores are provisional because the operating context is intentionally broad. Official project URLs are retained for verification and direct inspection.

## Interpretation limits

- Newsletter claims are treated as leads rather than independently verified facts.
- Exact deduplication does not merge semantically similar descriptions.
- Keyword themes can overlap and can miss unusual wording.
- Project maturity and workflow value can change after the analysis date.
- Public-source collection is displayed separately and does not retroactively alter reviewed AlphaSignal scores.

## Publication boundary

Only derivative analysis is published. Raw email bodies, full newsletter HTML, Gmail links, message identifiers, personal addresses, private headers, credentials, cookies, and OAuth tokens never enter Git. The public exporter is checked by the repository's privacy validator before deployment.
