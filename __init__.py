"""Hermes native plugin wrapper for mova-contract-plugin."""

from __future__ import annotations

try:
    from . import schemas, tools
except ImportError:  # pragma: no cover - top-level import fallback for local test/module loading
    import schemas  # type: ignore[no-redef]
    import tools  # type: ignore[no-redef]


def register(ctx) -> None:
    ctx.register_tool(
        name="submit_step_result",
        toolset="mova_contract",
        schema=schemas.SUBMIT_STEP_RESULT,
        handler=tools.submit_step_result,
        description="Submit result for the current MOVA contract step.",
    )
    if hasattr(ctx, "register_hook"):
        ctx.register_hook("post_tool_call", tools.on_post_tool_call)
