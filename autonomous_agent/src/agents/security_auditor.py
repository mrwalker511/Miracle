"""Security Auditor Agent - Specialized subagent for security vulnerability detection.

Based on Claude Code Mastery subagent patterns:
- Clear output format with XML tags
- Focused responsibility (security only)
- OWASP-aware vulnerability detection
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


class VulnerabilitySeverity(Enum):
    """Severity levels aligned with CVSS-like scoring."""
    CRITICAL = "critical"   # CVSS 9.0-10.0: Immediate exploitation risk
    HIGH = "high"           # CVSS 7.0-8.9: Significant risk
    MEDIUM = "medium"       # CVSS 4.0-6.9: Moderate risk
    LOW = "low"             # CVSS 0.1-3.9: Minor risk
    INFO = "info"           # Informational, best practice suggestion


class VulnerabilityCategory(Enum):
    """OWASP-aligned vulnerability categories."""
    INJECTION = "injection"              # SQL, Command, LDAP injection
    AUTH = "authentication"              # Broken authentication
    SENSITIVE_DATA = "sensitive_data"    # Sensitive data exposure
    XXE = "xxe"                          # XML External Entities
    ACCESS_CONTROL = "access_control"    # Broken access control
    MISCONFIG = "security_misconfiguration"
    XSS = "xss"                          # Cross-site scripting
    DESERIALIZATION = "insecure_deserialization"
    COMPONENTS = "vulnerable_components"  # Known vulnerable dependencies
    LOGGING = "insufficient_logging"      # Logging/monitoring issues
    PATH_TRAVERSAL = "path_traversal"    # Path traversal attacks
    CRYPTO = "weak_crypto"               # Weak cryptography
    HARDCODED_SECRETS = "hardcoded_secrets"  # Hardcoded credentials
    RESOURCE = "resource_exhaustion"     # DoS vulnerabilities


@dataclass
class SecurityFinding:
    """Individual security vulnerability finding."""
    severity: VulnerabilitySeverity
    category: VulnerabilityCategory
    cwe_id: Optional[str]  # Common Weakness Enumeration ID
    file: str
    line: Optional[int]
    code_snippet: str
    description: str
    impact: str
    remediation: str


@dataclass
class SecurityAuditResult:
    """Complete security audit results."""
    risk_level: str  # "critical", "high", "medium", "low", "secure"
    findings: List[SecurityFinding] = field(default_factory=list)
    summary: str = ""
    immediate_actions: List[str] = field(default_factory=list)

    def to_xml(self) -> str:
        """Convert to XML format for LLM consumption."""
        findings_xml = "\n".join([
            f"""    <vulnerability severity="{f.severity.value}" category="{f.category.value}">
      <cwe>{f.cwe_id or 'N/A'}</cwe>
      <file>{f.file}</file>
      <line>{f.line or 'N/A'}</line>
      <code_snippet><![CDATA[{f.code_snippet}]]></code_snippet>
      <description>{f.description}</description>
      <impact>{f.impact}</impact>
      <remediation>{f.remediation}</remediation>
    </vulnerability>"""
            for f in self.findings
        ])

        actions_xml = "\n".join([
            f"    <action>{action}</action>"
            for action in self.immediate_actions
        ])

        return f"""<security_audit>
  <risk_level>{self.risk_level}</risk_level>
  <summary>{self.summary}</summary>
  <findings>
{findings_xml}
  </findings>
  <immediate_actions>
{actions_xml}
  </immediate_actions>
</security_audit>"""

    @property
    def has_critical_vulnerabilities(self) -> bool:
        """Check if any critical/high vulnerabilities were found."""
        return any(
            f.severity in [VulnerabilitySeverity.CRITICAL, VulnerabilitySeverity.HIGH]
            for f in self.findings
        )

    @property
    def vulnerability_count(self) -> Dict[str, int]:
        """Count vulnerabilities by severity."""
        counts = {s.value: 0 for s in VulnerabilitySeverity}
        for f in self.findings:
            counts[f.severity.value] += 1
        return counts


class SecurityAuditorAgent(BaseAgent):
    """Specialized agent for security vulnerability detection.

    Focuses on OWASP Top 10 and common security issues:
    - Injection vulnerabilities (SQL, Command, etc.)
    - Authentication/Authorization issues
    - Sensitive data exposure
    - Security misconfigurations
    - Hardcoded secrets
    - Path traversal
    - Weak cryptography
    """

    AUDIT_SYSTEM_PROMPT = """You are an expert security auditor. Analyze the provided code for security vulnerabilities.

Focus on these categories (OWASP-aligned):
1. **Injection**: SQL, Command, LDAP, XPath injection
2. **Authentication**: Weak auth, session issues
3. **Sensitive Data**: Hardcoded secrets, unencrypted data
4. **Access Control**: Missing authorization checks
5. **Security Misconfiguration**: Unsafe defaults
6. **XSS**: Cross-site scripting
7. **Path Traversal**: Directory traversal attacks
8. **Weak Crypto**: Insecure algorithms, weak keys

Output your audit in this exact XML format:

<security_audit>
  <risk_level>critical|high|medium|low|secure</risk_level>
  <summary>Brief security posture summary</summary>
  <findings>
    <vulnerability severity="critical|high|medium|low|info" category="injection|authentication|sensitive_data|access_control|xss|path_traversal|weak_crypto|hardcoded_secrets">
      <cwe>CWE-XXX</cwe>
      <file>filename.py</file>
      <line>42</line>
      <code_snippet>The vulnerable code</code_snippet>
      <description>What the vulnerability is</description>
      <impact>What could happen if exploited</impact>
      <remediation>How to fix it</remediation>
    </vulnerability>
  </findings>
  <immediate_actions>
    <action>First priority fix</action>
    <action>Second priority fix</action>
  </immediate_actions>
</security_audit>

Be thorough. Security vulnerabilities can be subtle. When in doubt, flag it."""

    # Common patterns to detect (quick static analysis)
    DANGEROUS_PATTERNS = {
        'command_injection': [
            r'os\.system\s*\(',
            r'subprocess\.(?:call|run|Popen)\s*\([^)]*shell\s*=\s*True',
            r'eval\s*\(',
            r'exec\s*\(',
        ],
        'sql_injection': [
            r'execute\s*\(\s*["\'].*?%s',
            r'execute\s*\(\s*f["\']',
            r'cursor\.execute\s*\([^,]+\+',
        ],
        'path_traversal': [
            r'open\s*\([^)]*\+',
            r'Path\s*\([^)]*\+',
        ],
        'hardcoded_secrets': [
            r'(?:password|secret|api_key|token)\s*=\s*["\'][^"\']+["\']',
            r'Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+',
        ],
        'weak_crypto': [
            r'hashlib\.md5\s*\(',
            r'hashlib\.sha1\s*\(',
            r'DES\.',
            r'RC4\.',
        ],
    }

    def __init__(
        self,
        agent_type: str,
        openai_client: OpenAIClient,
        vector_store: VectorStore,
        prompts: Dict[str, Any],
    ):
        """Initialize the security auditor agent."""
        super().__init__(agent_type, openai_client, vector_store, prompts)
        self.system_prompt = self.AUDIT_SYSTEM_PROMPT

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute security audit on the provided code.

        Args:
            context: Must contain 'code_files' dict of filename -> content

        Returns:
            Dictionary with 'audit' (SecurityAuditResult) and 'passed' (bool)
        """
        code_files = context.get('code_files', {})

        if not code_files:
            self.logger.warning("security_audit_skipped", reason="no code files")
            return {
                'audit': SecurityAuditResult(
                    risk_level="unknown",
                    summary="No code files provided for audit"
                ),
                'passed': True
            }

        # First do quick static analysis
        static_findings = self._static_analysis(code_files)

        # Build code content for LLM audit
        code_content = self._format_code_for_audit(code_files)

        # Build messages including static findings
        static_context = ""
        if static_findings:
            static_context = f"\n\nStatic analysis already found these potential issues:\n"
            for f in static_findings:
                static_context += f"- {f.category.value}: {f.description} in {f.file}\n"

        messages = self.build_messages(f"""Perform a security audit on the following code:

{code_content}
{static_context}
Task context: {context.get('task_description', 'Unknown task')}
Language: {context.get('language', 'python')}
""")

        # Call LLM
        response = self.call_llm(messages, temperature=0.2)  # Lower temp for security
        response_text = self.extract_text_response(response)

        # Parse the XML response
        audit = self._parse_audit_response(response_text)

        # Merge static findings with LLM findings
        audit.findings = static_findings + audit.findings

        # Recalculate risk level
        audit.risk_level = self._calculate_risk_level(audit.findings)

        self.logger.info(
            "security_audit_completed",
            risk_level=audit.risk_level,
            vulnerability_count=len(audit.findings),
            has_critical=audit.has_critical_vulnerabilities
        )

        return {
            'audit': audit,
            'audit_xml': audit.to_xml(),
            'passed': not audit.has_critical_vulnerabilities,
            'vulnerability_counts': audit.vulnerability_count
        }

    def _static_analysis(self, code_files: Dict[str, str]) -> List[SecurityFinding]:
        """Perform quick static analysis for obvious vulnerabilities."""
        findings = []

        for filename, content in code_files.items():
            lines = content.split('\n')

            for category, patterns in self.DANGEROUS_PATTERNS.items():
                for pattern in patterns:
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            findings.append(self._create_static_finding(
                                category, filename, i, line.strip()
                            ))

        return findings

    def _create_static_finding(
        self,
        category: str,
        filename: str,
        line: int,
        code_snippet: str
    ) -> SecurityFinding:
        """Create a finding from static analysis."""
        category_mapping = {
            'command_injection': (VulnerabilityCategory.INJECTION, 'CWE-78'),
            'sql_injection': (VulnerabilityCategory.INJECTION, 'CWE-89'),
            'path_traversal': (VulnerabilityCategory.PATH_TRAVERSAL, 'CWE-22'),
            'hardcoded_secrets': (VulnerabilityCategory.HARDCODED_SECRETS, 'CWE-798'),
            'weak_crypto': (VulnerabilityCategory.CRYPTO, 'CWE-327'),
        }

        vuln_cat, cwe = category_mapping.get(
            category,
            (VulnerabilityCategory.MISCONFIG, None)
        )

        descriptions = {
            'command_injection': 'Potential command injection vulnerability',
            'sql_injection': 'Potential SQL injection vulnerability',
            'path_traversal': 'Potential path traversal vulnerability',
            'hardcoded_secrets': 'Hardcoded secret or credential detected',
            'weak_crypto': 'Weak cryptographic algorithm in use',
        }

        return SecurityFinding(
            severity=VulnerabilitySeverity.HIGH,
            category=vuln_cat,
            cwe_id=cwe,
            file=filename,
            line=line,
            code_snippet=code_snippet[:100],
            description=descriptions.get(category, f'Potential {category} issue'),
            impact='Could allow unauthorized access or code execution',
            remediation=f'Review and fix the {category} pattern'
        )

    def _format_code_for_audit(self, code_files: Dict[str, str]) -> str:
        """Format code files for audit prompt."""
        parts = []
        for filename, content in code_files.items():
            # Add line numbers for easier reference
            numbered_lines = []
            for i, line in enumerate(content.split('\n'), 1):
                numbered_lines.append(f"{i:4d} | {line}")
            numbered_content = '\n'.join(numbered_lines)
            parts.append(f"=== {filename} ===\n{numbered_content}\n")
        return "\n".join(parts)

    def _parse_audit_response(self, response: str) -> SecurityAuditResult:
        """Parse XML audit response into structured result."""
        # Extract risk level
        risk_match = re.search(r'<risk_level>(\w+)</risk_level>', response)
        risk_level = risk_match.group(1) if risk_match else "unknown"

        # Extract summary
        summary_match = re.search(r'<summary>(.*?)</summary>', response, re.DOTALL)
        summary = summary_match.group(1).strip() if summary_match else ""

        # Extract immediate actions
        actions = []
        action_pattern = re.compile(r'<action>(.*?)</action>', re.DOTALL)
        for match in action_pattern.finditer(response):
            actions.append(match.group(1).strip())

        # Extract findings
        findings = []
        finding_pattern = re.compile(
            r'<vulnerability\s+severity="(\w+)"\s+category="(\w+)">\s*'
            r'<cwe>(.*?)</cwe>\s*'
            r'<file>(.*?)</file>\s*'
            r'<line>(.*?)</line>\s*'
            r'<code_snippet>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</code_snippet>\s*'
            r'<description>(.*?)</description>\s*'
            r'<impact>(.*?)</impact>\s*'
            r'<remediation>(.*?)</remediation>\s*'
            r'</vulnerability>',
            re.DOTALL
        )

        for match in finding_pattern.finditer(response):
            (severity_str, category_str, cwe, file, line,
             code_snippet, description, impact, remediation) = match.groups()

            try:
                severity = VulnerabilitySeverity(severity_str.lower())
            except ValueError:
                severity = VulnerabilitySeverity.INFO

            try:
                category = VulnerabilityCategory(category_str.lower())
            except ValueError:
                category = VulnerabilityCategory.MISCONFIG

            try:
                line_num = int(line) if line.strip() and line.strip() != 'N/A' else None
            except ValueError:
                line_num = None

            findings.append(SecurityFinding(
                severity=severity,
                category=category,
                cwe_id=cwe.strip() if cwe.strip() != 'N/A' else None,
                file=file.strip(),
                line=line_num,
                code_snippet=code_snippet.strip(),
                description=description.strip(),
                impact=impact.strip(),
                remediation=remediation.strip()
            ))

        return SecurityAuditResult(
            risk_level=risk_level,
            findings=findings,
            summary=summary,
            immediate_actions=actions
        )

    def _calculate_risk_level(self, findings: List[SecurityFinding]) -> str:
        """Calculate overall risk level from findings."""
        if not findings:
            return "secure"

        severity_scores = {
            VulnerabilitySeverity.CRITICAL: 4,
            VulnerabilitySeverity.HIGH: 3,
            VulnerabilitySeverity.MEDIUM: 2,
            VulnerabilitySeverity.LOW: 1,
            VulnerabilitySeverity.INFO: 0,
        }

        max_severity = max(
            severity_scores.get(f.severity, 0)
            for f in findings
        )

        if max_severity >= 4:
            return "critical"
        elif max_severity >= 3:
            return "high"
        elif max_severity >= 2:
            return "medium"
        elif max_severity >= 1:
            return "low"
        return "secure"

    def quick_scan(self, code: str, filename: str = "code.py") -> Dict[str, Any]:
        """Perform a quick scan without LLM.

        Useful as a pre-check or for CI/CD integration.

        Args:
            code: Code content to scan
            filename: Name of the file

        Returns:
            Dictionary with findings and pass/fail status
        """
        findings = self._static_analysis({filename: code})

        return {
            'passed': not any(
                f.severity in [VulnerabilitySeverity.CRITICAL, VulnerabilitySeverity.HIGH]
                for f in findings
            ),
            'findings': findings,
            'finding_count': len(findings)
        }
