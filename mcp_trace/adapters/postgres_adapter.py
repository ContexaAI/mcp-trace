"""
PostgreSQL Trace Adapter for MCP Trace

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

You may add indexes or additional columns as needed for your use case.
"""

import psycopg2
import psycopg2.extras
import json
import uuid

class PostgresTraceAdapter:
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
            event_id = str(uuid.uuid4())
            timestamp = trace_data.get("timestamp")
            duration = trace_data.get("duration")
            type_ = trace_data.get("type")
            method = trace_data.get("method")
            session_id = trace_data.get("session_id")
            client_id = trace_data.get("client_id")
            request_id = trace_data.get("request_id")
            tool_name = trace_data.get("tool_name")
            tool_arguments = trace_data.get("tool_arguments")
            tool_response = trace_data.get("tool_response")
            tool_response_structured = trace_data.get("tool_response_structured")
            with self._conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self.table} (
                        id, timestamp, duration, type, method, session_id, client_id, request_id, tool_name, tool_arguments, tool_response, tool_response_structured
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        event_id,
                        timestamp,
                        duration,
                        type_,
                        method,
                        session_id,
                        client_id,
                        request_id,
                        tool_name,
                        json.dumps(tool_arguments) if tool_arguments is not None else None,
                        tool_response,
                        json.dumps(tool_response_structured) if tool_response_structured is not None else None
                    ]
                )
        except Exception as e:
            print(f"Error exporting trace data: {e}")

    def close(self):
        if self._conn:
            self._conn.close() 