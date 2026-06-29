# Architecture

## Component Diagram

```text
contract package files
-> load_package()
-> validate_package()
-> ContractSession
   -> AI_ATOMIC guard
   -> EvidenceWriter
   -> ExecutorBridge
-> hook adapter
   -> GenericContractHook
   -> HermesContractHook
   -> OpenAI-compatible tool adapter
```

## Core Invariants

- Contract package validation happens before runtime execution.
- `ContractSession` owns process order.
- The host cannot choose the next step directly.
- The agent can only submit a result for the current step.
- `ExecutorBridge` is the only execution surface for step handling.
- `AI_ATOMIC` steps must not emit final business decisions.
- Evidence records observe execution and do not change execution behavior.
- Hooks must not expose future flow.
- Hooks must not duplicate session logic.

## Execution Lifecycle

```text
load_package()
-> validate_package()
-> create ExecutorBridge
-> create EvidenceWriter
-> create ContractSession
-> attach hook adapter
-> host/agent receives current prompt
-> host/agent submits current step result
-> ContractSession validates step order
-> AI_ATOMIC guard runs if needed
-> EvidenceWriter records step_started
-> ExecutorBridge executes current step
-> EvidenceWriter records step_completed or step_failed
-> session advances
-> EvidenceWriter records contract_completed when done
```

## Adapter Model

- Adapters are thin.
- Adapters translate host-facing tool/event shape into `ContractSession.submit_result(...)`.
- Adapters do not own process order.
- Adapters do not own side effects.
- Adapters do not inspect future steps.
- Adapters do not call arbitrary tools.

Current adapters:

- `GenericContractHook`
- `HermesContractHook`
- OpenAI-compatible tool helpers

## Why ContractSession Owns Process

- Step order is contract state, not adapter state.
- Current step visibility must remain single-source.
- Guard logic must run before execution and before adapter-specific behavior.
- Session advancement must happen only after successful step execution.

If process ownership moved into adapters, step order would diverge between hosts.

## Why ExecutorBridge Owns Side Effects

- Side effects happen at step execution, not at session orchestration.
- Execution mode handlers must receive:
  - step
  - classification
  - binding
  - submitted result
  - current context
- Session should not perform host-specific action logic.

This keeps step execution controlled and testable.

## Why Hooks Are Thin

- Host integrations should adapt shape, not recreate runtime behavior.
- Thin hooks reduce divergence between Generic, Hermes, and OpenAI surfaces.
- Thin hooks prevent hidden process-order forks.
- Thin hooks keep the contract as the process controller.
