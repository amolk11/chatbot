# PHASE 0 — COMPLETE ARCHITECTURAL SPECIFICATION & TECHNICAL BLUEPRINT

**Project**: Modular, Scalable, Production-Ready AI Chatbot  
**Role**: Senior Software Architect & Lead AI Engineer  
**Status**: Specification Complete (Ready for User Review / Phase 1 Approval)

---

## 1. EXECUTIVE SUMMARY & ARCHITECTURAL OVERVIEW (DELIVERABLE 1)

The system is designed as a **clean, modular monolith** adhering to **Hexagonal / Ports-and-Adapters** architectural patterns with strict Layered Separation of Concerns. It separates inbound network protocols (FastAPI HTTP/SSE/WebSocket) from application workflows (LangGraph), business domain logic, LLM provider integrations, caching, and persistence mechanisms.

### 1.1 Key Principles
- **Modularity & Decoupling**: Application core and graph workflows have zero coupling to FastAPI or underlying DB/Redis drivers.
- **Multimodal-Ready by Design**: The canonical message domain model supports polymorphic content blocks (`text`, `image`, `audio`, `file_ref`) from Day 1, even though initial endpoints and processors activate text only.
- **Strict Boundary Abstractions**: LLM interactions use a provider-agnostic gateway; cache uses a declarative caching port; persistence uses repository interfaces.
- **Full-Spectrum Observability**: End-to-end distributed tracing correlating HTTP Request ID -> Conversation ID -> LangGraph Run ID -> LangSmith Traces -> Structured JSON Logs.

### 1.2 System Architecture Diagram (ASCII)

```text
+---------------------------------------------------------------------------------------------------------+
|                                           CLIENT APPLICATIONS                                           |
|                               (Web UI / Mobile / External API Consumers)                                |
+---------------------------------------------------------------------------------------------------------+
                                                     |  HTTPS (JSON / SSE Streaming)
                                                     v
+---------------------------------------------------------------------------------------------------------+
|                                        API LAYER (FastAPI)                                              |
|  - Middleware: Correlation ID, Request Logging, CORS, Rate Limiter (Token Bucket), Global Error Handler |
|  - Routers: /health, /api/v1/chat, /api/v1/conversations                                                |
|  - Pydantic v2 DTOs: Serialization, Request Validation, Response Schemas                               |
|  - Dependency Injection (DI): Injects Services & Repositories into route handlers                       |
+---------------------------------------------------+-----------------------------------------------------+
                                                    | Inbound DTOs converted to Domain Models
                                                    v
+---------------------------------------------------------------------------------------------------------+
|                                        SERVICE LAYER (Orchestration)                                    |
|  - ChatService: Conversation lifecycle, orchestrating input validation, graph invocation, persistence   |
|  - ConversationService: Session history retrieval, pagination, conversation deletion                   |
+---------------------------+------------------------+----------------------------------+------------------+
                            |                        |                                  |
                            v                        v                                  v
+----------------------------------+  +------------------------------+  +----------------------------------+
|      INPUT PROCESSOR PIPELINE    |  |   PERSISTENCE LAYER (Ports)  |  |       CACHE LAYER (Ports)        |
|  - TextProcessor (Active)        |  |  - IConversationRepository   |  |  - ICacheService                 |
|  - ImageProcessor (Plug-in stub) |  |  - IMessageRepository        |  |  - In-Memory Cache (Local Dev)   |
|  - AudioProcessor (Plug-in stub) |  |  Implementations:            |  |  - RedisCache (Production)      |
|  Produces: Normalized Message    |  |  - SQLModel / SQLAlchemy 2.0 |  |  Use: Semantics, History, State  |
+-------------------+--------------+  |    (SQLite / PostgreSQL)     |  +----------------------------------+
                    |                 +------------------------------+
                    v
+---------------------------------------------------------------------------------------------------------+
|                                     WORKFLOW LAYER (LangGraph)                                          |
|  - State: AppState (conversation_id, messages: list[CanonicalMessage], context, error, metadata)        |
|  - Nodes:                                                                                               |
|      1. `validate_and_normalize_input`: Validates token bounds, sanitizes input content                 |
|      2. `load_context`: Hydrates history window + system prompt + future RAG context                   |
|      3. `llm_generate`: Invokes ILLMService via LangGraph Runnable                                      |
|      4. `format_and_persist_state`: Formats output message, attaches usage metrics                      |
|  - Edges: Linear pipeline with conditional error-fallback routing                                       |
+---------------------------------------------------+-----------------------------------------------------+
                                                    |
                                                    v
+---------------------------------------------------------------------------------------------------------+
|                                     LLM GATEWAY LAYER (Abstraction)                                     |
|  - Interface: `ILLMService` (generate(), generate_stream(), count_tokens())                              |
|  - Adapters:                                                                                            |
|      * LangChain / ChatOpenAI / ChatAnthropic / ChatGoogleGenerativeAI wrapper                          |
|      * Fallback & Circuit Breaker: Retries with exponential backoff & secondary model fallback           |
|  - Observability Hook: LangSmith tracer callbacks attached to runnable invocations                      |
+---------------------------------------------------+-----------------------------------------------------+
                                                    |
                                                    v
+---------------------------------------------------------------------------------------------------------+
|                                        EXTERNAL PROVIDERS & INFRA                                       |
|  - LLM APIs (OpenAI / Anthropic / Gemini / Local Ollama)                                                |
|  - Observability: LangSmith (LLM Traces) + Structured JSON Logs (Stdout/File)                          |
|  - Database: PostgreSQL (Production) / SQLite (Local/CI)                                                 |
|  - Cache & State Store: Redis 7+ (Production) / In-Memory (Local/CI)                                     |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. FINAL RECOMMENDED DIRECTORY STRUCTURE (DELIVERABLE 2)

```text
chatbot/
├── .github/
│   └── workflows/
│       ├── ci.yml                    # Automated linting, type-checking, and unit/integration tests
│       └── eval.yml                  # Scheduled LangSmith model evaluation & regression runs
├── app/
│   ├── __init__.py
│   ├── main.py                       # FastAPI application factory, lifespan context, middleware setup
│   │
│   ├── api/                          # HTTP / Network Delivery Layer
│   │   ├── __init__.py
│   │   ├── dependencies.py           # FastAPI dependency injection providers (Services, DB sessions)
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── correlation.py        # Request ID / Correlation ID injection & propagation
│   │   │   ├── logging.py            # HTTP access logging with latency & status codes
│   │   │   └── rate_limit.py         # Memory/Redis Token Bucket Rate Limiting middleware
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py             # Aggregated API v1 router
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── chat.py           # POST /api/v1/chat, POST /api/v1/chat/stream
│   │           ├── conversations.py  # GET /api/v1/conversations/{id}, DELETE /api/v1/conversations/{id}
│   │           └── health.py         # GET /health, GET /health/ready (Liveness/Readiness probes)
│   │
│   ├── core/                         # Cross-Cutting Infrastructure & Settings
│   │   ├── __init__.py
│   │   ├── config.py                 # Pydantic-Settings BaseSettings configuration
│   │   ├── constants.py              # Application constants & Enums (Roles, ContentTypes, etc.)
│   │   ├── exceptions.py             # Domain & Infrastructure Exception hierarchy
│   │   ├── logging.py                # Structured JSON logging configuration (structlog/stdlib)
│   │   └── security.py               # API Key validation, input sanitization helpers, CORS rules
│   │
│   ├── schemas/                      # Public API Data Transfer Objects (Pydantic v2)
│   │   ├── __init__.py
│   │   ├── chat.py                   # ChatRequest, ChatResponse, StreamChunk DTOs
│   │   ├── common.py                 # Pagination, ErrorResponse, HealthResponse DTOs
│   │   ├── conversation.py           # ConversationRead, ConversationSummary DTOs
│   │   └── message.py                # MessageRequest, MessageResponse, ContentBlockDTO schemas
│   │
│   ├── domain/                       # Pure Business & Domain Entities (No Framework Dependencies)
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── conversation.py       # Domain Conversation aggregate root
│   │   │   ├── message.py            # CanonicalMessage & ContentBlock domain models
│   │   │   └── multimodal.py         # TextContent, ImageContent, AudioContent value objects
│   │   └── processors/               # Modality input processors
│   │       ├── __init__.py
│   │       ├── base.py               # IInputProcessor base interface
│   │       ├── text.py               # TextNormalizer & TokenEstimator
│   │       ├── image.py              # ImageProcessor stub (MIME check, dimensions, downsampling)
│   │       └── audio.py              # AudioProcessor stub (Duration check, format validation)
│   │
│   ├── graph/                        # AI Orchestration (LangGraph Workflow)
│   │   ├── __init__.py
│   │   ├── builder.py                # StateGraph assembly, node wiring, compilation
│   │   ├── state.py                  # GraphState definition (TypedDict / Pydantic)
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── validate_input.py     # Node: validates bounds, sanitizes input
│   │   │   ├── load_context.py       # Node: loads conversation window / system prompts
│   │   │   ├── llm_generate.py       # Node: interacts with ILLMService
│   │   │   └── format_output.py      # Node: packages response, tracks tokens & timestamps
│   │   └── edges.py                  # Conditional edges, retry routing, and error branches
│   │
│   ├── llm/                          # LLM Gateway & Provider Adapters
│   │   ├── __init__.py
│   │   ├── base.py                   # ILLMService abstract interface
│   │   ├── factory.py                # LLMFactory (instantiates providers based on config)
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── openai.py             # OpenAI / Azure OpenAI adapter
│   │   │   ├── anthropic.py          # Anthropic Claude adapter
│   │   │   ├── google.py             # Google Gemini adapter
│   │   │   └── mock.py               # MockLLM for unit tests & offline evaluation
│   │   └── fallback.py               # Fallback & Circuit Breaker LLM wrapper
│   │
│   ├── services/                     # Application Service Orchestration Layer
│   │   ├── __init__.py
│   │   ├── chat_service.py           # Main Chat Orchestrator (Input -> Graph -> Persistence)
│   │   └── conversation_service.py   # Conversation query & management service
│   │
│   ├── cache/                        # Caching Ports & Adapters
│   │   ├── __init__.py
│   │   ├── base.py                   # ICacheService abstract interface
│   │   ├── memory.py                 # In-Memory Cache adapter (for testing/local)
│   │   ├── redis.py                  # Redis Cache adapter (asyncio / redis-py)
│   │   └── keys.py                   # Cache key naming convention helpers
│   │
│   ├── db/                           # Persistence Ports, ORM Models & Migrations
│   │   ├── __init__.py
│   │   ├── session.py                # Async database engine & sessionmaker (SQLAlchemy 2.0)
│   │   ├── base.py                   # Base declarative class with timestamp mixins
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── conversation.py       # Conversation ORM table definition
│   │   │   └── message.py            # Message & MessageContent ORM table definitions
│   │   └── repositories/
│   │       ├── __init__.py
│   │       ├── base.py               # IRepository generic interface
│   │       ├── conversation_repo.py  # ConversationRepository (SQLAlchemy implementation)
│   │       └── message_repo.py       # MessageRepository (SQLAlchemy implementation)
│   │
│   └── observability/                # Tracing & Monitoring
│       ├── __init__.py
│       ├── langsmith.py              # LangSmith client setup, RunTree callbacks, tracer factory
│       └── metrics.py                # Prometheus / OpenTelemetry metrics counters & latency histograms
│
├── migrations/                       # Alembic Database Migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── tests/                            # Test Suite (Pytest)
│   ├── __init__.py
│   ├── conftest.py                   # Global fixtures (test client, mock LLM, in-memory DB, clean cache)
│   ├── unit/                         # Fast, fully-isolated unit tests
│   │   ├── test_config.py
│   │   ├── test_input_processors.py
│   │   ├── test_llm_factory.py
│   │   ├── test_cache_service.py
│   │   └── test_schemas.py
│   ├── integration/                  # Database, Redis, and LangGraph workflow tests
│   │   ├── test_repositories.py
│   │   ├── test_graph_execution.py
│   │   └── test_redis_cache.py
│   ├── api/                          # End-to-end HTTP endpoint tests (AsyncClient)
│   │   ├── test_health_api.py
│   │   ├── test_chat_api.py
│   │   └── test_conversation_api.py
│   └── evaluation/                   # LLM response quality & LangSmith eval datasets
│       ├── test_prompt_eval.py
│       └── dataset_definitions.json
│
├── scripts/                          # Utility & Administrative Scripts
│   ├── lint.sh / lint.bat            # Runs ruff, black, mypy
│   ├── test.sh / test.bat            # Runs pytest with coverage report
│   ├── seed_db.py                    # Populates development database with mock history
│   └── run_evals.py                  # Executes LangSmith automated evaluation pipelines
│
├── docs/                             # Project Documentation & Architecture
│   ├── architecture/
│   │   ├── adrs/                     # Architectural Decision Records (ADR-001 to ADR-009)
│   │   └── diagrams/
│   ├── api_spec.json                 # OpenAPI 3.1 JSON export
│   └── runbooks/
│
├── .env.example                      # Documented environment variable template
├── .gitignore                        # Git exclusion rules
├── pyproject.toml                    # Poetry / Hatch / UV project definition & dependency pins
├── alembic.ini                       # Alembic DB migration configuration
├── README.md                         # Developer onboarding & architectural overview
└── Dockerfile                        # Multi-stage production container build
```

---

## 3. COMPONENT RESPONSIBILITIES & DEPENDENCY BOUNDARIES (DELIVERABLE 3)

| Component / Layer | Primary Responsibility | Allowed Dependencies (Can Import) | Forbidden Dependencies (Must NEVER Import) |
| :--- | :--- | :--- | :--- |
| **API Layer** (`app/api`) | Request deserialization, HTTP status codes, routing, auth middleware, SSE streaming format. | `schemas`, `services`, `core`, `FastAPI` | `db.models`, `graph`, raw DB drivers, direct LLM SDKs |
| **Service Layer** (`app/services`) | Use-case orchestration, transaction boundaries, orchestrating Input Processors -> Graph -> Repositories -> Cache. | `domain`, `schemas`, `graph`, `db.repositories (interfaces)`, `cache (interfaces)`, `core` | `FastAPI` (Request/Response objects), specific DB ORM sessions |
| **Domain Layer** (`app/domain`) | Core business entities (`CanonicalMessage`, `ContentBlock`), validation rules, pure input normalization logic. | Pure Python, `pydantic` (if used for validation), `core.exceptions` | `FastAPI`, `LangGraph`, `SQLAlchemy`, `Redis`, `app.api`, `app.services` |
| **Graph Layer** (`app/graph`) | Workflow state definition, execution node functions, conditional branching, context assembly. | `domain`, `llm (interfaces)`, `core` | `FastAPI`, `app.api`, `app.services`, ORM database queries directly |
| **LLM Gateway** (`app/llm`) | Translating domain messages to provider prompts, model invocation, retries, fallback switching, streaming. | `domain`, `core`, LLM SDKs (LangChain / OpenAI / Anthropic / Gemini), `observability` | `FastAPI`, `app.api`, `app.services`, `db`, `cache` |
| **Persistence Layer** (`app/db`) | Data mapping, SQL generation, connection pooling, migrations, database queries via repositories. | `domain`, `core`, `SQLAlchemy`, `Alembic` | `FastAPI`, `app.api`, `graph`, `llm`, `services` |
| **Cache Layer** (`app/cache`) | Key generation, TTL enforcement, serialization/deserialization of cached entries. | `core`, `redis-py` (in adapter only) | `FastAPI`, `app.api`, `graph`, `services` |
| **Core Layer** (`app/core`) | Settings loading, logging setup, security utilities, base exception classes. | Pure Python, `pydantic-settings` | Everything else in `app/` (Base leaf layer) |

---

## 4. END-TO-END DATA FLOW (DELIVERABLE 4)

```text
Step 1: Client Request
   └─ Client sends HTTP POST /api/v1/chat with JSON payload containing `conversation_id` (optional) and polymorphic `message`.
Step 2: API & Middleware Processing
   ├─ `correlation.py`: Injects `X-Correlation-ID` into request state and logging context.
   ├─ `rate_limit.py`: Checks client rate limit budget via IP/User Key.
   ├─ `schemas.chat.ChatRequest`: Pydantic validates payload structure, content block types, and length bounds.
   └─ `api/v1/endpoints/chat.py`: Injects `ChatService` via FastAPI `Depends()`.
Step 3: Service Layer Orchestration (`ChatService.process_message`)
   ├─ Normalizes input DTO into domain `CanonicalMessage` via `InputProcessorPipeline`.
   ├─ If `conversation_id` is None: Generates new UUIDv4 and initializes new conversation aggregate.
   ├─ Checks `ICacheService` for cached responses (if deterministic query patterns apply).
   └─ Initializes `GraphState` for LangGraph execution.
Step 4: LangGraph Execution
   ├─ Node 1: `validate_input` -> Checks token limits, strips prohibited control characters.
   ├─ Node 2: `load_context` -> Queries `IConversationRepository` for the last N messages of the session; applies sliding window/truncation.
   ├─ Node 3: `llm_generate` -> Calls `ILLMService.generate()` with assembled conversation prompt + system prompt.
   │    └─ `ILLMService`: Attaches LangSmith RunTree tracer, manages timeout/retries, calls model provider API.
   ├─ Node 4: `format_output` -> Encapsulates assistant response in domain `CanonicalMessage` with metadata (token usage, latency, finish reason).
   └─ Graph reaches `END` state and outputs modified `GraphState`.
Step 5: State Persistence & Cache Update
   ├─ `ChatService` persists user input `CanonicalMessage` and assistant `CanonicalMessage` in DB via `IMessageRepository`.
   ├─ Updates `IConversationRepository` (last updated timestamp, message count).
   └─ Optionally writes ephemeral state / session context to `ICacheService`.
Step 6: Response Delivery
   ├─ `ChatService` maps domain `CanonicalMessage` to `ChatResponse` DTO.
   ├─ `api/v1/endpoints/chat.py` serializes response with HTTP 200 OK and response headers (`X-Correlation-ID`, `X-Response-Time`).
   └─ Client receives structured JSON response.
```

---

## 5. LANGGRAPH ARCHITECTURAL DESIGN (DELIVERABLE 5)

### 5.1 Graph State Definition (`GraphState`)
```python
from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict
import operator
from app.domain.models.message import CanonicalMessage

class GraphState(TypedDict):
    conversation_id: str
    user_id: Optional[str]
    input_message: CanonicalMessage
    conversation_history: List[CanonicalMessage]  # Loaded past turns
    system_prompt: str
    llm_response: Optional[CanonicalMessage]
    error: Optional[str]
    metadata: Dict[str, Any]
    retry_count: int
```

### 5.2 StateGraph Flow Diagram (ASCII)

```text
                      +-------------------+
                      |      START        |
                      +---------┬---------+
                                │
                                ▼
               +─────────────────────────────────+
               |      validate_and_sanitize      |
               | - Check payload bounds          |
               | - Strip dangerous control chars |
               +────────────────┬────────────────+
                                │
                                ▼
               +─────────────────────────────────+
               |          load_context           |
               | - Load history window (N turns) |
               | - Assemble system prompt        |
               +────────────────┬────────────────+
                                │
                                ▼
               +─────────────────────────────────+
               |          llm_generate           |◄───────────────┐ (Retry on
               | - Invoke ILLMService abstraction|                │  transient error)
               | - LangSmith trace attached      |                │
               +────────────────┬────────────────+                │
                                │                                 │
                     [ Conditional Edge ]                         │
                    /                    \                        │
             (Success)                  (Failure / Timeout)       │
                │                                  \              │
                ▼                                   ▼             │
+─────────────────────────────────+    +──────────────────────────┴──────+
|          format_output          |    |          error_recovery         |
| - Construct CanonicalMessage    |    | - If retry_count < MAX: Retry   |
| - Attach token metrics & latency|    | - If retry_count >= MAX: Fallback|
+───────────────┬─────────────────+    +────────────────┬────────────────+
                │                                       │
                │                                       ▼
                │                      +─────────────────────────────────+
                │                      |       generate_fallback_msg     |
                │                      | - Return graceful failure msg   |
                │                      +────────────────┬────────────────+
                │                                       │
                └───────────────────┬───────────────────┘
                                    │
                                    ▼
                          +-------------------+
                          |       END         |
                          +-------------------+
```

---

## 6. MULTIMODAL MESSAGE ARCHITECTURE & EVOLUTION (DELIVERABLE 6)

### 6.1 Polymorphic Content Block Model
```python
from enum import Enum
from typing import Annotated, List, Literal, Optional, Union
from pydantic import BaseModel, Field

class ContentType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    FILE_REF = "file_ref"

class BaseContentBlock(BaseModel):
    type: ContentType

class TextContentBlock(BaseContentBlock):
    type: Literal[ContentType.TEXT] = ContentType.TEXT
    text: str = Field(..., min_length=1, max_length=32000)

class ImageContentBlock(BaseContentBlock):
    type: Literal[ContentType.IMAGE] = ContentType.IMAGE
    media_type: str = Field(..., pattern=r"^image\/(jpeg|png|webp|gif)$")
    url: Optional[str] = None
    data_base64: Optional[str] = None

class AudioContentBlock(BaseContentBlock):
    type: Literal[ContentType.AUDIO] = ContentType.AUDIO
    media_type: str = Field(..., pattern=r"^audio\/(mpeg|wav|ogg|mp4|webm)$")
    url: Optional[str] = None
    data_base64: Optional[str] = None
    duration_seconds: Optional[float] = None

ContentBlock = Annotated[
    Union[TextContentBlock, ImageContentBlock, AudioContentBlock],
    Field(discriminator="type")
]
```

---

## 7. CACHING ARCHITECTURE & REDIS STRATEGY (DELIVERABLE 7)

| Cache Category | Cache Key Pattern | TTL | Invalidation Strategy | Safe for Production? | Correctness Risks & Mitigation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Exact LLM Query Cache** | `cache:llm:{model}:{sha256(system_prompt + full_history_json)}` | 1 hour | LRU eviction | **YES** (with strict conditions) | **Risk**: Dynamic conversation state returning stale answers.<br>**Mitigation**: Key MUST hash entire conversation history + system prompt, not just the latest user query. Only active for `temperature == 0.0`. |
| **Session / History Cache** | `cache:session:{conversation_id}:recent` | 15 mins | Write-through on new message; Explicit delete on conversation clear | **YES (Recommended)** | **Risk**: Desynchronization with DB.<br>**Mitigation**: DB is source of truth; cache acts as read-through buffer. Any append invalidates or appends to cache atomically. |
| **Rate Limiter Bucket** | `ratelimit:{client_ip_or_user_id}:{minute_timestamp}` | 60 secs | Key expiration (TTL) | **YES (Standard)** | **Risk**: Clock drift across nodes.<br>**Mitigation**: Use Redis server time via Lua script token bucket. |
| **Dynamic Conversational LLM Responses** | `cache:chat:{user_query_only}` | N/A | **DO NOT CACHE** | **NO (Forbidden)** | **Fatal Flaw**: Query "Why?" depends entirely on prior turn. Caching single-turn query returns hallucinated/irrelevant context. |

---

## 8. OBSERVABILITY, LOGGING & TRACING STRATEGY (DELIVERABLE 8)

- **Application Logs**: Structured JSON with `correlation_id`, `conversation_id`, execution duration, and token accounting.
- **Metrics**: Standard Prometheus counters for HTTP requests, errors, and histogram for latency.
- **LLM Tracing (LangSmith)**: Enabled via environment variables with zero code intrusive overhead, automatically capturing prompt graphs, latency per node, and token breakdown.

---

## 9. TESTING STRATEGY (DELIVERABLE 9)

- `tests/unit`: Tests pure functions, input processors, schemas, and cache logic with `MockLLMService`.
- `tests/integration`: Tests SQLAlchemy repository interactions in SQLite in-memory and LangGraph flow transitions.
- `tests/api`: Uses `httpx.AsyncClient` against FastAPI router for contract validation.
- `tests/evaluation`: Golden evaluation dataset measuring model accuracy, safety, and formatting adherence.

---

## 10. GIT STRATEGY (DELIVERABLE 10)

- **Branching Model**: Scaled Trunk-Based Development (`main` protected + short-lived `feature/*` and `fix/*`).
- **Commits**: Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
- **Hygiene**: `.gitignore` strictly protects `.env`, database binaries, and temporary build artifacts.

---

## 11. SECURITY ARCHITECTURE (DELIVERABLE 11)

- Inbound rate limiting via token bucket algorithm.
- Prompt injection protection via strict layer separation and input length sanitization.
- Future multimodal safety: magic byte checking, max file size guards (10MB image / 25MB audio), and isolated object storage.

---

## 12. IMPLEMENTATION ROADMAP (DELIVERABLE 12)

- **Phase 1**: Repository & Project Skeleton (Tooling, `pyproject.toml`, Settings, Logging).
- **Phase 2**: FastAPI Foundation (App factory, health endpoints, middleware, error handling).
- **Phase 3**: Basic LangGraph Chatbot (LLM Gateway, StateGraph, basic single-turn chat).
- **Phase 4**: Persistence & Conversation State (SQLAlchemy 2.0 Async, Alembic, Repositories).
- **Phase 5**: Caching Layer (In-Memory & Redis adapters, session caching).
- **Phase 6**: LangSmith Observability (RunTree tracing, metrics).
- **Phase 7**: Automated Testing & Evaluation Suite.
- **Phase 8**: Production Security Hardening (Auth, rate limiting, security headers).
- **Phase 9**: Multimodal Input Architecture (Image & Audio processor activation).
- **Phase 10**: Deployment & Containerization (`Dockerfile`, `docker-compose.yml`, runbooks).

---

## 13. ARCHITECTURAL DECISION RECORDS (ADRs) (DELIVERABLE 13)

- **ADR-001 (FastAPI)**: Selected for native async performance, Pydantic v2 support, and OpenAPI auto-generation.
- **ADR-002 (LangGraph)**: Selected for explicit state machine transitions, cyclic/acyclic graph control, and native LangSmith hooks.
- **ADR-003 (LLM Gateway `ILLMService`)**: Selected to decouple business logic from vendor SDKs and enable seamless offline testing and multi-provider fallback.
- **ADR-004 (Polymorphic Message Schema)**: Selected discriminated `ContentBlock` union to support images and audio seamlessly without breaking changes.
- **ADR-005 (SQLAlchemy 2.0 Async + Alembic)**: Selected for enterprise relational persistence with SQLite (dev) and PostgreSQL (prod) parity.
- **ADR-006 (ICacheService Port)**: Selected to enable testing with in-memory caching and production with Redis.
- **ADR-007 (LangSmith + JSON Logs)**: Selected for deep LLM-specific trace diagnostics paired with standard structured application logs.
- **ADR-008 (Scaled Trunk-Based Development)**: Selected for rapid iteration, clean pull requests, and minimal merge conflicts.
- **ADR-009 (Pydantic-Settings)**: Selected for validated environment variable parsing.

---

## 14. SELF-REVIEW & RESILIENCE SUMMARY

- **Maintainability**: Clear Hexagonal separation ensures any developer can navigate `api` vs `services` vs `domain` vs `graph` vs `llm`.
- **Extensibility**: Adding image/audio processors in Phase 9 requires zero rewrite of routing, database schemas, or graph core.
- **Failure Resilience**: Primary LLM failures trigger exponential backoff and fallback provider; Redis failures fall back to database; LangSmith network cuts do not block user chats.

---

## 15. READY FOR PHASE 1

1. **Final Architecture Decision**: Modular Monolith with Hexagonal Layering and Polymorphic Multimodal Schema.
2. **Final Directory Structure**: Standardized structure documented in Deliverable 2.
3. **Technology Choices**: Python 3.11+, FastAPI, LangGraph, SQLAlchemy 2.0 Async, Redis/In-Memory Cache, LangSmith, Pytest, Ruff, Mypy.
4. **Phase 1 Objective**: Initialize repository skeleton, `pyproject.toml`, directory tree, configuration (`BaseSettings`), structured logging, and initial test suite.
5. **Phase 1 Acceptance Criteria**:
   - [ ] Clean directory tree established.
   - [ ] `pyproject.toml` created with pinned dependencies.
   - [ ] `.env.example` created with documentation.
   - [ ] Core configuration (`app/core/config.py`) validated.
   - [ ] Structured logging initialized.
   - [ ] Ruff & Mypy passing with 0 warnings.
   - [ ] Smoke test passing with `pytest`.
6. **Unresolved Decisions**: None. All architectural decisions (ADR-001 to ADR-009) are resolved and specified.
