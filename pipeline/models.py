from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Source:
    id: str
    name: str
    channel: str
    collection: str
    source_quality: str = "unknown"
    commercial_bias: str = "unknown"
    author: str = ""
    affiliation: str = ""
    expertise: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SourceItem:
    id: str
    source_id: str
    source_type: str
    title: str
    url: str
    published_at: str
    summary: str = ""
    authors: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    sponsor_status: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Claim:
    id: str
    source_item_id: str
    statement: str
    claim_type: str
    stance: str = "supporting"
    confidence: float | None = None


@dataclass(slots=True)
class Project:
    id: str
    name: str
    project_type: str
    url: str = ""
    description: str = ""
    stack_layers: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Theme:
    id: str
    name: str
    definition: str
    aliases: list[str] = field(default_factory=list)
    primary_layer: str = ""
    secondary_layer: str = ""
    lens: str = ""
    maturity: str = "candidate"


@dataclass(slots=True)
class Evidence:
    id: str
    source_item_id: str
    theme_id: str
    relationship: str
    claim_id: str = ""
    project_ids: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass(slots=True)
class ThemeScore:
    recurrence: float
    acceleration: float
    persistence: float
    breadth: float

    @property
    def total(self) -> float:
        return round(self.recurrence + self.acceleration + self.persistence + self.breadth, 1)

    def to_dict(self) -> dict[str, float]:
        return {
            "recurrence": round(self.recurrence, 1),
            "acceleration": round(self.acceleration, 1),
            "persistence": round(self.persistence, 1),
            "breadth": round(self.breadth, 1),
            "total": self.total,
        }


@dataclass(slots=True)
class ScoreSnapshot:
    theme_id: str
    observed_at: str
    trend: ThemeScore
    abstraction_confidence: float | None = None
    hype_risk: float | None = None
