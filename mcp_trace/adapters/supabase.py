"""
Supabase PostgreSQL Trace Adapter for MCP Trace

Table schema required:

CREATE TABLE mcp_traces (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_id TEXT NOT NULL,
    trace_data JSONB NOT NULL
);

Usage:
from supabase import create_client, Client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
adapter = SupabasePostgresTraceAdapter(supabase)
"""

from typing import Any

class SupabasePostgresTraceAdapter:
    def __init__(self, supabase_client, table: str = "mcp_traces"):
        self.supabase = supabase_client
        self.table = table

    def export(self, trace_data: dict):
        session_id = trace_data.get("session_id")
        # Insert the trace data as a row
        data = {
            "session_id": session_id,
            "trace_data": trace_data,
        }
        # Insert into Supabase
        resp = self.supabase.table(self.table).insert(data).execute()
        if hasattr(resp, "error") and resp.error:
            raise RuntimeError(f"Supabase insert error: {resp.error}") 