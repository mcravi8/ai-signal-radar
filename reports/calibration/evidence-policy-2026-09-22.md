# Evidence policy calibration — September 22, 2026

## Purpose

This calibration tests the evidence policy for the AI-Native Startup Operating Model against six real Radar hypotheses. The policy asks a stricter question than the Early Signal Tracker: not merely whether a direction is visible, but whether the evidence is strong enough to treat it as a startup operating requirement.

No weighted score can bypass a failed maturity gate. Repeated coverage of one event is deduplicated, source concentration limits independence and confidence, and attention alone cannot prove technical reality or operational adoption.

## Results

| Requirement | Technical reality | Operational adoption | Market pull | Independence | Concentration | Confidence | Maturity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Evaluation and release gates | Strong | Low | Low | Low | High | Moderate | **Experimental** |
| Heterogeneous model routing | Moderate | Low | Low | Moderate | Moderate | Moderate | **Experimental** |
| AI-native GTM systems | N/O | Low | Low | Low | High | Low | **Narrative** |
| Modular agent operating stack | Strong | Moderate | Moderate | Moderate | Moderate | Moderate | **Emerging** |
| Shared operational context | Strong | Low | Low | Moderate | Moderate | Moderate | **Experimental** |
| Bounded workflow ownership | Low | Low | Moderate | Low | Moderate | Low | **Narrative** |

Only the modular agent operating stack reaches `emerging`. It is the sole case with qualifying technical evidence, two production deployments, sufficient independence, and an explicit counterevidence review. No case reaches `established` or `baseline`.

## 1. Evaluation and release gates

**Requirement:** Consequential AI workflows require evaluation and release gates.

**Result:** `experimental`

Three deduplicated technical events qualify: BLINDSPOT counts once despite having both a paper and repository, while Chronicle and EnterpriseVal are separate implementations. This makes the requirement technically real. The surrounding AlphaSignal, Hugging Face, and newsletter records provide context or discovery, not extra proof.

Promotion to `emerging` is blocked because operational adoption and evidence independence are low, and counterevidence has not been reviewed. The current corpus does not yet show independent production deployments with attributable intervention, rollback, incident, or business-outcome data.

**Next verification:** find production accounts with measured outcomes and examine cases where conventional testing and access controls were sufficient.

## 2. Heterogeneous model routing

**Requirement:** AI systems should route work across heterogeneous models and inference paths.

**Result:** `experimental`

Edge0 and SpecQuant provide two independent technical demonstrations. The Jev ecosystem index, AlphaSignal synthesis, Interconnects, Bluesky, and Hacker News show adjacent activity or help discover the direction, but do not establish production adoption.

One arXiv record—*Scalable Packet Tracking on FPGAs* (`arxiv:2609.21774v1`)—was explicitly excluded. It matched infrastructure language but does not concern model routing or heterogeneous inference selection. The exclusion is retained in the calibration data so a classifier false positive cannot inflate maturity.

Promotion to `emerging` is blocked by low operational adoption and the absence of a counterevidence review.

**Next verification:** compare production quality, latency, failure rate, and cost per accepted outcome, including the maintenance and fallback cost introduced by routing.

## 3. AI-native GTM systems

**Requirement:** Startups should operate closed-loop AI-native GTM systems that sense, decide, and act across revenue workflows.

**Result:** `narrative`

AirOps and Netic show company formation and investment activity, while AlphaSignal supplies related enterprise-AI context. The two primary observations, however, come from the same investor-publisher, and the corpus contains neither a qualifying technical implementation nor independent operating outcomes.

Promotion to `experimental` is blocked because technical reality is not observed and no qualifying technical artifact exists.

**Next verification:** obtain customer or operator evidence with attributable pipeline, revenue, or cycle-time outcomes; inspect independent technical descriptions; and add publishers unrelated to the investment announcements.

## 4. Modular agent operating stack

**Requirement:** AI systems should separate models, orchestration, reusable skills, execution environments, and assurance controls into replaceable operating layers.

**Result:** `emerging`

SoL-Pi, the harness-value experiments, and dscode provide independent technical artifacts. Wood Mackenzie's shared platform and Benchling's isolated agent execution provide two production deployments. The Hugging Face listing of SoL-Pi is deduplicated from the paper rather than counted as another event.

The review also considered the public critique that MCP and similar abstraction layers can add unnecessary complexity when a fully trusted terminal agent can call APIs directly. This prevents “modular” from being treated as universally superior: the evidence currently supports it for controlled, multi-workflow systems rather than every agent application.

Promotion to `established` is blocked because operational adoption and evidence independence are moderate rather than strong. Both detailed deployment accounts were published through AWS, creating a remaining concentration risk.

**Next verification:** find production accounts outside one infrastructure vendor, compare switching benefits with orchestration overhead, and test whether interfaces remain portable as models and runtimes change.

## 5. Shared operational context

**Requirement:** AI systems operating across organizational data should use a shared semantic and operational context layer instead of rebuilding retrieval and schemas for every workflow.

**Result:** `experimental`

RAFT, EvoOntology, Graphiti, and Cognee make the pattern technically credible across stateful retrieval, evolving ontologies, real-time knowledge graphs, and persistent graph memory. GraphRAG and WrenAI supply supporting context but do not independently prove cross-workflow operational adoption.

The software-archival knowledge-graph paper (`arxiv:2609.21667v1`) was excluded. It was selected through overlapping vocabulary but does not demonstrate an operational context layer for AI workflows.

Promotion to `emerging` is blocked because production adoption remains low and counterevidence has not been reviewed.

**Next verification:** find organizations sharing one governed context layer across several production agents, measure maintenance and permission correctness against workflow-specific RAG, and examine cases where simpler retrieval remains sufficient.

## 6. Bounded workflow ownership

**Requirement:** AI products should own bounded workflows with explicit completion states, exception routing, and outcome metrics.

**Result:** `narrative`

Sable and Probook show company formation and investment around AI systems that perform work, while the open-source AI Employees repository provides one implementation. OpenAI and DeepMind computer-use releases are discovery signals: they demonstrate enabling capability, not reliable ownership of a completed business workflow.

The Greylock Oak record was excluded because identity governance does not establish bounded end-to-end workflow ownership. The remaining evidence does not demonstrate reliable completion, exception handling, systems-of-record updates, or attributable business outcomes.

Promotion to `experimental` is blocked because technical reality remains low despite moderate market pull.

**Next verification:** collect customer-controlled completion, intervention, error-cost, and business-outcome measurements; inspect implementations with explicit terminal states and exception routing; and study workflows where assistance remains safer or more economical.

## Calibration verdict

The policy behaved as intended in all six cases:

- it separated technical feasibility from operational necessity;
- it prevented newsletters, social posts, and investor attention from becoming proof;
- it deduplicated a paper and repository describing one event;
- it exposed and excluded a classifier false positive;
- it required an explicit counterevidence record before accepting a reviewed-counterevidence flag;
- it allowed one requirement to advance only after production evidence appeared;
- it made source concentration visible instead of hiding it inside a composite score.

The Early Signal Tracker and operating-model maturity therefore remain complementary. Tracker states describe the breadth, persistence, and movement of observed attention. Requirement maturity describes how much technical, operational, market, and independent evidence supports acting on a claim. A direction can be corroborating in the tracker while remaining experimental as an operating requirement.

The machine-readable policy is in `config/evidence-policy.yml`; the adjudicated cases are in `config/evidence-policy-calibration.yml`. Run `python -m pipeline.cli calibrate-evidence` to reproduce these results.
