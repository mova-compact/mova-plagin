from __future__ import annotations

from mova_contract_plugin.executor_adapter import LocalExecutorAdapter
from mova_contract_plugin.executor_bridge import ExecutorBridge
from mova_contract_plugin.session import ContractSession
from mova_contract_plugin.types import (
    ContractPackage,
    ContractStep,
    ExecutionMode,
    RuntimeBinding,
    StepClassification,
    StepOutcome,
    StepResult,
)


class FakeBackend:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def execute(
        self,
        *,
        step_id: str,
        execution_mode: str,
        binding_raw: dict[str, object],
        result_payload: dict[str, object],
        context: dict[str, object],
    ) -> dict[str, object]:
        self.calls.append(
            {
                "step_id": step_id,
                "execution_mode": execution_mode,
                "binding_raw": dict(binding_raw),
                "result_payload": dict(result_payload),
                "context": dict(context),
            }
        )
        return {
            "status": "COMPLETED",
            "context_update": {"backend": {"seen": True, "step_id": step_id}},
            "payload": {"from_backend": True, "step_id": step_id},
        }


def test_local_executor_adapter_passes_binding_and_context_to_backend() -> None:
    backend = FakeBackend()
    adapter = LocalExecutorAdapter(backend=backend)

    result = adapter.execute(
        _step(),
        _classification(),
        _binding(),
        StepResult(step_id="step_1", payload={"ping": True}),
        {"existing": 1},
    )

    assert backend.calls == [
        {
            "step_id": "step_1",
            "execution_mode": "AI_ATOMIC",
            "binding_raw": {"step_id": "step_1", "execution_mode": "AI_ATOMIC", "connector_ref": None, "raw_note": "binding"},
            "result_payload": {"ping": True},
            "context": {"existing": 1},
        }
    ]
    assert result == {
        "status": "COMPLETED",
        "context_update": {"backend": {"seen": True, "step_id": "step_1"}},
        "payload": {"from_backend": True, "step_id": "step_1"},
    }


def test_executor_bridge_uses_local_executor_adapter_and_session_updates_context() -> None:
    backend = FakeBackend()
    adapter = LocalExecutorAdapter(backend=backend)
    bridge = ExecutorBridge()
    bridge.register_handler("AI_ATOMIC", adapter.execute)
    package = _package()
    session = ContractSession(package, executor_bridge=bridge)

    outcome = session.submit_result(StepResult(step_id="step_1", payload={"ping": True}))

    assert outcome == StepOutcome(
        step_id="step_1",
        status="COMPLETED",
        context_update={"backend": {"seen": True, "step_id": "step_1"}},
        payload={"from_backend": True, "step_id": "step_1"},
    )
    assert session.context() == {"backend": {"seen": True, "step_id": "step_1"}}


def _step() -> ContractStep:
    return ContractStep(
        step_id="step_1",
        instruction="Extract fields",
        input_schema={"type": "object"},
        raw={"step_id": "step_1"},
    )


def _classification() -> StepClassification:
    return StepClassification(
        step_id="step_1",
        execution_mode=ExecutionMode.AI_ATOMIC,
        raw={"execution_mode": "AI_ATOMIC"},
    )


def _binding() -> RuntimeBinding:
    return RuntimeBinding(
        step_id="step_1",
        execution_mode=ExecutionMode.AI_ATOMIC,
        connector_ref=None,
        raw={"step_id": "step_1", "execution_mode": "AI_ATOMIC", "connector_ref": None, "raw_note": "binding"},
    )


def _package() -> ContractPackage:
    return ContractPackage(
        manifest={"contract_id": "test-contract", "version": "0.1.0"},
        flow={"steps": [{"step_id": "step_1"}]},
        classifications={"step_1": _classification()},
        bindings={"step_1": _binding()},
        steps=[_step()],
    )
