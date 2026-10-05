# Weekly Operating Model Review — 2026-10-05

17 candidate decisions are recorded; 0 candidates remain in the bounded assessment queue.

> Candidate priority controls analyst attention only. It cannot create, promote, or demote an Operating Model requirement.

## Adjudicated candidates

| Candidate | Outcome | Linked requirement | Decision |
| --- | --- | --- | --- |
| Agent harnesses | covered-by-existing-requirement | Modular agent operating stack | Do not create a duplicate requirement. |
| ↳ Evidence audit | complete | 98 records / 0 links | New first-party examples show multi-agent migration, commerce, memory, tracing, and evaluation workflows, while research exposes global-coherence and adversarial coordination failure modes. Most operating examples still come from infrastructure vendors, and the simpler single-agent baseline remains material counterevidence. This strengthens the existing modular-stack case without clearing its promotion gates. |
| Open, local & efficient inference | covered-by-existing-requirements | Heterogeneous model routing, Governed proprietary data boundary | Treat open and local inference as an execution option, not a universal standalone requirement. |
| ↳ Evidence audit | complete | 125 records / 0 links | Small-model tuning, GGUF and Vulkan runtimes, MoE efficiency, open-weight supply, and sovereign deployment options materially strengthen technical feasibility. The corpus still lacks independent production comparisons of accepted-output quality, latency, maintenance, fallback, and hardware cost. Local inference remains an option chosen by routing and data-boundary needs, not a default architecture. |
| Robotics & embodied AI | conditional-requirement-revalidated | Simulation-first physical AI development | Keep the physical-AI requirement conditional and at experimental maturity. |
| ↳ Evidence audit | complete | 55 records / 0 links | The rising corpus adds geometry-aware world-action models, recursive manipulation, multi-robot coordination, and simulation tooling across sixteen sources. It confirms technical momentum but still lacks independent production comparisons of sim-to-real failure rates, intervention burden, and total validation cost. The requirement stays experimental and applies only to systems acting in the physical world. |
| Skills, protocols & integrations | covered-by-existing-requirement | Modular agent operating stack | Do not create a separate requirement for skills, protocols, and integrations. |
| ↳ Evidence audit | complete | 131 records / 0 links | New skills, MCP/A2A servers, authorization tests, compliance patterns, and usage metering show that the interface layer is becoming more concrete. Prompt-injection and fail-open evidence reinforces the need for constrained permissions and evaluation. This is still one layer of the modular stack, not a second operating requirement. |
| Training, evaluation & self-improvement | covered-by-existing-requirement | Evaluation and release gates | Merge the operating conclusion into evaluation and release gates; do not require every startup to train or self-improve models. |
| ↳ Evidence audit | complete | 363 records / 0 links | The largest volume increase is dominated by benchmarks, post-training methods, synthetic data, reward design, and research papers. It proves active technical work, not that every startup should train or recursively improve a model. The general obligation remains representative evaluation and controlled release of consequential outputs and system changes. |
| Multimodal generation & 3D | capability-domain-not-general-requirement | None | Treat multimodal generation and 3D as a capability domain, not a general startup operating requirement. |
| ↳ Evidence audit | complete | 51 records / 0 links | Eleven source families and thirty technical records establish broad capability progress, but the evidence spans unrelated product domains and benchmarks. It does not establish a common operating practice, measurable cost of absence, or production control that every AI startup should implement. |
| Validation is becoming the release gate for AI-generated work | linked-requirement-revalidated | Evaluation and release gates | Keep evaluation and release gates at experimental maturity while the direction is accelerating. |
| ↳ Evidence audit | complete | 8 records / 0 links | Seven sources create useful breadth, but only a subset directly supports validation as a release decision. The case still lacks independent deployments with intervention, rollback, escaped-defect, or incident metrics. The existing requirement is revalidated without a maturity change, and the weaker matches remain discovery context only. |
| Coding agents & developer tooling | domain-signal-not-separate-requirement | Evaluation and release gates, Bounded workflow ownership | Treat coding agents as an application domain, not a standalone operating requirement. |
| ↳ Evidence audit | complete | 168 records / 0 links | The new records show broader coding-agent adoption, session orchestration, sandboxing, skills, and benchmark activity. They also surface budget caps, uncertain output quality, and the need for independent review. Coding agents remain an application domain; the reusable obligations are release gates and bounded workflow ownership. |
| Governed proprietary-data boundaries | linked-requirement-revalidated | Governed proprietary data boundary | Use the new canonical theme to support the existing governed proprietary-data requirement. |
| ↳ Evidence audit | complete | 20 records / 0 links | Policy-compliant federated learning, confidential inference, zero-knowledge oversight, and encrypted computation expand the technical design space. They do not add the missing customer-controlled audits or independent production comparisons of privacy, quality, latency, portability, and cost. The governed boundary remains experimental. |
| Frontier inference infrastructure | infrastructure-signal-not-general-requirement | Heterogeneous model routing | Do not require ordinary startups to build frontier inference infrastructure. |
| ↳ Evidence audit | complete | 61 records / 0 links | Multi-device serving, throughput optimization, offloaded robotics inference, local runtimes, and confidential computing deepen the supplier-side capability signal. The sample also contains several adjacent or noisy matches, and it still does not show that an application startup should own a frontier cluster. The reusable requirement remains routing, capacity, latency, cost, and fallback control. |
| Voice & audio interfaces | modality-signal-not-general-requirement | Evaluation and release gates, Bounded workflow ownership | Treat voice as a conditional interface and workflow domain, not a general startup operating requirement. |
| ↳ Evidence audit | complete | 36 records / 0 links | Smaller speech models, multilingual TTS, cloning, full-duplex systems, and managed deployment paths strengthen capability and accessibility evidence. Adoption remains highly workflow-dependent, while impersonation, consent, recognition, and latency risks require domain-specific controls. Voice is not a universal startup requirement. |
| Proprietary enterprise data is moving behind a governed model boundary | conditional-requirement-added | Governed proprietary data boundary | Add an experimental requirement for startups handling proprietary, regulated, or customer-confidential data. |
| ↳ Evidence audit | complete | 8 records / 7 links | Benchling supplies one detailed tenant-isolation and exfiltration architecture; federated and trusted-computation systems make the pattern technically credible. Provider announcements show demand but do not verify contractual guarantees, while channel-level privacy leakage remains an unresolved counter-signal. The evidence clears experimental, not emerging, maturity. |
| Evaluation is moving from a final benchmark into the system-design loop | source-analysis-covered-by-existing-requirement | Evaluation and release gates | Use the expert pattern as directional context for evaluation and release gates, not as a separate requirement. |
| ↳ Evidence audit | complete | 5 records / 0 links | Five experts provide independent narrative breadth, but social observations do not verify deployment or effectiveness. The finding is retained as directional context; technical support comes from the calibrated benchmark, authorization, abstention, and regression-testing records linked to the existing requirement. |
| Attention is shifting from agent demos to the operating layer around them | source-analysis-covered-by-existing-requirements | Modular agent operating stack, Evaluation and release gates | Use the expert pattern as directional context for the modular stack and release gates. |
| ↳ Evidence audit | complete | 5 records / 0 links | Five experts independently emphasize the operating layer around agents. Technical and production evidence must still come from the linked requirements' underlying records, so no duplicate requirement or maturity promotion is warranted. |
| Simulation is becoming the development environment for physical AI | linked-requirement-revalidated | Simulation-first physical AI development | Keep simulation-first development as an experimental, physical-AI-only requirement. |
| ↳ Evidence audit | complete | 6 records / 0 links | Added source breadth confirms that simulation is an active development layer, while transfer quality remains the gating uncertainty. No universal software-startup requirement follows from this domain-specific evidence. |
| The agent stack is separating into modular operating layers | source-analysis-already-calibrated | Modular agent operating stack | Keep one calibrated modular-stack requirement; do not duplicate the Early Signal direction. |
| ↳ Evidence audit | complete | 8 records / 0 links | The direction and requirement refer to the same architecture. A seventh source adds breadth but does not overcome the requirement's explicit blockers: strong operational adoption and strong evidence independence. |
| Enterprise context is evolving from document retrieval into an operational ontology | linked-requirement-revalidated | Shared operational context | Keep the shared operational context requirement at experimental maturity. |
| ↳ Evidence audit | complete | 5 records / 0 links | Operational ontology, graph retrieval, and structured business context converge on one reusable layer. The evidence clears continued experimentation but not promotion to an established startup baseline. |

## Assessment queue

| Rank | Candidate | Origin | Priority | Action |
| ---: | --- | --- | ---: | --- |
| — | No material candidate changes | — | — | — |

## Operating Model changes

- No maturity or linked-evidence changes this cycle.

## Verification coverage

- **AI company formation** — 68 records across 1 sources; 1 newly observed in this review history.
- **Funding activity** — 27 records across 3 sources; 1 newly observed in this review history.
- **Customer case studies** — 58 records across 12 sources; 2 newly observed in this review history.
- **AI job postings** — 18 records across 1 sources; 0 newly observed in this review history.
- **GitHub adoption proxies** — 380 records across 1 sources; 14 newly observed in this review history.
- **Production architecture reports** — 118 records across 13 sources; 3 newly observed in this review history.

## Commitment boundary

A reviewer must update the calibrated case record before the Operating Model can change.
