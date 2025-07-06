from fastmcp import FastMCP
from mcp_trace.middleware import TraceMiddleware
from mcp_trace.adapters.local import LocalTraceAdapter

mcp = FastMCP("My MCP Server", stateless_http=True)

trace_adapter = LocalTraceAdapter("trace.log")
trace_middleware = TraceMiddleware(adapter=trace_adapter)

mcp.add_middleware(trace_middleware)

@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"

@mcp.tool
def add(a: int, b: int) -> int:
    return a + b

@mcp.tool(name="get_user_list", description="Get a list of users")
def get_user_list() -> list[str]:
    return ["John", "Jane", "Jim"]

@mcp.tool(name="get_user_by_id", description="Get a user by their ID")
def get_user_by_id(id: int) -> str:
    return f"User {id}"


if __name__ == "__main__":
    mcp.run(transport="http")