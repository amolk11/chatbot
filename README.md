# AI Chatbot

Production-oriented, modular, and scalable AI Chatbot built with FastAPI, LangGraph, SQLAlchemy 2.x Async, and Redis Caching.

## Status

**Phase 5 — Redis Caching & Cache Management** (Completed)

## Architectural Baseline

- **Pattern**: Modular Monolith with Hexagonal Architecture (Ports and Adapters)
- **API Layer**: FastAPI (Async) with structured middleware and global exception handling
- **AI Orchestration**: LangGraph state machine (`validate` -> `generate` -> `format`)
- **Persistence Layer**: SQLAlchemy 2.x Async ORM with Alembic schema migrations and `IConversationRepository` port
- **Caching Layer**: Context-aware caching (`ICache` port) with `RedisCacheAdapter` (production) and `InMemoryCache` (dev/testing)
- **LLM Integration**: Provider-agnostic gateway (`ILLMService`) with OpenAI adapter and deterministic Mock service
- **Observability**: Structured JSON logging with correlation IDs (LangSmith planned for Phase 6)
- **Configuration**: Environment-based with `pydantic-settings`
- **Data Modality**: Text initially, polymorphic content block architecture (`CanonicalMessage`, `ContentBlock`) prepared for future multimodal support (Images, Audio, Files)

## Technology Stack

### Currently Implemented (Phases 1, 2, 3, 4, 5)
- **Python 3.11+** (Active: Python 3.12)
- **FastAPI & Uvicorn** (Async ASGI server, application factory, lifespan context)
- **SQLAlchemy 2.x Async** (`aiosqlite` for local dev/testing, `asyncpg` compatible for PostgreSQL production)
- **Alembic** (Deterministic schema migrations)
- **Redis & redis-py** (Async Redis client with connection pooling, TTL, and error isolation)
- **LangGraph** (State graph orchestration, isolated nodes, state machine compilation)
- **OpenAI SDK** (Async API adapter with timeout and error translation)
- **Pydantic v2 & Pydantic-Settings** (DTO schemas, validation, environment configuration)
- **Middleware**: Correlation ID propagation (`X-Correlation-ID`), Request Logging, CORS
- **Global Exception Handlers**: Standardized RFC-compliant `ErrorResponse` schema
- **Code Quality**: Ruff (Linting & Formatting), MyPy (Strict typing)
- **Testing**: Pytest, pytest-asyncio, HTTPX (81 isolated unit, repository, transaction, migration, and cache tests)

### Planned Technologies (Future Phases)
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
Load Conversation History (up to CHAT_HISTORY_MAX_MESSAGES)
  ↓
Build Canonical Context Preimage (History + User Message + Provider/Model)
  ↓
Compute Deterministic Cache Key (chat:v1:{conversation_id}:{sha256(context)})
  ↓
Redis Cache Lookup (ICache.get)
      │
      ├── HIT ──────────────────────────────────────────┐
      │                                                 │
      └── MISS                                          │
            ↓                                           │
      LangGraph Workflow (validate → generate → format) │
            ↓                                           │
      LLM Gateway (MockLLM / OpenAILLM)                 │
            ↓                                           │
      Assistant CanonicalMessage                        │
            ↓                                           │
      Atomically Persist User + Assistant Turn (DB) ◄───┘
            ↓
      Populate Cache Entry (ICache.set with TTL) [on miss]
            ↓
      ChatResponse (HTTP 200 + conversation_id + X-Correlation-ID)
```

## Caching Strategy & Correctness

### 1. History-Sensitive Cache Keys
Cache keys are **never** constructed solely from the latest user message or conversation ID alone. The key includes a SHA-256 hash of the complete canonical context:
```text
chat:v1:{conversation_id}:{sha256(canonical_context_json)}
```
Where `canonical_context_json` includes:
- Chronological historical messages (role + content text)
- Current user message
- LLM Provider & Model names

*Example:*
- Conversation A (History: "My name is Amol", Question: "What is my name?") $\rightarrow$ `Key_A`
- Conversation B (History: "My name is Rahul", Question: "What is my name?") $\rightarrow$ `Key_B` (`Key_A != Key_B`)

### 2. Natural Cache Invalidation via History Evolution
As conversations advance with new messages, the context hash changes naturally, preventing stale response retrieval. Configurable TTL (`CACHE_TTL_SECONDS`) provides automated background expiration.

### 3. Turn Persistence on Cache Hits
When a response is served from cache, the current user message and cached assistant response are still persisted atomically to the database, ensuring history durability is never compromised.

### 4. Cache Failure Isolation (Non-fatal)
Redis is an acceleration optimization; the relational database is the single source of truth. If Redis is down or unreachable during `get` or `set`, the error is logged as a warning, and `ChatService` seamlessly continues normal LLM generation and database persistence without failing the client request.

## Database & Migrations

### Migration Management (Alembic)
Apply migrations to bring the database schema up to date:
```bash
# Run migrations against configured DATABASE_URL
uv run alembic upgrade head

# Rollback one revision
uv run alembic downgrade -1
```

### Database & Cache Configuration
- **Database (Development / Testing)**: `sqlite+aiosqlite:///./chatbot.db`
- **Database (PostgreSQL Production)**: `postgresql+asyncpg://<user>:<password>@<host>:<port>/<dbname>`
- **Cache**: `redis://localhost:6379/0` (or disabled via `CACHE_ENABLED=false`)

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
- `CACHE_ENABLED`: `false` (default offline) or `true`
- `CACHE_TTL_SECONDS`: `3600`
- `REDIS_URL`: `redis://localhost:6379/0`
- `DATABASE_URL`: `sqlite+aiosqlite:///./chatbot.db`
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

### 5. Running Quality Checks & Tests
```bash
# Linting
uv run ruff check .

# Formatting check
uv run ruff format --check .

# Type checking
uv run mypy app tests scripts

# Full offline test suite (81 tests)
uv run pytest -v

# Verification script
uv run python scripts/verify_api.py
```

## Git Workflow
- Branch naming: `feature/<feature-name>`, `fix/<bug-name>`, `chore/<task-name>`
- Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`, `ci:`


