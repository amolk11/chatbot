# AI Chatbot

Production-oriented, modular, and scalable AI Chatbot built with FastAPI, LangGraph, and SQLAlchemy 2.x Async.

## Status

**Phase 4 — Persistence & Conversation History** (Completed)

## Architectural Baseline

- **Pattern**: Modular Monolith with Hexagonal Architecture (Ports and Adapters)
- **API Layer**: FastAPI (Async) with structured middleware and global exception handling
- **AI Orchestration**: LangGraph state machine (`validate` -> `generate` -> `format`)
- **Persistence Layer**: SQLAlchemy 2.x Async ORM with Alembic schema migrations and `IConversationRepository` port
- **LLM Integration**: Provider-agnostic gateway (`ILLMService`) with OpenAI adapter and deterministic Mock service
- **Observability**: Structured JSON logging with correlation IDs (LangSmith planned for Phase 6)
- **Configuration**: Environment-based with `pydantic-settings`
- **Data Modality**: Text initially, polymorphic content block architecture (`CanonicalMessage`, `ContentBlock`) prepared for future multimodal support (Images, Audio, Files)

## Technology Stack

### Currently Implemented (Phases 1, 2, 3, 4)
- **Python 3.11+** (Active: Python 3.12)
- **FastAPI & Uvicorn** (Async ASGI server, application factory, lifespan context)
- **SQLAlchemy 2.x Async** (`aiosqlite` for local dev/testing, `asyncpg` compatible for PostgreSQL production)
- **Alembic** (Deterministic schema migrations)
- **LangGraph** (State graph orchestration, isolated nodes, state machine compilation)
- **OpenAI SDK** (Async API adapter with timeout and error translation)
- **Pydantic v2 & Pydantic-Settings** (DTO schemas, validation, environment configuration)
- **Middleware**: Correlation ID propagation (`X-Correlation-ID`), Request Logging, CORS
- **Global Exception Handlers**: Standardized RFC-compliant `ErrorResponse` schema
- **Code Quality**: Ruff (Linting & Formatting), MyPy (Strict typing)
- **Testing**: Pytest, pytest-asyncio, HTTPX (66 isolated unit, repository, transaction, and migration tests)

### Planned Technologies (Future Phases)
- Caching: Redis 7+ (Prod) / In-Memory (Dev) via `ICacheService` (Phase 5)
- Tracing & Monitoring: LangSmith, Prometheus metrics (Phase 6)
- Streaming Responses: Server-Sent Events / WebSockets (Future)
- RAG & Vector Storage (Future)
- User Authentication & Authorization (Future)

## Execution Flow

```text
Client
  ↓
FastAPI (POST /api/v1/chat)
  ↓
ChatService
  ↓
Conversation Repository Port (IConversationRepository)
  ↓
Resolve / Create Conversation Session & Load History (up to CHAT_HISTORY_MAX_MESSAGES)
  ↓
Build Canonical Message History + Append Current User Message
  ↓
LangGraph Workflow (validate → generate → format)
  ↓
LLM Gateway (MockLLM / OpenAILLM)
  ↓
Assistant CanonicalMessage
  ↓
Atomically Persist User + Assistant Turn (BEGIN TRANSACTION → commit / rollback)
  ↓
ChatResponse (HTTP 200 + conversation_id + X-Correlation-ID)
```

## Conversation Semantics

1. **New Conversation** (No `conversation_id` provided):
   - A new UUID conversation session is created.
   - The user turn and assistant response are persisted atomically.
   - The generated `conversation_id` is returned in the response.

2. **Continuing a Conversation** (Existing `conversation_id` provided):
   - The conversation is resolved. If it does not exist, a clean `HTTP 404 (CONVERSATION_NOT_FOUND)` is returned.
   - The preceding conversation history is loaded (bounded chronologically by `CHAT_HISTORY_MAX_MESSAGES`).
   - The user message is appended and passed into LangGraph along with the loaded history.
   - Upon successful generation, the user and assistant messages are committed together with updated sequence numbers.

3. **Atomic Turn Durability**:
   - Both the user prompt and assistant response for a given turn are committed in a single atomic database transaction.
   - If LLM generation or persistence fails, uncommitted records are rolled back. Partial turns or empty conversations are never leaked.

## Database & Migrations

### Migration Management (Alembic)
Apply migrations to bring the database schema up to date:
```bash
# Run migrations against configured DATABASE_URL
uv run alembic upgrade head

# Rollback one revision
uv run alembic downgrade -1
```

### Database URL Configuration
- **Development / Offline Testing (Default)**: `sqlite+aiosqlite:///./chatbot.db`
- **PostgreSQL Production**: `postgresql+asyncpg://<user>:<password>@<host>:<port>/<dbname>`

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
Key settings:
- `DATABASE_URL`: `sqlite+aiosqlite:///./chatbot.db` (or `postgresql+asyncpg://...`)
- `CHAT_HISTORY_MAX_MESSAGES`: `50`
- `LLM_PROVIDER`: `mock` (default for offline dev/tests) or `openai`
- `LLM_MODEL`: e.g. `gpt-4o-mini`
- `LLM_API_KEY`: Required only when `LLM_PROVIDER=openai`

### 4. Running Migrations & API Locally
```bash
# Apply database migrations
uv run alembic upgrade head

# Run FastAPI development server
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 5. API Endpoints & Interactive Documentation
- **Liveness Probe**: `GET http://127.0.0.1:8000/health`
- **Readiness Probe**: `GET http://127.0.0.1:8000/health/ready` (checks application and database connectivity)
- **Chat Endpoint**: `POST http://127.0.0.1:8000/api/v1/chat`
- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`
- **OpenAPI Schema**: `http://127.0.0.1:8000/openapi.json`

#### Example Multi-Turn Chat:

**Turn 1 (Initiate conversation):**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "My favorite color is blue."}'
```
Response:
```json
{
  "message": {
    "id": "eec3125e-ca55-4430-bf2c-c5ebc816b6fd",
    "role": "assistant",
    "content": [{"type": "text", "text": "This is a deterministic mock assistant response."}],
    "created_at": "2026-09-14T09:29:24.808542Z",
    "text": "This is a deterministic mock assistant response."
  },
  "conversation_id": "dcfe2150-221b-4fac-b493-baadcbf81daa"
}
```

**Turn 2 (Continue conversation):**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is my favorite color?", "conversation_id": "dcfe2150-221b-4fac-b493-baadcbf81daa"}'
```

### 6. Running Quality Checks & Tests
```bash
# Linting
uv run ruff check .

# Formatting check
uv run ruff format --check .

# Type checking
uv run mypy app tests scripts

# Full offline test suite (66 tests)
uv run pytest -v

# Verification script
uv run python scripts/verify_api.py
```

## Git Workflow
- Branch naming: `feature/<feature-name>`, `fix/<bug-name>`, `chore/<task-name>`
- Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`, `ci:`

