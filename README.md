# AI Chatbot

Production-oriented, modular, and scalable AI Chatbot built with FastAPI and LangGraph.

## Status

**Phase 2 — FastAPI Foundation** (Completed)

## Architectural Baseline

- **Pattern**: Modular Monolith with Hexagonal Architecture (Ports and Adapters)
- **API Layer**: FastAPI (Async) with structured middleware and global exception handling
- **AI Orchestration**: LangGraph (Planned Phase 3)
- **LLM Integration**: Provider-agnostic gateway abstraction (Planned Phase 3)
- **Observability**: LangSmith tracing (Planned Phase 6) and structured JSON logging with correlation IDs
- **Configuration**: Environment-based with `pydantic-settings`
- **Data Modality**: Text initially, extensible polymorphic content architecture for future multimodal support (Images, Audio, Files)

## Technology Stack

### Currently Implemented (Phase 1 & 2)
- Python 3.11+ (Active: Python 3.12)
- FastAPI & Uvicorn (ASGI application factory, router hierarchy, lifespan context)
- Pydantic v2 & Pydantic-Settings (DTO schemas, validation, environment configuration)
- Middleware: Correlation ID propagation (`X-Correlation-ID`), Request Logging, CORS
- Global Exception Handlers: Standardized `ErrorResponse` schema (RFC-compliant)
- Code Quality: Ruff (Linting & Formatting), MyPy (Strict typing)
- Testing: Pytest, pytest-asyncio, HTTPX (Isolated unit & integration tests)

### Planned Technologies (Future Phases)
- AI Workflow: LangGraph & LangChain Core (Phase 3)
- LLM Providers: OpenAI, Anthropic, Google Gemini via `ILLMService` (Phase 3)
- Persistence: PostgreSQL (Prod) / SQLite (Dev) via SQLAlchemy 2.0 Async & Alembic (Phase 4)
- Caching: Redis 7+ (Prod) / In-Memory (Dev) via `ICacheService` (Phase 5)
- Tracing & Monitoring: LangSmith, Prometheus metrics (Phase 6)

## Request Flow & Middleware Order

```text
Incoming Request
       │
       ▼
1. CORSMiddleware (Handles preflight OPTIONS & CORS headers)
       │
       ▼
2. CorrelationIdMiddleware (Validates/generates UUID and binds to contextvars)
       │
       ▼
3. RequestLoggingMiddleware (Measures request duration, logs with correlation ID)
       │
       ▼
4. Route & Exception Handlers (Standardized JSON responses: ChatbotError, 422, 404, 500)
       │
       ▼
Response (Includes X-Correlation-ID header)
```

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

### 4. Running the API Locally
```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 5. API Endpoints & Interactive Documentation
- **Liveness Probe**: `GET http://127.0.0.1:8000/health`
- **Readiness Probe**: `GET http://127.0.0.1:8000/health/ready`
- **Swagger UI**: `http://127.0.0.1:8000/docs` (available in development mode)
- **ReDoc**: `http://127.0.0.1:8000/redoc`
- **OpenAPI Schema**: `http://127.0.0.1:8000/openapi.json`

### 6. Running Quality Checks
```bash
# Linting
uv run ruff check .

# Formatting check
uv run ruff format --check .

# Type checking
uv run mypy app tests

# Testing
uv run pytest
```

## Git Workflow
- Branch naming: `feature/<feature-name>`, `fix/<bug-name>`, `chore/<task-name>`
- Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`, `ci:`
