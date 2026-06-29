from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .evidence import EvidenceWriter
from .executor_bridge import ExecutorBridge
from .errors import FinalDecisionViolation, StepOrderViolation
from .types import (
    ContractPackage,
    CurrentStepInstruction,
    ExecutionMode,
    StepOutcome,
    StepResult,
)


class ContractSession:
    _AI_ATOMIC_FORBIDDEN_FIELDS = {
        "approved",
        "rejected",
        "authorized",
        "authorize",
        "final_decision",
        "business_decision",
        "payment_approved",
        "decision",
    }

    def __init__(
        self,
        package: ContractPackage,
        executor_bridge: ExecutorBridge | None = None,
        evidence_writer: EvidenceWriter | None = None,
    ):
        self._package = package
        self._executor_bridge = executor_bridge or ExecutorBridge()
        self._evidence_writer = evidence_writer
        self._current_index = 0
        self._context: dict[str, Any] = {}

    def is_done(self) -> bool:
        return self._current_index >= len(self._package.steps)

    def current_step_id(self) -> str | None:
        if self.is_done():
            return None
        return self._package.steps[self._current_index].step_id

    def current_instruction(self) -> CurrentStepInstruction | None:
        if self.is_done():
            return None

        step = self._package.steps[self._current_index]
        classification = self._package.classifications[step.step_id]
        return CurrentStepInstruction(
            step_id=step.step_id,
            execution_mode=classification.execution_mode,
            instruction=step.instruction,
            input_schema=step.input_schema,
            context=dict(self._context),
        )

    def submit_result(self, result: StepResult | dict[str, Any]) -> StepOutcome:
        if self.is_done():
            raise StepOrderViolation("contract session is already complete")

        normalized = self._normalize_result(result)
        current_step_id = self.current_step_id()
        if normalized.step_id != current_step_id:
            raise StepOrderViolation(
                f"result step_id={normalized.step_id!r} does not match current step_id={current_step_id!r}"
            )

        step = self._package.steps[self._current_index]
        classification = self._package.classifications[step.step_id]
        contract_id = self._contract_id()
        try:
            self._guard_ai_atomic_payload(classification.execution_mode, normalized.payload)
        except FinalDecisionViolation:
            self._record_step_failed(
                contract_id=contract_id,
                step_id=step.step_id,
                execution_mode=classification.execution_mode,
                reason_code="final_decision_violation",
                payload={"result_payload": dict(normalized.payload)},
            )
            raise

        binding = self._package.bindings[step.step_id]
        self._record_step_started(
            contract_id=contract_id,
            step_id=step.step_id,
            execution_mode=classification.execution_mode,
            payload={"result_payload": dict(normalized.payload)},
        )
        try:
            outcome = self._executor_bridge.execute_step(
                step=step,
                classification=classification,
                binding=binding,
                result=normalized,
                context=self._context,
            )
        except Exception:
            self._record_step_failed(
                contract_id=contract_id,
                step_id=step.step_id,
                execution_mode=classification.execution_mode,
                reason_code="executor_error",
                payload={"result_payload": dict(normalized.payload)},
            )
            raise

        self._context.update(dict(outcome.context_update))
        self._current_index += 1
        self._record_step_completed(
            contract_id=contract_id,
            step_id=step.step_id,
            execution_mode=classification.execution_mode,
            payload={"outcome_payload": dict(outcome.payload)},
        )
        if self.is_done():
            self._record_contract_completed(contract_id=contract_id, payload={})
        return outcome

    def context(self) -> dict[str, Any]:
        return dict(self._context)

    def _normalize_result(self, result: StepResult | dict[str, Any]) -> StepResult:
        if isinstance(result, StepResult):
            return result
        if not isinstance(result, dict):
            raise TypeError("result must be StepResult or dict")

        step_id = str(result.get("step_id") or "").strip()
        payload = result.get("payload")
        if not step_id:
            raise ValueError("result.step_id is required")
        if not isinstance(payload, dict):
            raise ValueError("result.payload must be a dict")
        return StepResult(step_id=step_id, payload=dict(payload))

    def _guard_ai_atomic_payload(
        self,
        execution_mode: ExecutionMode,
        payload: dict[str, Any],
    ) -> None:
        if execution_mode is not ExecutionMode.AI_ATOMIC:
            return

        forbidden_path = self._find_forbidden_field(payload)
        if forbidden_path is None:
            return

        raise FinalDecisionViolation(
            f"AI_ATOMIC result payload contains forbidden final decision field at {forbidden_path}"
        )

    def _find_forbidden_field(self, value: Any, path: str = "payload") -> str | None:
        if isinstance(value, Mapping):
            for key, nested_value in value.items():
                normalized_key = str(key).strip().lower()
                nested_path = f"{path}.{key}"
                if normalized_key in self._AI_ATOMIC_FORBIDDEN_FIELDS:
                    return nested_path
                match = self._find_forbidden_field(nested_value, nested_path)
                if match is not None:
                    return match
            return None

        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for index, nested_value in enumerate(value):
                match = self._find_forbidden_field(nested_value, f"{path}[{index}]")
                if match is not None:
                    return match
            return None

        return None

    def _contract_id(self) -> str | None:
        value = self._package.manifest.get("contract_id")
        if value is None:
            return None
        return str(value)

    def _record_step_started(
        self,
        contract_id: str | None,
        step_id: str,
        execution_mode: ExecutionMode,
        payload: dict[str, Any],
    ) -> None:
        if self._evidence_writer is None:
            return
        self._evidence_writer.record_step_started(
            contract_id=contract_id,
            step_id=step_id,
            execution_mode=execution_mode,
            payload=payload,
        )

    def _record_step_completed(
        self,
        contract_id: str | None,
        step_id: str,
        execution_mode: ExecutionMode,
        payload: dict[str, Any],
    ) -> None:
        if self._evidence_writer is None:
            return
        self._evidence_writer.record_step_completed(
            contract_id=contract_id,
            step_id=step_id,
            execution_mode=execution_mode,
            payload=payload,
        )

    def _record_step_failed(
        self,
        contract_id: str | None,
        step_id: str,
        execution_mode: ExecutionMode,
        reason_code: str,
        payload: dict[str, Any],
    ) -> None:
        if self._evidence_writer is None:
            return
        self._evidence_writer.record_step_failed(
            contract_id=contract_id,
            step_id=step_id,
            execution_mode=execution_mode,
            reason_code=reason_code,
            payload=payload,
        )

    def _record_contract_completed(
        self,
        contract_id: str | None,
        payload: dict[str, Any],
    ) -> None:
        if self._evidence_writer is None:
            return
        self._evidence_writer.record_contract_completed(
            contract_id=contract_id,
            payload=payload,
        )
