# AI Chatbot

Production-oriented, modular, and scalable AI Chatbot built with FastAPI and LangGraph.

## Status

**Phase 1 — Project Foundation & Engineering Tooling**

## Architectural Baseline

- **Pattern**: Modular Monolith with Hexagonal Architecture (Ports and Adapters)
- **API Layer**: FastAPI (Async)
- **AI Orchestration**: LangGraph
- **LLM Integration**: Provider-agnostic gateway abstraction
- **Observability**: LangSmith tracing and structured JSON logging
- **Configuration**: Environment-based with `pydantic-settings`
- **Data Modality**: Text initially, extensible polymorphic content architecture for future multimodal support (Images, Audio, Files)

## Technology Stack

### Currently Implemented (Phase 1)
- Python 3.11+
- FastAPI & Uvicorn
- Pydantic v2 & Pydantic-Settings
- Code Quality: Ruff (Linting & Formatting), MyPy (Strict typing)
- Testing: Pytest, pytest-asyncio, HTTPX

### Planned Technologies (Future Phases)
- AI Workflow: LangGraph & LangChain Core
- LLM Providers: OpenAI, Anthropic, Google Gemini (via `ILLMService`)
- Persistence: PostgreSQL (Prod) / SQLite (Dev) via SQLAlchemy 2.0 Async & Alembic
- Caching: Redis 7+ (Prod) / In-Memory (Dev) via `ICacheService`
- Tracing & Monitoring: LangSmith, Prometheus metrics

## Developer Setup

### 1. Prerequisites
- Python >= 3.11
- `uv` (recommended) or `pip`

### 2. Environment Setup
```bash
# Clone the repository
git clone <repo-url>
cd chatbot

# Create virtual environment and install dependencies
uv venv
uv pip install -e ".[dev]"
```

### 3. Configuration
Copy `.env.example` to `.env` and fill in required values:
```bash
cp .env.example .env
```

### 4. Running Quality Checks
```bash
# Linting
uv run ruff check .

# Formatting check
uv run ruff format --check .

# Type checking
uv run mypy app

# Testing
uv run pytest
```

## Git Workflow
- Branch naming: `feature/<feature-name>`, `fix/<bug-name>`, `chore/<task-name>`
- Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`, `ci:`
