from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .types import EvidenceRecord


class EvidenceWriter:
    def __init__(self, path: str | Path | None = None):
        self._path = Path(path) if path is not None else None
        self._records: list[EvidenceRecord] = []
        self._episode_id = uuid4().hex

    def record(self, record: EvidenceRecord) -> None:
        self._records.append(record)
        if self._path is None:
            return

        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(asdict(record), ensure_ascii=True))
            handle.write("\n")

    def record_package_loaded(self, contract_id: str | None, payload: dict) -> None:
        self.record(
            self._build_record(
                contract_id=contract_id,
                step_id=None,
                execution_mode=None,
                status="package_loaded",
                reason_code="package_loaded",
                payload=payload,
            )
        )

    def record_step_started(
        self,
        contract_id: str | None,
        step_id: str,
        execution_mode,
        payload: dict | None = None,
    ) -> None:
        self.record(
            self._build_record(
                contract_id=contract_id,
                step_id=step_id,
                execution_mode=self._normalize_execution_mode(execution_mode),
                status="step_started",
                reason_code="step_started",
                payload=payload or {},
            )
        )

    def record_step_completed(
        self,
        contract_id: str | None,
        step_id: str,
        execution_mode,
        payload: dict | None = None,
    ) -> None:
        self.record(
            self._build_record(
                contract_id=contract_id,
                step_id=step_id,
                execution_mode=self._normalize_execution_mode(execution_mode),
                status="step_completed",
                reason_code="step_completed",
                payload=payload or {},
            )
        )

    def record_step_failed(
        self,
        contract_id: str | None,
        step_id: str,
        execution_mode,
        reason_code: str,
        payload: dict | None = None,
    ) -> None:
        self.record(
            self._build_record(
                contract_id=contract_id,
                step_id=step_id,
                execution_mode=self._normalize_execution_mode(execution_mode),
                status="step_failed",
                reason_code=reason_code,
                payload=payload or {},
            )
        )

    def record_contract_completed(
        self,
        contract_id: str | None,
        payload: dict | None = None,
    ) -> None:
        self.record(
            self._build_record(
                contract_id=contract_id,
                step_id=None,
                execution_mode=None,
                status="contract_completed",
                reason_code="contract_completed",
                payload=payload or {},
            )
        )

    def records(self) -> list[EvidenceRecord]:
        return list(self._records)

    def _build_record(
        self,
        contract_id: str | None,
        step_id: str | None,
        execution_mode: str | None,
        status: str,
        reason_code: str,
        payload: dict,
    ) -> EvidenceRecord:
        return EvidenceRecord(
            episode_id=self._episode_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            contract_id=contract_id,
            step_id=step_id,
            execution_mode=execution_mode,
            status=status,
            reason_code=reason_code,
            payload=dict(payload),
        )

    def _normalize_execution_mode(self, execution_mode) -> str | None:
        if execution_mode is None:
            return None
        value = getattr(execution_mode, "value", execution_mode)
        return str(value)
