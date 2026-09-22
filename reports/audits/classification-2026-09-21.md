# Classification-review audit — 2026-09-21

The audit began with 1,162 unclassified public records and 25.6% classification coverage.

## Method

A deterministic 120-record sample was drawn across all 35 public sources represented in the backlog. Each source received at least one record; the remaining sample was allocated in proportion to that source's unclassified volume. Candidate vocabulary was then checked against the complete backlog before entering the taxonomy.

The audit did not assume every collected record deserved a theme. Broad commentary, company announcements, adjacent scientific applications, duplicates, and off-topic community posts remain unresolved unless the evidence supports an existing engineering concept.

## Findings

1. **Specific technical vocabulary was missing.** Post-training, RLHF and GRPO, KV-cache and model-serving terms, open-model language, refusal calibration, MCP, VLM/VLA, and several robotics phrases mapped cleanly to existing themes.
2. **Substring matching was unsafe.** The original classifier could recognize a short acronym inside an unrelated word or silently depend on a singular term matching a plural. Classification now uses word boundaries, and plural or hyphenated variants are explicit.
3. **Generic keywords would make the radar worse.** Terms such as `agent`, `model`, `evaluation`, `robot`, and `inference` occur in records that span many unrelated categories. They were deliberately not added alone.

## Result

- 110 previously unclassified records gained one or more defensible themes.
- Classification coverage increased from 25.6% to 32.7%.
- The unresolved backlog fell from 1,162 to 1,052 records.
- 12 of the 120 sampled records were classified through the vocabulary changes; 108 remain queued for later taxonomy review or an explicit discard decision.
- No previously classified comparison record became unclassified after the final boundary and vocabulary pass.

## Boundary

This was a taxonomy-gap audit, not a full relevance judgment on all 1,162 records. The remaining backlog is kept visible rather than forced into a category. The next pass should inspect recurring unmatched clusters before creating a new theme or adding another phrase.
