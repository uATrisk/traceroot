import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from mcp_server import list_recent_traces

from rest.routers.public.deps import AuthResult


@pytest.fixture
def mock_auth(monkeypatch):
    monkeypatch.setenv("TRACEROOT_API_KEY", "test-key")
    auth_mock = AsyncMock(
        return_value=AuthResult(
            project_id="test-project",
            workspace_id="test-workspace",
            billing_plan="pro",
            ingestion_blocked=False,
        )
    )
    monkeypatch.setattr("mcp_server.authenticate_api_key", auth_mock)
    return auth_mock


@pytest.fixture
def mock_service(monkeypatch):
    service_mock = MagicMock()
    service_mock.list_traces.return_value = {"traces": [{"id": "t1"}]}

    get_service_mock = MagicMock(return_value=service_mock)
    monkeypatch.setattr("mcp_server.get_trace_reader_service", get_service_mock)
    return service_mock


@pytest.mark.asyncio
async def test_list_recent_traces_success(mock_auth, mock_service):
    """(1) Successful call with valid auth returns JSON serialized output, (3) start_after is forwarded."""
    result = await list_recent_traces(start_after="2024-01-01T00:00:00", limit=10, name="test-name")

    # Check JSON output
    data = json.loads(result)
    assert data == {"traces": [{"id": "t1"}]}

    # Check service was called with correct parameters including start_after
    mock_service.list_traces.assert_called_once()
    kwargs = mock_service.list_traces.call_args.kwargs
    assert kwargs["project_id"] == "test-project"
    assert kwargs["start_after"].isoformat() == "2024-01-01T00:00:00"
    assert kwargs["limit"] == 10
    assert kwargs["name"] == "test-name"
    assert kwargs["user_id"] is None


@pytest.mark.asyncio
async def test_list_recent_traces_auth_failure(monkeypatch, mock_service):
    """(2) Invalid auth raises expected error instead of proceeding."""
    monkeypatch.setenv("TRACEROOT_API_KEY", "invalid-key")
    auth_mock = AsyncMock(
        side_effect=HTTPException(status_code=401, detail="Authentication failed")
    )
    monkeypatch.setattr("mcp_server.authenticate_api_key", auth_mock)

    with pytest.raises(RuntimeError, match="Authentication failed: 401 Authentication failed"):
        await list_recent_traces(start_after="2024-01-01T00:00:00")

    # Ensure service was never called
    mock_service.list_traces.assert_not_called()


@pytest.mark.asyncio
async def test_list_recent_traces_invalid_start_after(mock_auth, mock_service):
    """Invalid start_after raises expected error and service is not called."""
    with pytest.raises(RuntimeError, match="Invalid start_after format:"):
        await list_recent_traces(start_after="not-a-date")

    mock_service.list_traces.assert_not_called()
