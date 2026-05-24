import pytest
from httpx import AsyncClient, ASGITransport
from main import app
import os

@pytest.mark.asyncio
async def test_webhook_security_forbidden():
    os.environ["WEBHOOK_SECRET"] = "secret123"
    
    # Reload or mock WEBHOOK_SECRET in main since it was imported early
    import main
    main.WEBHOOK_SECRET = "secret123"
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook", json={"type": "SCALP", "tier": "SCALP_GORENGAN", "ticker": "TEST", "signal": "HAKA"})
        assert response.status_code == 403

@pytest.mark.asyncio
async def test_webhook_security_allowed():
    os.environ["WEBHOOK_SECRET"] = "secret123"
    
    import main
    main.WEBHOOK_SECRET = "secret123"
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook?secret=secret123", json={"type": "SCALP", "tier": "SCALP_GORENGAN", "ticker": "TEST", "signal": "HAKA"})
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_webhook_security_header_allowed():
    os.environ["WEBHOOK_SECRET"] = "secret123"
    
    import main
    main.WEBHOOK_SECRET = "secret123"
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook", headers={"x-webhook-secret": "secret123"}, json={"type": "SCALP", "tier": "SCALP_GORENGAN", "ticker": "TEST", "signal": "HAKA"})
        assert response.status_code == 200
