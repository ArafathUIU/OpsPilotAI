# OpsPilot AI

> **Autonomous Multi-Agent Incident Response & Root Cause Analysis Platform**

OpsPilot AI is an enterprise-grade autonomous incident investigation platform. When production incidents occur across microservice architectures, OpsPilot orchestrates specialized AI agents (Supervisor, Log Analyst, Metrics Analyst, Code & Deployment Inspector, Incident Memory RAG, Root Cause Analysis, Critic, Remediation, Risk & Safety, Verification, and Reporting) within a deterministic LangGraph state machine to isolate root cause, challenge hypotheses, generate remediation plans, enforce deterministic human approvals for high-risk actions, execute fixes, and empirically verify recovery.

---

## Key Features

- **Deterministic Multi-Agent Orchestration**: Built on LangGraph state machine with typed Pydantic contracts and durable checkpoints.
- **Evidence-First Epistemology**: Root-cause hypotheses must cite immutable evidence IDs (`EV-xxxx`). Unsupported claims are rejected by the Critic Agent.
- **Human-in-the-Loop (HITL)**: Safe execution boundaries pause the graph before high-risk actions (`interrupt()`) awaiting operator approval.
- **RAG Episodic Memory**: PostgreSQL with `pgvector` indexing historical postmortems for contextual retrieval.
- **Multi-Provider LLM Resilience**: Dynamic failover across OpenAI, Gemini, and Groq with structured repair and token/cost budgeting.
- **Observability**: OpenTelemetry spans, Prometheus metrics, and structured JSON logs.

---

## Getting Started

### Prerequisites
- Python 3.12+
- Docker & Docker Compose

### Quick Start (Local Development)
```bash
# 1. Clone repository
git clone https://github.com/ArafathUIU/OpsPilotAI.git
cd OpsPilotAI

# 2. Configure environment
cp .env.example .env

# 3. Spin up infrastructure (PostgreSQL with pgvector, Redis)
docker compose up -d

# 4. Install dependencies
python -m venv .venv
source .venv/bin/activate  # Or .\.venv\Scripts\activate on Windows
pip install -e ".[dev]"

# 5. Run API server
uvicorn apps.api.main:app --reload --port 8000
```
