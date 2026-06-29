from __future__ import annotations

import json

from mova_contract_plugin.hooks.openai import (
    build_openai_tools,
    handle_openai_tool_call,
)
from mova_contract_plugin.session import ContractSession
from mova_contract_plugin.types import (
    ContractPackage,
    ContractStep,
    ExecutionMode,
    RuntimeBinding,
    StepClassification,
)


class _FunctionCall:
    def __init__(self, name: str, arguments):
        self.name = name
        self.arguments = arguments


class _ToolCall:
    def __init__(self, name: str, arguments):
        self.function = _FunctionCall(name, arguments)


def test_build_openai_tools_returns_exactly_one_function_tool() -> None:
    tools = build_openai_tools(ContractSession(_build_package()))

    assert len(tools) == 1
    assert tools[0]["type"] == "function"


def test_tool_name_is_submit_step_result() -> None:
    tool = build_openai_tools(ContractSession(_build_package()))[0]

    assert tool["function"]["name"] == "submit_step_result"


def test_tool_parameters_require_result() -> None:
    tool = build_openai_tools(ContractSession(_build_package()))[0]

    assert tool["function"]["parameters"]["required"] == ["result"]


def test_handle_dict_tool_call_successfully_submits_result() -> None:
    session = ContractSession(_build_package())

    response = handle_openai_tool_call(
        {
            "function": {
                "name": "submit_step_result",
                "arguments": {"result": {"field": "value"}},
            }
        },
        session,
    )

    parsed = json.loads(response)
    assert parsed["status"] == "step_complete"
    assert parsed["step_id"] == "step_1"
    assert session.context() == {"step_1": {"field": "value"}}


def test_handle_object_like_tool_call_successfully_submits_result() -> None:
    session = ContractSession(_build_package())

    response = handle_openai_tool_call(
        _ToolCall("submit_step_result", {"result": {"field": "value"}}),
        session,
    )

    parsed = json.loads(response)
    assert parsed["status"] == "step_complete"
    assert session.current_step_id() == "step_2"


def test_json_string_arguments_are_parsed() -> None:
    session = ContractSession(_build_package())

    response = handle_openai_tool_call(
        _ToolCall("submit_step_result", '{"result": {"field": "value"}}'),
        session,
    )

    parsed = json.loads(response)
    assert parsed["status"] == "step_complete"
    assert session.context() == {"step_1": {"field": "value"}}


def test_dict_arguments_are_accepted() -> None:
    session = ContractSession(_build_package())

    response = handle_openai_tool_call(
        _ToolCall("submit_step_result", {"result": {"field": "value"}}),
        session,
    )

    parsed = json.loads(response)
    assert parsed["outcome"]["payload"] == {"field": "value"}


def test_missing_result_returns_denied_missing_result_json() -> None:
    session = ContractSession(_build_package())

    response = handle_openai_tool_call(
        _ToolCall("submit_step_result", {}),
        session,
    )

    assert json.loads(response) == {
        "status": "denied",
        "reason_code": "missing_result",
    }


def test_unknown_tool_returns_denied_unknown_tool_json() -> None:
    session = ContractSession(_build_package())

    response = handle_openai_tool_call(
        _ToolCall("other_tool", {"result": {"field": "value"}}),
        session,
    )

    assert json.loads(response) == {
        "status": "denied",
        "reason_code": "unknown_tool",
    }


def test_done_session_returns_contract_complete_json() -> None:
    session = ContractSession(_build_single_step_package())
    handle_openai_tool_call(
        _ToolCall("submit_step_result", {"result": {"field": "value"}}),
        session,
    )

    response = handle_openai_tool_call(
        _ToolCall("submit_step_result", {"result": {"field": "again"}}),
        session,
    )

    assert json.loads(response) == {"status": "contract_complete"}


def test_valid_tool_call_advances_session() -> None:
    session = ContractSession(_build_package())

    handle_openai_tool_call(
        _ToolCall("submit_step_result", {"result": {"field": "value"}}),
        session,
    )

    assert session.current_step_id() == "step_2"


def test_final_step_response_includes_contract_complete_true() -> None:
    session = ContractSession(_build_single_step_package())

    response = handle_openai_tool_call(
        _ToolCall("submit_step_result", {"result": {"field": "value"}}),
        session,
    )

    parsed = json.loads(response)
    assert parsed["contract_complete"] is True


def test_response_is_always_valid_json_string() -> None:
    session = ContractSession(_build_package())

    response = handle_openai_tool_call(
        _ToolCall("submit_step_result", {"result": {"field": "value"}}),
        session,
    )

    parsed = json.loads(response)
    assert isinstance(response, str)
    assert parsed["status"] == "step_complete"


def test_package_imports_without_openai_installed() -> None:
    import mova_contract_plugin

    assert hasattr(mova_contract_plugin, "build_openai_tools")
    assert hasattr(mova_contract_plugin, "handle_openai_tool_call")


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
        manifest={"contract_id": "openai-hook-contract", "version": "0.1.0"},
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
        manifest={"contract_id": "openai-hook-contract", "version": "0.1.0"},
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
