from fastmcp import FastMCP
from mcp_trace.middleware import TraceMiddleware
from mcp_trace.adapters.console_adapter import ConsoleTraceAdapter

mcp = FastMCP("My MCP Server")

trace_adapter = ConsoleTraceAdapter()
trace_middleware = TraceMiddleware(adapter=trace_adapter)

mcp.add_middleware(trace_middleware)

@mcp.tool()
def hello(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run(transport="sse")