# Contract Package Format

## Required Files

Every package must contain:

- `manifest.json`
- `flow.json`
- `classification_results.json`
- `runtime_binding_set.json`

## Minimal Shapes

### manifest.json

```json
{
  "contract_id": "minimal-invoice-contract",
  "version": "0.1.0"
}
```

### flow.json

```json
{
  "steps": [
    {
      "step_id": "extract_invoice_data",
      "instruction": "Extract invoice fields from input",
      "input_schema": {
        "type": "object"
      }
    }
  ]
}
```

### classification_results.json

```json
{
  "results": {
    "extract_invoice_data": {
      "step_id": "extract_invoice_data",
      "execution_mode": "AI_ATOMIC"
    }
  }
}
```

### runtime_binding_set.json

```json
{
  "bindings": {
    "extract_invoice_data": {
      "step_id": "extract_invoice_data",
      "execution_mode": "AI_ATOMIC",
      "connector_ref": null
    }
  }
}
```

## Validation Invariants

- All required files must exist.
- Each file must contain a JSON object.
- `flow.json.steps` must be a non-empty list.
- Each step must contain:
  - `step_id`
  - `instruction`
- `input_schema` and `output_schema`, when present, must be JSON objects.
- Every step in `flow.json` must have a classification.
- Every step in `flow.json` must have a runtime binding.
- `step_id` values must be unique.
- `classification.execution_mode` must equal `binding.execution_mode`.
- `execution_mode` must be one of:
  - `AI_ATOMIC`
  - `HUMAN`
  - `RULE`
  - `EXTERNAL`

## Minimal Invoice Example

Reference:

- [examples/minimal_invoice_contract](/D:/Projects_MOVA/mova-plagin/examples/minimal_invoice_contract)

Steps:

1. `extract_invoice_data` (`AI_ATOMIC`)
2. `approve_invoice` (`HUMAN`)
3. `finalize_invoice` (`RULE`)

This package is used by the integration test:

- [test_full_contract_run.py](/D:/Projects_MOVA/mova-plagin/tests/integration/test_full_contract_run.py)
