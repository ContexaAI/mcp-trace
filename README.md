# mcp-trace

<div align="center">
  <img src="images/MCP-TRACE.png" alt="mcp-trace" width="100%"/>
</div>

[![PyPI version](https://badge.fury.io/py/mcp-trace.svg)](https://pypi.org/project/mcp-trace/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)

> **Flexible, pluggable tracing middleware for [FastMCP](https://github.com/jlowin/fastmcp) servers.**
> Log every request, tool call, and response to local files, PostgreSQL, Supabase, your own backend, or the console—with full control over what gets logged.

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
- [Configurable Logging](#configurable-logging)
- [Requirements](#requirements)
- [Contributing](#contributing)
- [License](#license)
- [Links & Acknowledgements](#links--acknowledgements)

---

## Features

- 📦 **Plug-and-play**: Add tracing to any FastMCP server in seconds
- 🗃️ **Pluggable adapters**: Log to file, PostgreSQL, Supabase, console, or your own
- 🛠️ **Configurable logging**: Enable/disable fields (tool args, responses, client ID, etc.)
- 🧩 **Composable**: Use multiple adapters at once
- 📝 **Schema-first**: All traces stored as JSON for easy querying
- 🔒 **Privacy-aware**: Control exactly what gets logged

---

## Quickstart

### Installation

```sh
pip install mcp-trace
```

### Minimal Example (File Adapter)

```python
from mcp_trace.middleware import TraceMiddleware
from mcp_trace.adapters.file_adapter import FileTraceAdapter

trace_adapter = FileTraceAdapter("trace.log")
trace_middleware = TraceMiddleware(adapter=trace_adapter)

# Add to your FastMCP server
mcp.add_middleware(trace_middleware)
```

### Console Adapter Example

```python
from mcp_trace.middleware import TraceMiddleware
from mcp_trace.adapters.console_adapter import ConsoleTraceAdapter

trace_adapter = ConsoleTraceAdapter()
trace_middleware = TraceMiddleware(adapter=trace_adapter)
mcp.add_middleware(trace_middleware)
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
from mcp_trace.middleware import TraceMiddleware
from mcp_trace.adapters.contexaai_adapter import ContexaTraceAdapter

# Option 1: Set environment variables
# import os
# os.environ["CONTEXA_API_KEY"] = "your-api-key"
# os.environ["CONTEXA_SERVER_ID"] = "your-server-id"
# contexa_adapter = ContexaTraceAdapter()

# Option 2: Pass directly
contexa_adapter = ContexaTraceAdapter(
    api_key="your-api-key",
    server_id="your-server-id"
)

trace_middleware = TraceMiddleware(adapter=contexa_adapter)
mcp.add_middleware(trace_middleware)

# On shutdown, ensure all events are sent:
contexa_adapter.flush(timeout=5)
contexa_adapter.shutdown()
```

### File Adapter

Logs each trace as a JSON line to a file.

```python
from mcp_trace.adapters.file_adapter import FileTraceAdapter
trace_adapter = FileTraceAdapter("trace.log")
```

### Console Adapter

Prints each trace to the console in a colorized, readable format.

```python
from mcp_trace.adapters.console_adapter import ConsoleTraceAdapter
trace_adapter = ConsoleTraceAdapter()
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
from mcp_trace.adapters.postgres_adapter import PostgresTraceAdapter
psql_adapter = PostgresTraceAdapter(dsn="postgresql://user:pass@host:port/dbname")
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
from supabase import create_client
from mcp_trace.adapters.supabase_adapter import SupabasePostgresTraceAdapter
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_adapter = SupabasePostgresTraceAdapter(supabase)
```

### Multi-Adapter Example

Send traces to multiple backends at once:

```python
class MultiAdapter:
    def __init__(self, *adapters):
        self.adapters = adapters
    def export(self, trace_data: dict):
        for adapter in self.adapters:
            adapter.export(trace_data)

file_adapter = FileTraceAdapter("trace.log")
psql_adapter = PostgresTraceAdapter(dsn="postgresql://user:pass@host:port/dbname")
supabase_adapter = SupabasePostgresTraceAdapter(supabase)
console_adapter = ConsoleTraceAdapter()
trace_middleware = TraceMiddleware(adapter=MultiAdapter(file_adapter, psql_adapter, supabase_adapter, console_adapter))
mcp.add_middleware(trace_middleware)
```

---

## Configurable Logging

Control exactly which fields are logged by passing a `log_fields` dictionary to `TraceMiddleware`. By default, all fields are logged unless set to `False`.

**Available fields:**

- `type`, `method`, `timestamp`, `session_id`, `client_id`, `client_version`, `duration`
- `entity_name`, `entity_params`, `entity_response`, `tool_response`, `error`

**Example: Only log entity name and response, hide params and client ID:**

```python
trace_middleware = TraceMiddleware(
    adapter=trace_adapter,
    log_fields={
        "entity_name": True,
        "entity_response": True,
        "entity_params": False,  # disables tool arguments
        "client_id": False,      # disables client_id
        # ...add more as needed
    }
)
mcp.add_middleware(trace_middleware)
```

---

## Requirements

- Python 3.8+
- [fastmcp](https://github.com/jlowin/fastmcp)
- [psycopg2-binary](https://pypi.org/project/psycopg2-binary/) (for PostgreSQL)
- [supabase-py](https://github.com/supabase-community/supabase-py) (for Supabase)
- [requests](https://pypi.org/project/requests/), [pydantic](https://pypi.org/project/pydantic/)

---

## Contributing

We love contributions! Please open issues for bugs or feature requests, and submit pull requests for improvements. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

[MIT](LICENSE)

---

## Links & Acknowledgements

- [FastMCP](https://github.com/jlowin/fastmcp) — Model Context Protocol server
