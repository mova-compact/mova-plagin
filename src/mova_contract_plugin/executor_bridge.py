from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .errors import BindingViolation
from .types import RuntimeBinding, StepClassification, StepOutcome, StepResult


class ExecutorBridge:
    def __init__(self) -> None:
        self._handlers: dict[str, Callable[..., StepOutcome | dict[str, Any]]] = {}

    def register_handler(self, execution_mode: str, handler) -> None:
        normalized_mode = str(execution_mode or "").strip()
        if not normalized_mode:
            raise ValueError("execution_mode is required")
        if not callable(handler):
            raise TypeError("handler must be callable")
        self._handlers[normalized_mode] = handler

    def execute_step(
        self,
        step,
        classification: StepClassification,
        binding: RuntimeBinding,
        result: StepResult,
        context: dict[str, Any],
    ) -> StepOutcome:
        if binding.execution_mode != classification.execution_mode:
            raise BindingViolation(
                "runtime binding execution_mode does not match step classification execution_mode"
            )

        execution_mode = binding.execution_mode.value
        handler = self._handlers.get(execution_mode)
        if handler is None:
            return StepOutcome(
                step_id=step.step_id,
                status="COMPLETED",
                context_update={step.step_id: dict(result.payload)},
                payload=dict(result.payload),
            )

        outcome = handler(step, classification, binding, result, dict(context))
        return self._normalize_outcome(step.step_id, outcome)

    def _normalize_outcome(self, step_id: str, outcome: StepOutcome | dict[str, Any]) -> StepOutcome:
        if isinstance(outcome, StepOutcome):
            return outcome
        if not isinstance(outcome, dict):
            raise TypeError("handler result must be StepOutcome or dict")

        normalized_step_id = str(outcome.get("step_id") or step_id).strip() or step_id
        status = str(outcome.get("status") or "").strip()
        if not status:
            raise ValueError("handler outcome status is required")

        context_update = outcome.get("context_update", {})
        payload = outcome.get("payload", {})
        if not isinstance(context_update, dict):
            raise ValueError("handler outcome context_update must be a dict")
        if not isinstance(payload, dict):
            raise ValueError("handler outcome payload must be a dict")

        return StepOutcome(
            step_id=normalized_step_id,
            status=status,
            context_update=dict(context_update),
            payload=dict(payload),
        )
