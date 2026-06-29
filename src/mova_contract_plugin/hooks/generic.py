from __future__ import annotations

from ..session import ContractSession


class GenericContractHook:
    def __init__(self, session: ContractSession):
        self._session = session

    def get_tool_definitions(self) -> list[dict]:
        return [
            {
                "name": "submit_step_result",
                "description": (
                    "Submit result for the current contract step only. "
                    "The agent may only submit a result for the current active step."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "result": {
                            "type": "object",
                            "description": "Result payload for the current contract step.",
                        }
                    },
                    "required": ["result"],
                    "additionalProperties": False,
                },
            }
        ]

    def handle_tool_call(self, tool_name: str, arguments: dict) -> dict:
        if self._session.is_done():
            return {"status": "contract_complete"}

        if tool_name != "submit_step_result":
            return {"status": "denied", "reason_code": "unknown_tool"}

        if "result" not in arguments:
            return {"status": "denied", "reason_code": "missing_result"}

        step_id = self._session.current_step_id()
        outcome = self._session.submit_result(
            {"step_id": step_id, "payload": arguments["result"]}
        )
        response = {
            "status": "step_complete",
            "step_id": outcome.step_id,
            "outcome": {
                "status": outcome.status,
                "context_update": dict(outcome.context_update),
                "payload": dict(outcome.payload),
            },
        }
        if self._session.is_done():
            response["contract_complete"] = True
        return response

    def get_current_prompt(self) -> str:
        if self._session.is_done():
            return "Contract is complete."

        instruction = self._session.current_instruction()
        assert instruction is not None
        return (
            f"Current step_id: {instruction.step_id}\n"
            f"Execution mode: {instruction.execution_mode.value}\n"
            f"Instruction: {instruction.instruction}\n"
            f"Current context: {instruction.context}\n"
            "Call submit_step_result with a result object for the current step only."
        )
