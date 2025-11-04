from mcp.server import FastMCP
from mcp_trace import TraceMiddleware, ConsoleAdapter

def identify_user(context) -> dict:
    """Identify user from context (e.g., from headers, session, etc.)."""
    # Example: Extract user info from request headers
    try:
        request_context = getattr(context, "request_context", None)
        if request_context:
            request = getattr(request_context, "request", None)
            if request:
                headers = getattr(request, "headers", {}) or {}
                headers_lower = {k.lower(): v for k, v in headers.items()}
                
                # Example: Get user info from custom headers
                user_id = headers_lower.get("x-user-id")
                user_name = headers_lower.get("x-user-name")
                user_email = headers_lower.get("x-user-email")
                
                if user_id:
                    return {
                        "user_id": user_id,
                        "user_name": user_name,
                        "user_email": user_email,
                    }
    except Exception:
        pass
    
    # Return None if user cannot be identified
    return None

def redact_pii(trace_data: dict) -> dict:
    """Redact PII from trace data before exporting."""
    # Example: redact user email
    if "user_email" in trace_data and trace_data["user_email"]:
        trace_data["user_email"] = "***REDACTED***"
    
    # Example: redact sensitive data from request/response
    if "request" in trace_data and isinstance(trace_data["request"], dict):
        if "password" in trace_data["request"]:
            trace_data["request"]["password"] = "***REDACTED***"
        if "api_key" in trace_data["request"]:
            trace_data["request"]["api_key"] = "***REDACTED***"
    
    if "response" in trace_data and isinstance(trace_data["response"], dict):
        if "token" in trace_data["response"]:
            trace_data["response"]["token"] = "***REDACTED***"
    
    return trace_data

mcp = FastMCP("My MCP Server")

# Initialize with identify and redact functions
trace_middleware = TraceMiddleware(
    adapter=ConsoleAdapter(),
    identifyUser=identify_user,
    redact=redact_pii
).init(mcp)

@mcp.tool()
def hello(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run(transport="streamable-http")