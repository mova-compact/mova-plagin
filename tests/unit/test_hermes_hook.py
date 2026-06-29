from __future__ import annotations

import inspect

from mova_contract_plugin.evidence import EvidenceWriter
from mova_contract_plugin.hooks.hermes import HermesContractHook
from mova_contract_plugin.session import ContractSession
from mova_contract_plugin.types import (
    ContractPackage,
    ContractStep,
    ExecutionMode,
    RuntimeBinding,
    StepClassification,
)


def test_on_agent_init_returns_ready() -> None:
    hook = HermesContractHook(ContractSession(_build_package()))

    result = hook.on_agent_init()

    assert result["status"] == "ready"
    assert result["contract_done"] is False
    assert result["current_step_id"] == "step_1"


def test_on_agent_init_does_not_mutate_session() -> None:
    session = ContractSession(_build_package())
    hook = HermesContractHook(session)

    hook.on_agent_init()

    assert session.current_step_id() == "step_1"
    assert session.context() == {}


def test_on_pre_execute_denies_unknown_tool() -> None:
    hook = HermesContractHook(ContractSession(_build_package()))

    result = hook.on_pre_execute(
        {"tool_name": "other_tool", "arguments": {}, "metadata": {}}
    )

    assert result == {
        "status": "denied",
        "reason_code": "unknown_tool",
        "message": "Only submit_step_result is allowed during contract execution.",
    }


def test_on_pre_execute_denies_missing_result() -> None:
    hook = HermesContractHook(ContractSession(_build_package()))

    result = hook.on_pre_execute(
        {"tool_name": "submit_step_result", "arguments": {}, "metadata": {}}
    )

    assert result == {"status": "denied", "reason_code": "missing_result"}


def test_on_pre_execute_submits_valid_result() -> None:
    session = ContractSession(_build_package())
    hook = HermesContractHook(session)

    result = hook.on_pre_execute(
        {
            "tool_name": "submit_step_result",
            "arguments": {"result": {"field": "value"}},
            "metadata": {},
        }
    )

    assert result["status"] == "step_complete"
    assert result["step_id"] == "step_1"
    assert session.context() == {"step_1": {"field": "value"}}


def test_on_pre_execute_advances_session() -> None:
    session = ContractSession(_build_package())
    hook = HermesContractHook(session)

    hook.on_pre_execute(
        {
            "tool_name": "submit_step_result",
            "arguments": {"result": {"field": "value"}},
            "metadata": {},
        }
    )

    assert session.current_step_id() == "step_2"


def test_final_step_response_includes_contract_complete_true() -> None:
    session = ContractSession(_build_single_step_package())
    hook = HermesContractHook(session)

    result = hook.on_pre_execute(
        {
            "tool_name": "submit_step_result",
            "arguments": {"result": {"field": "value"}},
            "metadata": {},
        }
    )

    assert result["contract_complete"] is True


def test_on_prompt_visibility_includes_current_step_id() -> None:
    hook = HermesContractHook(ContractSession(_build_package()))

    result = hook.on_prompt_visibility()

    assert result["status"] == "active"
    assert "step_1" in result["prompt"]


def test_on_prompt_visibility_does_not_expose_future_step_id() -> None:
    hook = HermesContractHook(ContractSession(_build_package()))

    result = hook.on_prompt_visibility()

    assert "step_2" not in result["prompt"]


def test_on_prompt_visibility_exposes_only_submit_step_result() -> None:
    hook = HermesContractHook(ContractSession(_build_package()))

    result = hook.on_prompt_visibility()

    assert result["visible_tools"] == ["submit_step_result"]


def test_on_evidence_handoff_returns_records_count() -> None:
    writer = EvidenceWriter()
    session = ContractSession(_build_single_step_package(), evidence_writer=writer)
    hook = HermesContractHook(session)
    hook.on_pre_execute(
        {
            "tool_name": "submit_step_result",
            "arguments": {"result": {"field": "value"}},
            "metadata": {},
        }
    )

    result = hook.on_evidence_handoff()

    assert result == {"status": "ok", "records_count": 3}


def test_adapter_does_not_import_hermes() -> None:
    import mova_contract_plugin.hooks.hermes as hermes_module

    source = inspect.getsource(hermes_module)

    assert "import hermes" not in source.lower()
    assert "from hermes" not in source.lower()


def test_adapter_does_not_expose_package_flow() -> None:
    hook = HermesContractHook(ContractSession(_build_package()))

    visibility = hook.on_prompt_visibility()
    init_state = hook.on_agent_init()

    assert "flow" not in visibility["prompt"].lower()
    assert "step_2" not in visibility["prompt"]
    assert "flow" not in "".join(init_state.keys()).lower()


def test_adapter_reuses_contract_session_behavior() -> None:
    session = ContractSession(_build_package())
    hook = HermesContractHook(session)

    hook.on_pre_execute(
        {
            "tool_name": "submit_step_result",
            "arguments": {"result": {"field": "value"}},
            "metadata": {},
        }
    )

    assert session.context() == {"step_1": {"field": "value"}}
    assert session.current_step_id() == "step_2"


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
        manifest={"contract_id": "hermes-hook-contract", "version": "0.1.0"},
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
        manifest={"contract_id": "hermes-hook-contract", "version": "0.1.0"},
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
