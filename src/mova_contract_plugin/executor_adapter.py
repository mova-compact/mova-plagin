from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Protocol

from .types import ContractStep, RuntimeBinding, StepClassification, StepResult


class ExecutorBackend(Protocol):
    def execute(
        self,
        *,
        step_id: str,
        execution_mode: str,
        binding_raw: dict[str, Any],
        result_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]: ...


class ProfileLocalExecutorBackend:
    """Adapter backend that validates inputs via the admin-profile local executor package."""

    def __init__(self, executor_root: Path | None = None):
        self._executor_root = executor_root or self._default_executor_root()

    def execute(
        self,
        *,
        step_id: str,
        execution_mode: str,
        binding_raw: dict[str, Any],
        result_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        executor_module = self._load_executor_module()
        executor = executor_module.Executor(self._executor_root)

        synthetic_input = {
            "step_id": step_id,
            "execution_mode": execution_mode,
            "binding_raw": dict(binding_raw),
            "result_payload": dict(result_payload),
            "context": dict(context),
        }
        synthetic_step = {
            "kind": "bounded_result",
            "fields": {
                "step_id": "input.step_id",
                "execution_mode": "input.execution_mode",
                "binding_raw": "input.binding_raw",
                "result_payload": "input.result_payload",
                "context": "input.context",
            },
        }
        resolved = executor._build_bounded_result(  # noqa: SLF001 - thin adapter around the existing executor
            synthetic_step,
            {
                "input": synthetic_input,
                "step_outputs": {},
                "last_step_id": None,
                "run_id": "adapter-run",
            },
        )

        if resolved.get("step_id") != step_id:
            raise RuntimeError("local executor returned mismatched step_id")
        if resolved.get("execution_mode") != execution_mode:
            raise RuntimeError("local executor returned mismatched execution_mode")
        if resolved.get("binding_raw") != dict(binding_raw):
            raise RuntimeError("local executor returned mismatched binding_raw")
        if resolved.get("result_payload") != dict(result_payload):
            raise RuntimeError("local executor returned mismatched result_payload")
        if resolved.get("context") != dict(context):
            raise RuntimeError("local executor returned mismatched context")

        return {
            "status": "COMPLETED",
            "context_update": {step_id: dict(result_payload)},
            "payload": dict(result_payload),
        }

    def _default_executor_root(self) -> Path:
        hermes_home = os.environ.get("HERMES_HOME")
        if hermes_home:
            return Path(hermes_home).resolve() / "mova-local-executor"
        return Path("/home/mova/.hermes/profiles/admin/mova-local-executor")

    def _load_executor_module(self):
        src_dir = self._executor_root / "src"
        build_dir = self._executor_root / "build" / "lib"
        for candidate in (src_dir, build_dir):
            if candidate.exists() and str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))

        from mova_local_executor import executor as executor_module  # type: ignore

        return executor_module


class LocalExecutorAdapter:
    def __init__(self, backend: ExecutorBackend | None = None):
        self._backend = backend or ProfileLocalExecutorBackend()

    def execute(
        self,
        step: ContractStep,
        classification: StepClassification,
        binding: RuntimeBinding,
        result: StepResult,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        backend_result = self._backend.execute(
            step_id=step.step_id,
            execution_mode=classification.execution_mode.value,
            binding_raw=dict(binding.raw),
            result_payload=dict(result.payload),
            context=dict(context),
        )

        status = str(backend_result.get("status") or "COMPLETED")
        context_update = backend_result.get("context_update")
        if not isinstance(context_update, dict):
            context_update = {step.step_id: dict(result.payload)}
        payload = backend_result.get("payload")
        if not isinstance(payload, dict):
            payload = dict(result.payload)

        return {
            "status": status,
            "context_update": context_update,
            "payload": payload,
        }
