from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExecutionMode(str, Enum):
    AI_ATOMIC = "AI_ATOMIC"
    HUMAN = "HUMAN"
    RULE = "RULE"
    EXTERNAL = "EXTERNAL"


class DecisionStatus(str, Enum):
    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    NEEDS_HUMAN = "NEEDS_HUMAN"
    DENY = "DENY"


@dataclass(frozen=True)
class StepClassification:
    step_id: str
    execution_mode: ExecutionMode
    raw: dict[str, Any]


@dataclass(frozen=True)
class RuntimeBinding:
    step_id: str
    execution_mode: ExecutionMode
    connector_ref: str | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class ContractStep:
    step_id: str
    instruction: str
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContractPackage:
    manifest: dict[str, Any]
    flow: dict[str, Any]
    classifications: dict[str, StepClassification]
    bindings: dict[str, RuntimeBinding]
    steps: list[ContractStep]

    def step_ids_in_order(self) -> list[str]:
        return [step.step_id for step in self.steps]


@dataclass(frozen=True)
class CurrentStepInstruction:
    step_id: str
    execution_mode: ExecutionMode
    instruction: str
    input_schema: dict[str, Any] | None
    context: dict[str, Any]


@dataclass(frozen=True)
class StepResult:
    step_id: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class StepOutcome:
    step_id: str
    status: str
    context_update: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceRecord:
    episode_id: str
    timestamp: str
    contract_id: str | None
    step_id: str | None
    execution_mode: str | None
    status: str
    reason_code: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class ReviewCase:
    review_id: str
    step_id: str
    reason_code: str
    summary: str
    payload: dict[str, Any]
