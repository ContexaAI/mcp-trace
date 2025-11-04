# mcp-trace

<div align="center">
  <img src="images/MCP-TRACE.png" alt="mcp-trace" width="100%"/>
</div>

[![PyPI version](https://badge.fury.io/py/mcp-trace.svg)](https://pypi.org/project/mcp-trace/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)

> **Flexible, pluggable tracing middleware for [FastMCP](https://github.com/jlowin/fastmcp) servers.**
> Log every request, tool call, and response to local files, PostgreSQL, Supabase, Contexa, your own backend, or the console—with full control over what gets logged, including user identification and PII redaction.

---

## Table of Contents

- [Features](#features)
- [Quickstart](#quickstart)
- [Adapters](#adapters)
  - [Contexa Adapter](#contexa-adapter)
  - [File Adapter](#file-adapter)
  - [Console Adapter](#console-adapter)
  - [PostgreSQL Adapter](#postgresql-adapter)
  - [Supabase Adapter](#supabase-adapter)
  - [Multi-Adapter Example](#multi-adapter-example)
- [Advanced Features](#advanced-features)
  - [User Identification](#user-identification)
  - [PII Redaction](#pii-redaction)
  - [Trace Data Fields](#trace-data-fields)
- [Requirements](#requirements)
- [Contributing](#contributing)
- [License](#license)
- [Links & Acknowledgements](#links--acknowledgements)

---

## Features

- 📦 **Plug-and-play**: Add tracing to any FastMCP server in seconds
- 🗃️ **Pluggable adapters**: Log to file, PostgreSQL, Supabase, Contexa, console, or your own
- 🧩 **Composable**: Use multiple adapters at once
- 📝 **Schema-first**: All traces stored as JSON for easy querying
- 🔒 **Privacy-aware**: Built-in PII redaction support
- 👤 **User identification**: Extract and log user information from requests
- 🌐 **Comprehensive data**: Captures request/response, client info, IP addresses, errors, and more

---

## Quickstart

### Installation

```sh
pip install mcp-trace
```

### Minimal Example (File Adapter)

```python
from mcp.server import FastMCP
from mcp_trace import TraceMiddleware, FileAdapter

mcp = FastMCP("My MCP Server")

trace_adapter = FileAdapter("trace.log")
trace_middleware = TraceMiddleware(adapter=trace_adapter).init(mcp)

@mcp.tool()
def hello(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

### Console Adapter Example

```python
from mcp.server import FastMCP
from mcp_trace import TraceMiddleware, ConsoleAdapter

mcp = FastMCP("My MCP Server")

trace_adapter = ConsoleAdapter()
trace_middleware = TraceMiddleware(adapter=trace_adapter).init(mcp)

@mcp.tool()
def hello(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

### Advanced Example (User Identification & PII Redaction)

```python
from mcp.server import FastMCP
from mcp_trace import TraceMiddleware, ConsoleAdapter

def identify_user(context) -> dict:
    """Identify user from context (e.g., from headers, session, etc.)."""
    try:
        request_context = getattr(context, "request_context", None)
        if request_context:
            request = getattr(request_context, "request", None)
            if request:
                headers = getattr(request, "headers", {}) or {}
                headers_lower = {k.lower(): v for k, v in headers.items()}
                
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
    return None

def redact_pii(trace_data: dict) -> dict:
    """Redact PII from trace data before exporting."""
    # Redact user email
    if "user_email" in trace_data and trace_data["user_email"]:
        trace_data["user_email"] = "***REDACTED***"
    
    # Redact sensitive data from request/response
    if "request" in trace_data and isinstance(trace_data["request"], dict):
        if "password" in trace_data["request"]:
            trace_data["request"]["password"] = "***REDACTED***"
        if "api_key" in trace_data["request"]:
            trace_data["request"]["api_key"] = "***REDACTED***"
    
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
```

---

## Adapters

### Contexa Adapter

Send traces to [Contexa](https://contexaai.com/) for cloud-based trace storage and analytics.

**Requirements:**

- Contexa API key (`CONTEXA_API_KEY`)
- Contexa Server ID (`CONTEXA_SERVER_ID`)
- [requests](https://pypi.org/project/requests/)

**Usage:**

You can provide your API key and server ID as environment variables or directly as arguments.

```python
from mcp.server import FastMCP
from mcp_trace import TraceMiddleware, ContexaAdapter

mcp = FastMCP("My MCP Server")

# Option 1: Set environment variables
# import os
# os.environ["CONTEXA_API_KEY"] = "your-api-key"
# os.environ["CONTEXA_SERVER_ID"] = "your-server-id"
# contexa_adapter = ContexaAdapter()

# Option 2: Pass directly
contexa_adapter = ContexaAdapter(
    api_key="your-api-key",
    server_id="your-server-id"
)

trace_middleware = TraceMiddleware(adapter=contexa_adapter).init(mcp)

@mcp.tool()
def hello(name: str) -> str:
    return f"Hello, {name}!"

# On shutdown, ensure all events are sent:
# contexa_adapter.flush(timeout=5)
# contexa_adapter.shutdown()

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

### File Adapter

Logs each trace as a JSON line to a file.

```python
from mcp_trace import FileAdapter
trace_adapter = FileAdapter("trace.log")
```

### Console Adapter

Prints each trace to the console in a colorized, readable format.

```python
from mcp_trace import ConsoleAdapter
trace_adapter = ConsoleAdapter()
```

### PostgreSQL Adapter

Store traces in a PostgreSQL table for easy querying and analytics.

**Table schema:**

```sql
CREATE TABLE mcp_traces (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_id TEXT NOT NULL,
    trace_data JSONB NOT NULL
);
```

**Usage:**

```python
from mcp.server import FastMCP
from mcp_trace import TraceMiddleware, PostgresAdapter

mcp = FastMCP("My MCP Server")

psql_adapter = PostgresAdapter(dsn="postgresql://user:pass@host:port/dbname")
trace_middleware = TraceMiddleware(adapter=psql_adapter).init(mcp)

@mcp.tool()
def hello(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

### Supabase Adapter

Log traces to [Supabase](https://supabase.com/) (PostgreSQL as a service).

**Table schema:** (same as above)

**Install:**

```sh
pip install supabase
```

**Usage:**

```python
from mcp.server import FastMCP
from supabase import create_client
from mcp_trace import TraceMiddleware, SupabaseAdapter

mcp = FastMCP("My MCP Server")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_adapter = SupabaseAdapter(supabase)
trace_middleware = TraceMiddleware(adapter=supabase_adapter).init(mcp)

@mcp.tool()
def hello(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

### Multi-Adapter Example

Send traces to multiple backends at once:

```python
from mcp.server import FastMCP
from mcp_trace import TraceMiddleware, FileAdapter, PostgresAdapter, SupabaseAdapter, ConsoleAdapter
from supabase import create_client

class MultiAdapter:
    def __init__(self, *adapters):
        self.adapters = adapters
    def export(self, trace_data: dict):
        for adapter in self.adapters:
            adapter.export(trace_data)

mcp = FastMCP("My MCP Server")

file_adapter = FileAdapter("trace.log")
psql_adapter = PostgresAdapter(dsn="postgresql://user:pass@host:port/dbname")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_adapter = SupabaseAdapter(supabase)
console_adapter = ConsoleAdapter()

trace_middleware = TraceMiddleware(
    adapter=MultiAdapter(file_adapter, psql_adapter, supabase_adapter, console_adapter)
).init(mcp)

@mcp.tool()
def hello(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

---

## Advanced Features

### User Identification

The middleware supports identifying users from request context. Pass an `identifyUser` function that extracts user information:

```python
def identify_user(context) -> dict:
    """Extract user info from context. Can be sync or async."""
    # Example: Extract from headers
    try:
        request_context = getattr(context, "request_context", None)
        if request_context:
            request = getattr(request_context, "request", None)
            if request:
                headers = getattr(request, "headers", {}) or {}
                headers_lower = {k.lower(): v for k, v in headers.items()}
                
                user_id = headers_lower.get("x-user-id")
                if user_id:
                    return {
                        "user_id": user_id,
                        "user_name": headers_lower.get("x-user-name"),
                        "user_email": headers_lower.get("x-user-email"),
                    }
    except Exception:
        pass
    return None

trace_middleware = TraceMiddleware(
    adapter=ConsoleAdapter(),
    identifyUser=identify_user
).init(mcp)
```

### PII Redaction

Protect sensitive data by providing a `redact` function that processes trace data before export:

```python
def redact_pii(trace_data: dict) -> dict:
    """Redact PII from trace data before exporting."""
    # Redact user email
    if "user_email" in trace_data:
        trace_data["user_email"] = "***REDACTED***"
    
    # Redact sensitive request fields
    if "request" in trace_data and isinstance(trace_data["request"], dict):
        if "password" in trace_data["request"]:
            trace_data["request"]["password"] = "***REDACTED***"
        if "api_key" in trace_data["request"]:
            trace_data["request"]["api_key"] = "***REDACTED***"
    
    return trace_data

trace_middleware = TraceMiddleware(
    adapter=ConsoleAdapter(),
    redact=redact_pii
).init(mcp)
```

### Trace Data Fields

The middleware captures comprehensive trace data including:

- **Request info**: `type`, `method`, `timestamp`, `duration`, `session_id`
- **User info**: `user_id`, `user_name`, `user_email` (if `identifyUser` is provided)
- **Client info**: `client_id`, `client_name`, `client_version`
- **Request details**: `request` (with query_params, path_params, url, method)
- **Response data**: `response` (structured or text content)
- **Error info**: `is_error`, `error`
- **Network info**: `ip_address` (from X-Forwarded-For or X-Real-IP headers)
- **Entity info**: `entity_name` (tool/resource/prompt name)
- **Metadata**: Custom metadata dictionary

---

## Requirements

- Python 3.8+
- [mcp](https://github.com/modelcontextprotocol/python-sdk) (with CLI support: `mcp[cli]`)
- [psycopg2-binary](https://pypi.org/project/psycopg2-binary/) (for PostgreSQL adapter)
- [supabase](https://github.com/supabase-community/supabase-py) (for Supabase adapter)
- [requests](https://pypi.org/project/requests/) (for Contexa adapter)
- [pydantic](https://pypi.org/project/pydantic/)

---

## Contributing

We love contributions! Please open issues for bugs or feature requests, and submit pull requests for improvements. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

[MIT](LICENSE)

---

## Links & Acknowledgements

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) — Model Context Protocol Python SDK
- [FastMCP](https://github.com/jlowin/fastmcp) — FastMCP server framework
