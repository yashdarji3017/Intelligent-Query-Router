import asyncio
import os
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_six_concurrent_requests(async_client: AsyncClient):
    test_queries = [
        {"user_id": "user_1", "session_id": "sess_1", "query": "Hello, how are you today?"},
        {"user_id": "user_2", "session_id": "sess_2", "query": "Our production API is down!"},
        {"user_id": "user_3", "session_id": "sess_3", "query": "Where can I view my billing invoice?"},
        {"user_id": "user_4", "session_id": "sess_4", "query": "How do I reset my account password?"},
        {"user_id": "user_5", "session_id": "sess_5", "query": "Please architect a multi-step workflow."},
        {"user_id": "user_6", "session_id": "sess_6", "query": "It is not working."},
    ]

    expected_categories = [
        "general",
        "technical",
        "billing",
        "account",
        "complex",
        "unknown",
    ]

    expected_handlers = [
        "general_handler",
        "technical_handler",
        "billing_handler",
        "account_handler",
        "complex_handler",
        "fallback_handler",
    ]

    tasks = [
        async_client.post("/chat", json=payload)
        for payload in test_queries
    ]

    responses = await asyncio.gather(*tasks)

    assert len(responses) == 6

    received_request_ids = set()

    for idx, resp in enumerate(responses):
        assert resp.status_code == 200, f"Request {idx} failed with {resp.text}"
        data = resp.json()

        req_id = data["request_id"]
        assert req_id not in received_request_ids, f"Duplicate request_id detected: {req_id}"
        received_request_ids.add(req_id)

        assert data["category"] == expected_categories[idx], (
            f"Query {idx} expected category {expected_categories[idx]}, got {data['category']}"
        )
        assert data["target_agent"] == expected_handlers[idx], (
            f"Query {idx} expected handler {expected_handlers[idx]}, got {data['target_agent']}"
        )


def test_absence_of_persistent_storage():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    disallowed_extensions = {".db", ".sqlite", ".sqlite3", ".rdb"}

    for root, dirs, files in os.walk(project_root):
        if ".git" in root or ".venv" in root :
            continue
        for file in files:
            _, ext = os.path.splitext(file)
            assert ext not in disallowed_extensions, f"Disallowed persistent storage file found: {file}"
