# MVP Acceptance

## Checklist

- [x] Package validation
- [x] Session step order
- [x] Bridge execution
- [x] AI_ATOMIC guard
- [x] Evidence records
- [x] Generic hook
- [x] Hermes hook
- [x] OpenAI hook
- [x] Full E2E fake agent run

## Current Test Status

- Current passing test count: `80 passed`

## Verified MVP Scope

- Package loads from required JSON files.
- Validation rejects malformed or inconsistent packages.
- Session exposes only the current step.
- Bridge controls step execution.
- AI_ATOMIC guard blocks final-decision payloads.
- Evidence records are written for start, completion, failure, and contract completion.
- Generic hook drives fake agent execution without exposing future flow.
- Hermes hook adapts plain dict host events without importing Hermes.
- OpenAI-compatible adapter exposes one function tool without importing `openai`.
- End-to-end example proves contract-controlled execution order.

## Out Of Scope For Current MVP

- HTTP API
- External runtime
- LangChain hook
- Review queue
- Real LLM calls
- Real connector calls
