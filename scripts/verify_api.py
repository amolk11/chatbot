"""Manual verification script for Phase 4 Persistence & Conversation History."""

import asyncio
import json

from httpx import ASGITransport, AsyncClient

from app.db.base import Base
from app.db.session import get_engine
from app.main import app


async def main() -> None:
    # Ensure database tables exist for verification run
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
        print("=== 1. Health Probe ===")
        r1 = await client.get("/health")
        print(f"Status: {r1.status_code}, Correlation-ID: {r1.headers.get('x-correlation-id')}")
        print(f"Body: {json.dumps(r1.json())}")

        print("\n=== 2. Readiness Probe (with Database Check) ===")
        r2 = await client.get("/health/ready")
        print(f"Status: {r2.status_code}, Correlation-ID: {r2.headers.get('x-correlation-id')}")
        print(f"Body: {json.dumps(r2.json())}")

        print("\n=== 3. Chat API - Turn 1 (New Conversation) ===")
        r3 = await client.post(
            "/api/v1/chat",
            json={"message": "echo: My favorite color is blue."},
            headers={"X-Correlation-ID": "manual-trace-001"},
        )
        print(f"Status: {r3.status_code}, Correlation-ID: {r3.headers.get('x-correlation-id')}")
        data_3 = r3.json()
        print(f"Response Body: {json.dumps(data_3, indent=2)}")
        conv_id = data_3.get("conversation_id")
        print(f"Generated conversation_id: {conv_id}")

        print("\n=== 4. Chat API - Turn 2 (Continuation with conversation_id) ===")
        r4 = await client.post(
            "/api/v1/chat",
            json={
                "message": "echo: What is my favorite color?",
                "conversation_id": conv_id,
            },
            headers={"X-Correlation-ID": "manual-trace-002"},
        )
        print(f"Status: {r4.status_code}, Correlation-ID: {r4.headers.get('x-correlation-id')}")
        print(f"Response Body: {json.dumps(r4.json(), indent=2)}")

        print("\n=== 5. Chat API - Nonexistent conversation_id (Expect 404) ===")
        r5 = await client.post(
            "/api/v1/chat",
            json={
                "message": "Hello",
                "conversation_id": "nonexistent-conversation-uuid-9999",
            },
            headers={"X-Correlation-ID": "manual-trace-003"},
        )
        print(f"Status: {r5.status_code}, Correlation-ID: {r5.headers.get('x-correlation-id')}")
        print(f"Response Body: {json.dumps(r5.json(), indent=2)}")

        print("\n=== 6. Chat API - Validation Error (Empty Message) ===")
        r6 = await client.post("/api/v1/chat", json={"message": ""})
        print(f"Status: {r6.status_code}, Correlation-ID: {r6.headers.get('x-correlation-id')}")
        print(f"Response Body: {json.dumps(r6.json(), indent=2)}")

        print("\n=== 7. OpenAPI Registration ===")
        r7 = await client.get("/openapi.json")
        paths = list(r7.json().get("paths", {}).keys())
        print(f"Status: {r7.status_code}, Registered Routes: {paths}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

