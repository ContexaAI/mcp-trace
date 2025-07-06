"""
PostgreSQL Trace Adapter for MCP Trace

Table schema required:

CREATE TABLE mcp_traces (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_id TEXT NOT NULL,
    trace_data JSONB NOT NULL
);

You may add indexes or additional columns as needed for your use case.
"""

import psycopg2
import psycopg2.extras
import json

class PostgresTraceAdapter:
    def __init__(self, dsn: str, table: str = "mcp_traces"):
        self.dsn = dsn
        self.table = table
        self._conn = psycopg2.connect(self.dsn)
        self._conn.autocommit = True

    def export(self, trace_data: dict):
        session_id = trace_data.get("session_id")
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {self.table} (session_id, trace_data)
                VALUES (%s, %s)
                """,
                [session_id, json.dumps(trace_data)],
            )

    def close(self):
        if self._conn:
            self._conn.close() 