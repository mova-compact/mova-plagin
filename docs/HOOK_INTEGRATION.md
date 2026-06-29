# Hook Integration

## Rule Set

- Adapters must not expose future flow.
- Adapters must not duplicate session logic.
- Adapters must submit results through `ContractSession`.
- Adapters must not choose the next step.
- Adapters must not call arbitrary tools.

## GenericContractHook

### Purpose

- Framework-neutral adapter around `ContractSession`.

### Input

```python
hook.handle_tool_call(
    "submit_step_result",
    {"result": {"field": "value"}},
)
```

### Output

```python
{
    "status": "step_complete",
    "step_id": "extract_invoice_data",
    "outcome": {
        "status": "COMPLETED",
        "context_update": {"extract_invoice_data": {"field": "value"}},
        "payload": {"field": "value"},
    },
    "contract_complete": False,
}
```

### Prompt Surface

- Includes:
  - current `step_id`
  - current `execution_mode`
  - current instruction
  - current context
  - explicit instruction to call `submit_step_result`
- Excludes:
  - full flow
  - future steps

## HermesContractHook

### Purpose

- Plain dict adapter for Hermes-like host event surfaces.
- Does not import Hermes.

### Input

```python
hook.on_pre_execute(
    {
        "tool_name": "submit_step_result",
        "arguments": {
            "result": {"field": "value"},
        },
        "metadata": {},
    }
)
```

### Output

```python
{
    "status": "step_complete",
    "step_id": "extract_invoice_data",
    "outcome": {
        "status": "COMPLETED",
        "context_update": {"extract_invoice_data": {"field": "value"}},
        "payload": {"field": "value"},
    },
    "contract_complete": False,
}
```

### Visibility

```python
{
    "status": "active",
    "prompt": "...",
    "visible_tools": ["submit_step_result"],
}
```

## OpenAI-Compatible Function Adapter

### Purpose

- OpenAI-compatible function-based adapter without OpenAI SDK dependency.
- This surface is provided by:
  - `build_openai_tools(session)`
  - `handle_openai_tool_call(tool_call, session)`

### Tool Schema

```python
tools = build_openai_tools(session)
```

Returns exactly one function tool:

- `submit_step_result`

### Input

Dict-like:

```python
{
    "function": {
        "name": "submit_step_result",
        "arguments": {"result": {"field": "value"}},
    }
}
```

Object-like:

```python
tool_call.function.name
tool_call.function.arguments
```

### Output

Returns a JSON string:

```json
{"status":"step_complete","step_id":"extract_invoice_data","outcome":{"status":"COMPLETED","context_update":{"extract_invoice_data":{"field":"value"}},"payload":{"field":"value"}}}
```

## Error Shapes

Unknown tool:

```python
{"status": "denied", "reason_code": "unknown_tool"}
```

Missing result:

```python
{"status": "denied", "reason_code": "missing_result"}
```

Contract complete:

```python
{"status": "contract_complete"}
```
