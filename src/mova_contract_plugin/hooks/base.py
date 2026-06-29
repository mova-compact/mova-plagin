from __future__ import annotations

from typing import Protocol


class AgentHook(Protocol):
    def get_tool_definitions(self) -> list[dict]: ...

    def handle_tool_call(self, tool_name: str, arguments: dict) -> dict: ...

    def get_current_prompt(self) -> str: ...
