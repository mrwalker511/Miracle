# LLM Integration Architecture

> **Purpose**: How the system integrates with OpenAI's LLM models.

---

## 6.1 Model Selection Strategy

```yaml
# config/openai.yaml
provider: "openai"

models:
  planner: "gpt-4-turbo-preview"     # Reasoning-heavy, needs GPT-4
  coder: "gpt-4-turbo-preview"       # Code generation, needs GPT-4
  tester: "gpt-4-turbo-preview"      # Test generation, can use GPT-4
  reflector: "gpt-4-turbo-preview"   # Error analysis, needs GPT-4
  embedding: "text-embedding-3-large" # 1536-dim embeddings

fallback_sequence:
  - "gpt-4-turbo-preview"
  - "gpt-4"
  - "gpt-3.5-turbo-16k"  # Last resort (cheaper but less capable)

parameters:
  temperature: 0.2      # Low for deterministic code
  top_p: 1.0
  max_tokens: 4096
  frequency_penalty: 0.0
  presence_penalty: 0.0
```

**Why These Models?**

| Agent | Model Choice | Rationale |
|-------|-------------|-----------|
| Planner | GPT-4 Turbo | Needs strong reasoning for task decomposition |
| Coder | GPT-4 Turbo | Best code generation quality, fewer syntax errors |
| Tester | GPT-4 Turbo | Generates comprehensive tests, edge cases |
| Reflector | GPT-4 Turbo | Deep error analysis, root cause identification |
| Embedding | text-embedding-3-large | High-dimensional embeddings (1536D) for better similarity |

---

## 6.2 Cost Optimization

**Strategies**:

1. **Cache similar queries**: Don't re-embed identical error messages
2. **Lazy retrieval**: Only query vector DB when needed
3. **Prompt compression**: Remove unnecessary context
4. **Model fallback**: Use GPT-3.5 for simple tasks (if configured)
5. **Token counting**: Warn when approaching budget limits

```python
class CostTracker:
    GPT4_TURBO_INPUT_COST = 0.01 / 1000   # $0.01 per 1K tokens
    GPT4_TURBO_OUTPUT_COST = 0.03 / 1000  # $0.03 per 1K tokens
    EMBEDDING_COST = 0.00013 / 1000       # $0.00013 per 1K tokens

    def calculate_cost(self, prompt_tokens, completion_tokens, embedding_tokens):
        cost = (
            prompt_tokens * self.GPT4_TURBO_INPUT_COST +
            completion_tokens * self.GPT4_TURBO_OUTPUT_COST +
            embedding_tokens * self.EMBEDDING_COST
        )
        return cost

    def check_budget(self, task_id):
        total_cost = self.get_total_cost(task_id)
        if total_cost > self.config.max_budget_per_task:
            raise BudgetExceededError(
                f"Task {task_id} exceeded budget: ${total_cost:.2f}"
            )
```

---

## 6.3 Prompt Engineering

**System Prompts** (loaded from `config/system_prompts.yaml`):

```yaml
coder: |
  You are an expert software engineer. Generate clean, well-documented code.

  Guidelines:
  - Follow language best practices (PEP 8 for Python, ESLint for Node.js)
  - Include type hints (Python) or JSDoc (Node.js)
  - Handle errors gracefully
  - Write self-documenting code with clear variable names
  - Add comments only where logic is non-obvious

  Use the provided tools to create files:
  - create_file(path, content): Create a new file
  - read_file(path): Read existing file
  - list_files(): List workspace contents

  Generate code iteratively. If tests fail, learn from the feedback.

reflector: |
  You are an expert debugger. Analyze test failures and identify root causes.

  Process:
  1. Parse the error message and stack trace
  2. Identify the root cause (not just the symptom)
  3. Consider similar past failures and their solutions
  4. Generate a specific fix hypothesis

  Be precise. Avoid vague suggestions like "check your code" or "add error handling".
  Provide actionable fixes: "Change line X to Y because Z".
```

**Prompt Optimization Techniques**:

1. **Context compression**: Remove redundant information
2. **Structured formatting**: Use bullet points and clear sections
3. **Error highlighting**: Use markdown to emphasize key issues
4. **Length control**: Keep prompts under 3000 tokens for best results
5. **Iterative refinement**: Learn from past failures to improve prompts