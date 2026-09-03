import asyncio
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from fastmcp import Client

logger = logging.getLogger(__name__)

# Agent code calls MCPToolCall.call_tool synchronously, but it may be invoked from
# inside an already-running asyncio event loop (e.g. FastAPI's async route handler).
# asyncio.run() would raise "cannot be called from a running event loop" in that case,
# so each call is executed in a dedicated worker thread that has no loop of its own.
_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="mcp-client")


class MCPToolCall:
    """Helper to call tools on a real MCP server (streamable-HTTP transport, via fastmcp.Client)."""

    @staticmethod
    def call_tool(base_url: str, tool_name: str, arguments: dict) -> dict:
        """Call an MCP tool over streamable-HTTP and return its structured result as a dict."""

        async def _call() -> dict:
            async with Client(f"{base_url}/mcp") as client:
                result = await client.call_tool(tool_name, arguments)
                if result.data is not None:
                    return result.data
                if result.structured_content is not None:
                    return result.structured_content
                if result.content:
                    text = getattr(result.content[0], "text", None)
                    if text is not None:
                        return json.loads(text)
                return {}

        def _run_in_new_loop() -> dict:
            return asyncio.run(_call())

        try:
            result = _executor.submit(_run_in_new_loop).result()
            logger.info(f"MCP call {tool_name} on {base_url} returned: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to call MCP tool {tool_name} on {base_url}: {e}")
            return {"error": str(e), "tool": tool_name}

    @staticmethod
    def wait_for_service(base_url: str, timeout: int = 10) -> bool:
        """Wait for MCP service to be ready."""
        import requests

        start = time.time()
        while time.time() - start < timeout:
            try:
                response = requests.get(f"{base_url}/health", timeout=1)
                if response.status_code == 200:
                    logger.info(f"Service {base_url} is ready")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(0.5)

        logger.warning(f"Service {base_url} did not become ready in {timeout}s")
        return False
