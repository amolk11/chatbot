# AI Chatbot

Production-oriented, modular, and scalable AI Chatbot built with FastAPI and LangGraph.

## Status

**Phase 3 — Basic LangGraph Chatbot Workflow & LLM Gateway** (Completed)

## Architectural Baseline

- **Pattern**: Modular Monolith with Hexagonal Architecture (Ports and Adapters)
- **API Layer**: FastAPI (Async) with structured middleware and global exception handling
- **AI Orchestration**: LangGraph state machine (`validate` -> `generate` -> `format`)
- **LLM Integration**: Provider-agnostic gateway (`ILLMService`) with OpenAI adapter and deterministic Mock service
- **Observability**: Structured JSON logging with correlation IDs (LangSmith planned for Phase 6)
- **Configuration**: Environment-based with `pydantic-settings`
- **Data Modality**: Text initially, polymorphic content block architecture (`CanonicalMessage`, `ContentBlock`) prepared for future multimodal support (Images, Audio, Files)

## Technology Stack

### Currently Implemented (Phases 1, 2, 3)
- Python 3.11+ (Active: Python 3.12)
- FastAPI & Uvicorn (Async ASGI server, application factory, lifespan context)
- LangGraph (State graph orchestration, isolated nodes, state machine compilation)
- OpenAI SDK (Async API adapter with timeout and error translation)
- Pydantic v2 & Pydantic-Settings (DTO schemas, validation, environment configuration)
- Middleware: Correlation ID propagation (`X-Correlation-ID`), Request Logging, CORS
- Global Exception Handlers: Standardized RFC-compliant `ErrorResponse` schema
- Code Quality: Ruff (Linting & Formatting), MyPy (Strict typing)
- Testing: Pytest, pytest-asyncio, HTTPX (52 isolated unit & integration tests)

### Planned Technologies (Future Phases)
- Persistence: PostgreSQL (Prod) / SQLite (Dev) via SQLAlchemy 2.0 Async & Alembic (Phase 4)
- Caching: Redis 7+ (Prod) / In-Memory (Dev) via `ICacheService` (Phase 5)
- Tracing & Monitoring: LangSmith, Prometheus metrics (Phase 6)
- Conversation Persistence & Long-term Memory (Phase 4)
- Streaming Responses: Server-Sent Events / WebSockets (Future)

## Execution Flow

```text
HTTP Client
    │
    ▼
POST /api/v1/chat
    │
    ▼
ChatService
    │
    ▼
LangGraph (ChatGraphState)
    ├── 1. Validate Node (Message structure & non-empty content)
    ├── 2. Generate Node
    │       │
    │       ▼
    │   ILLMService (Interface)
    │       ├── OpenAILLMService (Real Provider)
    │       └── MockLLMService (Offline / Testing)
    └── 3. Format Node (Normalize response to CanonicalMessage)
    │
    ▼
FastAPI Response (HTTP 200 + X-Correlation-ID)
```

> **Note on State**: Phase 3 chatbot execution is single-turn and stateless per request. Conversation persistence and history memory will be introduced in Phase 4.

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
Copy `.env.example` to `.env` and configure settings:
```bash
cp .env.example .env
```
Key settings for Phase 3:
- `LLM_PROVIDER`: `mock` (default for offline dev/tests) or `openai`
- `LLM_MODEL`: e.g. `gpt-4o-mini`
- `LLM_API_KEY`: Required only when `LLM_PROVIDER=openai`

### 4. Running the API Locally
```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 5. API Endpoints & Interactive Documentation
- **Liveness Probe**: `GET http://127.0.0.1:8000/health`
- **Readiness Probe**: `GET http://127.0.0.1:8000/health/ready`
- **Chat Endpoint**: `POST http://127.0.0.1:8000/api/v1/chat`
- **Swagger UI**: `http://127.0.0.1:8000/docs` (available in development mode)
- **ReDoc**: `http://127.0.0.1:8000/redoc`
- **OpenAPI Schema**: `http://127.0.0.1:8000/openapi.json`

#### Example Chat Request:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-Correlation-ID: my-trace-id-123" \
  -d '{"message": "Hello, how are you?"}'
```

#### Example Chat Response:
```json
{
  "message": {
    "id": "c7f26d24-3861-424a-81aa-1a4a408719bc",
    "role": "assistant",
    "content": [
      {
        "type": "text",
        "text": "This is a deterministic mock assistant response."
      }
    ],
    "created_at": "2026-09-14T09:05:36.265207Z",
    "text": "This is a deterministic mock assistant response."
  },
  "conversation_id": null
}
```

### 6. Running Quality Checks
```bash
# Linting
uv run ruff check .

# Formatting check
uv run ruff format --check .

# Type checking
uv run mypy app tests scripts

# Testing (Offline test suite)
uv run pytest
```

## Git Workflow
- Branch naming: `feature/<feature-name>`, `fix/<bug-name>`, `chore/<task-name>`
- Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`, `ci:`
