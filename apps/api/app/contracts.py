"""Immutable evidence contracts. Observations are never edited; corrections add history."""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class Observation(Frozen):
    id: str
    modality: Literal["sketch", "speech"]
    entity: str
    predicate: str
    value: str
    source_ref: str  # e.g. "sketch:label-3" or "speech:sentence-2"
    wording: str = ""


class Contradiction(Frozen):
    id: str
    entity: str
    predicate: str
    observations: tuple[Observation, ...]  # all alternatives, both source refs kept
    question: str = ""


class Anchor(Frozen):
    id: str
    entity: str
    label: str
    order: Optional[int] = None
    lon: Optional[float] = None
    lat: Optional[float] = None
    status: Literal["unresolved", "proposed", "confirmed"] = "unresolved"
    evidence: tuple[str, ...] = ()
    reason: str = ""


class DraftBoundary(Frozen):
    status: Literal["insufficient_evidence", "invalid", "valid_draft"]
    vertex_ids: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    area_m2: Optional[float] = None
    local_xy_m: tuple[tuple[float, float], ...] = ()
    lonlat: tuple[tuple[float, float], ...] = ()
    note: str = "Geometric validity only; does not show the land exists at these coordinates."


class AgentStep(BaseModel):
    agent: str
    role: str
    model: str
    input_summary: str
    output_summary: str = ""
    duration_ms: float = 0.0
    status: str = "ok"


class Resolution(Frozen):
    contradiction_id: str
    chosen_observation_id: Optional[str] = None  # None = leave unresolved
    note: str = Field(default="", max_length=300)
