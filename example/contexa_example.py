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
    api_key="1873c789fdc8cec9871b7345f5e8a2a8982bd4a54a0cd0817bf778049d010196",
    server_id="6F8tjNTkr6ZuV62VXgh0C"
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