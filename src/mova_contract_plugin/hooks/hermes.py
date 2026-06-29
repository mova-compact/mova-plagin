from __future__ import annotations

from ..session import ContractSession


class HermesContractHook:
    def __init__(self, session: ContractSession):
        self._session = session

    def on_agent_init(self, host_context: dict | None = None) -> dict:
        del host_context
        return {
            "status": "ready",
            "contract_done": self._session.is_done(),
            "current_step_id": self._session.current_step_id(),
        }

    def on_pre_execute(self, event: dict) -> dict:
        if self._session.is_done():
            return {"status": "contract_complete"}

        tool_name = event.get("tool_name")
        arguments = event.get("arguments", {})
        if tool_name != "submit_step_result":
            return {
                "status": "denied",
                "reason_code": "unknown_tool",
                "message": "Only submit_step_result is allowed during contract execution.",
            }

        if "result" not in arguments:
            return {
                "status": "denied",
                "reason_code": "missing_result",
            }

        outcome = self._session.submit_result(
            {
                "step_id": self._session.current_step_id(),
                "payload": arguments["result"],
            }
        )
        return {
            "status": "step_complete",
            "step_id": outcome.step_id,
            "outcome": {
                "status": outcome.status,
                "context_update": dict(outcome.context_update),
                "payload": dict(outcome.payload),
            },
            "contract_complete": self._session.is_done(),
        }

    def on_prompt_visibility(self, host_context: dict | None = None) -> dict:
        del host_context
        if self._session.is_done():
            return {
                "status": "contract_complete",
                "prompt": "Contract is complete.",
            }

        instruction = self._session.current_instruction()
        assert instruction is not None
        return {
            "status": "active",
            "prompt": (
                f"Current step_id: {instruction.step_id}\n"
                f"Execution mode: {instruction.execution_mode.value}\n"
                f"Instruction: {instruction.instruction}\n"
                f"Current context: {instruction.context}\n"
                "Call submit_step_result with a result object for the current step only."
            ),
            "visible_tools": ["submit_step_result"],
        }

    def on_evidence_handoff(self, host_context: dict | None = None) -> dict:
        del host_context
        evidence_writer = getattr(self._session, "_evidence_writer", None)
        if evidence_writer is None:
            return {"status": "ok", "records_count": 0}

        records = evidence_writer.records()
        return {"status": "ok", "records_count": len(records)}
