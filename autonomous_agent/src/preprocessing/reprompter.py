"""Reprompter System - Convert rough task descriptions into structured prompts.

Based on Claude Code Mastery reprompter patterns:
- Takes rough/vague task descriptions
- Generates clarifying questions when needed
- Produces structured XML-tagged prompts
- Extracts constraints, requirements, and acceptance criteria
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from src.llm.openai_client import OpenAIClient
from src.ui.logger import get_logger


class TaskComplexity(Enum):
    """Estimated task complexity level."""
    TRIVIAL = "trivial"        # Simple one-liner
    SIMPLE = "simple"          # Single function/component
    MODERATE = "moderate"      # Multiple components
    COMPLEX = "complex"        # Full feature
    ARCHITECTURAL = "architectural"  # System-wide changes


class ClarificationPriority(Enum):
    """Priority of clarification questions."""
    BLOCKING = "blocking"      # Must answer before proceeding
    IMPORTANT = "important"    # Should answer for best results
    OPTIONAL = "optional"      # Nice to have


@dataclass
class ClarificationQuestion:
    """A clarifying question to ask the user."""
    question: str
    priority: ClarificationPriority
    category: str  # e.g., "requirements", "constraints", "scope"
    default_answer: Optional[str] = None
    options: List[str] = field(default_factory=list)


@dataclass
class StructuredTask:
    """Fully structured task ready for agent processing."""
    # Core task definition
    title: str
    description: str
    goal: str

    # Requirements
    functional_requirements: List[str] = field(default_factory=list)
    non_functional_requirements: List[str] = field(default_factory=list)

    # Constraints
    constraints: List[str] = field(default_factory=list)
    out_of_scope: List[str] = field(default_factory=list)

    # Technical details
    language: str = "python"
    framework: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)

    # Acceptance criteria
    acceptance_criteria: List[str] = field(default_factory=list)
    test_scenarios: List[str] = field(default_factory=list)

    # Metadata
    complexity: TaskComplexity = TaskComplexity.MODERATE
    estimated_files: int = 1
    tags: List[str] = field(default_factory=list)

    def to_xml(self) -> str:
        """Convert to XML format for LLM consumption."""
        requirements_xml = "\n".join([
            f"    <requirement>{r}</requirement>"
            for r in self.functional_requirements
        ])

        nfr_xml = "\n".join([
            f"    <requirement>{r}</requirement>"
            for r in self.non_functional_requirements
        ])

        constraints_xml = "\n".join([
            f"    <constraint>{c}</constraint>"
            for c in self.constraints
        ])

        acceptance_xml = "\n".join([
            f"    <criterion>{c}</criterion>"
            for c in self.acceptance_criteria
        ])

        tests_xml = "\n".join([
            f"    <scenario>{s}</scenario>"
            for s in self.test_scenarios
        ])

        return f"""<task>
  <title>{self.title}</title>
  <description>{self.description}</description>
  <goal>{self.goal}</goal>

  <requirements>
    <functional>
{requirements_xml}
    </functional>
    <non_functional>
{nfr_xml}
    </non_functional>
  </requirements>

  <constraints>
{constraints_xml}
  </constraints>

  <technical>
    <language>{self.language}</language>
    <framework>{self.framework or 'none'}</framework>
    <dependencies>{', '.join(self.dependencies) or 'none'}</dependencies>
  </technical>

  <acceptance_criteria>
{acceptance_xml}
  </acceptance_criteria>

  <test_scenarios>
{tests_xml}
  </test_scenarios>

  <metadata>
    <complexity>{self.complexity.value}</complexity>
    <estimated_files>{self.estimated_files}</estimated_files>
    <tags>{', '.join(self.tags)}</tags>
  </metadata>
</task>"""

    def to_prompt(self) -> str:
        """Convert to a structured prompt string."""
        parts = [
            f"# Task: {self.title}",
            "",
            f"## Description",
            self.description,
            "",
            f"## Goal",
            self.goal,
        ]

        if self.functional_requirements:
            parts.extend([
                "",
                "## Requirements",
                *[f"- {r}" for r in self.functional_requirements],
            ])

        if self.constraints:
            parts.extend([
                "",
                "## Constraints",
                *[f"- {c}" for c in self.constraints],
            ])

        if self.acceptance_criteria:
            parts.extend([
                "",
                "## Acceptance Criteria",
                *[f"- {c}" for c in self.acceptance_criteria],
            ])

        parts.extend([
            "",
            f"## Technical",
            f"- Language: {self.language}",
            f"- Framework: {self.framework or 'none'}",
        ])

        return "\n".join(parts)


class Reprompter:
    """Converts rough task descriptions into structured prompts.

    Uses LLM to:
    1. Analyze vague input
    2. Generate clarifying questions if needed
    3. Extract structured requirements
    4. Produce XML-tagged prompts
    """

    ANALYSIS_PROMPT = """Analyze this task description and extract structured information.

Task: {input}

Return your analysis in this exact XML format:

<analysis>
  <clarity_score>1-10</clarity_score>
  <missing_info>
    <item priority="blocking|important|optional" category="requirements|constraints|scope">What is unclear</item>
  </missing_info>
  <extracted>
    <title>Short task title</title>
    <goal>Clear goal statement</goal>
    <requirements>
      <item>Requirement 1</item>
    </requirements>
    <constraints>
      <item>Constraint 1</item>
    </constraints>
    <language>python|javascript|typescript|go|other</language>
    <complexity>trivial|simple|moderate|complex|architectural</complexity>
    <acceptance_criteria>
      <item>Criterion 1</item>
    </acceptance_criteria>
  </extracted>
</analysis>

Be thorough in identifying what information is missing for a successful implementation."""

    CLARIFICATION_PROMPT = """Based on this task description and the missing information identified,
generate specific clarifying questions.

Task: {input}

Missing information:
{missing}

Generate 1-3 targeted questions to clarify the most important unknowns.
Return questions in this format:

<questions>
  <question priority="blocking|important|optional" category="requirements|constraints|scope">
    <text>The question to ask</text>
    <default>A reasonable default if not answered</default>
    <options>option1,option2,option3</options>
  </question>
</questions>

Focus on blocking and important questions first."""

    def __init__(
        self,
        openai_client: OpenAIClient,
        auto_fill_defaults: bool = True,
        min_clarity_score: int = 7,
    ):
        """Initialize reprompter.

        Args:
            openai_client: OpenAI client for LLM calls
            auto_fill_defaults: Whether to auto-fill with defaults
            min_clarity_score: Minimum clarity score before asking questions
        """
        self.openai = openai_client
        self.auto_fill_defaults = auto_fill_defaults
        self.min_clarity_score = min_clarity_score
        self.logger = get_logger('reprompter')

    def process(
        self,
        raw_input: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[StructuredTask, List[ClarificationQuestion]]:
        """Process raw input into structured task.

        Args:
            raw_input: Raw task description from user
            additional_context: Optional context (e.g., existing code, project info)

        Returns:
            Tuple of (structured task, list of clarification questions)
        """
        self.logger.info("reprompter_started", input_length=len(raw_input))

        # First pass: analyze input
        analysis = self._analyze_input(raw_input, additional_context)

        # Check if clarification is needed
        questions = []
        if analysis['clarity_score'] < self.min_clarity_score:
            questions = self._generate_questions(raw_input, analysis)

        # Build structured task from analysis
        task = self._build_structured_task(raw_input, analysis, additional_context)

        self.logger.info(
            "reprompter_completed",
            clarity_score=analysis['clarity_score'],
            question_count=len(questions),
            complexity=task.complexity.value
        )

        return task, questions

    def quick_structure(self, raw_input: str) -> StructuredTask:
        """Quick structuring without LLM (pattern-based).

        Useful for simple or well-formed inputs.

        Args:
            raw_input: Raw task description

        Returns:
            Basic structured task
        """
        # Extract language if mentioned
        language = "python"
        language_patterns = {
            'python': r'\b(python|py)\b',
            'javascript': r'\b(javascript|js|node)\b',
            'typescript': r'\b(typescript|ts)\b',
            'go': r'\b(golang|go)\b',
            'rust': r'\b(rust)\b',
        }
        for lang, pattern in language_patterns.items():
            if re.search(pattern, raw_input, re.IGNORECASE):
                language = lang
                break

        # Extract framework if mentioned
        framework = None
        framework_patterns = {
            'react': r'\breact\b',
            'django': r'\bdjango\b',
            'flask': r'\bflask\b',
            'fastapi': r'\bfastapi\b',
            'express': r'\bexpress\b',
        }
        for fw, pattern in framework_patterns.items():
            if re.search(pattern, raw_input, re.IGNORECASE):
                framework = fw
                break

        # Estimate complexity
        complexity = self._estimate_complexity(raw_input)

        # Generate basic structure
        title = raw_input.split('.')[0][:50].strip()
        if len(title) < 5:
            title = raw_input[:50].strip()

        return StructuredTask(
            title=title,
            description=raw_input,
            goal=f"Implement: {title}",
            language=language,
            framework=framework,
            complexity=complexity,
            acceptance_criteria=["Code runs without errors", "Tests pass"],
        )

    def refine_with_answers(
        self,
        task: StructuredTask,
        answers: Dict[str, str]
    ) -> StructuredTask:
        """Refine task with answers to clarifying questions.

        Args:
            task: Initial structured task
            answers: Dict of question text -> answer

        Returns:
            Refined structured task
        """
        # Apply answers to refine the task
        for question, answer in answers.items():
            question_lower = question.lower()

            if 'language' in question_lower:
                task.language = answer

            elif 'framework' in question_lower:
                task.framework = answer

            elif 'requirement' in question_lower:
                task.functional_requirements.append(answer)

            elif 'constraint' in question_lower:
                task.constraints.append(answer)

            elif 'test' in question_lower or 'accept' in question_lower:
                task.acceptance_criteria.append(answer)

        return task

    def _analyze_input(
        self,
        raw_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze input using LLM."""
        context_str = ""
        if context:
            context_str = f"\n\nAdditional context: {context}"

        prompt = self.ANALYSIS_PROMPT.format(input=raw_input + context_str)

        messages = [
            {"role": "system", "content": "You are an expert at analyzing coding tasks and extracting requirements."},
            {"role": "user", "content": prompt}
        ]

        try:
            response = self.openai.chat_completion(
                agent_type="reprompter",
                messages=messages,
                temperature=0.3
            )
            response_text = response.choices[0].message.content

            return self._parse_analysis(response_text)

        except Exception as e:
            self.logger.error("analysis_failed", error=str(e))
            # Return minimal analysis
            return {
                'clarity_score': 5,
                'missing_info': [],
                'extracted': {
                    'title': raw_input[:50],
                    'goal': raw_input,
                    'requirements': [],
                    'constraints': [],
                    'language': 'python',
                    'complexity': 'moderate',
                    'acceptance_criteria': [],
                }
            }

    def _parse_analysis(self, response: str) -> Dict[str, Any]:
        """Parse LLM analysis response."""
        analysis = {
            'clarity_score': 5,
            'missing_info': [],
            'extracted': {},
        }

        # Extract clarity score
        score_match = re.search(r'<clarity_score>(\d+)</clarity_score>', response)
        if score_match:
            analysis['clarity_score'] = int(score_match.group(1))

        # Extract missing info
        missing_pattern = re.compile(
            r'<item\s+priority="(\w+)"\s+category="(\w+)">(.*?)</item>',
            re.DOTALL
        )
        for match in missing_pattern.finditer(response):
            analysis['missing_info'].append({
                'priority': match.group(1),
                'category': match.group(2),
                'text': match.group(3).strip()
            })

        # Extract structured info
        extracted = {}

        title_match = re.search(r'<title>(.*?)</title>', response, re.DOTALL)
        if title_match:
            extracted['title'] = title_match.group(1).strip()

        goal_match = re.search(r'<goal>(.*?)</goal>', response, re.DOTALL)
        if goal_match:
            extracted['goal'] = goal_match.group(1).strip()

        lang_match = re.search(r'<language>(\w+)</language>', response)
        if lang_match:
            extracted['language'] = lang_match.group(1).strip()

        complexity_match = re.search(r'<complexity>(\w+)</complexity>', response)
        if complexity_match:
            extracted['complexity'] = complexity_match.group(1).strip()

        # Extract list items
        for tag in ['requirements', 'constraints', 'acceptance_criteria']:
            items = re.findall(
                rf'<{tag}>\s*(?:<item>(.*?)</item>\s*)+</{tag}>',
                response,
                re.DOTALL
            )
            if items:
                extracted[tag] = [
                    m.strip()
                    for m in re.findall(r'<item>(.*?)</item>', items[0], re.DOTALL)
                ]

        analysis['extracted'] = extracted
        return analysis

    def _generate_questions(
        self,
        raw_input: str,
        analysis: Dict[str, Any]
    ) -> List[ClarificationQuestion]:
        """Generate clarifying questions based on analysis."""
        missing_items = analysis.get('missing_info', [])

        if not missing_items:
            return []

        missing_text = "\n".join([
            f"- [{m['priority']}] {m['category']}: {m['text']}"
            for m in missing_items
        ])

        prompt = self.CLARIFICATION_PROMPT.format(
            input=raw_input,
            missing=missing_text
        )

        messages = [
            {"role": "system", "content": "You generate helpful clarifying questions for coding tasks."},
            {"role": "user", "content": prompt}
        ]

        try:
            response = self.openai.chat_completion(
                agent_type="reprompter",
                messages=messages,
                temperature=0.4
            )
            response_text = response.choices[0].message.content

            return self._parse_questions(response_text)

        except Exception as e:
            self.logger.error("question_generation_failed", error=str(e))
            return []

    def _parse_questions(self, response: str) -> List[ClarificationQuestion]:
        """Parse generated questions."""
        questions = []

        question_pattern = re.compile(
            r'<question\s+priority="(\w+)"\s+category="(\w+)">\s*'
            r'<text>(.*?)</text>\s*'
            r'(?:<default>(.*?)</default>)?\s*'
            r'(?:<options>(.*?)</options>)?\s*'
            r'</question>',
            re.DOTALL
        )

        for match in question_pattern.finditer(response):
            priority_str, category, text, default, options = match.groups()

            try:
                priority = ClarificationPriority(priority_str.lower())
            except ValueError:
                priority = ClarificationPriority.OPTIONAL

            options_list = []
            if options:
                options_list = [o.strip() for o in options.split(',')]

            questions.append(ClarificationQuestion(
                question=text.strip(),
                priority=priority,
                category=category.strip(),
                default_answer=default.strip() if default else None,
                options=options_list
            ))

        return questions

    def _build_structured_task(
        self,
        raw_input: str,
        analysis: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> StructuredTask:
        """Build structured task from analysis."""
        extracted = analysis.get('extracted', {})

        # Map complexity string to enum
        complexity_map = {
            'trivial': TaskComplexity.TRIVIAL,
            'simple': TaskComplexity.SIMPLE,
            'moderate': TaskComplexity.MODERATE,
            'complex': TaskComplexity.COMPLEX,
            'architectural': TaskComplexity.ARCHITECTURAL,
        }
        complexity = complexity_map.get(
            extracted.get('complexity', 'moderate'),
            TaskComplexity.MODERATE
        )

        return StructuredTask(
            title=extracted.get('title', raw_input[:50]),
            description=raw_input,
            goal=extracted.get('goal', f"Implement: {extracted.get('title', 'task')}"),
            functional_requirements=extracted.get('requirements', []),
            constraints=extracted.get('constraints', []),
            language=extracted.get('language', 'python'),
            acceptance_criteria=extracted.get('acceptance_criteria', []),
            complexity=complexity,
        )

    def _estimate_complexity(self, raw_input: str) -> TaskComplexity:
        """Estimate complexity from input text."""
        input_lower = raw_input.lower()

        # Look for complexity indicators
        if len(raw_input) < 50:
            return TaskComplexity.SIMPLE

        complex_indicators = [
            'system', 'architecture', 'refactor', 'migrate',
            'integrate', 'authentication', 'authorization',
            'database', 'api', 'multiple'
        ]
        complex_count = sum(1 for ind in complex_indicators if ind in input_lower)

        if complex_count >= 3:
            return TaskComplexity.ARCHITECTURAL
        elif complex_count >= 2:
            return TaskComplexity.COMPLEX
        elif complex_count >= 1:
            return TaskComplexity.MODERATE
        elif len(raw_input) < 100:
            return TaskComplexity.SIMPLE

        return TaskComplexity.MODERATE
