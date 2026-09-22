# Evidence policy calibration — September 22, 2026

## Purpose

This calibration tests the evidence policy for the AI-Native Startup Operating Model against three real Radar hypotheses. The policy asks a stricter question than the Early Signal Tracker: not merely whether a direction is visible, but whether the evidence is strong enough to treat it as a startup operating requirement.

No weighted score can bypass a failed maturity gate. Repeated coverage of one event is deduplicated, source concentration limits independence and confidence, and attention alone cannot prove technical reality or operational adoption.

## Results

| Requirement | Technical reality | Operational adoption | Market pull | Independence | Concentration | Confidence | Maturity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Evaluation and release gates | Strong | Low | Low | Low | High | Moderate | **Experimental** |
| Heterogeneous model routing | Moderate | Low | Low | Moderate | Moderate | Moderate | **Experimental** |
| AI-native GTM systems | N/O | Low | Low | Low | High | Low | **Narrative** |

No case reaches `emerging`. That is not a failure of the source system: it identifies the specific evidence still missing before the Radar should recommend a practice as an operating requirement.

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

## Calibration verdict

The policy behaved as intended in all three cases:

- it separated technical feasibility from operational necessity;
- it prevented newsletters, social posts, and investor attention from becoming proof;
- it deduplicated a paper and repository describing one event;
- it exposed and excluded a classifier false positive;
- it made source concentration visible instead of hiding it inside a composite score.

The Early Signal Tracker and operating-model maturity therefore remain complementary. Tracker states describe the breadth, persistence, and movement of observed attention. Requirement maturity describes how much technical, operational, market, and independent evidence supports acting on a claim. A direction can be corroborating in the tracker while remaining experimental as an operating requirement.

The machine-readable policy is in `config/evidence-policy.yml`; the adjudicated cases are in `config/evidence-policy-calibration.yml`. Run `python -m pipeline.cli calibrate-evidence` to reproduce these results.
