"""Execution Hooks System for Safety Guardrails.

Based on Claude Code Mastery PreToolUse/PostToolUse hook patterns:
- Pre-execution hooks: Validate, block dangerous operations
- Post-execution hooks: Auto-format, cleanup, verify results
- Hook registry for extensible safety rules
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from pathlib import Path

from src.ui.logger import get_logger


class HookPhase(Enum):
    """When the hook executes."""
    PRE_EXECUTION = "pre_execution"
    POST_EXECUTION = "post_execution"


class HookResult(Enum):
    """Result of hook execution."""
    ALLOW = "allow"          # Continue with operation
    BLOCK = "block"          # Stop operation
    MODIFY = "modify"        # Continue with modified input/output
    WARN = "warn"            # Log warning but continue
    REQUIRE_APPROVAL = "require_approval"  # Pause for user approval


@dataclass
class HookContext:
    """Context passed to hooks for decision making."""
    operation: str           # e.g., "write_file", "execute_code", "call_llm"
    agent_type: str          # Which agent is performing the operation
    iteration: int           # Current iteration number
    target: str              # e.g., filename, command, etc.
    content: Any             # The actual content/data
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HookResponse:
    """Response from a hook execution."""
    result: HookResult
    message: str = ""
    modified_content: Optional[Any] = None
    blocked_reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class ExecutionHook(ABC):
    """Base class for execution hooks."""

    def __init__(self, name: str, phase: HookPhase, priority: int = 50):
        """Initialize hook.

        Args:
            name: Unique hook name
            phase: When hook executes (pre/post)
            priority: Execution order (lower = earlier, 0-100)
        """
        self.name = name
        self.phase = phase
        self.priority = priority
        self.enabled = True
        self.logger = get_logger(f'hook.{name}')

    @abstractmethod
    def should_run(self, context: HookContext) -> bool:
        """Determine if this hook should run for the given context."""
        pass

    @abstractmethod
    def execute(self, context: HookContext) -> HookResponse:
        """Execute the hook logic."""
        pass


class BlockDangerousCommandsHook(ExecutionHook):
    """Block dangerous shell commands from execution.

    Based on Claude Code safety patterns - blocks commands that could:
    - Delete important files
    - Modify system configuration
    - Expose sensitive data
    """

    DANGEROUS_PATTERNS = [
        # Destructive commands
        r'\brm\s+-rf\s+[/~]',           # rm -rf / or ~
        r'\brm\s+-rf\s+\*',             # rm -rf *
        r'>\s*/dev/sd',                 # Write to disk devices
        r'mkfs\.',                      # Format filesystems
        r':(){:|:&};:',                 # Fork bomb

        # System modification
        r'\bsudo\s+',                   # Sudo commands
        r'\bchmod\s+777',               # Overly permissive
        r'\bchown\s+.*:.*\s+/',         # Changing system file ownership

        # Data exfiltration
        r'curl.*\|\s*sh',               # Pipe from internet to shell
        r'wget.*\|\s*sh',
        r'\bnc\s+-l',                   # Netcat listener
        r'curl.*--data.*password',      # Sending passwords

        # Credential access
        r'cat\s+.*/\.ssh/',             # SSH keys
        r'cat\s+.*/\.aws/',             # AWS credentials
        r'cat\s+.*\.env',               # Environment files
    ]

    def __init__(self):
        super().__init__(
            name="block_dangerous_commands",
            phase=HookPhase.PRE_EXECUTION,
            priority=10  # Run early
        )
        self.compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_PATTERNS
        ]

    def should_run(self, context: HookContext) -> bool:
        return context.operation in ['execute_command', 'run_shell']

    def execute(self, context: HookContext) -> HookResponse:
        command = str(context.content)

        for pattern in self.compiled_patterns:
            if pattern.search(command):
                self.logger.warning(
                    "dangerous_command_blocked",
                    command=command[:100],
                    pattern=pattern.pattern
                )
                return HookResponse(
                    result=HookResult.BLOCK,
                    blocked_reason=f"Command matches dangerous pattern: {pattern.pattern}",
                    message="Blocked potentially dangerous command"
                )

        return HookResponse(result=HookResult.ALLOW)


class ProtectSensitiveFilesHook(ExecutionHook):
    """Prevent modification of sensitive files."""

    PROTECTED_PATTERNS = [
        r'\.env$',
        r'\.env\.',
        r'credentials\.json$',
        r'secrets\.ya?ml$',
        r'\.ssh/',
        r'\.aws/',
        r'\.git/config$',
        r'__pycache__/',
        r'\.pyc$',
        r'node_modules/',
    ]

    def __init__(self):
        super().__init__(
            name="protect_sensitive_files",
            phase=HookPhase.PRE_EXECUTION,
            priority=10
        )
        self.compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.PROTECTED_PATTERNS
        ]

    def should_run(self, context: HookContext) -> bool:
        return context.operation in ['write_file', 'delete_file', 'modify_file']

    def execute(self, context: HookContext) -> HookResponse:
        filepath = str(context.target)

        for pattern in self.compiled_patterns:
            if pattern.search(filepath):
                self.logger.warning(
                    "sensitive_file_protected",
                    filepath=filepath,
                    pattern=pattern.pattern
                )
                return HookResponse(
                    result=HookResult.REQUIRE_APPROVAL,
                    message=f"Modifying protected file: {filepath}",
                    blocked_reason=f"File matches protected pattern: {pattern.pattern}"
                )

        return HookResponse(result=HookResult.ALLOW)


class AutoFormatCodeHook(ExecutionHook):
    """Auto-format code after generation.

    Applies formatting standards to generated code.
    """

    def __init__(self):
        super().__init__(
            name="auto_format_code",
            phase=HookPhase.POST_EXECUTION,
            priority=80  # Run late
        )

    def should_run(self, context: HookContext) -> bool:
        return (
            context.operation == 'write_file' and
            context.target.endswith(('.py', '.js', '.ts', '.json'))
        )

    def execute(self, context: HookContext) -> HookResponse:
        content = str(context.content)
        modified = content

        # Basic formatting for Python files
        if context.target.endswith('.py'):
            # Ensure file ends with newline
            if not modified.endswith('\n'):
                modified += '\n'

            # Remove trailing whitespace
            lines = modified.split('\n')
            lines = [line.rstrip() for line in lines]
            modified = '\n'.join(lines)

        # Basic formatting for JSON files
        elif context.target.endswith('.json'):
            try:
                import json
                parsed = json.loads(modified)
                modified = json.dumps(parsed, indent=2) + '\n'
            except json.JSONDecodeError:
                pass  # Leave as-is if invalid JSON

        if modified != content:
            return HookResponse(
                result=HookResult.MODIFY,
                modified_content=modified,
                message="Auto-formatted code"
            )

        return HookResponse(result=HookResult.ALLOW)


class TokenBudgetHook(ExecutionHook):
    """Enforce token budget limits for LLM calls."""

    def __init__(self, max_tokens: int = 50000):
        super().__init__(
            name="token_budget",
            phase=HookPhase.PRE_EXECUTION,
            priority=20
        )
        self.max_tokens = max_tokens
        self.tokens_used = 0

    def should_run(self, context: HookContext) -> bool:
        return context.operation == 'call_llm'

    def execute(self, context: HookContext) -> HookResponse:
        estimated_tokens = context.metadata.get('estimated_tokens', 0)

        if self.tokens_used + estimated_tokens > self.max_tokens:
            self.logger.warning(
                "token_budget_exceeded",
                used=self.tokens_used,
                requested=estimated_tokens,
                limit=self.max_tokens
            )
            return HookResponse(
                result=HookResult.WARN,
                message=f"Token budget warning: {self.tokens_used}/{self.max_tokens}",
                warnings=[f"Approaching token limit: {self.tokens_used + estimated_tokens}/{self.max_tokens}"]
            )

        return HookResponse(result=HookResult.ALLOW)

    def record_usage(self, tokens: int):
        """Record actual token usage after LLM call."""
        self.tokens_used += tokens


class IterationGuardHook(ExecutionHook):
    """Guard against excessive iterations on same error."""

    def __init__(self, max_same_error: int = 3):
        super().__init__(
            name="iteration_guard",
            phase=HookPhase.PRE_EXECUTION,
            priority=15
        )
        self.max_same_error = max_same_error
        self.error_history: List[str] = []

    def should_run(self, context: HookContext) -> bool:
        return context.operation == 'start_iteration'

    def execute(self, context: HookContext) -> HookResponse:
        current_error = context.metadata.get('previous_error', '')

        if not current_error:
            return HookResponse(result=HookResult.ALLOW)

        # Normalize error for comparison
        normalized_error = self._normalize_error(current_error)

        # Count occurrences
        same_error_count = sum(
            1 for e in self.error_history[-5:]
            if self._normalize_error(e) == normalized_error
        )

        self.error_history.append(current_error)

        if same_error_count >= self.max_same_error:
            self.logger.warning(
                "repeated_error_detected",
                error=normalized_error[:100],
                count=same_error_count + 1
            )
            return HookResponse(
                result=HookResult.WARN,
                message=f"Same error repeated {same_error_count + 1} times",
                warnings=["Consider a different approach - same error recurring"]
            )

        return HookResponse(result=HookResult.ALLOW)

    def _normalize_error(self, error: str) -> str:
        """Normalize error for comparison."""
        # Remove line numbers and file paths
        normalized = re.sub(r'line \d+', 'line X', error)
        normalized = re.sub(r'File ".*?"', 'File "X"', normalized)
        return normalized.strip()[:200]


class HookRegistry:
    """Registry and executor for all hooks."""

    def __init__(self):
        self.hooks: List[ExecutionHook] = []
        self.logger = get_logger('hook_registry')
        self._execution_log: List[Dict[str, Any]] = []

    def register(self, hook: ExecutionHook):
        """Register a hook."""
        self.hooks.append(hook)
        self.hooks.sort(key=lambda h: h.priority)
        self.logger.info("hook_registered", hook=hook.name, phase=hook.phase.value)

    def unregister(self, hook_name: str):
        """Unregister a hook by name."""
        self.hooks = [h for h in self.hooks if h.name != hook_name]

    def enable(self, hook_name: str):
        """Enable a hook."""
        for hook in self.hooks:
            if hook.name == hook_name:
                hook.enabled = True

    def disable(self, hook_name: str):
        """Disable a hook."""
        for hook in self.hooks:
            if hook.name == hook_name:
                hook.enabled = False

    def execute_pre_hooks(
        self,
        context: HookContext
    ) -> Tuple[HookResult, HookContext, List[str]]:
        """Execute all pre-execution hooks.

        Args:
            context: Execution context

        Returns:
            Tuple of (final result, possibly modified context, warnings)
        """
        return self._execute_hooks(HookPhase.PRE_EXECUTION, context)

    def execute_post_hooks(
        self,
        context: HookContext
    ) -> Tuple[HookResult, HookContext, List[str]]:
        """Execute all post-execution hooks.

        Args:
            context: Execution context

        Returns:
            Tuple of (final result, possibly modified context, warnings)
        """
        return self._execute_hooks(HookPhase.POST_EXECUTION, context)

    def _execute_hooks(
        self,
        phase: HookPhase,
        context: HookContext
    ) -> Tuple[HookResult, HookContext, List[str]]:
        """Execute hooks for a given phase."""
        all_warnings = []
        current_context = context

        for hook in self.hooks:
            if not hook.enabled or hook.phase != phase:
                continue

            if not hook.should_run(current_context):
                continue

            try:
                response = hook.execute(current_context)

                # Log execution
                self._execution_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'hook': hook.name,
                    'phase': phase.value,
                    'result': response.result.value,
                    'operation': current_context.operation,
                })

                # Collect warnings
                all_warnings.extend(response.warnings)
                if response.message:
                    all_warnings.append(f"[{hook.name}] {response.message}")

                # Handle result
                if response.result == HookResult.BLOCK:
                    self.logger.warning(
                        "hook_blocked_operation",
                        hook=hook.name,
                        reason=response.blocked_reason
                    )
                    return (HookResult.BLOCK, current_context, all_warnings)

                elif response.result == HookResult.REQUIRE_APPROVAL:
                    self.logger.info(
                        "hook_requires_approval",
                        hook=hook.name,
                        message=response.message
                    )
                    return (HookResult.REQUIRE_APPROVAL, current_context, all_warnings)

                elif response.result == HookResult.MODIFY:
                    # Update context with modified content
                    current_context = HookContext(
                        operation=current_context.operation,
                        agent_type=current_context.agent_type,
                        iteration=current_context.iteration,
                        target=current_context.target,
                        content=response.modified_content,
                        metadata=current_context.metadata,
                    )

            except Exception as e:
                self.logger.error(
                    "hook_execution_failed",
                    hook=hook.name,
                    error=str(e)
                )
                # Continue with other hooks on error

        return (HookResult.ALLOW, current_context, all_warnings)

    def get_execution_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent execution log entries."""
        return self._execution_log[-limit:]


def create_default_hook_registry() -> HookRegistry:
    """Create a registry with default safety hooks."""
    registry = HookRegistry()

    # Register default hooks
    registry.register(BlockDangerousCommandsHook())
    registry.register(ProtectSensitiveFilesHook())
    registry.register(AutoFormatCodeHook())
    registry.register(TokenBudgetHook())
    registry.register(IterationGuardHook())

    return registry
