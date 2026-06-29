from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import BindingViolation, ClassificationViolation, PackageValidationError
from .types import ContractPackage, ContractStep, ExecutionMode, RuntimeBinding, StepClassification
from .validation import validate_package

_REQUIRED_FILES = (
    "manifest.json",
    "flow.json",
    "classification_results.json",
    "runtime_binding_set.json",
)


def load_package(package_path: str | Path) -> ContractPackage:
    base_path = Path(package_path)
    payloads = {name: _read_json(base_path / name) for name in _REQUIRED_FILES}

    flow = payloads["flow.json"]
    steps_payload = flow.get("steps")
    if not isinstance(steps_payload, list):
        raise PackageValidationError("flow.json must contain a list at 'steps'")

    steps = [_build_step(item) for item in steps_payload]
    classifications = _build_classifications(payloads["classification_results.json"])
    bindings = _build_bindings(payloads["runtime_binding_set.json"])

    package = ContractPackage(
        manifest=payloads["manifest.json"],
        flow=flow,
        classifications=classifications,
        bindings=bindings,
        steps=steps,
    )
    return validate_package(package)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise PackageValidationError(f"required package file is missing: {path.name}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PackageValidationError(f"invalid JSON in {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise PackageValidationError(f"{path.name} must contain a JSON object")
    return data


def _build_step(raw: Any) -> ContractStep:
    if not isinstance(raw, dict):
        raise PackageValidationError("each flow step must be a JSON object")

    step_id = str(raw.get("step_id") or "").strip()
    instruction = str(raw.get("instruction") or "").strip()
    if not step_id:
        raise PackageValidationError("flow step is missing required field 'step_id'")
    if not instruction:
        raise PackageValidationError(f"flow step '{step_id}' is missing required field 'instruction'")

    input_schema = raw.get("input_schema")
    output_schema = raw.get("output_schema")
    if input_schema is not None and not isinstance(input_schema, dict):
        raise PackageValidationError(f"flow step '{step_id}' input_schema must be an object when present")
    if output_schema is not None and not isinstance(output_schema, dict):
        raise PackageValidationError(f"flow step '{step_id}' output_schema must be an object when present")

    return ContractStep(
        step_id=step_id,
        instruction=instruction,
        input_schema=input_schema,
        output_schema=output_schema,
        raw=dict(raw),
    )


def _build_classifications(payload: dict[str, Any]) -> dict[str, StepClassification]:
    results = payload.get("results")
    if not isinstance(results, dict):
        raise ClassificationViolation("classification_results.json must contain an object at 'results'")

    items: dict[str, StepClassification] = {}
    for step_id, raw in results.items():
        if not isinstance(raw, dict):
            raise ClassificationViolation(f"classification for step_id={step_id} must be an object")
        normalized_step_id = str(raw.get("step_id") or step_id).strip()
        execution_mode = _coerce_execution_mode(raw.get("execution_mode"), step_id=normalized_step_id)
        items[normalized_step_id] = StepClassification(
            step_id=normalized_step_id,
            execution_mode=execution_mode,
            raw=dict(raw),
        )
    return items


def _build_bindings(payload: dict[str, Any]) -> dict[str, RuntimeBinding]:
    bindings = payload.get("bindings")
    if not isinstance(bindings, dict):
        raise BindingViolation("runtime_binding_set.json must contain an object at 'bindings'")

    items: dict[str, RuntimeBinding] = {}
    for step_id, raw in bindings.items():
        if not isinstance(raw, dict):
            raise BindingViolation(f"binding for step_id={step_id} must be an object")
        normalized_step_id = str(raw.get("step_id") or step_id).strip()
        execution_mode = _coerce_execution_mode(raw.get("execution_mode"), step_id=normalized_step_id)
        connector_ref_raw = raw.get("connector_ref")
        connector_ref = None if connector_ref_raw is None else str(connector_ref_raw)
        items[normalized_step_id] = RuntimeBinding(
            step_id=normalized_step_id,
            execution_mode=execution_mode,
            connector_ref=connector_ref,
            raw=dict(raw),
        )
    return items


def _coerce_execution_mode(value: Any, *, step_id: str) -> ExecutionMode:
    normalized = str(value or "").strip()
    if not normalized:
        raise PackageValidationError(f"execution_mode is required for step_id={step_id}")
    try:
        return ExecutionMode(normalized)
    except ValueError as exc:
        raise PackageValidationError(f"unknown execution_mode '{normalized}' for step_id={step_id}") from exc
