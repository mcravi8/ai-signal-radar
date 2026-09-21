from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.export_public import validate_public_payload


MONTHS = ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"]

TREND_RULES = {
    "Open/local models and inference efficiency": r"open[- ]source|open weights?|local|on-device|quantiz|llama\.cpp|gguf|mixture of experts|\bmoe\b|small model",
    "Agent orchestration and autonomy": r"agent|orchestrat|parallel|sandbox|tool use|handoff|long-running|autonom",
    "Coding agents and developer tooling": r"codex|claude code|cursor|coding agent|code agent|repository|\brepo\b|github|software engineer",
    "Training, evaluation and self-improvement": r"train|fine-tun|eval|benchmark|reinforcement learning|distill|self-improv|optimizes? prompts?",
    "Validation and release bottlenecks": r"validat|test|verification|\bci\b|review|observab|trac|deploy|release",
    "Multimodal generation and 3D": r"video|image|avatar|\b3d\b|depth|vision|world model|point cloud",
    "Skills, plugins, MCP and harnesses": r"skill|plugin|\bmcp\b|harness|tool protocol|command-line|\bcli\b",
    "Voice and audio interfaces": r"voice|audio|speech|\btts\b|transcri|dubbing|telephony",
    "Documents, retrieval and structured data": r"document|\bpdf\b|\bocr\b|\brag\b|retriev|knowledge graph|structured data|\bjson\b|\bsql\b",
    "Security, safety and observability": r"secur|safety|prompt injection|permission|red[- ]team|\bpii\b|privacy|de-ident",
    "Memory and context engineering": r"memory|context|compaction|prun|cache|persistent",
    "Enterprise and vertical AI": r"enterprise|salesforce|legal|finance|healthcare|clinical|sales|business system",
    "Web and browser automation": r"browser|scrap|web agent|website|cloudflare",
    "Robotics and embodied AI": r"robot|embodied|gr00t|physical|motion|navigation",
    "Model routing and heterogeneous stacks": r"rout|cascade|ensemble|openrouter|mixture of agents|model selector",
}

TREND_LAYERS = {
    "Open/local models and inference efficiency": ["Models & capabilities", None, False],
    "Agent orchestration and autonomy": ["Harness & orchestration", "Tools, skills & integrations", True],
    "Coding agents and developer tooling": ["Harness & orchestration", "Tools, skills & integrations", True],
    "Training, evaluation and self-improvement": ["Assurance layer", "Models & capabilities", True],
    "Validation and release bottlenecks": ["Assurance layer", "Harness & orchestration", True],
    "Multimodal generation and 3D": ["Models & capabilities", "Tools, skills & integrations", True],
    "Skills, plugins, MCP and harnesses": ["Tools, skills & integrations", "Harness & orchestration", True],
    "Voice and audio interfaces": ["Models & capabilities", "Tools, skills & integrations", True],
    "Documents, retrieval and structured data": ["Tools, skills & integrations", "Harness & orchestration", True],
    "Security, safety and observability": ["Assurance layer", "Harness & orchestration", True],
    "Memory and context engineering": ["Harness & orchestration", "Assurance layer", True],
    "Enterprise and vertical AI": ["Tools, skills & integrations", "Harness & orchestration", True],
    "Web and browser automation": ["Tools, skills & integrations", "Harness & orchestration", True],
    "Robotics and embodied AI": ["Models & capabilities", "Tools, skills & integrations", True],
    "Model routing and heterogeneous stacks": ["Harness & orchestration", "Models & capabilities", True],
}

OPPORTUNITY_RATINGS = {
    "DeepSeek Harness": [5, 2, 5, 5, 3, 5, "Medium"],
    "LoopX": [5, 3, 5, 4, 3, 5, "Medium"],
    "CLI-Anything": [5, 3, 5, 5, 3, 5, "Medium"],
    "Nango": [5, 5, 5, 3, 3, 5, "Low"],
    "Docling": [5, 4, 5, 5, 4, 5, "Low"],
    "pdf-inspector": [4, 3, 5, 5, 5, 4, "Medium"],
    "Outlines": [5, 4, 5, 5, 4, 5, "Low"],
    "Microsoft GraphRAG": [4, 4, 4, 3, 2, 4, "Medium"],
    "WrenAI": [5, 4, 4, 4, 3, 5, "Medium"],
    "Scrapling": [4, 4, 4, 5, 3, 4, "High"],
    "Unsloth Desktop": [4, 4, 4, 5, 3, 4, "Medium"],
    "OpenMed": [4, 3, 3, 5, 2, 3, "Medium"],
    "Dograh": [5, 4, 4, 4, 3, 4, "Medium"],
    "VoiceStudio": [4, 3, 4, 5, 3, 4, "High"],
    "OpenReel Video": [4, 3, 4, 5, 4, 4, "Medium"],
    "depth-anything.cpp": [4, 4, 4, 5, 2, 3, "High"],
    "Hallmark": [3, 3, 5, 5, 5, 4, "Medium"],
    "PromptWizard": [4, 3, 4, 5, 3, 4, "Medium"],
    "TypeSafe AI Jev": [4, 2, 3, 3, 2, 4, "High"],
    "WikiSkill": [5, 2, 4, 5, 2, 5, "High"],
}

OPPORTUNITY_LAYERS = {
    "DeepSeek Harness": ["Harness & orchestration", "Tools, skills & integrations", True],
    "LoopX": ["Harness & orchestration", "Assurance layer", True],
    "CLI-Anything": ["Tools, skills & integrations", "Harness & orchestration", True],
    "Nango": ["Tools, skills & integrations", "Harness & orchestration", True],
    "Docling": ["Tools, skills & integrations", "Harness & orchestration", True],
    "pdf-inspector": ["Tools, skills & integrations", "Assurance layer", True],
    "Outlines": ["Assurance layer", "Tools, skills & integrations", True],
    "Microsoft GraphRAG": ["Tools, skills & integrations", "Harness & orchestration", True],
    "WrenAI": ["Tools, skills & integrations", "Harness & orchestration", True],
    "Scrapling": ["Tools, skills & integrations", None, False],
    "Unsloth Desktop": ["Models & capabilities", "Tools, skills & integrations", True],
    "OpenMed": ["Assurance layer", "Models & capabilities", True],
    "Dograh": ["Tools, skills & integrations", "Harness & orchestration", True],
    "VoiceStudio": ["Models & capabilities", "Tools, skills & integrations", True],
    "OpenReel Video": ["Tools, skills & integrations", None, False],
    "depth-anything.cpp": ["Models & capabilities", "Tools, skills & integrations", True],
    "Hallmark": ["Assurance layer", "Tools, skills & integrations", True],
    "PromptWizard": ["Assurance layer", "Models & capabilities", True],
    "TypeSafe AI Jev": ["Harness & orchestration", "Models & capabilities", True],
    "WikiSkill": ["Harness & orchestration", "Tools, skills & integrations", True],
}

LAYER_COUNTS = {
    "Models & capabilities": 217,
    "Harness & orchestration": 300,
    "Tools, skills & integrations": 188,
    "Assurance layer": 194,
}

LAYER_DEFINITIONS = {
    "Models & capabilities": "Foundation models, specialized models, multimodal capabilities, and local inference.",
    "Harness & orchestration": "Agent loops, state, memory, routing, sandboxes, and execution control.",
    "Tools, skills & integrations": "Reusable capabilities, data access, application connectors, and workflow components.",
    "Assurance layer": "Evaluation, validation, security, governance, and observability.",
}

EXECUTIVE_FINDINGS = [
    {
        "finding": "Deployability is the dominant model story",
        "evidence": "Open weights, mixture-of-experts architectures, quantization, local inference, and routing appeared in 270 matched records.",
    },
    {
        "finding": "Agents are becoming systems rather than chat interfaces",
        "evidence": "Durable state, parallel work, sandboxes, handoffs, skills, and model-independent harnesses form a distinct control layer.",
    },
    {
        "finding": "Reliability is becoming the constraint",
        "evidence": "Validation, evaluation, observability, context management, and security recur alongside the largest applied categories.",
    },
    {
        "finding": "Enabling layers offer the nearest-term leverage",
        "evidence": "Document routing, structured output, integrations, CLI wrappers, and durable agent state can upgrade many workflows at once.",
    },
    {
        "finding": "The late-period mix shifts toward vertical deployment",
        "evidence": "September coverage increasingly combines domain indexes, live business-system access, governed data interfaces, and specialized agents.",
    },
]


def entity_key(statement: str) -> str:
    cleaned = re.sub(r"^[^A-Za-z0-9]+", "", statement).strip()
    verb = re.match(
        r"^(.{2,55}?)\s+(?:ships|releases|launches|drops|open-sources|unveils|publishes|trains|builds|introduces|adds|turns|gives|cuts|makes|merges|raises|acquires)\b",
        cleaned,
        re.I,
    )
    lead = verb.group(1) if verb else " ".join(cleaned.split()[:4])
    return re.sub(r"[^a-z0-9]+", " ", lead.lower()).strip()


def js_round(value: float) -> int:
    """Match JavaScript Math.round used in the reviewed workbook."""
    return math.floor(value + 0.5)


def build_payload(source: dict) -> dict:
    eligible = [row for row in source["catalog"] if row.get("sponsored") != "Yes"]
    max_mentions = max(row["mentions"] for row in source["trendRows"])
    bases = {}
    for name, expression in TREND_RULES.items():
        pattern = re.compile(expression, re.I)
        matches = [row for row in eligible if pattern.search(row.get("statement", ""))]
        monthly = [sum(row.get("month") == month for row in matches) for month in MONTHS]
        bases[name] = {
            "monthly": monthly,
            "breadth_count": len({entity_key(row.get("statement", "")) for row in matches}),
        }
    max_breadth = max(base["breadth_count"] for base in bases.values())

    trends = []
    for row in source["trendRows"]:
        base = bases[row["name"]]
        early_rate = sum(base["monthly"][:4]) / 4
        recent_rate = sum(base["monthly"][4:]) / 2
        recurrence = js_round(25 * math.log1p(row["mentions"]) / math.log1p(max_mentions))
        acceleration = js_round(max(0, min(25, 12.5 + 10 * math.log2((recent_rate + 1) / (early_rate + 1)))))
        persistence = js_round(25 * sum(value > 0 for value in base["monthly"]) / len(MONTHS))
        breadth = js_round(25 * math.log1p(base["breadth_count"]) / math.log1p(max_breadth))
        score = recurrence + acceleration + persistence + breadth
        tier = "Structural" if score >= 80 else "Strong" if score >= 65 else "Emerging" if score >= 50 else "Niche / uncertain"
        primary, secondary, cross_layer = TREND_LAYERS[row["name"]]
        trends.append(
            {
                "name": row["name"],
                "mentions": row["mentions"],
                "direction": row["direction"],
                "finding": row["evidence"],
                "examples": [value.strip() for value in row["examples"].split(",")],
                "primary_layer": primary,
                "secondary_layer": secondary,
                "cross_layer": cross_layer,
                "monthly_mentions": dict(zip(MONTHS, base["monthly"], strict=True)),
                "score": {
                    "recurrence": recurrence,
                    "acceleration": acceleration,
                    "persistence": persistence,
                    "breadth": breadth,
                    "total": score,
                    "tier": tier,
                },
            }
        )
    trends.sort(key=lambda item: (-item["score"]["total"], item["name"]))

    weights = [25, 15, 20, 15, 15, 10]
    projects = []
    for row in source["shortlist"]:
        leverage, maturity, composability, cost, ease, relevance, hype_risk = OPPORTUNITY_RATINGS[row["name"]]
        ratings = [leverage, maturity, composability, cost, ease, relevance]
        score = js_round(sum(rating * weight / 5 for rating, weight in zip(ratings, weights, strict=True)))
        action = "Test now" if score >= 85 else "Pilot / watch" if score >= 75 else "Selective" if score >= 65 else "Research only"
        primary, secondary, cross_layer = OPPORTUNITY_LAYERS[row["name"]]
        projects.append(
            {
                "name": row["name"],
                "editorial_rank": row["rank"],
                "source_date": row["date"],
                "category": row["category"],
                "why_it_matters": row["why"],
                "workflow_opportunity": row["use"],
                "caveat": row["maturity"],
                "official_url": row["official_url"],
                "primary_layer": primary,
                "secondary_layer": secondary,
                "cross_layer": cross_layer,
                "ratings": {
                    "leverage": leverage,
                    "maturity": maturity,
                    "composability": composability,
                    "cost_accessibility": cost,
                    "ease": ease,
                    "relevance": relevance,
                },
                "opportunity_score": score,
                "action": action,
                "hype_risk": hype_risk,
            }
        )
    projects.sort(key=lambda item: (-item["opportunity_score"], item["editorial_rank"]))
    for rank, project in enumerate(projects, 1):
        project["rank"] = rank

    meta = source["meta"]
    return {
        "meta": {
            "title": "AlphaSignal corpus analysis",
            "source": "AlphaSignal newsletter",
            "analysis_date": "2026-09-21",
            "coverage_start": meta["period_start"],
            "coverage_end": meta["period_end"],
            "email_count": meta["email_count"],
            "substantive_email_count": meta["substantive_email_count"],
            "raw_signal_records": meta["raw_signal_records"],
            "unique_catalog_records": meta["unique_catalog_records"],
            "sponsored_records": meta["sponsored_records"],
            "trend_count": len(trends),
            "project_count": len(projects),
            "publication_boundary": "Derivative analysis only. No email addresses, mailbox links, message identifiers, private headers, or full newsletter text are included.",
        },
        "layers": [
            {"name": name, "catalog_records": count, "definition": LAYER_DEFINITIONS[name]}
            for name, count in LAYER_COUNTS.items()
        ],
        "findings": EXECUTIVE_FINDINGS,
        "trends": trends,
        "projects": projects,
        "methodology": {
            "corpus": meta["method"],
            "trend_score": {
                "purpose": "Measures whether a capability represents a durable pattern in the AlphaSignal corpus.",
                "components": {
                    "recurrence": "Log-scaled AlphaSignal mentions, 25 points.",
                    "acceleration": "August–September monthly rate compared with April–July, 25 points.",
                    "persistence": "Active months across the six-month observation window, 25 points.",
                    "breadth": "Log-scaled distinct lead entities in non-sponsored records, 25 points.",
                },
            },
            "opportunity_score": {
                "purpose": "Measures whether a specific project is worth testing for workflow automation; it does not inherit the trend score.",
                "weights": {
                    "leverage": 25,
                    "maturity": 15,
                    "composability": 20,
                    "cost_accessibility": 15,
                    "ease": 15,
                    "relevance": 10,
                },
                "scale": "Each component is an analyst rating from 1 (weak) to 5 (strong). Hype risk remains separate.",
            },
            "limitations": [
                "Counts measure AlphaSignal editorial attention, not total market adoption.",
                "Keyword themes overlap; a catalog record may contribute to more than one trend.",
                "Sponsored records remain counted in corpus metadata but are excluded from trend interpretation and project ranking.",
                "Newsletter claims were treated as leads rather than independently verified facts.",
                "Project relevance is provisional because it reflects a broad workflow-automation goal rather than a detailed operating context.",
            ],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a public-safe derivative of the private AlphaSignal analysis corpus.")
    parser.add_argument("input", type=Path, help="Private alpha_analysis_data.json path")
    parser.add_argument("--output", type=Path, default=Path("data/public/alphasignal-research.json"))
    args = parser.parse_args()
    payload = build_payload(json.loads(args.input.read_text(encoding="utf-8")))
    validate_public_payload(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}: {len(payload['trends'])} trends, {len(payload['projects'])} projects")


if __name__ == "__main__":
    main()
