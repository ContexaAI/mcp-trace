"""
Supabase PostgreSQL Trace Adapter for MCP Trace

Table schema required:

CREATE TABLE trace_events (
    id UUID PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    duration DOUBLE PRECISION NOT NULL,
    type TEXT,
    method TEXT,
    session_id TEXT,
    client_id TEXT,
    request_id TEXT,
    tool_name TEXT,
    tool_arguments JSONB,
    tool_response TEXT,
    tool_response_structured JSONB
);

Usage:
from supabase import create_client, Client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
adapter = SupabasePostgresTraceAdapter(supabase)
"""

from typing import Any
import uuid

class SupabasePostgresTraceAdapter:
    def __init__(self, supabase_client, table: str = "trace_events"):
        self.supabase = supabase_client
        self.table = table

    def export(self, trace_data: dict):
        event_id = str(uuid.uuid4())
        data = {
            "id": event_id,
            "timestamp": trace_data.get("timestamp"),
            "duration": trace_data.get("duration"),
            "type": trace_data.get("type"),
            "method": trace_data.get("method"),
            "session_id": trace_data.get("session_id"),
            "client_id": trace_data.get("client_id"),
            "request_id": trace_data.get("request_id"),
            "tool_name": trace_data.get("tool_name"),
            "tool_arguments": trace_data.get("tool_arguments"),
            "tool_response": trace_data.get("tool_response"),
            "tool_response_structured": trace_data.get("tool_response_structured"),
        }
        resp = self.supabase.table(self.table).insert(data).execute()
        if hasattr(resp, "error") and resp.error:
            raise RuntimeError(f"Supabase insert error: {resp.error}") 