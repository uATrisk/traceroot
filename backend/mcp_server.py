import asyncio
import json
import os
from datetime import datetime

from fastapi import HTTPException
from mcp.server.mcpserver import MCPServer

from rest.routers.public.deps import authenticate_api_key
from rest.services.trace_reader import get_trace_reader_service

mcp = MCPServer("traceroot-mcp")


async def _get_auth():
    """Authenticate via the provided API key."""
    api_key = os.environ.get("TRACEROOT_API_KEY")
    if not api_key:
        raise RuntimeError("TRACEROOT_API_KEY environment variable is required")
    try:
        return await authenticate_api_key(authorization=f"Bearer {api_key}")
    except HTTPException as e:
        raise RuntimeError(f"Authentication failed: {e.status_code} {e.detail}") from e


@mcp.tool()
async def list_recent_traces(
    limit: int = 50,
    name: str | None = None,
    user_id: str | None = None,
    search_query: str | None = None,
    start_after: str | None = None,
) -> str:
    """List recent traces for the current project.

    Args:
        limit: Items per page (default 50).
        name: Filter by trace name.
        user_id: Filter by user id.
        search_query: Search across trace attributes.
        start_after: Cursor for pagination.
    """
    auth = await _get_auth()

    parsed_start_after = datetime.fromisoformat(start_after) if start_after else None

    service = get_trace_reader_service()
    result = service.list_traces(
        project_id=auth.project_id,
        limit=limit,
        name=name,
        user_id=user_id,
        search_query=search_query,
        include_evaluations=False,
        filters=None,
        start_after=parsed_start_after,
        end_before=None,
    )

    return json.dumps(result, default=str, indent=2)


async def main():
    # Verify auth on startup to fail fast
    await _get_auth()

    # Run the stdio server
    await mcp.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())
