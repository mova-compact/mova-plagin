from __future__ import annotations

from typing import Iterable

from .errors import BindingViolation, ClassificationViolation, PackageValidationError
from .types import ContractPackage, ExecutionMode


def validate_package(package: ContractPackage) -> ContractPackage:
    if not isinstance(package.manifest, dict) or not package.manifest:
        raise PackageValidationError("manifest.json is required and must be a non-empty object")
    if not package.steps:
        raise PackageValidationError("flow.json must contain at least one step")

    _validate_unique_step_ids(package.step_ids_in_order())

    for step in package.steps:
        step_id = step.step_id
        if not step_id:
            raise PackageValidationError("every flow step must contain step_id")

        classification = package.classifications.get(step_id)
        if classification is None:
            raise ClassificationViolation(f"missing classification for step_id={step_id}")

        binding = package.bindings.get(step_id)
        if binding is None:
            raise BindingViolation(f"missing runtime binding for step_id={step_id}")

        if not isinstance(classification.execution_mode, ExecutionMode):
            raise ClassificationViolation(f"unknown classification execution_mode for step_id={step_id}")
        if not isinstance(binding.execution_mode, ExecutionMode):
            raise BindingViolation(f"unknown binding execution_mode for step_id={step_id}")
        if classification.execution_mode != binding.execution_mode:
            raise PackageValidationError(
                f"classification.execution_mode != binding.execution_mode for step_id={step_id}"
            )

    return package


def _validate_unique_step_ids(step_ids: Iterable[str]) -> None:
    seen: set[str] = set()
    for step_id in step_ids:
        if step_id in seen:
            raise PackageValidationError(f"duplicate step_id is invalid: {step_id}")
        seen.add(step_id)
