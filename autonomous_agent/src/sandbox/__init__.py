"""Sandbox — isolated code execution environment.

Generated code runs inside Docker containers (with subprocess fallback)
so it cannot affect the host system. Resource limits (CPU, memory, disk,
timeout) are enforced per execution.

  sandbox_manager:  Chooses Docker or subprocess, runs tests, returns results
  docker_executor:  Docker container lifecycle and resource limits
  resource_limits:  Configurable CPU/memory/disk/timeout constraints
  safety_checker:   AST + Bandit static analysis before execution
"""
