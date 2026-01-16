# Scalability & Performance

> **Purpose**: Current limitations and future scaling strategies.

---

## 8.1 Current Limitations

| Resource | Current Limit | Bottleneck |
|----------|--------------|------------|
| Concurrent tasks | 1 | Single-threaded orchestrator |
| Max iterations | 15 | Cost control |
| LLM API rate | 10K RPM (depends on tier) | OpenAI rate limits |
| Vector search | <100K embeddings | pgvector index size |
| Docker containers | Unlimited | System resources |

---

## 8.2 Scaling Strategies

**Horizontal Scaling** (future enhancement):

```
┌─────────────────────────────────────────────────────────┐
│                   Load Balancer / Queue                  │
│                    (Celery + Redis)                      │
└────────┬────────────────┬───────────────┬───────────────┘
         │                │               │
         ▼                ▼               ▼
    ┌─────────┐      ┌─────────┐    ┌─────────┐
    │ Worker 1│      │ Worker 2│    │ Worker N│
    │ Orchestr│      │ Orchestr│    │ Orchestr│
    └────┬────┘      └────┬────┘    └────┬────┘
         │                │               │
         └────────────────┴───────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │ Shared PostgreSQL      │
              │ (task queue + results) │
              └────────────────────────┘
```

**Vertical Scaling** (current):
- Increase Docker container limits (CPU, RAM)
- Use faster GPU-based embedding generation
- Cache frequently-retrieved patterns in Redis

---

## 8.3 Performance Optimizations

**Database**:
```sql
-- Use prepared statements (avoid SQL injection + faster)
PREPARE get_similar_failures AS
SELECT id, error_message, solution, similarity
FROM (
    SELECT id, error_message, solution,
           1 - (embedding <=> $1::vector) AS similarity
    FROM failures
) subquery
WHERE similarity > $2
ORDER BY similarity DESC
LIMIT $3;

-- Execute with parameters
EXECUTE get_similar_failures('[...]'::vector, 0.6, 5);

-- Create materialized view for analytics
CREATE MATERIALIZED VIEW task_success_rates AS
SELECT
    language,
    task_type,
    COUNT(*) AS total,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS successful,
    AVG(current_iteration) AS avg_iterations
FROM tasks
GROUP BY language, task_type;

-- Refresh periodically
REFRESH MATERIALIZED VIEW task_success_rates;
```

**Caching**:
```python
from functools import lru_cache
import hashlib

class VectorStore:
    @lru_cache(maxsize=1000)
    def _generate_embedding_cached(self, text: str) -> tuple:
        """Cache embeddings for identical text (returns tuple for hashability)"""
        embedding = self._generate_embedding(text)  # Calls OpenAI API
        return tuple(embedding)  # Convert list to tuple for caching

    def embed(self, text: str) -> List[float]:
        """Public method with caching"""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        cached_key = f"embedding:{text_hash}"

        # Check Redis cache first
        cached = self.redis_client.get(cached_key)
        if cached:
            return json.loads(cached)

        # Generate and cache
        embedding = list(self._generate_embedding_cached(text))
        self.redis_client.setex(cached_key, 86400, json.dumps(embedding))  # 24h TTL
        return embedding
```

**Optimization Areas**:
1. **Vector search**: Cache frequent queries
2. **LLM calls**: Batch similar requests
3. **Database**: Use prepared statements and materialized views
4. **Memory**: Implement LRU caching for embeddings
5. **Parallelization**: Execute independent operations concurrently