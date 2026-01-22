# Memory & Learning

Vector-based memory system for learning from past successes and failures.

---

## Overview

The system learns by storing embeddings of successful patterns and failures, then using vector similarity search to retrieve relevant past experiences.

**Database**: PostgreSQL with pgvector extension  
**Embedding Model**: `text-embedding-3-large` (1536 dimensions)  
**Similarity Metric**: Cosine distance

---

## Pattern Storage

### When Patterns Are Stored

After a task completes successfully (all tests pass), the system:
1. Extracts the solution (code + tests)
2. Categorizes the problem type
3. Generates an embedding
4. Stores in `patterns` table

### Pattern Schema

```sql
CREATE TABLE patterns (
    id UUID PRIMARY KEY,
    problem_type VARCHAR(255),        -- Category (e.g., "REST API", "Data Processing")
    code_template TEXT,                -- Reusable code
    test_template TEXT,                -- Associated test pattern
    dependencies JSONB,                -- Required packages
    usage_count INTEGER DEFAULT 0,     -- How many times retrieved
    success_rate FLOAT DEFAULT 0.0,    -- Success rate when used
    embedding vector(1536),            -- Vector embedding
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX idx_patterns_embedding ON patterns USING ivfflat (embedding vector_cosine_ops);
```

### Storing a Pattern

**File**: `src/memory/pattern_matcher.py`

```python
class PatternMatcher:
    """Store and retrieve successful solution patterns."""
    
    async def store_pattern(
        self,
        problem_type: str,
        code: str,
        tests: str,
        dependencies: List[str]
    ) -> str:
        """Store a successful solution pattern.
        
        Args:
            problem_type: Category of problem solved
            code: Code solution
            tests: Test code
            dependencies: Required packages
            
        Returns:
            Pattern ID
        """
        # Extract reusable template (remove task-specific details)
        code_template = self._extract_template(code)
        test_template = self._extract_template(tests)
        
        # Generate embedding from problem description + code
        text = f"{problem_type}\n{code_template}"
        embedding = await self.vector_store.generate_embedding(text)
        
        # Store in database
        pattern_id = await self.db.execute(
            """
            INSERT INTO patterns (id, problem_type, code_template, test_template, 
                                 dependencies, embedding, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
            """,
            uuid4(), problem_type, code_template, test_template,
            json.dumps(dependencies), embedding, datetime.now()
        )
        
        return pattern_id
    
    def _extract_template(self, code: str) -> str:
        """Extract reusable template from code.
        
        Removes task-specific details like variable names, hardcoded values.
        """
        # Remove comments
        code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        
        # Normalize whitespace
        code = re.sub(r'\n\s*\n', '\n\n', code)
        
        # Keep structure, remove specifics
        # (More sophisticated extraction can be added)
        
        return code.strip()
```

---

## Pattern Retrieval

### When Patterns Are Retrieved

During **PLANNING** state, the Planner agent searches for similar past successful solutions.

### Retrieval Process

```python
class PatternMatcher:
    async def search_patterns(
        self,
        problem_description: str,
        threshold: float = 0.7,
        limit: int = 5
    ) -> List[dict]:
        """Search for similar successful patterns.
        
        Args:
            problem_description: Description of current problem
            threshold: Similarity threshold (0-1, lower = more similar)
            limit: Maximum number of results
            
        Returns:
            List of similar patterns with code templates
        """
        # Generate embedding for query
        query_embedding = await self.vector_store.generate_embedding(
            problem_description
        )
        
        # Query database with vector similarity
        results = await self.db.fetch(
            """
            SELECT 
                id,
                problem_type,
                code_template,
                test_template,
                dependencies,
                usage_count,
                success_rate,
                1 - (embedding <=> $1::vector) as similarity
            FROM patterns
            WHERE 1 - (embedding <=> $1::vector) > $2
            ORDER BY embedding <=> $1::vector
            LIMIT $3
            """,
            query_embedding, threshold, limit
        )
        
        # Increment usage count for retrieved patterns
        for result in results:
            await self._increment_usage_count(result["id"])
        
        return [dict(r) for r in results]
```

### Vector Search Query Explanation

```sql
-- <=> is pgvector's cosine distance operator
-- Returns distance from 0 (identical) to 2 (opposite)
-- We convert to similarity: 1 - distance

SELECT 
    1 - (embedding <=> query_embedding) as similarity
FROM patterns
WHERE 1 - (embedding <=> query_embedding) > 0.7  -- threshold
ORDER BY embedding <=> query_embedding           -- sort by distance
LIMIT 5
```

**Similarity Scores**:
- `1.0` - Identical
- `0.9-1.0` - Very similar
- `0.7-0.9` - Similar
- `0.5-0.7` - Somewhat related
- `<0.5` - Not related

---

## Failure Storage

### When Failures Are Stored

After a test failure occurs (REFLECTING state), the system:
1. Normalizes the error message
2. Generates an embedding
3. Stores in `failures` table
4. If later fixed, updates with solution

### Failure Schema

```sql
CREATE TABLE failures (
    id UUID PRIMARY KEY,
    error_signature VARCHAR(500),      -- Normalized error pattern
    error_type VARCHAR(100),           -- ImportError, AttributeError, etc.
    error_message TEXT,                -- Full error message
    solution TEXT,                     -- How it was fixed (null if not fixed)
    code_context TEXT,                 -- Relevant code snippet
    task_id UUID,                      -- Reference to task
    iteration INTEGER,                 -- Which iteration failed
    embedding vector(1536),            -- Vector embedding
    created_at TIMESTAMP,
    fixed_at TIMESTAMP
);

CREATE INDEX idx_failures_embedding ON failures USING ivfflat (embedding vector_cosine_ops);
```

### Storing a Failure

**File**: `src/memory/failure_analyzer.py`

```python
class FailureAnalyzer:
    """Analyze and store test failures."""
    
    async def store_failure(
        self,
        error_type: str,
        error_message: str,
        code_context: str,
        task_id: str,
        iteration: int
    ) -> str:
        """Store a test failure.
        
        Args:
            error_type: Type of error (ImportError, AttributeError, etc.)
            error_message: Full error message
            code_context: Relevant code snippet
            task_id: Task ID
            iteration: Iteration number
            
        Returns:
            Failure ID
        """
        # Normalize error signature
        error_signature = self._normalize_error(error_type, error_message)
        
        # Generate embedding
        text = f"{error_type}: {error_message}"
        embedding = await self.vector_store.generate_embedding(text)
        
        # Store in database
        failure_id = await self.db.execute(
            """
            INSERT INTO failures (id, error_signature, error_type, error_message,
                                 code_context, task_id, iteration, embedding, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
            """,
            uuid4(), error_signature, error_type, error_message,
            code_context, task_id, iteration, embedding, datetime.now()
        )
        
        return failure_id
    
    def _normalize_error(self, error_type: str, error_message: str) -> str:
        """Normalize error to a pattern signature.
        
        Example:
            "ImportError: No module named 'flask'" 
            → "ImportError: missing module"
        """
        if error_type == "ImportError":
            # Extract module name
            match = re.search(r"No module named ['\"](\w+)['\"]", error_message)
            if match:
                return f"ImportError: missing module"
        
        elif error_type == "AttributeError":
            # Normalize to pattern
            return "AttributeError: missing attribute"
        
        # Default: use first line
        return error_message.split('\n')[0][:500]
```

### Updating Failure with Solution

When a failure is eventually fixed:

```python
async def update_failure_solution(
    self,
    failure_id: str,
    solution: str
) -> None:
    """Update failure record with solution.
    
    Args:
        failure_id: Failure ID
        solution: How the error was fixed
    """
    await self.db.execute(
        """
        UPDATE failures
        SET solution = $1, fixed_at = $2
        WHERE id = $3
        """,
        solution, datetime.now(), failure_id
    )
```

---

## Failure Retrieval

### When Failures Are Retrieved

During **REFLECTING** state, the Reflector agent searches for similar past failures.

### Retrieval Process

```python
class FailureAnalyzer:
    async def search_similar_failures(
        self,
        error_message: str,
        threshold: float = 0.6,
        limit: int = 5
    ) -> List[dict]:
        """Search for similar past failures.
        
        Args:
            error_message: Current error message
            threshold: Similarity threshold (0-1)
            limit: Maximum results
            
        Returns:
            List of similar failures with solutions
        """
        # Generate embedding
        query_embedding = await self.vector_store.generate_embedding(
            error_message
        )
        
        # Query database - only return failures with solutions
        results = await self.db.fetch(
            """
            SELECT 
                id,
                error_type,
                error_message,
                solution,
                code_context,
                1 - (embedding <=> $1::vector) as similarity
            FROM failures
            WHERE solution IS NOT NULL                      -- Only fixed failures
              AND 1 - (embedding <=> $1::vector) > $2      -- Above threshold
            ORDER BY embedding <=> $1::vector
            LIMIT $3
            """,
            query_embedding, threshold, limit
        )
        
        return [dict(r) for r in results]
```

---

## Embedding Generation

**File**: `src/memory/vector_store.py`

### Generating Embeddings

```python
class VectorStore:
    """Manage embeddings and vector operations."""
    
    def __init__(self, llm_client: OpenAIClient):
        self.llm_client = llm_client
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            1536-dimensional embedding vector
        """
        # Truncate if too long (model limit: ~8k tokens)
        if len(text) > 30000:  # ~8k tokens
            text = text[:30000]
        
        # Call OpenAI embeddings API
        response = await self.llm_client.create_embedding(
            input=text,
            model="text-embedding-3-large"
        )
        
        return response.data[0].embedding
```

### Batch Embedding Generation

For better performance when storing multiple patterns:

```python
async def generate_embeddings_batch(
    self,
    texts: List[str]
) -> List[List[float]]:
    """Generate embeddings for multiple texts.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List of embedding vectors
    """
    # OpenAI supports batch embedding
    response = await self.llm_client.create_embedding(
        input=texts,
        model="text-embedding-3-large"
    )
    
    return [data.embedding for data in response.data]
```

---

## Learning Effectiveness Metrics

Track how well the memory system is working.

### Pattern Hit Rate

```python
async def get_pattern_hit_rate(self, time_range: str = "7d") -> float:
    """Calculate percentage of planning queries that find useful patterns.
    
    Args:
        time_range: Time range (e.g., "7d", "30d")
        
    Returns:
        Hit rate as percentage (0-100)
    """
    query = """
    SELECT 
        COUNT(*) as total_queries,
        COUNT(*) FILTER (WHERE patterns_found > 0) as successful_queries
    FROM iterations
    WHERE phase = 'planning'
      AND created_at > NOW() - INTERVAL $1
    """
    
    result = await self.db.fetchone(query, time_range)
    
    if result["total_queries"] == 0:
        return 0.0
    
    return (result["successful_queries"] / result["total_queries"]) * 100
```

### Pattern Success Rate

```python
async def calculate_pattern_success_rate(self, pattern_id: str) -> float:
    """Calculate success rate when this pattern is used.
    
    Args:
        pattern_id: Pattern ID
        
    Returns:
        Success rate as percentage (0-100)
    """
    query = """
    SELECT 
        COUNT(*) as total_uses,
        COUNT(*) FILTER (WHERE t.status = 'SUCCESS') as successful_uses
    FROM tasks t
    JOIN iterations i ON i.task_id = t.id
    WHERE i.patterns_used @> $1::jsonb  -- Pattern was used
    """
    
    result = await self.db.fetchone(query, json.dumps([pattern_id]))
    
    if result["total_uses"] == 0:
        return 0.0
    
    return (result["successful_uses"] / result["total_uses"]) * 100
```

### Memory Dashboard

```python
async def get_memory_stats(self) -> dict:
    """Get memory system statistics.
    
    Returns:
        Dictionary with memory stats
    """
    return {
        "total_patterns": await self.db.fetchval("SELECT COUNT(*) FROM patterns"),
        "total_failures": await self.db.fetchval("SELECT COUNT(*) FROM failures"),
        "failures_with_solutions": await self.db.fetchval(
            "SELECT COUNT(*) FROM failures WHERE solution IS NOT NULL"
        ),
        "pattern_hit_rate_7d": await self.get_pattern_hit_rate("7d"),
        "pattern_hit_rate_30d": await self.get_pattern_hit_rate("30d"),
        "most_used_patterns": await self.get_most_used_patterns(limit=10),
        "most_common_failures": await self.get_most_common_failures(limit=10)
    }
```

---

## Index Optimization

### Creating IVFFlat Index

```sql
-- Create IVFFlat index for faster similarity search
-- Lists parameter depends on dataset size:
-- - Small (<100k rows): 100
-- - Medium (100k-1M rows): 1000
-- - Large (>1M rows): 10000

CREATE INDEX idx_patterns_embedding 
ON patterns 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX idx_failures_embedding 
ON failures 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

### Index Maintenance

```python
async def rebuild_indexes(self) -> None:
    """Rebuild vector indexes for better performance.
    
    Should be run periodically as data grows.
    """
    await self.db.execute("REINDEX INDEX idx_patterns_embedding")
    await self.db.execute("REINDEX INDEX idx_failures_embedding")
```

---

## Configuration

**File**: `config/database.yaml`

```yaml
vector_search:
  embedding_model: "text-embedding-3-large"
  embedding_dimensions: 1536
  similarity_threshold_patterns: 0.7
  similarity_threshold_failures: 0.6
  max_results: 5
  
  # Index configuration
  ivfflat_lists: 100  # Adjust based on data size
  
  # Performance
  enable_batch_embedding: true
  cache_embeddings: true
  cache_ttl_seconds: 3600
```

---

## Best Practices

### When to Store Patterns

✅ **Do store**:
- Successfully completed tasks
- Solutions that passed all tests
- Solutions with good code quality (no major Bandit issues)

❌ **Don't store**:
- Failed tasks
- Solutions with hardcoded credentials
- Solutions with major security issues
- One-off hacks or workarounds

### When to Store Failures

✅ **Do store**:
- All test failures during iterations
- Include full context (error message, code snippet, iteration)
- Update with solution when fixed

❌ **Don't store**:
- Syntax errors (usually typos, not useful for learning)
- User interruptions (Ctrl+C)
- Infrastructure failures (DB down, API timeout)

### Threshold Tuning

- **Patterns**: 0.7-0.9 (high similarity required for reuse)
- **Failures**: 0.6-0.7 (more lenient, similar errors can have similar solutions)

Adjust based on metrics:
- Too high: No results found
- Too low: Irrelevant results

---

## For More Information

- **Database schema**: See `scripts/init_db.sql`
- **Architecture**: See [Architecture](architecture.md)
- **Agent behaviors**: See [Agent Behaviors](agent-behaviors.md)
