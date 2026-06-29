from __future__ import annotations

from mova_contract_plugin.executor_bridge import ExecutorBridge
from mova_contract_plugin.errors import FinalDecisionViolation
from mova_contract_plugin.session import ContractSession
from mova_contract_plugin.types import (
    ContractPackage,
    ContractStep,
    ExecutionMode,
    RuntimeBinding,
    StepClassification,
    StepResult,
)


def test_ai_atomic_with_top_level_approved_raises_final_decision_violation() -> None:
    session = ContractSession(_build_package(ExecutionMode.AI_ATOMIC))

    _assert_final_decision_violation(
        session,
        {"step_id": "step_1", "payload": {"approved": True}},
    )


def test_ai_atomic_with_nested_final_decision_raises_final_decision_violation() -> None:
    session = ContractSession(_build_package(ExecutionMode.AI_ATOMIC))

    _assert_final_decision_violation(
        session,
        {"step_id": "step_1", "payload": {"analysis": {"final_decision": "accept"}}},
    )


def test_ai_atomic_with_mixed_case_approved_raises_final_decision_violation() -> None:
    session = ContractSession(_build_package(ExecutionMode.AI_ATOMIC))

    _assert_final_decision_violation(
        session,
        {"step_id": "step_1", "payload": {"Approved": True}},
    )


def test_ai_atomic_with_list_item_containing_rejected_raises_final_decision_violation() -> None:
    session = ContractSession(_build_package(ExecutionMode.AI_ATOMIC))

    _assert_final_decision_violation(
        session,
        {
            "step_id": "step_1",
            "payload": {"items": [{"field": "x"}, {"rejected": True}]},
        },
    )


def test_valid_ai_atomic_extraction_passes() -> None:
    session = ContractSession(_build_package(ExecutionMode.AI_ATOMIC))

    outcome = session.submit_result(
        StepResult(step_id="step_1", payload={"customer_name": "Ada", "amount": 150})
    )

    assert outcome.status == "COMPLETED"
    assert session.is_done() is True
    assert session.context() == {"step_1": {"customer_name": "Ada", "amount": 150}}


def test_rule_can_emit_approved() -> None:
    session = ContractSession(_build_package(ExecutionMode.RULE))

    outcome = session.submit_result(
        StepResult(step_id="step_1", payload={"approved": True})
    )

    assert outcome.status == "COMPLETED"
    assert session.context() == {"step_1": {"approved": True}}


def test_human_can_emit_rejected() -> None:
    session = ContractSession(_build_package(ExecutionMode.HUMAN))

    outcome = session.submit_result(
        StepResult(step_id="step_1", payload={"rejected": True})
    )

    assert outcome.status == "COMPLETED"
    assert session.context() == {"step_1": {"rejected": True}}


def test_external_can_emit_decision() -> None:
    session = ContractSession(_build_package(ExecutionMode.EXTERNAL))

    outcome = session.submit_result(
        StepResult(step_id="step_1", payload={"decision": "allow"})
    )

    assert outcome.status == "COMPLETED"
    assert session.context() == {"step_1": {"decision": "allow"}}


def test_session_does_not_advance_after_violation() -> None:
    session = ContractSession(_build_package(ExecutionMode.AI_ATOMIC))

    _assert_final_decision_violation(
        session,
        {"step_id": "step_1", "payload": {"approved": True}},
    )

    assert session.current_step_id() == "step_1"
    assert session.is_done() is False
    assert session.context() == {}


def test_bridge_handler_is_not_called_after_guard_violation() -> None:
    bridge = ExecutorBridge()
    calls: list[str] = []

    def handler(step, classification, binding, result, context):
        calls.append(step.step_id)
        return {"status": "HANDLED", "context_update": {}, "payload": {}}

    bridge.register_handler("AI_ATOMIC", handler)
    session = ContractSession(
        _build_package(ExecutionMode.AI_ATOMIC),
        executor_bridge=bridge,
    )

    _assert_final_decision_violation(
        session,
        {"step_id": "step_1", "payload": {"business_decision": "accept"}},
    )

    assert calls == []
    assert session.current_step_id() == "step_1"


def _assert_final_decision_violation(
    session: ContractSession,
    result: StepResult | dict[str, object],
) -> None:
    try:
        session.submit_result(result)
    except FinalDecisionViolation:
        return
    raise AssertionError("FinalDecisionViolation was not raised")


def _build_package(mode: ExecutionMode) -> ContractPackage:
    step = ContractStep(
        step_id="step_1",
        instruction="Process payload",
        input_schema={"type": "object"},
        raw={"step_id": "step_1"},
    )
    return ContractPackage(
        manifest={"contract_id": "guard-contract", "version": "0.1.0"},
        flow={"steps": [{"step_id": "step_1"}]},
        classifications={
            "step_1": StepClassification(
                step_id="step_1",
                execution_mode=mode,
                raw={"execution_mode": mode.value},
            )
        },
        bindings={
            "step_1": RuntimeBinding(
                step_id="step_1",
                execution_mode=mode,
                connector_ref=None,
                raw={"execution_mode": mode.value},
            )
        },
        steps=[step],
    )
