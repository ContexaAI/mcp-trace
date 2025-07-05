from typing import Any, Optional
import time
from datetime import datetime, timezone
from fastmcp.server.middleware import MiddlewareContext, CallNext
from fastmcp.server.context import Context

# Try importing TextContent for tool response formatting
try:
    from mcp.types import TextContent
except ImportError:
    TextContent = None


class TraceMiddleware:
    """
    Middleware to trace incoming MCP requests and responses.

    Captures metadata like request type, session ID, duration, tool call arguments, and outputs.
    Supports configurable logging of fields via `log_fields`.
    """

    def __init__(self, adapter, log_fields: Optional[dict[str, bool]] = None):
        """
        Args:
            adapter: Logger/exporter with an `export(dict)` method.
            log_fields: Dict specifying which fields to include in logs.
                        Example: {'tool_arguments': True, 'client_id': False}
        """
        self.adapter = adapter
        self.log_fields = log_fields or {}

    def _should_log(self, field: str) -> bool:
        """
        Checks if a given field should be logged.
        Defaults to True if not explicitly configured.
        """
        return self.log_fields.get(field, True)

    async def __call__(self, context: MiddlewareContext, call_next: CallNext):
        """
        Entry point for the middleware. Times the request and logs relevant trace data.
        """
        start_time = time.time()
        response = await call_next(context)
        duration = time.time() - start_time

        trace_data = self._extract_base_trace_data(context, duration)

        if self._is_tool_call(context):
            trace_data.update(self._extract_tool_call_trace(context, response))

        self.adapter.export(trace_data)
        return response

    def _extract_base_trace_data(self, context: MiddlewareContext, duration: float) -> dict[str, Any]:
        """
        Extracts trace metadata common to all requests.
        """
        fastmcp_ctx: Optional[Context] = getattr(context, 'fastmcp_context', None)
        timestamp = getattr(context, 'timestamp', datetime.now(timezone.utc))

        field_extractors = {
            'type': lambda: getattr(context, 'type', None),
            'method': lambda: getattr(context, 'method', None),
            'timestamp': lambda: timestamp.isoformat(),
            'session_id': lambda: getattr(fastmcp_ctx, 'session_id', None),
            'request_id': lambda: getattr(fastmcp_ctx, 'request_id', None),
            'client_id': lambda: getattr(fastmcp_ctx, 'client_id', None),
            'duration': lambda: duration,
        }

        return {
            key: extractor()
            for key, extractor in field_extractors.items()
            if self._should_log(key)
        }

    def _is_tool_call(self, context: MiddlewareContext) -> bool:
        """
        Returns True if the request is a `tools/call` operation.
        """
        return (
            getattr(context, 'type', None) == 'request'
            and getattr(context, 'method', None) == 'tools/call'
        )

    def _extract_tool_call_trace(self, context: MiddlewareContext, response: Any) -> dict[str, Any]:
        """
        Extracts tool-specific request and response data.
        """
        trace = {}
        request_msg = getattr(context, 'message', None)

        # Request-related fields
        if request_msg:
            if self._should_log('tool_name') and hasattr(request_msg, 'name'):
                trace['tool_name'] = getattr(request_msg, 'name', None)
            if self._should_log('tool_arguments') and hasattr(request_msg, 'arguments'):
                trace['tool_arguments'] = getattr(request_msg, 'arguments', None)

        # Response-related fields
        if self._should_log('tool_response'):
            response_text = self._extract_text_response(response)
            if response_text:
                trace['tool_response'] = response_text

        if self._should_log('tool_response_structured'):
            structured = self._extract_structured_response(response)
            if structured:
                trace['tool_response_structured'] = structured

        return trace

    def _extract_text_response(self, response: Any) -> Optional[str]:
        """
        Extracts concatenated plain-text output from the response content blocks.
        """
        content_blocks = getattr(response, 'content', [])
        if not content_blocks:
            return None

        if TextContent:
            texts = [
                block.text for block in content_blocks
                if isinstance(block, TextContent)
            ]
        else:
            texts = [str(block) for block in content_blocks]

        return '\n'.join(texts) if texts else None

    def _extract_structured_response(self, response: Any) -> Optional[Any]:
        """
        Extracts structured content from response, supporting both camelCase and snake_case.
        """
        return (
            getattr(response, 'structured_content', None)
            or getattr(response, 'structuredContent', None)
        )
