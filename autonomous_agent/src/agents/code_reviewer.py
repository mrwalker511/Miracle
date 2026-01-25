"""Code Reviewer Agent - Specialized subagent for code quality analysis.

Based on Claude Code Mastery subagent patterns:
- Clear output format with XML tags
- Focused responsibility (code quality only)
- Structured findings for easy parsing
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

from src.agents.base_agent import BaseAgent
from src.llm.openai_client import OpenAIClient
from src.memory.vector_store import VectorStore


class ReviewSeverity(Enum):
    """Severity levels for code review findings."""
    CRITICAL = "critical"    # Must fix before proceeding
    WARNING = "warning"      # Should fix, may cause issues
    SUGGESTION = "suggestion"  # Nice to have improvements
    INFO = "info"            # Informational observations


@dataclass
class ReviewFinding:
    """Individual code review finding."""
    severity: ReviewSeverity
    category: str  # e.g., "logic", "style", "performance", "maintainability"
    file: str
    line: Optional[int]
    message: str
    suggestion: str


@dataclass
class CodeReviewResult:
    """Complete code review results."""
    overall_quality: str  # "good", "acceptable", "needs_work", "poor"
    findings: List[ReviewFinding] = field(default_factory=list)
    summary: str = ""
    recommended_action: str = ""

    def to_xml(self) -> str:
        """Convert to XML format for LLM consumption."""
        findings_xml = "\n".join([
            f"""    <finding severity="{f.severity.value}" category="{f.category}">
      <file>{f.file}</file>
      <line>{f.line or 'N/A'}</line>
      <message>{f.message}</message>
      <suggestion>{f.suggestion}</suggestion>
    </finding>"""
            for f in self.findings
        ])

        return f"""<code_review>
  <overall_quality>{self.overall_quality}</overall_quality>
  <summary>{self.summary}</summary>
  <findings>
{findings_xml}
  </findings>
  <recommended_action>{self.recommended_action}</recommended_action>
</code_review>"""

    @property
    def has_critical_issues(self) -> bool:
        """Check if any critical issues were found."""
        return any(f.severity == ReviewSeverity.CRITICAL for f in self.findings)

    @property
    def blocking_count(self) -> int:
        """Count of issues that should block progress."""
        return len([f for f in self.findings
                   if f.severity in [ReviewSeverity.CRITICAL, ReviewSeverity.WARNING]])


class CodeReviewerAgent(BaseAgent):
    """Specialized agent for reviewing code quality.

    Focuses on:
    - Logic correctness
    - Code style and readability
    - Best practices adherence
    - Potential bugs
    - Maintainability concerns
    """

    REVIEW_SYSTEM_PROMPT = """You are a senior code reviewer. Analyze the provided code and return structured feedback.

Your review should focus on:
1. **Logic Errors**: Bugs, edge cases, incorrect algorithms
2. **Code Quality**: Readability, naming, structure
3. **Best Practices**: Language idioms, patterns, anti-patterns
4. **Maintainability**: Documentation, complexity, modularity

Output your review in this exact XML format:

<code_review>
  <overall_quality>good|acceptable|needs_work|poor</overall_quality>
  <summary>Brief 1-2 sentence summary</summary>
  <findings>
    <finding severity="critical|warning|suggestion|info" category="logic|style|performance|maintainability">
      <file>filename.py</file>
      <line>42</line>
      <message>Description of the issue</message>
      <suggestion>How to fix it</suggestion>
    </finding>
  </findings>
  <recommended_action>Overall recommendation</recommended_action>
</code_review>

Be thorough but constructive. Focus on actionable feedback."""

    def __init__(
        self,
        agent_type: str,
        openai_client: OpenAIClient,
        vector_store: VectorStore,
        prompts: Dict[str, Any],
    ):
        """Initialize the code reviewer agent."""
        super().__init__(agent_type, openai_client, vector_store, prompts)
        self.system_prompt = self.REVIEW_SYSTEM_PROMPT

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute code review on the provided code.

        Args:
            context: Must contain 'code_files' dict of filename -> content

        Returns:
            Dictionary with 'review' (CodeReviewResult) and 'passed' (bool)
        """
        code_files = context.get('code_files', {})

        if not code_files:
            self.logger.warning("code_review_skipped", reason="no code files")
            return {
                'review': CodeReviewResult(
                    overall_quality="unknown",
                    summary="No code files provided for review"
                ),
                'passed': True
            }

        # Build code content for review
        code_content = self._format_code_for_review(code_files)

        # Build messages
        messages = self.build_messages(f"""Review the following code:

{code_content}

Task context: {context.get('task_description', 'Unknown task')}
Language: {context.get('language', 'python')}
""")

        # Call LLM
        response = self.call_llm(messages, temperature=0.3)
        response_text = self.extract_text_response(response)

        # Parse the XML response
        review = self._parse_review_response(response_text, code_files)

        self.logger.info(
            "code_review_completed",
            overall_quality=review.overall_quality,
            finding_count=len(review.findings),
            has_critical=review.has_critical_issues
        )

        return {
            'review': review,
            'review_xml': review.to_xml(),
            'passed': not review.has_critical_issues,
            'blocking_issues': review.blocking_count
        }

    def _format_code_for_review(self, code_files: Dict[str, str]) -> str:
        """Format code files for review prompt."""
        parts = []
        for filename, content in code_files.items():
            parts.append(f"=== {filename} ===\n{content}\n")
        return "\n".join(parts)

    def _parse_review_response(
        self,
        response: str,
        code_files: Dict[str, str]
    ) -> CodeReviewResult:
        """Parse XML review response into structured result."""
        # Extract overall quality
        quality_match = re.search(
            r'<overall_quality>(\w+)</overall_quality>',
            response
        )
        overall_quality = quality_match.group(1) if quality_match else "unknown"

        # Extract summary
        summary_match = re.search(
            r'<summary>(.*?)</summary>',
            response,
            re.DOTALL
        )
        summary = summary_match.group(1).strip() if summary_match else ""

        # Extract recommended action
        action_match = re.search(
            r'<recommended_action>(.*?)</recommended_action>',
            response,
            re.DOTALL
        )
        recommended_action = action_match.group(1).strip() if action_match else ""

        # Extract findings
        findings = []
        finding_pattern = re.compile(
            r'<finding\s+severity="(\w+)"\s+category="(\w+)">\s*'
            r'<file>(.*?)</file>\s*'
            r'<line>(.*?)</line>\s*'
            r'<message>(.*?)</message>\s*'
            r'<suggestion>(.*?)</suggestion>\s*'
            r'</finding>',
            re.DOTALL
        )

        for match in finding_pattern.finditer(response):
            severity_str, category, file, line, message, suggestion = match.groups()

            try:
                severity = ReviewSeverity(severity_str.lower())
            except ValueError:
                severity = ReviewSeverity.INFO

            try:
                line_num = int(line) if line.strip() and line.strip() != 'N/A' else None
            except ValueError:
                line_num = None

            findings.append(ReviewFinding(
                severity=severity,
                category=category.strip(),
                file=file.strip(),
                line=line_num,
                message=message.strip(),
                suggestion=suggestion.strip()
            ))

        return CodeReviewResult(
            overall_quality=overall_quality,
            findings=findings,
            summary=summary,
            recommended_action=recommended_action
        )

    def quick_check(self, code: str, filename: str = "code.py") -> bool:
        """Perform a quick check for obvious issues.

        This is a lighter-weight check that can be used as a gate
        before full review.

        Args:
            code: Code content to check
            filename: Name of the file

        Returns:
            True if code passes quick check
        """
        # Quick static checks without LLM
        issues = []

        # Check for common anti-patterns
        if 'eval(' in code or 'exec(' in code:
            issues.append("Contains eval/exec")

        if 'import *' in code:
            issues.append("Uses wildcard import")

        if code.count('except:') > 0:
            issues.append("Uses bare except clause")

        # Check for very long lines
        for i, line in enumerate(code.split('\n'), 1):
            if len(line) > 200:
                issues.append(f"Line {i} exceeds 200 characters")

        if issues:
            self.logger.info("quick_check_failed", issues=issues)
            return False

        return True
