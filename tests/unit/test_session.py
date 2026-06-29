from __future__ import annotations

from mova_contract_plugin.executor_bridge import ExecutorBridge
from mova_contract_plugin.errors import StepOrderViolation
from mova_contract_plugin.session import ContractSession
from mova_contract_plugin.types import (
    ContractPackage,
    ContractStep,
    CurrentStepInstruction,
    ExecutionMode,
    RuntimeBinding,
    StepClassification,
    StepResult,
)


def test_session_starts_at_first_step() -> None:
    session = ContractSession(_build_package())

    assert session.is_done() is False
    assert session.current_step_id() == "step_1"


def test_current_instruction_exposes_only_current_step() -> None:
    session = ContractSession(_build_package())

    instruction = session.current_instruction()

    assert isinstance(instruction, CurrentStepInstruction)
    assert instruction.step_id == "step_1"
    assert instruction.execution_mode is ExecutionMode.AI_ATOMIC
    assert instruction.instruction == "Extract fields"
    assert instruction.input_schema == {"type": "object"}
    assert instruction.context == {}
    assert not hasattr(instruction, "steps")
    assert not hasattr(instruction, "flow")


def test_submit_result_advances_one_step() -> None:
    session = ContractSession(_build_package())

    outcome = session.submit_result(
        StepResult(step_id="step_1", payload={"field": "value"})
    )

    assert outcome.step_id == "step_1"
    assert outcome.status == "COMPLETED"
    assert session.current_step_id() == "step_2"
    assert session.is_done() is False


def test_wrong_step_id_raises_step_order_violation() -> None:
    session = ContractSession(_build_package())

    try:
        session.submit_result(StepResult(step_id="step_2", payload={"field": "value"}))
    except StepOrderViolation:
        pass
    else:
        raise AssertionError("StepOrderViolation was not raised")


def test_session_completes_after_last_step() -> None:
    session = ContractSession(_build_package())

    session.submit_result(StepResult(step_id="step_1", payload={"field": "value"}))
    session.submit_result(StepResult(step_id="step_2", payload={"approved": True}))

    assert session.is_done() is True
    assert session.current_step_id() is None
    assert session.current_instruction() is None


def test_context_accumulates_submitted_results() -> None:
    session = ContractSession(_build_package())

    session.submit_result(StepResult(step_id="step_1", payload={"field": "value"}))
    session.submit_result(StepResult(step_id="step_2", payload={"approved": True}))

    assert session.context() == {
        "step_1": {"field": "value"},
        "step_2": {"approved": True},
    }


def test_session_uses_executor_bridge() -> None:
    calls: list[tuple[str, str, str, dict[str, object]]] = []
    bridge = ExecutorBridge()

    def handler(step, classification, binding, result, context):
        calls.append(
            (
                step.step_id,
                classification.execution_mode.value,
                binding.execution_mode.value,
                dict(context),
            )
        )
        return {
            "status": "HANDLED",
            "context_update": {"bridge_step": {"accepted": True}},
            "payload": {"handled": True},
        }

    bridge.register_handler("AI_ATOMIC", handler)
    session = ContractSession(_build_package(), executor_bridge=bridge)

    outcome = session.submit_result(StepResult(step_id="step_1", payload={"field": "value"}))

    assert outcome.status == "HANDLED"
    assert calls == [("step_1", "AI_ATOMIC", "AI_ATOMIC", {})]
    assert session.current_step_id() == "step_2"
    assert session.context() == {"bridge_step": {"accepted": True}}


def test_full_flow_is_not_exposed_from_current_instruction() -> None:
    session = ContractSession(_build_package())

    instruction = session.current_instruction()

    assert isinstance(instruction, CurrentStepInstruction)
    assert instruction.step_id == "step_1"
    assert instruction.context == {}
    assert instruction.__dict__.keys() == {
        "step_id",
        "execution_mode",
        "instruction",
        "input_schema",
        "context",
    }


def _build_package() -> ContractPackage:
    steps = [
        ContractStep(
            step_id="step_1",
            instruction="Extract fields",
            input_schema={"type": "object"},
            raw={"step_id": "step_1"},
        ),
        ContractStep(
            step_id="step_2",
            instruction="Approve extraction",
            input_schema={"type": "object"},
            raw={"step_id": "step_2"},
        ),
    ]
    return ContractPackage(
        manifest={"contract_id": "test-contract", "version": "0.1.0"},
        flow={"steps": [{"step_id": "step_1"}, {"step_id": "step_2"}]},
        classifications={
            "step_1": StepClassification(
                step_id="step_1",
                execution_mode=ExecutionMode.AI_ATOMIC,
                raw={"execution_mode": "AI_ATOMIC"},
            ),
            "step_2": StepClassification(
                step_id="step_2",
                execution_mode=ExecutionMode.HUMAN,
                raw={"execution_mode": "HUMAN"},
            ),
        },
        bindings={
            "step_1": RuntimeBinding(
                step_id="step_1",
                execution_mode=ExecutionMode.AI_ATOMIC,
                connector_ref=None,
                raw={"execution_mode": "AI_ATOMIC"},
            ),
            "step_2": RuntimeBinding(
                step_id="step_2",
                execution_mode=ExecutionMode.HUMAN,
                connector_ref=None,
                raw={"execution_mode": "HUMAN"},
            ),
        },
        steps=steps,
    )
