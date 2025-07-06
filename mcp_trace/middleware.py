from typing import Any, Optional
import time
from datetime import datetime, timezone

from fastmcp.server.middleware import MiddlewareContext, CallNext
from fastmcp.server.context import Context
from fastmcp.server.dependencies import get_http_request, get_http_headers
from mcp_trace.adapters.local import LocalTraceAdapter

# Try importing TextContent to parse response content more cleanly
try:
    from mcp.types import TextContent
except ImportError:
    TextContent = None

# Header to look for session ID in requests
HEADER_NAME = "mcp-session-id"


class TraceMiddleware:
    """
    Middleware to trace incoming MCP requests and responses.

    It logs metadata such as session ID, request type, duration, tool arguments, and outputs.
    Logging fields are configurable via the `log_fields` dictionary.
    """

    def __init__(self, adapter, log_fields: Optional[dict[str, bool]] = None):
        """
        Args:
            adapter: Logger/exporter with an `export(dict)` method (e.g., LocalTraceAdapter).
            log_fields: Dict that controls which fields are logged.
                        Example: {'tool_arguments': True, 'client_id': False}
        """
        self.adapter = adapter
        self.log_fields = log_fields or {}

    def _should_log(self, field: str) -> bool:
        """
        Returns True if the given field should be included in logs.
        Defaults to True unless explicitly disabled.
        """
        return self.log_fields.get(field, True)

    async def __call__(self, context: MiddlewareContext, call_next: CallNext):
        """
        Middleware entrypoint. Times the request and logs trace data on completion.
        """
        start_time = time.time()

        # Proceed with the actual request
        response = await call_next(context)

        # Measure duration in milliseconds
        duration = (time.time() - start_time) * 1000  # ms

        # Collect base trace data
        trace_data = self._extract_base_trace_data(context, duration)

        # Don't log if session ID is missing (unless using local debug adapter)
        if not isinstance(self.adapter, LocalTraceAdapter) and not trace_data.get("session_id"):
            return response

        # Add tool-specific fields if it's a tool call
        if self._is_tool_call(context):
            trace_data.update(self._extract_tool_call_trace(context, response))

        # Export the trace to the adapter
        self.adapter.export(trace_data)

        return response

    def _extract_base_trace_data(self, context: MiddlewareContext, duration: float) -> dict[str, Any]:
        """
        Extracts general-purpose trace metadata for any request.
        Includes type, method, session/client/request ID, and duration.
        Only includes fields allowed by `log_fields`.
        """
        fastmcp_ctx: Optional[Context] = context.fastmcp_context
        timestamp = getattr(context, "timestamp", datetime.now(timezone.utc))

        base_fields = {
            "type": getattr(context, "type", None),
            "method": getattr(context, "method", None),
            "timestamp": timestamp.isoformat(),
            "session_id": self._session_id(context),
            "request_id": getattr(fastmcp_ctx, "request_id", None),
            "client_id": getattr(fastmcp_ctx, "client_id", None),
            "duration": duration,
        }

        # Filter based on log_fields config
        return {k: v for k, v in base_fields.items() if self._should_log(k) and v is not None}

    def _is_tool_call(self, context: MiddlewareContext) -> bool:
        """
        Returns True if this is a `tools/call` type request.
        Used to decide whether to extract tool-related metadata.
        """
        return (
            getattr(context, "type", None) == "request" and
            getattr(context, "method", None) == "tools/call"
        )

    def _extract_tool_call_trace(self, context: MiddlewareContext, response: Any) -> dict[str, Any]:
        """
        Extracts tool call details:
        - Tool name and arguments from the request
        - Tool response (text and structured content) from the response
        Only includes fields allowed by `log_fields`.
        """
        trace: dict[str, Any] = {}
        request_msg = getattr(context, "message", None)

        # Include tool name and arguments if available
        if request_msg:
            if self._should_log("tool_name") and hasattr(request_msg, "name"):
                trace["tool_name"] = getattr(request_msg, "name", None)

            if self._should_log("tool_arguments") and hasattr(request_msg, "arguments"):
                trace["tool_arguments"] = getattr(request_msg, "arguments", None)

        # Extract plain-text output from the tool response
        if self._should_log("tool_response"):
            response_text = self._extract_text_response(response)
            if response_text:
                trace["tool_response"] = response_text

        # Extract structured tool output (e.g., JSON)
        if self._should_log("tool_response_structured"):
            structured = self._extract_structured_response(response)
            if structured:
                trace["tool_response_structured"] = structured

        return trace

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

    def _extract_structured_response(self, response: Any) -> Optional[Any]:
        """
        Tries to get structured tool output from the response.
        Supports both `structured_content` (snake_case) and `structuredContent` (camelCase).
        """
        return (
            getattr(response, "structured_content", None) or
            getattr(response, "structuredContent", None)
        )

    def _session_id(self, context: MiddlewareContext) -> Optional[str]:
        """
        Extracts session ID in priority order:
        1. `context.fastmcp_context.session_id`
        2. `mcp-session-id` from HTTP headers (case-insensitive)
        3. `mcp-session-id` from raw request headers
        Returns None if not found.
        """
        target_header = HEADER_NAME.lower()

        # 1. From fastmcp_context
        session_id = getattr(context.fastmcp_context, "session_id", None)
        if session_id:
            return session_id

        # 2. From high-level HTTP headers
        try:
            headers = {k.lower(): v for k, v in get_http_headers(include_all=True).items()}
            if target_header in headers:
                return headers[target_header]
        except RuntimeError:
            pass  # Likely not in an HTTP request context

        # 3. From raw request object (e.g., Starlette/FastAPI Request)
        try:
            request_headers = {
                k.lower(): v for k, v in get_http_request().headers.items()
            }
            return request_headers.get(target_header)
        except (AttributeError, RuntimeError):
            return None
