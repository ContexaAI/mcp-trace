import json
from mcp_trace.adapters.base import TraceAdapter

# ANSI color codes
CYAN = '\033[96m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

class ConsoleTraceAdapter(TraceAdapter):
    """
    A TraceAdapter that logs formatted TraceData to the console.
    Similar to the Node.js version with colorized output.
    """

    def export(self, trace_data: dict):
        print(f"{CYAN}--- TraceData ---{RESET}")
        
        def log(label: str, value, color=YELLOW):
            if value is not None:
                print(f"{color}{label:<16}:{RESET} {value}")

        log("Type", trace_data.get("type"))
        log("Method", trace_data.get("method"))
        log("Timestamp", trace_data.get("timestamp"))
        log("Session ID", trace_data.get("session_id"))
        log("Client ID", trace_data.get("client_id"))
        log("Duration", f"{trace_data.get('duration')} ms" if trace_data.get("duration") is not None else None)
        log("Entity Name", trace_data.get("entity_name"))

        entity_params = trace_data.get("entity_params")
        if entity_params is not None:
            print(f"{YELLOW}Entity Params    :{RESET}")
            print(json.dumps(entity_params, indent=2, ensure_ascii=False))

        entity_response = trace_data.get("entity_response")
        if entity_response is not None:
            print(f"{YELLOW}Entity Response  :{RESET}")
            print(json.dumps(entity_response, indent=2, ensure_ascii=False))

        error = trace_data.get("error")
        if error:
            print(f"{RED}Error            :{RESET} {error}")

        print(f"{CYAN}-----------------{RESET}")

    async def flush(self, timeout: int = None):
        # No-op for console logging
        pass

    async def shutdown(self):
        # No cleanup needed for console adapter
        pass
