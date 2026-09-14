# AI Chatbot

Production-oriented, modular, and scalable AI Chatbot built with FastAPI, LangGraph, SQLAlchemy 2.x Async, Redis Caching, and LangSmith Observability.

## Status

**Phase 6 — Observability, LangSmith & Monitoring** (Completed)

## Architectural Baseline

- **Pattern**: Modular Monolith with Hexagonal Architecture (Ports and Adapters)
- **API Layer**: FastAPI (Async) with structured middleware and global exception handling
- **AI Orchestration**: LangGraph state machine (`validate` -> `generate` -> `format`)
- **Persistence Layer**: SQLAlchemy 2.x Async ORM with Alembic schema migrations and `IConversationRepository` port
- **Caching Layer**: Context-aware caching (`ICache` port) with `RedisCacheAdapter` (production) and `InMemoryCache` (dev/testing)
- **LLM Integration**: Provider-agnostic gateway (`ILLMService`) with OpenAI adapter and deterministic Mock service
- **Observability**: Distributed LangSmith tracing, structured JSON logging with correlation IDs, and process-level metrics collection
- **Configuration**: Environment-based with `pydantic-settings`
- **Data Modality**: Text initially, polymorphic content block architecture (`CanonicalMessage`, `ContentBlock`) prepared for future multimodal support (Images, Audio, Files)

## Technology Stack

### Currently Implemented (Phases 1, 2, 3, 4, 5, 6)
- **Python 3.11+** (Active: Python 3.12)
- **FastAPI & Uvicorn** (Async ASGI server, application factory, lifespan context)
- **SQLAlchemy 2.x Async** (`aiosqlite` for local dev/testing, `asyncpg` compatible for PostgreSQL production)
- **Alembic** (Deterministic schema migrations)
- **Redis & redis-py** (Async Redis client with connection pooling, TTL, and error isolation)
- **LangSmith & LangGraph** (Distributed execution tracing, state graph orchestration, metadata tagging)
- **OpenAI SDK** (Async API adapter with timeout, token usage parsing, and monotonic latency measurement)
- **Pydantic v2 & Pydantic-Settings** (DTO schemas, validation, environment configuration)
- **Middleware**: Correlation ID propagation (`X-Correlation-ID`), Request Logging, CORS
- **Global Exception Handlers**: Standardized RFC-compliant `ErrorResponse` schema
- **Code Quality**: Ruff (Linting & Formatting), MyPy (Strict typing)
- **Testing**: Pytest, pytest-asyncio, HTTPX (89 isolated unit, repository, transaction, migration, cache, and observability tests)

### Planned Technologies (Future Phases)
- Streaming Responses: Server-Sent Events / WebSockets (Future)
- RAG & Vector Storage (Future)
- User Authentication & Authorization (Future)

## Execution Flow

```text
Client
  ↓
FastAPI (POST /api/v1/chat with X-Correlation-ID)
  ↓
RequestLoggingMiddleware & CorrelationIdMiddleware (captures trace context)
  ↓
ChatService
  ↓
Load Conversation History (up to CHAT_HISTORY_MAX_MESSAGES) [record_persistence_event]
  ↓
Build Canonical Context Preimage (History + User Message + Provider/Model)
  ↓
Compute Deterministic Cache Key (chat:v1:{conversation_id}:{sha256(context)})
  ↓
Redis Cache Lookup (ICache.get) [record_cache_event]
      │
      ├── HIT ──────────────────────────────────────────┐
      │                                                 │
      └── MISS                                          │
            ↓                                           │
      Build LangGraph Trace Config (metadata + tags)    │
            ↓                                           │
      LangGraph Workflow (validate → generate → format) │
            ↓                                           │
      LLM Gateway (MockLLM / OpenAILLM)                 │
      [records latency + token counts via record_llm_event]
            ↓                                           │
      Assistant CanonicalMessage                        │
            ↓                                           │
      Atomically Persist User + Assistant Turn (DB) ◄───┘
      [record_persistence_event]
            ↓
      Populate Cache Entry (ICache.set with TTL) [on miss]
            ↓
      ChatResponse (HTTP 200 + conversation_id + X-Correlation-ID)
```

## Observability & Monitoring Architecture

### 1. LangSmith Distributed Tracing
- Enabled via `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY`.
- Tracing is **disabled by default** to preserve 100% offline development and testing.
- LangGraph execution turns are enriched via `build_langgraph_trace_config` attaching:
  - `correlation_id`: Distributed HTTP request correlation identifier
  - `conversation_id`: Persistent conversation session identifier
  - `provider`: Active LLM provider (`openai`, `mock`)
  - `model`: Configured model identifier (`gpt-4o-mini`)
  - `tags`: `["chatbot", "provider:<provider>", "env:<env>"]`

### 2. Metrics Collection
The application incorporates a process-local, thread-safe `MetricsCollector` singleton tracking:
- **Counters**:
  - `http_requests_total`, `http_request_errors_total`
  - `llm_requests_total`, `llm_errors_total`
  - `cache_hits_total`, `cache_misses_total`, `cache_errors_total`
  - `persistence_operations_total`, `persistence_errors_total`
- **Summary Distributions (Rolling Window Percentiles)**:
  - `http_duration_ms` (avg, min, max, p95)
  - `llm_latency_ms` (avg, min, max, p95)
  - `persistence_duration_ms` (avg, min, max, p95)

### 3. Structured Event Logging & Privacy Protection
- Standardized logging helpers: `record_cache_event`, `record_persistence_event`, and `record_llm_event`.
- `SensitiveDataFilter` automatically scrubs API keys (e.g. `sk-...`, `lsv2_...`), bearer tokens, and credentials from all log outputs.

### 4. Failure Isolation (Non-Fatal)
Observability instrumentation is strictly non-blocking and isolated:
- Tracing or telemetry network drops never fail chat turns (`HTTP 500`).
- Health and readiness probes (`/health`, `/health/ready`) maintain independent lifecycle checks.

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

### Database, Cache & Observability Configuration
- **Database (Development / Testing)**: `sqlite+aiosqlite:///./chatbot.db`
- **Database (PostgreSQL Production)**: `postgresql+asyncpg://<user>:<password>@<host>:<port>/<dbname>`
- **Cache**: `redis://localhost:6379/0` (or disabled via `CACHE_ENABLED=false`)
- **LangSmith Tracing**: Disabled by default (`LANGSMITH_TRACING=false`), configure with `LANGSMITH_API_KEY` and `LANGSMITH_PROJECT`

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
- `LANGSMITH_TRACING`: `false` (default) or `true`
- `LANGSMITH_API_KEY`: Required if `LANGSMITH_TRACING=true`
- `LANGSMITH_PROJECT`: e.g. `chatbot-dev`
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

# Full offline test suite (89 tests)
uv run pytest -v

# Verification script
uv run python scripts/verify_api.py
```

## Git Workflow
- Branch naming: `feature/<feature-name>`, `fix/<bug-name>`, `chore/<task-name>`
- Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`, `ci:`
