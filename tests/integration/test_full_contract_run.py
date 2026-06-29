from __future__ import annotations

from pathlib import Path

import pytest

from mova_contract_plugin.evidence import EvidenceWriter
from mova_contract_plugin.errors import FinalDecisionViolation
from mova_contract_plugin.executor_bridge import ExecutorBridge
from mova_contract_plugin.hooks.generic import GenericContractHook
from mova_contract_plugin.loader import load_package
from mova_contract_plugin.session import ContractSession
from mova_contract_plugin.types import StepOutcome


def test_full_contract_run_end_to_end() -> None:
    package = load_package(_example_contract_path())
    bridge = ExecutorBridge()
    writer = EvidenceWriter(path=None)
    executed_steps: list[str] = []

    def ai_handler(step, classification, binding, result, context):
        executed_steps.append(step.step_id)
        assert classification.execution_mode.value == "AI_ATOMIC"
        assert binding.execution_mode.value == "AI_ATOMIC"
        assert "approve_invoice" not in context
        return StepOutcome(
            step_id=step.step_id,
            status="COMPLETED",
            context_update={
                step.step_id: {
                    "invoice_number": result.payload["invoice_number"],
                    "amount": result.payload["amount"],
                    "currency": result.payload["currency"],
                }
            },
            payload=dict(result.payload),
        )

    def human_handler(step, classification, binding, result, context):
        executed_steps.append(step.step_id)
        assert classification.execution_mode.value == "HUMAN"
        assert binding.execution_mode.value == "HUMAN"
        assert "extract_invoice_data" in context
        return StepOutcome(
            step_id=step.step_id,
            status="COMPLETED",
            context_update={step.step_id: dict(result.payload)},
            payload=dict(result.payload),
        )

    def rule_handler(step, classification, binding, result, context):
        executed_steps.append(step.step_id)
        assert classification.execution_mode.value == "RULE"
        assert binding.execution_mode.value == "RULE"
        assert context["approve_invoice"]["approved"] is True
        final_status = (
            "invoice_approved"
            if context["approve_invoice"]["approved"]
            else "invoice_rejected"
        )
        return StepOutcome(
            step_id=step.step_id,
            status="COMPLETED",
            context_update={
                step.step_id: {
                    "final_status": final_status,
                    "recorded": True,
                }
            },
            payload=dict(result.payload),
        )

    bridge.register_handler("AI_ATOMIC", ai_handler)
    bridge.register_handler("HUMAN", human_handler)
    bridge.register_handler("RULE", rule_handler)

    session = ContractSession(package, executor_bridge=bridge, evidence_writer=writer)
    hook = GenericContractHook(session)

    first_prompt = hook.get_current_prompt()
    assert "extract_invoice_data" in first_prompt
    assert "approve_invoice" not in first_prompt
    assert "finalize_invoice" not in first_prompt

    fake_agent_results = {
        "extract_invoice_data": {
            "invoice_number": "INV-001",
            "amount": 1200,
            "currency": "EUR",
        },
        "approve_invoice": {
            "approved": True,
            "reviewer": "ops",
        },
        "finalize_invoice": {
            "record": "invoice_status",
        },
    }

    seen_step_ids: list[str] = []
    while not session.is_done():
        current_step_id = session.current_step_id()
        assert current_step_id is not None
        seen_step_ids.append(current_step_id)

        prompt = hook.get_current_prompt()
        assert current_step_id in prompt
        future_steps = [step_id for step_id in fake_agent_results if step_id != current_step_id]
        for future_step_id in future_steps:
            if future_step_id in seen_step_ids:
                continue
            assert future_step_id not in prompt

        tool_definition = hook.get_tool_definitions()[0]
        assert tool_definition["name"] == "submit_step_result"
        assert "step_id" not in tool_definition["parameters"]["properties"]

        response = hook.handle_tool_call(
            "submit_step_result",
            {"result": fake_agent_results[current_step_id]},
        )
        assert response["status"] == "step_complete"
        assert response["step_id"] == current_step_id

    assert session.is_done() is True
    assert executed_steps == [
        "extract_invoice_data",
        "approve_invoice",
        "finalize_invoice",
    ]
    assert seen_step_ids == [
        "extract_invoice_data",
        "approve_invoice",
        "finalize_invoice",
    ]
    assert session.context() == {
        "extract_invoice_data": {
            "invoice_number": "INV-001",
            "amount": 1200,
            "currency": "EUR",
        },
        "approve_invoice": {
            "approved": True,
            "reviewer": "ops",
        },
        "finalize_invoice": {
            "final_status": "invoice_approved",
            "recorded": True,
        },
    }

    records = writer.records()
    statuses = [record.status for record in records]
    assert statuses.count("step_started") == 3
    assert statuses.count("step_completed") == 3
    assert statuses.count("contract_completed") == 1


def test_ai_atomic_step_cannot_emit_final_decision() -> None:
    package = load_package(_example_contract_path())
    writer = EvidenceWriter(path=None)
    session = ContractSession(package, evidence_writer=writer)
    hook = GenericContractHook(session)

    with pytest.raises(FinalDecisionViolation):
        hook.handle_tool_call(
            "submit_step_result",
            {"result": {"approved": True, "invoice_number": "INV-001"}},
        )

    assert session.current_step_id() == "extract_invoice_data"
    statuses = [record.status for record in writer.records()]
    assert statuses == ["step_failed"]


def _example_contract_path() -> Path:
    return Path(__file__).resolve().parents[2] / "examples" / "minimal_invoice_contract"
