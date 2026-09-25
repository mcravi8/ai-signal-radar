# Weekly Operating Model Review — 2026-09-25

16 candidate decisions are recorded; 0 candidates remain in the bounded assessment queue.

> Candidate priority controls analyst attention only. It cannot create, promote, or demote an Operating Model requirement.

## Adjudicated candidates

| Candidate | Outcome | Linked requirement | Decision |
| --- | --- | --- | --- |
| Coding agents & developer tooling | domain-signal-not-separate-requirement | Evaluation and release gates, Bounded workflow ownership | Treat coding agents as an application domain, not a standalone operating requirement. |
| ↳ Evidence audit | complete | 101 records / 5 links | Claude Code, AI-coding, and development-tool records materially expand capability and adoption evidence. They do not create a separate startup obligation: overclaiming, incomplete review, and CI bottlenecks instead reinforce independent release gates and bounded workflow ownership. |
| Open, local & efficient inference | covered-by-existing-requirements | Heterogeneous model routing, Governed proprietary data boundary | Treat open and local inference as an execution option, not a universal standalone requirement. |
| ↳ Evidence audit | complete | 98 records / 3 links | Quantized runtime integration, adaptive inference research, and wider open-weight availability strengthen technical feasibility. The corpus still lacks independent production comparisons proving that local execution beats hosted inference after quality, operations, fallback, and hardware costs are included. |
| Voice & audio interfaces | modality-signal-not-general-requirement | Evaluation and release gates, Bounded workflow ownership | Treat voice as a conditional interface and workflow domain, not a general startup operating requirement. |
| ↳ Evidence audit | complete | 23 records / 0 links | Full-duplex models, self-hosted stacks, multilingual systems, and practitioner tooling show strong capability breadth. The corpus does not establish that voice is a default operating layer, and impersonation risk plus domain-specific recognition failures make it unsuitable as a universal requirement. |
| Proprietary enterprise data is moving behind a governed model boundary | conditional-requirement-added | Governed proprietary data boundary | Add an experimental requirement for startups handling proprietary, regulated, or customer-confidential data. |
| ↳ Evidence audit | complete | 8 records / 7 links | Benchling supplies one detailed tenant-isolation and exfiltration architecture; federated and trusted-computation systems make the pattern technically credible. Provider announcements show demand but do not verify contractual guarantees, while channel-level privacy leakage remains an unresolved counter-signal. The evidence clears experimental, not emerging, maturity. |
| Frontier inference infrastructure | infrastructure-signal-not-general-requirement | Heterogeneous model routing | Do not require ordinary startups to build frontier inference infrastructure. |
| ↳ Evidence audit | complete | 46 records / 6 links | CUDA, GPU-kernel, NIM, and inference-time-compute records deepen the supplier-side infrastructure signal. They still do not show that an application startup should own a frontier cluster; the reusable requirement remains routing, capacity, latency, cost, and fallback control across supplied inference paths. |
| Skills, protocols & integrations | covered-by-existing-requirement | Modular agent operating stack | Do not create a separate requirement for skills, protocols, and integrations. |
| ↳ Evidence audit | complete | 80 records / 5 links | Evaluated domain skills, repeatable deployment skills, MCP authorization, and graph-structured skill optimization materially strengthen technical reality. Direct API and single-agent critiques remain valid counterevidence: an interoperability layer is useful when governance or reuse warrants it, not as mandatory ceremony for every simple workflow. |
| Training, evaluation & self-improvement | covered-by-existing-requirement | Evaluation and release gates | Merge the operating conclusion into evaluation and release gates; do not require every startup to train or self-improve models. |
| ↳ Evidence audit | complete | 204 records / 3 links | The vocabulary audit added pretraining, synthetic-data, federated-learning, scaling-law, and representation-learning records. This strengthens the capability family but makes it more heterogeneous, not more universal: the general operating obligation remains evaluation and release control rather than training a model. |
| Robotics & embodied AI | conditional-requirement-added | Simulation-first physical AI development | Add a conditional requirement for physical-AI startups, not a universal startup requirement. |
| ↳ Evidence audit | complete | 36 records / 0 links | The broader vocabulary pass added first-party robotics systems, implementation reports, research, and repositories. It strengthens the physical-AI domain but does not change the operating conclusion: simulation and staged validation remain a conditional requirement only for systems acting in the physical world. |
| Agent harnesses | covered-by-existing-requirement | Modular agent operating stack | Do not create a duplicate requirement. |
| ↳ Evidence audit | complete | 67 records / 4 links | Sixteen sources now support the orchestration layer, while the generic-agent cluster was deliberately left unresolved. The industrial comparison favoring a simpler single-agent baseline remains material counterevidence, so the modular-stack requirement stays emerging and conditional. |
| The agent stack is separating into modular operating layers | source-analysis-already-calibrated | Modular agent operating stack | Keep one calibrated modular-stack requirement; do not duplicate the Early Signal direction. |
| ↳ Evidence audit | complete | 8 records / 0 links | The direction and requirement refer to the same architecture. A seventh source adds breadth but does not overcome the requirement's explicit blockers: strong operational adoption and strong evidence independence. |
| Multimodal generation & 3D | capability-domain-not-general-requirement | None | Treat multimodal generation and 3D as a capability domain, not a general startup operating requirement. |
| ↳ Evidence audit | complete | 51 records / 0 links | Eleven source families and thirty technical records establish broad capability progress, but the evidence spans unrelated product domains and benchmarks. It does not establish a common operating practice, measurable cost of absence, or production control that every AI startup should implement. |
| Governed proprietary-data boundaries | covered-by-existing-requirement | Governed proprietary data boundary | Use the new canonical theme to support the existing governed proprietary-data requirement. |
| ↳ Evidence audit | complete | 10 records / 0 links | Six independent sources establish a corroborated technical category, but repeatable production comparisons and verified provider guarantees remain thin. The corresponding startup requirement therefore remains experimental. |
| Enterprise context is evolving from document retrieval into an operational ontology | linked-requirement-revalidated | Shared operational context | Keep the shared operational context requirement at experimental maturity. |
| ↳ Evidence audit | complete | 5 records / 0 links | Operational ontology, graph retrieval, and structured business context converge on one reusable layer. The evidence clears continued experimentation but not promotion to an established startup baseline. |
| Attention is shifting from agent demos to the operating layer around them | source-analysis-covered-by-existing-requirements | Modular agent operating stack, Evaluation and release gates | Use the expert pattern as directional context for the modular stack and release gates. |
| ↳ Evidence audit | complete | 5 records / 0 links | Five experts independently emphasize the operating layer around agents. Technical and production evidence must still come from the linked requirements' underlying records, so no duplicate requirement or maturity promotion is warranted. |
| Evaluation is moving from a final benchmark into the system-design loop | source-analysis-covered-by-existing-requirement | Evaluation and release gates | Use the expert pattern as directional context for evaluation and release gates, not as a separate requirement. |
| ↳ Evidence audit | complete | 5 records / 0 links | Five experts provide independent narrative breadth, but social observations do not verify deployment or effectiveness. The finding is retained as directional context; technical support comes from the calibrated benchmark, authorization, abstention, and regression-testing records linked to the existing requirement. |
| Simulation is becoming the development environment for physical AI | linked-requirement-revalidated | Simulation-first physical AI development | Keep simulation-first development as an experimental, physical-AI-only requirement. |
| ↳ Evidence audit | complete | 6 records / 0 links | Added source breadth confirms that simulation is an active development layer, while transfer quality remains the gating uncertainty. No universal software-startup requirement follows from this domain-specific evidence. |

## Assessment queue

| Rank | Candidate | Origin | Priority | Action |
| ---: | --- | --- | ---: | --- |
| — | No material candidate changes | — | — | — |

## Operating Model changes

- No maturity or linked-evidence changes this cycle.

## Verification coverage

- **AI company formation** — 57 records across 1 sources; 0 newly observed in this review history.
- **Funding activity** — 24 records across 3 sources; 0 newly observed in this review history.
- **Customer case studies** — 30 records across 12 sources; 0 newly observed in this review history.
- **AI job postings** — 14 records across 1 sources; 0 newly observed in this review history.
- **GitHub adoption proxies** — 242 records across 1 sources; 0 newly observed in this review history.
- **Production architecture reports** — 77 records across 13 sources; 0 newly observed in this review history.

## Commitment boundary

A reviewer must update the calibrated case record before the Operating Model can change.
