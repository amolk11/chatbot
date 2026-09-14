"""Manual verification script for Phase 3 LangGraph Chatbot & LLM Gateway."""

import asyncio
import json

from httpx import ASGITransport, AsyncClient

from app.main import app


async def main() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
        print("=== 1. Health Probe ===")
        r1 = await client.get("/health")
        print(f"Status: {r1.status_code}, Correlation-ID: {r1.headers.get('x-correlation-id')}")
        print(f"Body: {json.dumps(r1.json())}")

        print("\n=== 2. Readiness Probe ===")
        r2 = await client.get("/health/ready")
        print(f"Status: {r2.status_code}, Correlation-ID: {r2.headers.get('x-correlation-id')}")
        print(f"Body: {json.dumps(r2.json())}")

        print("\n=== 3. Chat API - Standard Turn ===")
        chat_payload = {
            "message": "echo: Hello AI Chatbot!",
            "conversation_id": "manual-session-123",
        }
        r3 = await client.post(
            "/api/v1/chat",
            json=chat_payload,
            headers={"X-Correlation-ID": "manual-trace-001"},
        )
        print(f"Status: {r3.status_code}, Correlation-ID: {r3.headers.get('x-correlation-id')}")
        print(f"Response Body: {json.dumps(r3.json(), indent=2)}")

        print("\n=== 4. Chat API - Validation Error (Empty Message) ===")
        r4 = await client.post("/api/v1/chat", json={"message": ""})
        print(f"Status: {r4.status_code}, Correlation-ID: {r4.headers.get('x-correlation-id')}")
        print(f"Response Body: {json.dumps(r4.json(), indent=2)}")

        print("\n=== 5. OpenAPI Registration ===")
        r5 = await client.get("/openapi.json")
        paths = list(r5.json().get("paths", {}).keys())
        print(f"Status: {r5.status_code}, Registered Routes: {paths}")


if __name__ == "__main__":
    asyncio.run(main())
