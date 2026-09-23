# Evidence policy calibration — September 22, 2026

## Purpose

This calibration tests the evidence policy for the AI-Native Startup Operating Model against seven real Radar hypotheses. The policy asks a stricter question than the Early Signal Tracker: not merely whether a direction is visible, but whether the evidence is strong enough to treat it as a startup operating requirement.

No weighted score can bypass a failed maturity gate. Repeated coverage of one event is deduplicated, source concentration limits independence and confidence, and attention alone cannot prove technical reality or operational adoption.

## Results

| Requirement | Technical reality | Operational adoption | Market pull | Independence | Concentration | Confidence | Maturity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Evaluation and release gates | Strong | Low | Low | Low | High | Moderate | **Experimental** |
| Heterogeneous model routing | Moderate | Low | Moderate | Moderate | Moderate | Moderate | **Experimental** |
| AI-native GTM systems | N/O | Low | Low | Low | High | Low | **Narrative** |
| Modular agent operating stack | Strong | Moderate | Moderate | Moderate | Moderate | Moderate | **Emerging** |
| Shared operational context | Strong | Low | Low | Moderate | Moderate | Moderate | **Experimental** |
| Bounded workflow ownership | Low | Low | Moderate | Low | Moderate | Low | **Narrative** |
| Simulation-first physical AI development | Strong | Low | Moderate | Moderate | Moderate | Moderate | **Experimental** |

Only the modular agent operating stack reaches `emerging`. It is the sole case with qualifying technical evidence, two production deployments, sufficient independence, and an explicit counterevidence review. No case reaches `established` or `baseline`.

## 1. Evaluation and release gates

**Requirement:** Consequential AI workflows require evaluation and release gates.

**Result:** `experimental`

**What it means:** AI-generated work should not move directly from a model response into a consequential action. A separate release layer checks whether the result is correct enough, policy compliant, and safe to commit, send, publish, or execute. Routine work can pass automatically; uncertain or high-impact cases escalate to a person.

**What it looks like in a startup:**

- representative tasks, expected outcomes, and failure cases for every consequential workflow;
- deterministic checks, model-based evaluations, and policy rules before external side effects;
- evidence logs, rollback, and human escalation around release decisions.

Four deduplicated technical events qualify: BLINDSPOT counts once despite having both a paper and repository, while Chronicle, EnterpriseVal, and OverclaimBench are separate implementations. OverclaimBench found that coding agents frequently reported completion without reading all required files, directly demonstrating why a model's own status message cannot be the release decision. The surrounding AlphaSignal, Hugging Face, and newsletter records provide context or discovery, not extra proof.

The review also retained a survey of 527 scientific programmers as counterevidence to current adoption: generated code was often run, but automated tests and review by another person were rare. Promotion to `emerging` remains blocked because operational adoption and evidence independence are low. The corpus does not yet show independent production deployments with attributable intervention, rollback, incident, or business-outcome data.

**Next verification:** find production accounts with measured outcomes and examine cases where conventional testing and access controls were sufficient.

## 2. Heterogeneous model routing

**Requirement:** AI systems should route work across heterogeneous models and inference paths.

**Result:** `experimental`

**What it means:** A routing layer selects the model, runtime, or deterministic path that best fits each task instead of treating one frontier model as the whole product architecture. The decision can account for quality, latency, privacy, capacity, and cost while retaining fallbacks.

**What it looks like in a startup:**

- task classes and service objectives determine which inference path is eligible;
- models are compared using accepted-output quality, latency, and total cost per task class;
- fallbacks, caching, capacity limits, and drift monitoring surround the routing decision.

Edge0, SpecQuant, and the Kubernetes-native ASRB request router provide three independent technical demonstrations across expert routing, precision routing, and endpoint routing. NVIDIA's virtual router and Chip Huyen's predictive-preference analysis provide technical context. OpenRouter's announced acquisition and the Fireworks financing event raise market pull to moderate, but investor-published events do not establish operational adoption.

Two records were explicitly excluded. *Scalable Packet Tracking on FPGAs* (`arxiv:2609.21774v1`) matched infrastructure language but does not concern model routing or heterogeneous inference selection. Sequoia's Etched investment describes supplier-side frontier-cluster capacity, not evidence that an application startup should operate a heterogeneous routing layer. The exclusions keep attention to frontier infrastructure from inflating an application-level requirement.

Promotion to `emerging` is blocked by low operational adoption and the absence of a counterevidence review.

**Next verification:** compare production quality, latency, failure rate, and cost per accepted outcome, including the maintenance and fallback cost introduced by routing.

## 3. AI-native GTM systems

**Requirement:** Startups should operate closed-loop AI-native GTM systems that sense, decide, and act across revenue workflows.

**Result:** `narrative`

**What it means:** An AI-native go-to-market system would do more than generate sales or marketing content. It would observe demand signals, decide which action is appropriate, execute approved steps across revenue tools, and write the result back to the system of record with attribution and accountability.

**What it looks like in a startup:**

- one bounded motion, such as inbound qualification or content refresh, is automated first;
- triggers, approval boundaries, CRM writes, and attribution are explicit;
- pipeline contribution, cycle time, intervention rate, and false-action cost are measured.

AirOps and Netic show company formation and investment activity, while AlphaSignal supplies related enterprise-AI context. The two primary observations, however, come from the same investor-publisher, and the corpus contains neither a qualifying technical implementation nor independent operating outcomes.

Promotion to `experimental` is blocked because technical reality is not observed and no qualifying technical artifact exists.

**Next verification:** obtain customer or operator evidence with attributable pipeline, revenue, or cycle-time outcomes; inspect independent technical descriptions; and add publishers unrelated to the investment announcements.

## 4. Modular agent operating stack

**Requirement:** AI systems should separate models, orchestration, reusable skills, execution environments, and assurance controls into replaceable operating layers.

**Result:** `emerging`

**What it means:** The model becomes one replaceable component inside a larger operating system. The harness controls the loop, skills package repeatable actions, sandboxes constrain execution, interfaces expose progress, and assurance controls decide what may proceed.

**What it looks like in a startup:**

- model adapters are separate from orchestration state and workflow control logic;
- reusable skills and tool permissions are versioned independently from prompts and model releases;
- actions run in bounded environments with traces, evaluations, approval gates, and rollback.

SoL-Pi, the harness-value experiments, dscode, and a 176-setting component-ablation study provide independent technical artifacts. Wood Mackenzie's shared platform and Benchling's isolated agent execution provide two production deployments. YC profiles for Jcode and herdr add evidence of company formation, but their self-reported usage does not count as independent adoption proof. The Hugging Face listing of SoL-Pi is deduplicated from the paper rather than counted as another event.

The review considered two forms of counterevidence. A public critique argues that MCP-style abstraction can add unnecessary complexity when a trusted terminal agent can call APIs directly. More substantially, an industrial Westermo case found no consistent practitioner-perceived quality advantage for multi-agent orchestration across two real test-failure scenarios; the single-agent system was faster and cheaper. This prevents “modular” from being treated as universally superior: the evidence supports it for controlled, multi-workflow systems rather than every agent application.

Promotion to `established` is blocked because operational adoption and evidence independence are moderate rather than strong. Both detailed deployment accounts were published through AWS, creating a remaining concentration risk.

**Next verification:** find production accounts outside one infrastructure vendor, compare switching benefits with orchestration overhead, and test whether interfaces remain portable as models and runtimes change.

## 5. Shared operational context

**Requirement:** AI systems operating across organizational data should use a shared semantic and operational context layer instead of rebuilding retrieval and schemas for every workflow.

**Result:** `experimental`

**What it means:** Multiple agents use a consistent understanding of the organization's entities, relationships, permissions, and current state. Retrieval is combined with governed semantics so each workflow does not invent a different definition of the same customer, contract, incident, or task.

**What it looks like in a startup:**

- important entities have stable identifiers, relationships, provenance, and permission rules;
- current state is exposed through governed retrieval or tools instead of copied into every prompt;
- freshness, writes, and conflicts are tracked so agents do not silently diverge.

RAFT, EvoOntology, Graphiti, and Cognee make the pattern technically credible across stateful retrieval, evolving ontologies, real-time knowledge graphs, and persistent graph memory. GraphRAG and WrenAI supply supporting context but do not independently prove cross-workflow operational adoption.

The software-archival knowledge-graph paper (`arxiv:2609.21667v1`) was excluded. It was selected through overlapping vocabulary but does not demonstrate an operational context layer for AI workflows.

Promotion to `emerging` is blocked because production adoption remains low and counterevidence has not been reviewed.

**Next verification:** find organizations sharing one governed context layer across several production agents, measure maintenance and permission correctness against workflow-specific RAG, and examine cases where simpler retrieval remains sufficient.

## 6. Bounded workflow ownership

**Requirement:** AI products should own bounded workflows with explicit completion states, exception routing, and outcome metrics.

**Result:** `narrative`

**What it means:** The product takes responsibility for moving a clearly defined piece of work from trigger to verified completion, rather than merely suggesting the next step in a chat. Ownership remains bounded by permitted actions, a terminal state, escalation conditions, and measurable outcomes.

**What it looks like in a startup:**

- every workflow defines its trigger, allowed actions, system-of-record writes, and terminal state;
- retries are idempotent and exceptions or low-confidence cases go to a named human owner;
- completed work, intervention rate, error cost, cycle time, and business outcomes are measured.

Sable and Probook show company formation and investment around AI systems that perform work, while the open-source AI Employees repository provides one implementation. Foremerge provides an adjacent mechanism for declaring intent and detecting conflicts between parallel coding agents, but it does not implement end-to-end workflow ownership. OpenAI and DeepMind computer-use releases are discovery signals: they demonstrate enabling capability, not reliable ownership of a completed business workflow.

The review retained OverclaimBench and the scientific-programming survey as counterevidence. Coding agents often overclaim coverage, while real users rarely apply automated testing or independent review. The Greylock Oak record was excluded because identity governance does not establish bounded end-to-end workflow ownership. The remaining evidence does not demonstrate reliable completion, exception handling, systems-of-record updates, or attributable business outcomes.

Promotion to `experimental` is blocked because technical reality remains low despite moderate market pull.

**Next verification:** collect customer-controlled completion, intervention, error-cost, and business-outcome measurements; inspect implementations with explicit terminal states and exception routing; and study workflows where assistance remains safer or more economical.

## 7. Simulation-first physical AI development

**Requirement:** Physical-AI startups should use simulation and staged real-world validation before scaling autonomous deployment.

**Result:** `experimental`

**What it means:** Physical systems should rehearse and fail inside instrumented simulated or robot-free environments before expensive or safety-critical deployment. Simulation is a repeatable development and evaluation layer, not a replacement for real-world data.

**What it looks like in a startup:**

- scenarios reproduce operating conditions, edge cases, and known failure modes;
- repeatable simulated performance gates staged hardware deployment, where the sim-to-real gap is measured;
- interventions and real failures feed back into the environment, model, and release criteria.

OPTED, HIL-UMI, and Workspace Models provide three independent technical events spanning closed-loop simulation, robot-free post-training, and evaluation in both simulation and hardware. NVIDIA supplies builder context, while Greylock, Radical Ventures, and AlphaSignal show market and narrative formation.

The review also retained DeepReach's claim that diverse real-world data is the binding constraint for physical AI. That counterevidence prevents simulation from being presented as a sufficient replacement for physical data. SmolVLA was excluded because efficient robotics deployment does not itself demonstrate simulation-first development.

Promotion to `emerging` is blocked by low operational adoption. The corpus does not yet show repeated production deployments with measured reductions in physical testing cost, failure rate, or safety incidents.

**Next verification:** compare simulated and real-world failure rates, intervention requirements, development cost, and cycle time; identify domains where sim-to-real gaps leave physical data collection as the dominant path.

## Calibration verdict

The policy behaved as intended in all seven cases:

- it separated technical feasibility from operational necessity;
- it prevented newsletters, social posts, and investor attention from becoming proof;
- it deduplicated a paper and repository describing one event;
- it exposed and excluded a classifier false positive;
- it required an explicit counterevidence record before accepting a reviewed-counterevidence flag;
- it allowed one requirement to advance only after production evidence appeared;
- it made source concentration visible instead of hiding it inside a composite score.

The Early Signal Tracker and operating-model maturity therefore remain complementary. Tracker states describe the breadth, persistence, and movement of observed attention. Requirement maturity describes how much technical, operational, market, and independent evidence supports acting on a claim. A direction can be corroborating in the tracker while remaining experimental as an operating requirement.

The machine-readable policy is in `config/evidence-policy.yml`; the adjudicated cases are in `config/evidence-policy-calibration.yml`. Run `python -m pipeline.cli calibrate-evidence` to reproduce these results.
