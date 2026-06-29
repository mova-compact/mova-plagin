"""Hermes plugin tool handlers for mova-contract-plugin."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from mova_contract_plugin import (
    ContractSession,
    EvidenceWriter,
    ExecutorBridge,
    load_package,
)

logger = logging.getLogger(__name__)

_SESSION: ContractSession | None = None


def submit_step_result(args: dict, **kwargs) -> str:
    """Submit the current step result through the MOVA ContractSession."""
    del kwargs
    if not isinstance(args, dict):
        return json.dumps(
            {"success": False, "error": "arguments must be an object"},
            ensure_ascii=True,
        )

    package_path = os.getenv("MOVA_CONTRACT_PACKAGE_PATH", "").strip()
    if not package_path:
        return json.dumps(
            {"success": False, "error": "MOVA_CONTRACT_PACKAGE_PATH is not set"},
            ensure_ascii=True,
        )

    if "result" not in args:
        return json.dumps(
            {"status": "denied", "reason_code": "missing_result"},
            ensure_ascii=True,
        )

    result_payload = args.get("result")
    if not isinstance(result_payload, dict):
        return json.dumps(
            {"success": False, "error": "result must be an object"},
            ensure_ascii=True,
        )

    try:
        session = _get_or_create_session(package_path)
        if session.is_done():
            return json.dumps({"status": "contract_complete"}, ensure_ascii=True)

        outcome = session.submit_result(
            {
                "step_id": session.current_step_id(),
                "payload": dict(result_payload),
            }
        )
        response: dict[str, Any] = {
            "status": "step_complete",
            "step_id": outcome.step_id,
            "outcome": {
                "status": outcome.status,
                "context_update": dict(outcome.context_update),
                "payload": dict(outcome.payload),
            },
            "contract_complete": session.is_done(),
        }
        return json.dumps(response, ensure_ascii=True)
    except Exception as exc:
        return json.dumps(
            {
                "success": False,
                "error": str(exc),
            },
            ensure_ascii=True,
        )


def on_post_tool_call(tool_name, args=None, result=None, task_id=None, **kwargs) -> None:
    """Lightweight debug hook for Hermes plugin lifecycle."""
    del args, result, task_id, kwargs
    if tool_name == "submit_step_result":
        logger.debug("mova-contract-plugin handled submit_step_result")


def _get_or_create_session(package_path: str) -> ContractSession:
    global _SESSION
    if _SESSION is not None:
        return _SESSION

    package = load_package(package_path)
    bridge = ExecutorBridge()
    evidence_path = os.getenv("MOVA_EVIDENCE_PATH", "").strip()
    writer = EvidenceWriter(Path(evidence_path)) if evidence_path else EvidenceWriter(path=None)
    _SESSION = ContractSession(
        package,
        executor_bridge=bridge,
        evidence_writer=writer,
    )
    return _SESSION
