"""
PostgreSQL Trace Adapter for MCP Trace

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

You may add indexes or additional columns as needed for your use case.
"""

import psycopg2
import psycopg2.extras
import uuid
import json

class PostgresAdapter:
    def __init__(self, dsn: str, table: str = "trace_events"):
        try:
            self.dsn = dsn
            self.table = table
            self._conn = psycopg2.connect(self.dsn)
            self._conn.autocommit = True
        except Exception as e:
            print(f"Error connecting to PostgreSQL: {e}")
            raise e
        
    def is_connected(self):
        return self._conn and self._conn.closed == 0

    def export(self, trace_data: dict):
        try:
            event_id = trace_data.get("id") or str(uuid.uuid4())
            # Prepare payload mapping directly from TraceData keys
            payload = {
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
            with self._conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self.table} (
                        id,
                        type, method, entity_name, request, response,
                        timestamp, duration,
                        session_id,
                        user_id, user_name, user_email,
                        client_id, client_name, client_version,
                        server_id, server_name, server_version,
                        is_error, error,
                        ip_address,
                        context, sdk_language, sdk_version, mcp_trace_version,
                        metadata
                    ) VALUES (
                        %s,
                        %s, %s, %s, %s, %s,
                        %s, %s,
                        %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s,
                        %s, %s, %s, %s,
                        %s
                    )
                    """,
                    [
                        payload["id"],
                        payload["type"], payload["method"], payload["entity_name"],
                        json.dumps(payload["request"]) if payload["request"] is not None else None,
                        json.dumps(payload["response"]) if payload["response"] is not None else None,
                        payload["timestamp"], payload["duration"],
                        payload["session_id"],
                        payload["user_id"], payload["user_name"], payload["user_email"],
                        payload["client_id"], payload["client_name"], payload["client_version"],
                        payload["server_id"], payload["server_name"], payload["server_version"],
                        payload["is_error"], payload["error"],
                        payload["ip_address"],
                        payload["context"], payload["sdk_language"], payload["sdk_version"], payload["mcp_trace_version"],
                        json.dumps(payload["metadata"]) if payload["metadata"] is not None else None,
                    ]
                )
        except Exception as e:
            print(f"Error exporting trace data: {e}")

    def close(self):
        if self._conn:
            self._conn.close() 