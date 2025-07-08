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
    entity_name TEXT,
    entity_params JSONB,
    entity_response JSONB,
    error TEXT
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
            entity_name = trace_data.get("entity_name")
            entity_params = trace_data.get("entity_params")
            entity_response = trace_data.get("entity_response")
            error = trace_data.get("error")
            with self._conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self.table} (
                        id, timestamp, duration, type, method, session_id, client_id, entity_name, entity_params, entity_response, error
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
                        entity_name,
                        json.dumps(entity_params) if entity_params is not None else None,
                        json.dumps(entity_response) if entity_response is not None else None,
                        error
                    ]
                )
        except Exception as e:
            print(f"Error exporting trace data: {e}")

    def close(self):
        if self._conn:
            self._conn.close() 