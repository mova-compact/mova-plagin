from __future__ import annotations

import json
from typing import Any

from ..session import ContractSession


def build_openai_tools(session: ContractSession) -> list[dict]:
    del session
    return [
        {
            "type": "function",
            "function": {
                "name": "submit_step_result",
                "description": (
                    "Submit result data for the current contract step only. "
                    "The contract controls execution order and only the current step may be completed."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "result": {
                            "type": "object",
                            "description": "Result data for the current contract step",
                        }
                    },
                    "required": ["result"],
                },
            },
        }
    ]


def handle_openai_tool_call(tool_call, session: ContractSession) -> str:
    if session.is_done():
        return json.dumps({"status": "contract_complete"}, ensure_ascii=True)

    tool_name, arguments = _extract_tool_call(tool_call)
    if tool_name != "submit_step_result":
        return json.dumps(
            {"status": "denied", "reason_code": "unknown_tool"},
            ensure_ascii=True,
        )

    normalized_arguments = _normalize_arguments(arguments)
    if "result" not in normalized_arguments:
        return json.dumps(
            {"status": "denied", "reason_code": "missing_result"},
            ensure_ascii=True,
        )

    outcome = session.submit_result(
        {
            "step_id": session.current_step_id(),
            "payload": normalized_arguments["result"],
        }
    )
    response: dict[str, Any] = {
        "status": "step_complete",
        "step_id": outcome.step_id,
        "outcome": {
            "status": outcome.status,
            "context_update": dict(outcome.context_update),
            "payload": dict(outcome.payload),
        },
    }
    if session.is_done():
        response["contract_complete"] = True
    return json.dumps(response, ensure_ascii=True)


def _extract_tool_call(tool_call) -> tuple[str | None, Any]:
    if isinstance(tool_call, dict):
        if "function" in tool_call and isinstance(tool_call["function"], dict):
            function = tool_call["function"]
            return function.get("name"), function.get("arguments")
        return tool_call.get("name"), tool_call.get("arguments")

    function = getattr(tool_call, "function", None)
    if function is not None:
        return getattr(function, "name", None), getattr(function, "arguments", None)

    return getattr(tool_call, "name", None), getattr(tool_call, "arguments", None)


def _normalize_arguments(arguments: Any) -> dict[str, Any]:
    if arguments is None:
        return {}
    if isinstance(arguments, str):
        loaded = json.loads(arguments)
        if not isinstance(loaded, dict):
            raise ValueError("tool call arguments JSON must decode to an object")
        return dict(loaded)
    if isinstance(arguments, dict):
        return dict(arguments)
    raise TypeError("tool call arguments must be dict, JSON string, or None")
