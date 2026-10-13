import pytest
from httpx import AsyncClient
from app.core.exceptions import ProviderTimeoutError, RateLimitError
from tests.conftest import MockClassifierAgent


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    """Verifies /health endpoint returns safe system metadata without secrets."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "model" in data
    assert "key" not in data
    assert "secret" not in data


@pytest.mark.asyncio
async def test_classify_endpoint_success(async_client: AsyncClient):
    """Verifies /classify endpoint returns structured classification without executing handler."""
    response = await async_client.post(
        "/classify",
        json={"query": "Our production API is down and cannot log in."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["request_id"].startswith("req_")
    assert data["category"] == "technical"
    assert data["urgency"] == "critical"
    assert data["target_agent"] == "technical_handler"
    assert "classification_latency_ms" in data


@pytest.mark.asyncio
async def test_classify_endpoint_validation_error(async_client: AsyncClient):
    """Verifies /classify returns 422 on empty query."""
    response = await async_client.post("/classify", json={"query": ""})
    assert response.status_code == 422
    data = response.json()
    assert data["status"] == "error"
    assert data["error_type"] == "ValidationError"


@pytest.mark.asyncio
async def test_chat_endpoint_greeting(async_client: AsyncClient):
    """Verifies /chat handles greetings through general_handler."""
    response = await async_client.post(
        "/chat",
        json={
            "query": "Hello, how are you?",
            "user_id": "user_42",
            "session_id": "sess_100",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["request_id"].startswith("req_")
    assert data["category"] == "general"
    assert data["target_agent"] == "general_handler"
    assert len(data["answer"]) > 0


@pytest.mark.asyncio
async def test_chat_endpoint_technical_incident(async_client: AsyncClient):
    """Verifies /chat handles urgent technical issues through technical_handler."""
    response = await async_client.post(
        "/chat",
        json={"query": "Our production API is down, customers cannot log in!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "technical"
    assert data["urgency"] == "critical"
    assert data["target_agent"] == "technical_handler"
    assert "Incident Detected" in data["answer"]


@pytest.mark.asyncio
async def test_chat_endpoint_ambiguous_query(async_client: AsyncClient):
    """Verifies /chat routes ambiguous queries to fallback_handler asking for clarification."""
    response = await async_client.post(
        "/chat",
        json={"query": "It is not working."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "unknown"
    assert data["target_agent"] == "fallback_handler"
    assert data["requires_clarification"] is True
    assert "clarification" in data["answer"].lower()


@pytest.mark.asyncio
async def test_chat_endpoint_provider_timeout_handled(
    async_client: AsyncClient, mock_classifier: MockClassifierAgent
):
    """Verifies provider timeouts produce clean 504 responses."""
    mock_classifier.simulate_exception = ProviderTimeoutError("Provider timed out after 30s")
    response = await async_client.post("/chat", json={"query": "Will cause timeout"})
    assert response.status_code == 504
    data = response.json()
    assert data["status"] == "error"
    assert data["error_type"] == "ProviderTimeoutError"
    assert "request_id" in data


@pytest.mark.asyncio
async def test_chat_endpoint_rate_limit_handled(
    async_client: AsyncClient, mock_classifier: MockClassifierAgent
):
    """Verifies provider rate limits produce clean 429 responses."""
    mock_classifier.simulate_exception = RateLimitError("Provider rate limit reached")
    response = await async_client.post("/chat", json={"query": "Will cause rate limit"})
    assert response.status_code == 429
    data = response.json()
    assert data["status"] == "error"
    assert data["error_type"] == "RateLimitError"
    assert "request_id" in data
