from typing import Any, Optional
import time
from datetime import datetime, timezone

from fastmcp.server.middleware import MiddlewareContext, CallNext
from fastmcp.server.context import Context
from mcp_trace.adapters.file_adapter import FileTraceAdapter
from mcp_trace.adapters.contexaai_adapter import ContexaTraceAdapter

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

    def __init__(self, adapter=None, log_fields: Optional[dict[str, bool]] = None):
        """
        Args:
            adapter: Logger/exporter with an `export(dict)` method (e.g., ContexaTraceAdapter by default).
            log_fields: Dict that controls which fields are logged.
                        Example: {'tool_arguments': True, 'client_id': False}
        """
        if adapter is None:
            try:
                adapter = ContexaTraceAdapter()
            except Exception as e:
                raise RuntimeError(
                    "ContexaTraceAdapter is the default, but could not be initialized. "
                    "Set CONTEXA_API_KEY and CONTEXA_SERVER_ID env vars, or pass an adapter explicitly."
                ) from e
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
        trace_data = self._extract_base_trace_data(context, duration, response)

        # Don't log if session ID is missing (unless using local debug adapter)
        if not isinstance(self.adapter, FileTraceAdapter) and not trace_data.get("session_id"):
            return response

        # Add tool-specific fields if it's a tool call
        if self._is_tool_call(context):
            trace_data.update(self._extract_tool_call_trace(context, response))

        # Export the trace to the adapter
        self.adapter.export(trace_data)

        return response

    def _extract_base_trace_data(self, context: MiddlewareContext, duration: float, response: Any = None) -> dict[str, Any]:
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
            "session_id": self._session_id(context, response),
            "client_id": self.get_client_info(context),
            "client_version": self.get_client_version(context),
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
            if self._should_log("entity_name") and hasattr(request_msg, "name"):
                trace["entity_name"] = getattr(request_msg, "name", None)

            if self._should_log("entity_params") and hasattr(request_msg, "arguments"):
                trace["entity_params"] = getattr(request_msg, "arguments", None)

        # Extract plain-text output from the tool response
        if self._should_log("tool_response"):
            response_text = self._extract_text_response(response)
            if response_text:
                trace["tool_response"] = response_text

        # Extract structured tool output (e.g., JSON)
        if self._should_log("entity_response"):
            structured = self._extract_structured_response(response)
            if structured:
                trace["entity_response"] = structured

        # Extract error if present
        error = getattr(response, "error", None) or getattr(context, "error", None)
        if self._should_log("error") and error:
            trace["error"] = error

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
        
    def get_client_info(self, context: MiddlewareContext) -> Optional[str]:
        """
        Extracts client information from the context.
        """
        try:
            session = context.fastmcp_context.request_context.session
            client_info = session.client_params.clientInfo
            return client_info.name
        except (AttributeError, RuntimeError):
            return None

    def get_client_version(self, context: MiddlewareContext) -> Optional[str]:
        """
        Extracts client version from the context.
        """
        session = context.fastmcp_context.request_context.session
        client_info = session.client_params.clientInfo
        return client_info.version