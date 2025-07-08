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
    entity_name TEXT,
    entity_params JSONB,
    entity_response JSONB,
    error TEXT
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
            "entity_name": trace_data.get("entity_name"),
            "entity_params": trace_data.get("entity_params"),
            "entity_response": trace_data.get("entity_response"),
            "error": trace_data.get("error"),
        }
        resp = self.supabase.table(self.table).insert(data).execute()
        if hasattr(resp, "error") and resp.error:
            raise RuntimeError(f"Supabase insert error: {resp.error}") 