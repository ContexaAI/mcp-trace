import json
from mcp_trace.adapters.base import TraceAdapter

# ANSI color codes
CYAN = '\033[96m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

class ConsoleAdapter(TraceAdapter):
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
        log("Client Name", trace_data.get("client_name"))
        log("Client Ver", trace_data.get("client_version"))
        log("Server ID", trace_data.get("server_id"))
        log("Server Name", trace_data.get("server_name"))
        log("Server Ver", trace_data.get("server_version"))
        log("Duration", f"{trace_data.get('duration')} ms" if trace_data.get("duration") is not None else None)
        log("Entity Name", trace_data.get("entity_name"))
        log("User ID", trace_data.get("user_id"))
        log("User Name", trace_data.get("user_name"))
        log("User Email", trace_data.get("user_email"))
        log("IP Address", trace_data.get("ip_address"))
        log("SDK Lang", trace_data.get("sdk_language"))
        log("SDK Version", trace_data.get("sdk_version"))
        log("Trace Ver", trace_data.get("mcp_trace_version"))

        request = trace_data.get("request")
        if request is not None:
            print(f"{YELLOW}Request       :{RESET}")
            print(json.dumps(request, indent=2, ensure_ascii=False))

        response = trace_data.get("response")
        if response is not None:
            print(f"{YELLOW}Response      :{RESET}")
            print(json.dumps(response, indent=2, ensure_ascii=False))

        error = trace_data.get("error")
        if error:
            print(f"{RED}Error            :{RESET} {error}")

        metadata = trace_data.get("metadata")
        if metadata is not None:
            print(f"{YELLOW}Metadata      :{RESET}")
            print(json.dumps(metadata, indent=2, ensure_ascii=False))

        print(f"{CYAN}-----------------{RESET}")

    async def flush(self, timeout: int = None):
        # No-op for console logging
        pass

    async def shutdown(self):
        # No cleanup needed for console adapter
        pass
