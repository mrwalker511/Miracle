# Technical Decisions

> **Purpose**: Key architectural decisions and their rationale.

---

## 10.1 Key Architectural Decisions

### Decision 1: PostgreSQL + pgvector instead of dedicated vector DB (Pinecone, Weaviate)

**Rationale**:
- ✅ **Simplicity**: One database for both relational and vector data
- ✅ **ACID guarantees**: Task state + embeddings in same transaction
- ✅ **Cost**: No additional SaaS fees for vector DB
- ✅ **Scale**: pgvector handles <100K embeddings well (sufficient for MVP)
- ❌ **Scale limitations**: Dedicated vector DBs are faster at >1M embeddings

**Trade-off**: Accepted. If we reach 100K+ tasks, migrate to Pinecone.

---

### Decision 2: Max 15 iterations (hard limit)

**Rationale**:
- ✅ **Cost control**: Each iteration costs $0.10-$0.50 in LLM API calls
- ✅ **User experience**: Prevents tasks running indefinitely
- ✅ **Forcing function**: Encourages better task decomposition
- ❌ **Capability limit**: Some complex tasks might need >15 iterations

**Trade-off**: Accepted. Users can resume with more context if needed.

---

### Decision 3: Synchronous orchestration (not async agents)

**Rationale**:
- ✅ **Simplicity**: State transitions are deterministic and debuggable
- ✅ **Cost**: Don't pay for multiple parallel LLM calls
- ✅ **Correctness**: Each iteration learns from the previous
- ❌ **Speed**: Could parallelize some operations (e.g., test generation + pattern retrieval)

**Trade-off**: Accepted for MVP. Future: Parallelize where safe (no dependencies).

---

### Decision 4: Docker sandboxing (not VMs or cloud functions)

**Rationale**:
- ✅ **Speed**: Containers start in <1 second (VMs take minutes)
- ✅ **Cost**: No per-invocation costs (unlike Lambda)
- ✅ **Portability**: Works on any machine with Docker
- ✅ **Isolation**: Good enough for code execution safety
- ❌ **Security**: Not as isolated as VMs (shared kernel)

**Trade-off**: Accepted. For production, consider Firecracker (microVMs) for stronger isolation.

---

### Decision 5: OpenAI API (not self-hosted LLMs)

**Rationale**:
- ✅ **Quality**: GPT-4 is state-of-the-art for code generation
- ✅ **Simplicity**: No model training or GPU infrastructure
- ✅ **Reliability**: 99.9% uptime SLA
- ❌ **Cost**: $0.01-$0.03 per 1K tokens (adds up)
- ❌ **Latency**: Network calls add ~1-2 seconds per request
- ❌ **Privacy**: Code is sent to OpenAI (not suitable for proprietary code)

**Trade-off**: Accepted for MVP. Future: Support self-hosted LLMs (Ollama, vLLM) for privacy-sensitive use cases.

---

## 10.2 Open Questions

1. **Should we support multi-file refactoring in one iteration?**
   - Pros: More powerful, fewer iterations
   - Cons: Harder to test, more tokens used, higher risk of breaking changes

2. **How to handle very large codebases (>10K lines)?**
   - Current approach: Generate file by file
   - Alternative: Generate module structure first, then implement

3. **Should we implement a "human in the loop" mode?**
   - Pros: Better for complex tasks, user can guide the process
   - Cons: Loses full autonomy, requires user attention

4. **How to handle external API dependencies?**
   - Current approach: Block all network access
   - Alternative: Allow approved API calls with mocking

5. **Should we support more languages?**
   - Current: Python, Node.js
   - Candidates: TypeScript, Go, Java, C#
   - Consideration: Each language needs test framework integration