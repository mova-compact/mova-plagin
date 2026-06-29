from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from mova_contract_plugin.evidence import EvidenceWriter
from mova_contract_plugin.errors import FinalDecisionViolation
from mova_contract_plugin.executor_bridge import ExecutorBridge
from mova_contract_plugin.session import ContractSession
from mova_contract_plugin.types import (
    ContractPackage,
    ContractStep,
    EvidenceRecord,
    ExecutionMode,
    RuntimeBinding,
    StepClassification,
    StepResult,
)


def test_evidence_writer_stores_in_memory_when_path_is_none() -> None:
    writer = EvidenceWriter()

    writer.record_package_loaded("contract-1", {"source": "fixture"})

    records = writer.records()
    assert len(records) == 1
    assert records[0].contract_id == "contract-1"
    assert records[0].status == "package_loaded"


def test_evidence_writer_writes_jsonl_when_path_is_provided() -> None:
    output_path = (
        Path("D:/Projects_MOVA/mova-plagin/tests/.tmp")
        / f"evidence_{uuid4().hex}.jsonl"
    )
    writer = EvidenceWriter(output_path)

    writer.record_step_started("contract-1", "step_1", "AI_ATOMIC", {"x": 1})
    writer.record_step_completed("contract-1", "step_1", "AI_ATOMIC", {"y": 2})

    lines = output_path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 2
    parsed = [json.loads(line) for line in lines]
    assert parsed[0]["status"] == "step_started"
    assert parsed[1]["status"] == "step_completed"


def test_jsonl_contains_valid_json_object_per_line() -> None:
    writer = EvidenceWriter()

    record = EvidenceRecord(
        episode_id="episode-1",
        timestamp="2026-06-29T00:00:00+00:00",
        contract_id="contract-1",
        step_id="step_1",
        execution_mode="AI_ATOMIC",
        status="step_started",
        reason_code="step_started",
        payload={"x": 1},
    )

    writer.record(record)

    stored = writer.records()[0]
    parsed = json.loads(json.dumps(stored.__dict__))
    assert parsed["episode_id"] == "episode-1"
    assert parsed["payload"] == {"x": 1}


def test_record_includes_episode_id_and_timestamp() -> None:
    writer = EvidenceWriter()

    writer.record_step_started("contract-1", "step_1", "AI_ATOMIC", {"x": 1})

    record = writer.records()[0]
    assert record.episode_id
    assert record.timestamp


def test_contract_session_writes_step_started_and_step_completed_on_success() -> None:
    writer = EvidenceWriter()
    session = ContractSession(_build_package(ExecutionMode.AI_ATOMIC), evidence_writer=writer)

    session.submit_result(StepResult(step_id="step_1", payload={"field": "value"}))

    statuses = [record.status for record in writer.records()]
    assert statuses == ["step_started", "step_completed", "contract_completed"]


def test_contract_session_writes_contract_completed_after_last_step() -> None:
    writer = EvidenceWriter()
    session = ContractSession(_build_package(ExecutionMode.AI_ATOMIC), evidence_writer=writer)

    session.submit_result(StepResult(step_id="step_1", payload={"field": "value"}))

    contract_completed = writer.records()[-1]
    assert contract_completed.status == "contract_completed"
    assert contract_completed.contract_id == "guard-contract"
    assert contract_completed.step_id is None


def test_final_decision_violation_writes_step_failed() -> None:
    writer = EvidenceWriter()
    session = ContractSession(_build_package(ExecutionMode.AI_ATOMIC), evidence_writer=writer)

    try:
        session.submit_result(StepResult(step_id="step_1", payload={"approved": True}))
    except FinalDecisionViolation:
        pass
    else:
        raise AssertionError("FinalDecisionViolation was not raised")

    failed = writer.records()[-1]
    assert failed.status == "step_failed"
    assert failed.reason_code == "final_decision_violation"


def test_executor_bridge_error_writes_step_failed() -> None:
    writer = EvidenceWriter()
    bridge = ExecutorBridge()

    def handler(step, classification, binding, result, context):
        raise RuntimeError("bridge failed")

    bridge.register_handler("AI_ATOMIC", handler)
    session = ContractSession(
        _build_package(ExecutionMode.AI_ATOMIC),
        executor_bridge=bridge,
        evidence_writer=writer,
    )

    try:
        session.submit_result(StepResult(step_id="step_1", payload={"field": "value"}))
    except RuntimeError:
        pass
    else:
        raise AssertionError("RuntimeError was not raised")

    statuses = [record.status for record in writer.records()]
    assert statuses == ["step_started", "step_failed"]
    assert writer.records()[-1].reason_code == "executor_error"


def test_evidence_failure_is_not_swallowed_silently() -> None:
    class FailingEvidenceWriter(EvidenceWriter):
        def record(self, record: EvidenceRecord) -> None:
            raise RuntimeError("evidence write failed")

    writer = FailingEvidenceWriter()
    session = ContractSession(_build_package(ExecutionMode.AI_ATOMIC), evidence_writer=writer)

    try:
        session.submit_result(StepResult(step_id="step_1", payload={"field": "value"}))
    except RuntimeError as exc:
        assert str(exc) == "evidence write failed"
    else:
        raise AssertionError("evidence write failure was not raised")


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
