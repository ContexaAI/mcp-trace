from fastmcp import FastMCP
from mcp_trace.middleware import TraceMiddleware
from mcp_trace.adapters.contexaai_adapter import ContexaTraceAdapter
import os

# Set these in your environment or pass as arguments below
# os.environ["CONTEXA_API_KEY"] = "your-api-key"
# os.environ["CONTEXA_SERVER_ID"] = "your-server-id"

mcp = FastMCP("MCP Server with Contexa Trace")

# You can pass api_key/server_id as arguments, or rely on env vars
contexa_adapter = ContexaTraceAdapter(
    api_key="ac28024f69a584a9e3bf249492d8494264a630fc0d2d91297cf96d6c0768cf1a",
    server_id="4n0lNwENz_PRUHUfPIXCM"
)
trace_middleware = TraceMiddleware(adapter=contexa_adapter)

mcp.add_middleware(trace_middleware)

@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"

@mcp.tool
def add(a: int, b: int) -> int:
    return a + b

if __name__ == "__main__":
    try:
        mcp.run(transport="sse")
    finally:
        # Ensure all trace events are sent before exit
        contexa_adapter.flush(timeout=5)
        contexa_adapter.shutdown() 