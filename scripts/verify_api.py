"""Manual verification script for Phase 2 FastAPI Foundation."""

import asyncio
import json

from httpx import ASGITransport, AsyncClient

from app.main import app


async def main() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
        # 1. Health Probe
        r1 = await client.get("/health")
        print(
            f"1. /health -> Status: {r1.status_code}, Correlation-ID: {r1.headers.get('x-correlation-id')}"
        )
        print(f"   Body: {json.dumps(r1.json())}")

        # 2. Readiness Probe
        r2 = await client.get("/health/ready")
        print(
            f"2. /health/ready -> Status: {r2.status_code}, Correlation-ID: {r2.headers.get('x-correlation-id')}"
        )
        print(f"   Body: {json.dumps(r2.json())}")

        # 3. Custom Correlation ID Propagation
        custom_id = "test-session-trace-789"
        r3 = await client.get("/health", headers={"X-Correlation-ID": custom_id})
        print(
            f"3. Custom X-Correlation-ID sent: {custom_id} -> Returned: {r3.headers.get('x-correlation-id')}"
        )

        # 4. Versioned Route
        r4 = await client.get("/api/v1/health")
        print(f"4. /api/v1/health -> Status: {r4.status_code}, Body: {json.dumps(r4.json())}")

        # 5. OpenAPI Registration
        r5 = await client.get("/openapi.json")
        paths = list(r5.json().get("paths", {}).keys())
        print(f"5. OpenAPI Schema -> Status: {r5.status_code}, Registered Routes: {paths}")

        # 6. Standardized 404 Error Contract
        r6 = await client.get("/unmapped-route")
        print(f"6. 404 Error -> Status: {r6.status_code}, Body: {json.dumps(r6.json())}")


if __name__ == "__main__":
    asyncio.run(main())
