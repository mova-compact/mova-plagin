from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def test_hermes_plugin_root_files_exist() -> None:
    root = _repo_root()

    assert (root / "plugin.yaml").exists()
    assert (root / "__init__.py").exists()
    assert (root / "schemas.py").exists()
    assert (root / "tools.py").exists()


def test_submit_step_result_schema_has_correct_name() -> None:
    schemas_module = _load_module("mova_contract_plugin_root.schemas", "schemas.py")

    assert schemas_module.SUBMIT_STEP_RESULT["name"] == "submit_step_result"


def test_root_init_exposes_register() -> None:
    root_module = _load_package_root()

    assert hasattr(root_module, "register")
    assert callable(root_module.register)


def test_submit_step_result_returns_json_when_contract_path_missing(monkeypatch) -> None:
    tools_module = _load_module("mova_contract_plugin_root.tools", "tools.py")
    monkeypatch.delenv("MOVA_CONTRACT_PACKAGE_PATH", raising=False)

    result = tools_module.submit_step_result({"result": {"field": "value"}})

    parsed = json.loads(result)
    assert parsed == {
        "success": False,
        "error": "MOVA_CONTRACT_PACKAGE_PATH is not set",
    }


def _load_package_root():
    root = _repo_root()
    spec = importlib.util.spec_from_file_location(
        "mova_contract_plugin_root",
        root / "__init__.py",
        submodule_search_locations=[str(root)],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_module(module_name: str, relative_path: str):
    root = _repo_root()
    spec = importlib.util.spec_from_file_location(module_name, root / relative_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
