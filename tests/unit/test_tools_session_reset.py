from __future__ import annotations

from types import SimpleNamespace

import tools


class FakeBridge:
    def __init__(self) -> None:
        self.registered: list[str] = []

    def register_handler(self, execution_mode, handler) -> None:
        self.registered.append(execution_mode)
        self.handler = handler


class FakeSession:
    instances: list[tuple[object, object, object]] = []

    def __init__(self, package, executor_bridge=None, evidence_writer=None):
        self.package = package
        self.executor_bridge = executor_bridge
        self.evidence_writer = evidence_writer
        FakeSession.instances.append((package, executor_bridge, evidence_writer))


class FakeAdapter:
    def __init__(self) -> None:
        self.execute = lambda *args, **kwargs: {"status": "COMPLETED", "context_update": {}, "payload": {}}


def test_get_or_create_session_resets_when_package_path_changes(monkeypatch) -> None:
    calls: list[str] = []
    fake_package = SimpleNamespace()

    def load_package(package_path):
        calls.append(package_path)
        return fake_package

    monkeypatch.setattr(tools, "_SESSION", object())
    monkeypatch.setattr(tools, "_SESSION_PACKAGE_PATH", "/old/path")
    monkeypatch.setattr(tools, "load_package", load_package)
    monkeypatch.setattr(tools, "ContractSession", FakeSession)
    monkeypatch.setattr(tools, "ExecutorBridge", FakeBridge)
    monkeypatch.setattr(tools, "EvidenceWriter", lambda path=None: {"path": path})
    monkeypatch.setattr(tools, "LocalExecutorAdapter", FakeAdapter)
    monkeypatch.delenv("MOVA_EVIDENCE_PATH", raising=False)

    session1 = tools._get_or_create_session("/new/path")
    session2 = tools._get_or_create_session("/new/path")

    assert session1 is session2
    assert calls == ["/new/path"]
    assert tools._SESSION_PACKAGE_PATH == "/new/path"
    assert isinstance(getattr(session1, "executor_bridge"), FakeBridge)
    assert getattr(session1, "executor_bridge").registered == ["AI_ATOMIC", "RULE", "EXTERNAL"]
    assert FakeSession.instances == [(fake_package, getattr(session1, "executor_bridge"), {"path": None})]
