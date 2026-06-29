from __future__ import annotations

from mova_contract_plugin.hooks.generic import GenericContractHook
from mova_contract_plugin.session import ContractSession
from mova_contract_plugin.types import (
    ContractPackage,
    ContractStep,
    ExecutionMode,
    RuntimeBinding,
    StepClassification,
)


def test_hook_exposes_exactly_one_tool() -> None:
    hook = GenericContractHook(ContractSession(_build_package()))

    tools = hook.get_tool_definitions()

    assert len(tools) == 1


def test_tool_name_is_submit_step_result() -> None:
    hook = GenericContractHook(ContractSession(_build_package()))

    tool = hook.get_tool_definitions()[0]

    assert tool["name"] == "submit_step_result"


def test_unknown_tool_is_denied() -> None:
    hook = GenericContractHook(ContractSession(_build_package()))

    response = hook.handle_tool_call("other_tool", {})

    assert response == {"status": "denied", "reason_code": "unknown_tool"}


def test_missing_result_is_denied() -> None:
    hook = GenericContractHook(ContractSession(_build_package()))

    response = hook.handle_tool_call("submit_step_result", {})

    assert response == {"status": "denied", "reason_code": "missing_result"}


def test_valid_tool_call_submits_current_step_result() -> None:
    session = ContractSession(_build_package())
    hook = GenericContractHook(session)

    response = hook.handle_tool_call("submit_step_result", {"result": {"field": "value"}})

    assert response["status"] == "step_complete"
    assert response["step_id"] == "step_1"
    assert session.context() == {"step_1": {"field": "value"}}


def test_valid_tool_call_advances_session() -> None:
    session = ContractSession(_build_package())
    hook = GenericContractHook(session)

    hook.handle_tool_call("submit_step_result", {"result": {"field": "value"}})

    assert session.current_step_id() == "step_2"


def test_when_session_completes_response_includes_contract_complete_true() -> None:
    session = ContractSession(_build_single_step_package())
    hook = GenericContractHook(session)

    response = hook.handle_tool_call("submit_step_result", {"result": {"field": "value"}})

    assert response["contract_complete"] is True


def test_get_current_prompt_includes_current_step_id() -> None:
    hook = GenericContractHook(ContractSession(_build_package()))

    prompt = hook.get_current_prompt()

    assert "step_1" in prompt


def test_get_current_prompt_does_not_expose_future_step_id() -> None:
    hook = GenericContractHook(ContractSession(_build_package()))

    prompt = hook.get_current_prompt()

    assert "step_2" not in prompt


def test_done_session_prompt_says_contract_is_complete() -> None:
    session = ContractSession(_build_single_step_package())
    hook = GenericContractHook(session)
    hook.handle_tool_call("submit_step_result", {"result": {"field": "value"}})

    assert hook.get_current_prompt() == "Contract is complete."


def test_done_session_tool_call_returns_contract_complete() -> None:
    session = ContractSession(_build_single_step_package())
    hook = GenericContractHook(session)
    hook.handle_tool_call("submit_step_result", {"result": {"field": "value"}})

    response = hook.handle_tool_call("submit_step_result", {"result": {"field": "again"}})

    assert response == {"status": "contract_complete"}


def test_hook_does_not_expose_package_flow() -> None:
    hook = GenericContractHook(ContractSession(_build_package()))

    prompt = hook.get_current_prompt()
    tool = hook.get_tool_definitions()[0]

    assert "steps" not in prompt
    assert "flow" not in prompt
    assert "steps" not in tool["description"].lower()


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
        manifest={"contract_id": "hook-contract", "version": "0.1.0"},
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


def _build_single_step_package() -> ContractPackage:
    step = ContractStep(
        step_id="step_1",
        instruction="Extract fields",
        input_schema={"type": "object"},
        raw={"step_id": "step_1"},
    )
    return ContractPackage(
        manifest={"contract_id": "hook-contract", "version": "0.1.0"},
        flow={"steps": [{"step_id": "step_1"}]},
        classifications={
            "step_1": StepClassification(
                step_id="step_1",
                execution_mode=ExecutionMode.AI_ATOMIC,
                raw={"execution_mode": "AI_ATOMIC"},
            )
        },
        bindings={
            "step_1": RuntimeBinding(
                step_id="step_1",
                execution_mode=ExecutionMode.AI_ATOMIC,
                connector_ref=None,
                raw={"execution_mode": "AI_ATOMIC"},
            )
        },
        steps=[step],
    )
