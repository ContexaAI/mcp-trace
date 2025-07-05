from .base import TraceAdapter
import json

class LocalTraceAdapter(TraceAdapter):
    def __init__(self, filename: str):
        self.filename = filename

    def export(self, trace_data: dict):
        with open(self.filename, 'a') as f:
            f.write(json.dumps(trace_data) + '\n') 