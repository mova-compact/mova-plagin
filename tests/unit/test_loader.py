from __future__ import annotations

from pathlib import Path

import pytest

from mova_contract_plugin.errors import ClassificationViolation, PackageValidationError
from mova_contract_plugin.loader import load_package
from mova_contract_plugin.types import ExecutionMode


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def test_valid_minimal_package_loads() -> None:
    package = load_package(FIXTURES_DIR / "minimal_contract_package")

    assert package.manifest["contract_id"] == "minimal-contract-package"
    assert package.step_ids_in_order() == ["extract_invoice_fields"]
    assert package.classifications["extract_invoice_fields"].execution_mode is ExecutionMode.AI_ATOMIC
    assert package.bindings["extract_invoice_fields"].execution_mode is ExecutionMode.AI_ATOMIC


def test_missing_classification_fails() -> None:
    with pytest.raises(ClassificationViolation):
        load_package(FIXTURES_DIR / "invalid_missing_classification")


def test_missing_binding_fails() -> None:
    with pytest.raises(PackageValidationError, match="missing runtime binding"):
        load_package(FIXTURES_DIR / "invalid_missing_binding")


def test_mismatched_execution_mode_fails() -> None:
    with pytest.raises(PackageValidationError, match="classification.execution_mode != binding.execution_mode"):
        load_package(FIXTURES_DIR / "invalid_mismatched_execution_mode")


def test_duplicate_step_id_is_invalid() -> None:
    with pytest.raises(PackageValidationError, match="duplicate step_id"):
        load_package(FIXTURES_DIR / "invalid_duplicate_step_id")


def test_empty_flow_is_invalid() -> None:
    with pytest.raises(PackageValidationError, match="at least one step"):
        load_package(FIXTURES_DIR / "invalid_empty_flow")
