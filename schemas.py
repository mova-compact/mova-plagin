"""Hermes plugin tool schemas for mova-contract-plugin."""

SUBMIT_STEP_RESULT = {
    "name": "submit_step_result",
    "description": "Submit result for current MOVA contract step",
    "parameters": {
        "type": "object",
        "properties": {
            "result": {
                "type": "object",
                "description": "Result data for the current contract step",
            }
        },
        "required": ["result"],
    },
}
