"""Safety and support utilities — not part of the core agent loop.

  circuit_breaker:  Stops iteration if the agent is looping on the same error
  context_hygiene:  Monitors token budget and compacts context before overflow
  execution_hooks:  Pre/post-iteration safety guardrails (blocks dangerous
                    commands, protects sensitive files, enforces token limits)
  state_saver:      Checkpoint/resume support (saves state every 5 iterations)
  metrics_collector: Records token usage, test pass rates, iteration duration
"""
