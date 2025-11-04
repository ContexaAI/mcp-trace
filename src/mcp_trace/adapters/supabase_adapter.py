"""
Supabase PostgreSQL Trace Adapter for MCP Trace

Table schema example (aligns with TraceData shape; adjust as needed):

CREATE TABLE trace_events (
    id UUID PRIMARY KEY,
    type TEXT,
    method TEXT,
    entity_name TEXT,
    request JSONB,
    response JSONB,

    timestamp TIMESTAMPTZ NOT NULL,
    duration DOUBLE PRECISION,

    session_id TEXT,

    user_id TEXT,
    user_name TEXT,
    user_email TEXT,

    client_id TEXT,
    client_name TEXT,
    client_version TEXT,

    server_id TEXT,
    server_name TEXT,
    server_version TEXT,

    is_error BOOLEAN,
    error TEXT,

    ip_address TEXT,

    context TEXT,
    sdk_language TEXT,
    sdk_version TEXT,
    mcp_trace_version TEXT,

    metadata JSONB
);

Usage:
from supabase import create_client, Client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
adapter = SupabasePostgresTraceAdapter(supabase)
"""

from typing import Any
import uuid

class SupabaseAdapter:
    def __init__(self, supabase_client, table: str = "trace_events"):
        self.supabase = supabase_client
        self.table = table

    def export(self, trace_data: dict):
        event_id = trace_data.get("id") or str(uuid.uuid4())
        data = {
            "id": event_id,
            "type": trace_data.get("type"),
            "method": trace_data.get("method"),
            "entity_name": trace_data.get("entity_name"),
            "request": trace_data.get("request"),
            "response": trace_data.get("response"),

            "timestamp": trace_data.get("timestamp"),
            "duration": trace_data.get("duration"),

            "session_id": trace_data.get("session_id"),

            "user_id": trace_data.get("user_id"),
            "user_name": trace_data.get("user_name"),
            "user_email": trace_data.get("user_email"),

            "client_id": trace_data.get("client_id"),
            "client_name": trace_data.get("client_name"),
            "client_version": trace_data.get("client_version"),

            "server_id": trace_data.get("server_id"),
            "server_name": trace_data.get("server_name"),
            "server_version": trace_data.get("server_version"),

            "is_error": trace_data.get("is_error"),
            "error": trace_data.get("error"),

            "ip_address": trace_data.get("ip_address"),

            "context": trace_data.get("context"),
            "sdk_language": trace_data.get("sdk_language"),
            "sdk_version": trace_data.get("sdk_version"),
            "mcp_trace_version": trace_data.get("mcp_trace_version"),

            "metadata": trace_data.get("metadata"),
        }
        resp = self.supabase.table(self.table).insert(data).execute()
        if hasattr(resp, "error") and resp.error:
            raise RuntimeError(f"Supabase insert error: {resp.error}") 