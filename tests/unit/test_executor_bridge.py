from __future__ import annotations

from mova_contract_plugin.executor_bridge import ExecutorBridge
from mova_contract_plugin.types import (
    ContractStep,
    ExecutionMode,
    RuntimeBinding,
    StepClassification,
    StepOutcome,
    StepResult,
)


def test_default_bridge_stores_result_under_step_id() -> None:
    bridge = ExecutorBridge()

    outcome = bridge.execute_step(
        step=_step(),
        classification=_classification(),
        binding=_binding(),
        result=StepResult(step_id="step_1", payload={"field": "value"}),
        context={},
    )

    assert outcome == StepOutcome(
        step_id="step_1",
        status="COMPLETED",
        context_update={"step_1": {"field": "value"}},
        payload={"field": "value"},
    )


def test_registered_handler_is_called_and_receives_full_inputs() -> None:
    bridge = ExecutorBridge()
    seen: list[tuple[str, str, str, dict[str, object], dict[str, object]]] = []

    def handler(step, classification, binding, result, context):
        seen.append(
            (
                step.step_id,
                classification.execution_mode.value,
                binding.execution_mode.value,
                dict(result.payload),
                dict(context),
            )
        )
        return StepOutcome(
            step_id=step.step_id,
            status="HANDLED",
            context_update={"handled": True},
            payload={"ok": True},
        )

    bridge.register_handler("AI_ATOMIC", handler)

    outcome = bridge.execute_step(
        step=_step(),
        classification=_classification(),
        binding=_binding(),
        result=StepResult(step_id="step_1", payload={"field": "value"}),
        context={"existing": 1},
    )

    assert outcome.status == "HANDLED"
    assert seen == [("step_1", "AI_ATOMIC", "AI_ATOMIC", {"field": "value"}, {"existing": 1})]


def test_dict_handler_result_is_normalized_into_step_outcome() -> None:
    bridge = ExecutorBridge()

    def handler(step, classification, binding, result, context):
        return {
            "status": "NORMALIZED",
            "context_update": {"normalized": True},
            "payload": {"ok": True},
        }

    bridge.register_handler("AI_ATOMIC", handler)

    outcome = bridge.execute_step(
        step=_step(),
        classification=_classification(),
        binding=_binding(),
        result=StepResult(step_id="step_1", payload={"field": "value"}),
        context={},
    )

    assert outcome == StepOutcome(
        step_id="step_1",
        status="NORMALIZED",
        context_update={"normalized": True},
        payload={"ok": True},
    )


def test_bridge_dispatches_by_runtime_binding_execution_mode() -> None:
    bridge = ExecutorBridge()
    called_modes: list[str] = []

    def handler(step, classification, binding, result, context):
        called_modes.append(binding.execution_mode.value)
        return {"status": "BOUND", "context_update": {}, "payload": {}}

    bridge.register_handler("AI_ATOMIC", handler)

    outcome = bridge.execute_step(
        step=_step(),
        classification=_classification(),
        binding=_binding(),
        result=StepResult(step_id="step_1", payload={"field": "value"}),
        context={},
    )

    assert outcome.status == "BOUND"
    assert called_modes == ["AI_ATOMIC"]


def test_bridge_has_no_public_method_for_arbitrary_tool_execution() -> None:
    bridge = ExecutorBridge()

    assert not hasattr(bridge, "execute_tool")
    assert not hasattr(bridge, "call_tool")
    assert not hasattr(bridge, "execute_raw_tool")


def _step() -> ContractStep:
    return ContractStep(
        step_id="step_1",
        instruction="Extract fields",
        input_schema={"type": "object"},
        raw={"step_id": "step_1"},
    )


def _classification() -> StepClassification:
    return StepClassification(
        step_id="step_1",
        execution_mode=ExecutionMode.AI_ATOMIC,
        raw={"execution_mode": "AI_ATOMIC"},
    )


def _binding() -> RuntimeBinding:
    return RuntimeBinding(
        step_id="step_1",
        execution_mode=ExecutionMode.AI_ATOMIC,
        connector_ref=None,
        raw={"execution_mode": "AI_ATOMIC"},
    )
