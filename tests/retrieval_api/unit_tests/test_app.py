import pytest
from httpx import AsyncClient
from app import app  # Ensure this path is correct relative to your test file


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}


@pytest.mark.asyncio
async def test_chat_endpoint(monkeypatch):
    """Test chat endpoint with mock response."""

    async def mock_process_rag_chat(request):
        for chunk in ["Hello ", "World"]:
            yield chunk

    from app import chat_service
    monkeypatch.setattr(chat_service, "process_rag_chat", mock_process_rag_chat)

    payload = {
        "chat_id": "test-chat",
        "query": "Hello",
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/v1/chat", json=payload)
    
    assert response.status_code == 200
    text = (await response.aread()).decode()
    assert "Hello" in text
    assert "World" in text


@pytest.mark.asyncio
async def test_report_endpoint(monkeypatch):
    """Test report endpoint with mock response."""

    async def mock_process_rag_report_request(request):
        for chunk in ["Report ", "Generated"]:
            yield chunk

    from app import chat_service
    monkeypatch.setattr(chat_service, "process_rag_report_request", mock_process_rag_report_request)

    payload = {
        "chat_id": "test-report",
        "query": "Generate Report",
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/v1/report", json=payload)
    
    assert response.status_code == 200
    text = (await response.aread()).decode()
    assert "Report" in text
    assert "Generated" in text
