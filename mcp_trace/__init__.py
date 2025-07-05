# mcp_trace package 

from fastmcp import FastMCP
from mcp_trace.middleware import TraceMiddleware
from mcp_trace.adapters.local import LocalTraceAdapter
from fastmcp.server.middleware import MiddlewareContext  # Re-export for convenience

mcp = FastMCP("My MCP Server")

# 1. Create the trace adapter (writes to trace.log)
trace_adapter = LocalTraceAdapter("trace.log")

# 2. Create the middleware with the adapter
trace_middleware = TraceMiddleware(adapter=trace_adapter)

# 3. Add the middleware to FastMCP
mcp.add_middleware(trace_middleware)

@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run(transport="http") 