# Deployment Architecture

> **Purpose**: How to deploy the system in different environments.

---

## 9.1 Local Development

```
┌──────────────────────────────────────────┐
│           Developer Laptop                │
│                                           │
│  ┌────────────────────────────────────┐  │
│  │  Python 3.11 Virtual Environment   │  │
│  │  - src/ (autonomous agent code)    │  │
│  │  - pytest (running tests)          │  │
│  └────────────────────────────────────┘  │
│                  │                        │
│                  ▼                        │
│  ┌────────────────────────────────────┐  │
│  │  Docker Compose                    │  │
│  │  ┌──────────────┐  ┌────────────┐ │  │
│  │  │ PostgreSQL   │  │  Sandbox   │ │  │
│  │  │ + pgvector   │  │ Container  │ │  │
│  │  └──────────────┘  └────────────┘ │  │
│  └────────────────────────────────────┘  │
│                                           │
└──────────────────────────────────────────┘
```

**Setup**:
```bash
# Install dependencies
pip install -r requirements.txt

# Start services (Docker is optional; PostgreSQL 14+ required)
docker-compose up -d

# Initialize database
python scripts/setup_db.py

# Run agent
python -m src.main run --task "Your task here"
```

---

## 9.2 Production Deployment (Future)

```
┌─────────────────────────────────────────────────────────┐
│                      Cloud Provider                      │
│                   (AWS / GCP / Azure)                    │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │              Load Balancer / API Gateway            │ │
│  └────────┬───────────────────────┬───────────────────┘ │
│           │                       │                      │
│           ▼                       ▼                      │
│  ┌─────────────────┐     ┌─────────────────┐           │
│  │  ECS/K8s Pod 1  │     │  ECS/K8s Pod N  │           │
│  │  - Orchestrator │     │  - Orchestrator │           │
│  │  - Agents       │     │  - Agents       │           │
│  └────────┬────────┘     └────────┬────────┘           │
│           │                       │                      │
│           └───────────┬───────────┘                      │
│                       │                                  │
│           ┌───────────┴──────────────┐                  │
│           │  Shared Redis Cache    │                  │
│           │  - Rate limiting      │                  │
│           │  - Embedding cache     │                  │
│           └──────────────────────────┘                  │
│                       │                                  │
│           ┌───────────┴──────────────┐                  │
│           │  Task Queue            │                  │
│           │  (Celery + Redis)      │                  │
│           └──────────────────────────┘                  │
│                       │                                  │
│           ┌───────────┴──────────────┐                  │
│           │                          │                  │
│           ▼                          ▼                  │
│  ┌──────────────────┐       ┌──────────────────┐      │
│  │  RDS PostgreSQL  │       │  Docker Runtime  │      │
│  │  + pgvector      │       │  (for sandboxes) │      │
│  └──────────────────┘       └──────────────────┘      │
│           │                                             │
│           ▼                                             │
│  ┌──────────────────┐                                  │
│  │  S3 / Cloud      │                                  │
│  │  Storage (logs)  │                                  │
│  └──────────────────┘                                  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Considerations**:
- **Database**: Managed PostgreSQL (RDS, Cloud SQL) with pgvector extension
- **Container orchestration**: Kubernetes or ECS for auto-scaling
- **Secrets management**: AWS Secrets Manager, GCP Secret Manager
- **Logging**: CloudWatch, Stackdriver, or ELK stack
- **Monitoring**: Prometheus + Grafana for metrics
- **Cost tracking**: Tag resources by task_id for cost attribution

**Production Requirements**:
1. **High availability**: Multi-AZ database deployment
2. **Scalability**: Auto-scaling based on queue depth
3. **Security**: IAM roles, VPC isolation, encryption at rest
4. **Observability**: Comprehensive logging and monitoring
5. **Cost control**: Budget alerts and rate limiting