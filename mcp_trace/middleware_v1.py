import time
from datetime import datetime, timezone
from typing import Any
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.middleware.middleware import CallNext
from mcp.types import Notification, TextContent
from typing import Optional

# Header to look for session ID in requests
HEADER_NAME = "mcp-session-id"

class TraceAdapter(Middleware):
    """Middleware that logs all MCP operations."""

    def __init__(self, adapter=None):
        self.adapter = adapter

    def _session_id(self, context: MiddlewareContext, response: Any = None) -> Optional[str]:
        """
        Extracts the session ID using the following priority:
        1. `context.fastmcp_context.session_id`
        2. `mcp-session-id` from HTTP headers (case-insensitive)
        3. `mcp-session-id` from raw request headers
        4. `mcp-session-id` from query parameters
        5. `mcp-session-id` from response headers (if response is provided)
        Returns None if not found.
        """
        target_header = HEADER_NAME.lower()

        # 1. From context's fastmcp_context (highest priority)
        session_id = getattr(context.fastmcp_context, "session_id", None)
        if session_id:
            return session_id

        # 2. From raw request headers and query params (access request only once)
        try:
            request = context.fastmcp_context.request_context.request
            headers = {k.lower(): v for k, v in request.headers.items()}
            if target_header in headers:
                return headers[target_header]

            # 3. From query parameters (last priority)
            session_id = request.query_params.get('session_id')
            if session_id:
                return session_id
        except (AttributeError, RuntimeError):
            pass

        # 4. From response headers if available
        if response is not None:
            response_headers = getattr(response, "headers", None)
            if response_headers and target_header in response_headers:
                return response_headers[target_header]

        return None
    

    def _extract_structured_response(self, response: Any) -> Optional[Any]:
        """
        Tries to get structured tool output from the response.
        Supports both `structured_content` (snake_case) and `structuredContent` (camelCase).
        """
        return (
            getattr(response, "structured_content", None) or
            getattr(response, "structuredContent", None)
        )

    def _extract_text_response(self, response: Any) -> Optional[str]:
        """
        Parses `response.content` to extract a single text blob.
        Supports `TextContent` if available, falls back to stringifying blocks.
        """
        content_blocks = getattr(response, "content", [])
        if not content_blocks:
            return None

        if TextContent:
            texts = [block.text for block in content_blocks if isinstance(block, TextContent)]
        else:
            texts = [str(block) for block in content_blocks]

        return "\n".join(texts) if texts else None

    def build_trace_data(self, context, extra=None, start_time=None, end_time=None):
        duration = None
        if start_time and end_time:
            duration = (end_time - start_time) * 1000  # ms
        session_id = self._session_id(context)
        client_info = None
        try:
            session = context.fastmcp_context.request_context.session
            client_info = session.client_params.clientInfo.name
            
        except Exception:
            pass
        trace_data = {
            "type": getattr(context, "type", None),
            "method": getattr(context, "method", None),
            "timestamp": getattr(context, "timestamp", datetime.now(timezone.utc)).isoformat(),
            "session_id": session_id,
            "client_id": client_info,
            "error": getattr(context, "error", None),
            "duration": duration,
        }
        if extra:
            trace_data.update(extra)
        if self.adapter:
            self.adapter.export(trace_data)
        else:
            print(f"Trace: {trace_data}")
        return trace_data

    async def on_notification(self, context: MiddlewareContext[Notification], call_next: CallNext[Notification, Any]) -> Any:
        start_time = time.time()
        result = await call_next(context)
        end_time = time.time()
        self.build_trace_data(context, start_time=start_time, end_time=end_time)
        return result

    async def on_call_tool(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        start_time = time.time()
        result = await call_next(context)
        end_time = time.time()
        extra = {}
        msg = getattr(context, "message", None)
        if msg is not None:
            if hasattr(msg, "name"):
                extra["entity_name"] = getattr(msg, "name", None)
            if hasattr(msg, "arguments"):
                extra["arguments"] = getattr(msg, "arguments", None)
        self.build_trace_data(context, extra=extra, start_time=start_time, end_time=end_time)
        return result

    async def on_read_resource(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        start_time = time.time()
        result = await call_next(context)
        end_time = time.time()
        
        extra = {}
        msg = getattr(context, "message", None)
        if msg is not None:
            if hasattr(msg, "name"):
                extra["entity_name"] = getattr(msg, "name", None)
            if hasattr(msg, "arguments"):
                extra["arguments"] = getattr(msg, "arguments", None)
        self.build_trace_data(context, extra=extra, start_time=start_time, end_time=end_time)
        return result

    async def on_get_prompt(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        start_time = time.time()
        result = await call_next(context)
        end_time = time.time()
        
        extra = {}
        msg = getattr(context, "message", None)
        if msg is not None:
            if hasattr(msg, "name"):
                extra["entity_name"] = getattr(msg, "name", None)
            if hasattr(msg, "arguments"):
                extra["arguments"] = getattr(msg, "arguments", None)
        extra["response"] = self._extract_structured_response(result) or self._extract_text_response(result) 
        self.build_trace_data(context, extra=extra, start_time=start_time, end_time=end_time)
        return result

    async def on_list_tools(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        start_time = time.time()
        result = await call_next(context)
        end_time = time.time()
        extra = {}
        extra["response"] = self._extract_structured_response(result) or self._extract_text_response(result) 
        self.build_trace_data(context, extra=extra, start_time=start_time, end_time=end_time)
        return result

    async def on_list_resources(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        start_time = time.time()
        result = await call_next(context)
        end_time = time.time()
        extra = {}
        extra["response"] = self._extract_structured_response(result) or self._extract_text_response(result) 
        self.build_trace_data(context, extra=extra, start_time=start_time, end_time=end_time)
        return result

    async def on_list_resource_templates(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        start_time = time.time()
        result = await call_next(context)
        end_time = time.time()
        extra = {}
        extra["response"] = self._extract_structured_response(result) or self._extract_text_response(result) 
        self.build_trace_data(context, extra=extra, start_time=start_time, end_time=end_time)
        return result

    async def on_list_prompts(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        start_time = time.time()
        result = await call_next(context)
        end_time = time.time()
        extra = {}
        extra["response"] = self._extract_structured_response(result) or self._extract_text_response(result) 
        self.build_trace_data(context, extra=extra, start_time=start_time, end_time=end_time)
        return result

 