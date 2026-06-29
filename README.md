# mova-contract-plugin

Lightweight Python contract execution plugin for agent frameworks.

## What This Package Is

- A small contract execution layer for Python agent hosts.
- The contract controls process order.
- The agent is only allowed to submit the result for the current step.
- `ContractSession` owns step order and execution state.
- `ExecutorBridge` owns controlled step execution side effects.
- Hook adapters are thin wrappers over `ContractSession`.

## What This Package Is Not

- Not an HTTP API.
- Not an external runtime.
- Not MOVA Agent API.
- Not a deep host fork.

## Installed MVP Surface

- `load_package()`
- `ContractSession`
- `ExecutorBridge`
- `EvidenceWriter`
- `GenericContractHook`
- `HermesContractHook`
- OpenAI-compatible function-tool helpers:
  - `build_openai_tools()`
  - `handle_openai_tool_call()`

## Minimal Usage

```python
from mova_contract_plugin import (
    ContractSession,
    EvidenceWriter,
    ExecutorBridge,
    GenericContractHook,
    load_package,
)

package = load_package("examples/minimal_invoice_contract")

bridge = ExecutorBridge()

def ai_handler(step, classification, binding, result, context):
    return {
        "status": "COMPLETED",
        "context_update": {step.step_id: dict(result.payload)},
        "payload": dict(result.payload),
    }

def human_handler(step, classification, binding, result, context):
    return {
        "status": "COMPLETED",
        "context_update": {step.step_id: dict(result.payload)},
        "payload": dict(result.payload),
    }

def rule_handler(step, classification, binding, result, context):
    return {
        "status": "COMPLETED",
        "context_update": {step.step_id: dict(result.payload)},
        "payload": dict(result.payload),
    }

bridge.register_handler("AI_ATOMIC", ai_handler)
bridge.register_handler("HUMAN", human_handler)
bridge.register_handler("RULE", rule_handler)

writer = EvidenceWriter(path=None)
session = ContractSession(
    package,
    executor_bridge=bridge,
    evidence_writer=writer,
)
hook = GenericContractHook(session)

fake_results = {
    "extract_invoice_data": {
        "invoice_number": "INV-001",
        "amount": 1200,
        "currency": "EUR",
    },
    "approve_invoice": {
        "approved": True,
        "reviewer": "ops",
    },
    "finalize_invoice": {
        "record": "invoice_status",
    },
}

while True:
    if session.is_done():
        break

    current_step_id = session.current_step_id()
    prompt = hook.get_current_prompt()
    print(prompt)

    response = hook.handle_tool_call(
        "submit_step_result",
        {"result": fake_results[current_step_id]},
    )
    if response.get("contract_complete"):
        break

print(session.context())
print(len(writer.records()))
```

## Available Hooks

- `GenericContractHook`
- `HermesContractHook`
- OpenAI-compatible functions:
  - `build_openai_tools(session)`
  - `handle_openai_tool_call(tool_call, session)`

## Hermes Plugin Installation

```bash
hermes plugins install mova-compact/mova-contract-plugin --enable
hermes plugins list
```

Required environment:

```bash
MOVA_CONTRACT_PACKAGE_PATH=/path/to/contract_package
MOVA_EVIDENCE_PATH=/path/to/evidence.jsonl
```

Notes:

- installed per active Hermes profile
- registers the `submit_step_result` tool
- contract execution is controlled by `ContractSession`

## Example Contract Package

- `examples/minimal_invoice_contract/`

This example provides a 3-step invoice process:

1. `extract_invoice_data` (`AI_ATOMIC`)
2. `approve_invoice` (`HUMAN`)
3. `finalize_invoice` (`RULE`)

## Test Command

```bash
python -m pytest -p no:cacheprovider tests
```

## Development

Run tests:

```bash
python -m pytest -p no:cacheprovider tests
```

CI automatically validates:

- Python 3.11
- Python 3.12
