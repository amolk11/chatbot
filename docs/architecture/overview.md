# Architecture Overview

## 1. Architectural Style
The application is structured as a **Modular Monolith** using **Hexagonal Architecture (Ports and Adapters)** principles with clear layered separation:

```text
Client (Web/Mobile/API)
       │
       ▼
  API Layer (FastAPI)
       │
       ▼
 Service Layer (Orchestration)
       │
       ▼
  Workflow Layer (LangGraph)
       │
       ▼
  LLM Gateway Layer (ILLMService)
       │
       ▼
 External Providers & Infrastructure (OpenAI / Anthropic / Gemini / DB / Redis / LangSmith)
```

## 2. Layer Responsibilities & Dependency Boundaries

| Layer | Responsibility | Permitted Imports | Forbidden Imports |
| :--- | :--- | :--- | :--- |
| **API (`app/api`)** | HTTP/SSE transport, DTO serialization, route handling, authentication & rate limiting middleware. | `app.schemas`, `app.services`, `app.core`, `FastAPI` | `app.db.models`, `app.graph`, raw DB drivers, direct LLM SDKs |
| **Services (`app/services`)** | Application orchestration, transaction boundaries, combining domain processors, graphs, repositories, and caches. | `app.domain`, `app.schemas`, `app.graph`, `app.db (interfaces)`, `app.cache (interfaces)`, `app.core` | `FastAPI` (Request/Response objects), raw DB ORM sessions |
| **Domain (`app/domain`)** | Pure business entities (`CanonicalMessage`, `ContentBlock`), domain validation rules, input normalization. | Pure Python, `pydantic`, `app.core.exceptions` | `FastAPI`, `LangGraph`, `SQLAlchemy`, `Redis`, `app.api`, `app.services` |
| **Graph (`app/graph`)** | AI workflow state definition, LangGraph node implementations, routing edges, context assembly. | `app.domain`, `app.llm (interfaces)`, `app.core` | `FastAPI`, `app.api`, `app.services`, ORM database queries directly |
| **LLM Gateway (`app/llm`)** | Translates canonical domain messages into provider-specific prompts, manages retries, fallback switching, and streaming. | `app.domain`, `app.core`, `app.observability`, Provider SDKs | `FastAPI`, `app.api`, `app.services`, `app.db`, `app.cache` |
| **Persistence (`app/db`)** | Relational data persistence, SQLAlchemy 2.0 async sessions, Alembic migrations, repository implementations. | `app.domain`, `app.core`, `SQLAlchemy`, `Alembic` | `FastAPI`, `app.api`, `app.graph`, `app.llm`, `app.services` |
| **Cache (`app/cache`)** | Caching ports, Redis adapter, in-memory adapter, TTL and key management. | `app.core`, `redis-py` (adapter only) | `FastAPI`, `app.api`, `app.graph`, `app.services` |
| **Core (`app/core`)** | Configuration (`BaseSettings`), constants, structured logging, exception hierarchy. | Pure Python, `pydantic-settings` | All other `app/*` modules |

## 3. Multimodal Strategy
The domain model uses polymorphic content blocks (`TextContentBlock`, `ImageContentBlock`, `AudioContentBlock`, `FileRefContentBlock`) from Day 1.
While Phase 1-3 activate text only, the schema design prevents any database or API rewrites when activating vision and audio in Phase 9.

## 4. Phase Roadmap Summary
- **Phase 0**: Architecture & Technical Specification *(Completed)*
- **Phase 1**: Project Foundation + Git + Engineering Tooling *(Current)*
- **Phase 2**: FastAPI Foundation & Health Endpoints
- **Phase 3**: Basic LangGraph Chatbot Workflow
- **Phase 4**: Persistence & Conversation History
- **Phase 5**: Caching Layer (In-Memory & Redis)
- **Phase 6**: LangSmith Observability & Tracing
- **Phase 7**: Automated Testing & Evaluation Suite
- **Phase 8**: Production Security & Hardening
- **Phase 9**: Multimodal Input Architecture
- **Phase 10**: Container Deployment & Production Readiness
