import time
import uuid
import inspect
from datetime import datetime, timezone
from typing import Any, Optional, Callable, Dict, Union
from importlib import metadata
from mcp.types import Notification, TextContent
from mcp.server import FastMCP, Server

# Header to look for session ID in requests
HEADER_NAME = "mcp-session-id"

class TraceMiddleware:
    """Middleware that logs all MCP operations."""

    server = None

    def __init__(self, adapter=None, redact: Optional[Callable[[Dict], Dict]] = None, identifyUser: Optional[Callable[[Any], Union[Dict, Any]]] = None, **kwargs):
        """
        Initialize TraceMiddleware with options.
        
        Args:
            adapter: The trace adapter to use for exporting trace data
            redact: Optional function to redact PII from trace data before exporting.
                   Should accept a dict and return a dict.
            identify: Optional function to identify user from context. Can be sync or async.
                     Should accept the context and return a dict with user_id, user_name, user_email
                     (or any subset). Returns None if user cannot be identified.
            **kwargs: For backward compatibility, accepts 'server' but it's deprecated.
                     Use init(server) instead.
        """
        # Support old API for backward compatibility
        if 'server' in kwargs:
            import warnings
            warnings.warn(
                "Passing 'server' to TraceMiddleware constructor is deprecated. "
                "Use TraceMiddleware({adapter, redact, identify}).init(server) instead.",
                DeprecationWarning,
                stacklevel=2
            )
            self.server = kwargs['server']._mcp_server if hasattr(kwargs['server'], '_mcp_server') else kwargs['server']
        
        self.adapter = adapter
        self.redact = redact
        self.identifyUser = identifyUser
        self._initialized = False

    def init(self, server: FastMCP | Server):
        """
        Initialize and attach the middleware to the given MCP server.
        
        Args:
            server: The FastMCP or Server instance to attach to
            
        Returns:
            self for chaining
        """
        if self._initialized:
            raise RuntimeError("TraceMiddleware.init() can only be called once")
        
        # Get the underlying MCP server
        if hasattr(server, '_mcp_server'):
            self.server = server._mcp_server
        else:
            self.server = server
        
        # Hook into the server's request handlers
        if hasattr(self.server, 'request_handlers'):
            from mcp import types as mcp_types
            from mcp.server.lowlevel.server import request_ctx
            
            handlers = self.server.request_handlers
            
            # Wrap handlers for each request type
            request_type_map = {
                mcp_types.CallToolRequest: self.on_call_tool,
                mcp_types.ListToolsRequest: self.on_list_tools,
                mcp_types.ListResourcesRequest: self.on_list_resources,
                mcp_types.ListResourceTemplatesRequest: self.on_list_resource_templates,
                mcp_types.ListPromptsRequest: self.on_list_prompts,
                mcp_types.ReadResourceRequest: self.on_read_resource,
                mcp_types.GetPromptRequest: self.on_get_prompt,
            }
            
            # Wrap each handler that exists
            def create_wrapped_handler(orig_handler, mw_method):
                async def wrapped_handler(req):
                    # Get the request context from the global context variable
                    try:
                        context = request_ctx.get()
                    except LookupError:
                        # No context available, create a minimal one
                        context = None
                    
                    async def call_next():
                        return await orig_handler(req)
                    
                    if context:
                        # Create a context object that has the request
                        class ContextWrapper:
                            def __init__(self, req, req_ctx):
                                self.request = req
                                self.request_context = req_ctx
                                self.type = type(req).__name__
                                self.method = getattr(req, 'method', None)
                                # Extract message if available
                                self.message = getattr(req, 'params', None)
                        
                        wrapped_context = ContextWrapper(req, context)
                        return await mw_method(wrapped_context, call_next)
                    else:
                        # Fallback: call original handler directly
                        return await orig_handler(req)
                
                return wrapped_handler
            
            for request_type, middleware_method in request_type_map.items():
                if request_type in handlers:
                    original_handler = handlers[request_type]
                    handlers[request_type] = create_wrapped_handler(original_handler, middleware_method)
        
        self._initialized = True
        return self

    def _session_id(self, context: Any, response: Any = None) -> Optional[str]:
        """
        Extracts the session ID using the following priority:
        1. `context.session_id`
        2. `mcp-session-id` from HTTP headers (case-insensitive)
        3. `mcp-session-id` from raw request headers
        4. `mcp-session-id` from query parameters
        5. `mcp-session-id` from response headers (if response is provided)
        Returns None if not found.
        """
        target_header = HEADER_NAME.lower()

        # 1. From context's session_id (highest priority)
        session_id = getattr(context, "session_id", None)
        if session_id:
            return session_id

        # 2. From raw request headers and query params (access request only once)
        try:
            # Try to get request from context
            request = getattr(getattr(context, "request_context", None), "request", None)
            if request:
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

    async def build_trace_data(self, context, extra=None, start_time=None, end_time=None):
        duration = None
        if start_time and end_time:
            duration = (end_time - start_time) * 1000  # ms

        # Core request info
        session_id = self._session_id(context)

        # Extract request object and IP address from headers if available
        request_obj = None
        ip_address = None
        try:
            request_context = getattr(context, "request_context", None)
            if request_context:
                request = getattr(request_context, "request", None)
                if request:
                    request_obj = {
                        "query_params": dict(getattr(request, "query_params", {}) or {}),
                        "path_params": dict(getattr(request, "path_params", {}) or {}),
                        "url": str(getattr(request, "url", "")),
                        "method": getattr(request, "method", None),
                    }
                    headers_lower = {k.lower(): v for k, v in (request.headers or {}).items()}
                    ip_address = headers_lower.get("x-forwarded-for") or headers_lower.get("x-real-ip")
        except Exception:
            pass

        # Extract client info if present (best-effort)
        client_id = None
        client_name = None
        client_version = None
        try:
            request_context = getattr(context, "request_context", None)
            if request_context:
                session = getattr(request_context, "session", None)
                if session:
                    client_params = getattr(session, "client_params", None)
                    if client_params:
                        client_info = getattr(client_params, "clientInfo", None)
                        if client_info:
                            client_id = getattr(client_info, "id", None)
                            client_name = getattr(client_info, "name", None)
                            client_version = getattr(client_info, "version", None)
        except Exception:
            pass

        # Error info
        error_value = getattr(context, "error", None)
        is_error = bool(error_value) if error_value is not None else None

        # SDK/package versions
        try:
            mcp_trace_version = metadata.version("mcp-trace")
        except Exception:
            mcp_trace_version = None

        # Identify user if identify function is provided
        user_id = None
        user_name = None
        user_email = None
        
        if self.identifyUser:
            try:
                user_info = self.identifyUser(context)
                # Support async identify functions
                if inspect.isawaitable(user_info):
                    user_info = await user_info
                if user_info and isinstance(user_info, dict):
                    user_id = user_info.get("user_id")
                    user_name = user_info.get("user_name")
                    user_email = user_info.get("user_email")
            except Exception as e:
                # Silently fail identification - don't break tracing
                pass

        # Build TraceData compatible dict
        trace_data = {
            "type": getattr(context, "type", None),
            "method": getattr(context, "method", None),
            "entity_name": (extra or {}).get("entity_name"),
            "request": (extra or {}).get("request", request_obj),
            "response": (extra or {}).get("response"),

            "timestamp": getattr(context, "timestamp", datetime.now(timezone.utc)).isoformat(),
            "duration": duration,

            "id": str(uuid.uuid4()),
            "session_id": session_id,

            "user_id": user_id,
            "user_name": user_name,
            "user_email": user_email,

            "client_id": client_id,
            "client_name": client_name,
            "client_version": client_version,

            "server_id": None,
            "server_name": None,
            "server_version": None,

            "is_error": is_error,
            "error": error_value,

            "ip_address": ip_address,

            "context": None,
            "sdk_language": "python",
            "sdk_version": None,
            "mcp_trace_version": mcp_trace_version,

            "metadata": (extra or {}).get("metadata"),
        }

        if extra:
            # Allow any additional fields supplied in extra to override defaults
            trace_data.update({k: v for k, v in extra.items() if v is not None})

        # Apply redaction if provided
        if self.redact:
            trace_data = self.redact(trace_data)

        if self.adapter:
            self.adapter.export(trace_data)
        else:
            print(f"Trace: {trace_data}")
        return trace_data

    async def on_notification(self, context: Any, call_next: Any) -> Any:
        start_time = time.time()
        result = await call_next()
        end_time = time.time()
        await self.build_trace_data(context, start_time=start_time, end_time=end_time)
        return result

    async def on_call_tool(self, context: Any, call_next: Any) -> Any:
        start_time = time.time()
        result = await call_next()
        end_time = time.time()
        extra = {}
        msg = getattr(context, "message", None)
        if msg is not None:
            if hasattr(msg, "name"):
                extra["entity_name"] = getattr(msg, "name", None)
            if hasattr(msg, "arguments"):
                extra["request"] = getattr(msg, "arguments", None)
        if result is not None:
            extracted = self._extract_structured_response(result) or self._extract_text_response(result)
            if extracted is None:
                # Fallback: serialize the result directly
                try:
                    import json
                    if hasattr(result, 'model_dump'):
                        extracted = result.model_dump()
                    elif hasattr(result, 'dict'):
                        extracted = result.dict()
                    elif isinstance(result, (dict, list, str, int, float, bool, type(None))):
                        extracted = result
                    else:
                        extracted = str(result)
                except Exception:
                    extracted = str(result)
            extra["response"] = extracted 
        await self.build_trace_data(context, extra=extra, start_time=start_time, end_time=end_time)
        return result

    async def on_read_resource(self, context: Any, call_next: Any) -> Any:
        start_time = time.time()
        result = await call_next()
        end_time = time.time()
        
        extra = {}
        msg = getattr(context, "message", None)
        if msg is not None:
            if hasattr(msg, "name"):
                extra["entity_name"] = getattr(msg, "name", None)
            if hasattr(msg, "arguments"):
                extra["request"] = getattr(msg, "arguments", None)
        await self.build_trace_data(context, extra=extra, start_time=start_time, end_time=end_time)
        return result

    async def on_get_prompt(self, context: Any, call_next: Any) -> Any:
        start_time = time.time()
        result = await call_next()
        end_time = time.time()
        
        extra = {}
        msg = getattr(context, "message", None)
        if msg is not None:
            if hasattr(msg, "name"):
                extra["entity_name"] = getattr(msg, "name", None)
            if hasattr(msg, "arguments"):
                extra["request"] = getattr(msg, "arguments", None)
        extracted = self._extract_structured_response(result) or self._extract_text_response(result)
        if extracted is None:
            # Fallback: serialize the result directly
            try:
                import json
                if hasattr(result, 'model_dump'):
                    extracted = result.model_dump()
                elif hasattr(result, 'dict'):
                    extracted = result.dict()
                elif isinstance(result, (dict, list, str, int, float, bool, type(None))):
                    extracted = result
                else:
                    extracted = str(result)
            except Exception:
                extracted = str(result)
        extra["response"] = extracted
        await self.build_trace_data(context, extra=extra, start_time=start_time, end_time=end_time)
        return result

    async def on_list_tools(self, context: Any, call_next: Any) -> Any:
        start_time = time.time()
        result = await call_next()
        end_time = time.time()
        extra = {}
        extracted = self._extract_structured_response(result) or self._extract_text_response(result)
        if extracted is None:
            # Fallback: serialize the result directly
            try:
                import json
                if hasattr(result, 'model_dump'):
                    extracted = result.model_dump()
                elif hasattr(result, 'dict'):
                    extracted = result.dict()
                elif isinstance(result, (dict, list, str, int, float, bool, type(None))):
                    extracted = result
                else:
                    extracted = str(result)
            except Exception:
                extracted = str(result)
        extra["response"] = extracted
        await self.build_trace_data(context, extra=extra, start_time=start_time, end_time=end_time)
        return result

    async def on_list_resources(self, context: Any, call_next: Any) -> Any:
        start_time = time.time()
        result = await call_next()
        end_time = time.time()
        extra = {}
        extracted = self._extract_structured_response(result) or self._extract_text_response(result)
        if extracted is None:
            # Fallback: serialize the result directly
            try:
                import json
                if hasattr(result, 'model_dump'):
                    extracted = result.model_dump()
                elif hasattr(result, 'dict'):
                    extracted = result.dict()
                elif isinstance(result, (dict, list, str, int, float, bool, type(None))):
                    extracted = result
                else:
                    extracted = str(result)
            except Exception:
                extracted = str(result)
        extra["response"] = extracted
        await self.build_trace_data(context, extra=extra, start_time=start_time, end_time=end_time)
        return result

    async def on_list_resource_templates(self, context: Any, call_next: Any) -> Any:
        start_time = time.time()
        result = await call_next()
        end_time = time.time()
        extra = {}
        extracted = self._extract_structured_response(result) or self._extract_text_response(result)
        if extracted is None:
            # Fallback: serialize the result directly
            try:
                import json
                if hasattr(result, 'model_dump'):
                    extracted = result.model_dump()
                elif hasattr(result, 'dict'):
                    extracted = result.dict()
                elif isinstance(result, (dict, list, str, int, float, bool, type(None))):
                    extracted = result
                else:
                    extracted = str(result)
            except Exception:
                extracted = str(result)
        extra["response"] = extracted
        await self.build_trace_data(context, extra=extra, start_time=start_time, end_time=end_time)
        return result

    async def on_list_prompts(self, context: Any, call_next: Any) -> Any:
        start_time = time.time()
        result = await call_next()
        end_time = time.time()
        extra = {}
        extracted = self._extract_structured_response(result) or self._extract_text_response(result)
        if extracted is None:
            # Fallback: serialize the result directly
            try:
                import json
                if hasattr(result, 'model_dump'):
                    extracted = result.model_dump()
                elif hasattr(result, 'dict'):
                    extracted = result.dict()
                elif isinstance(result, (dict, list, str, int, float, bool, type(None))):
                    extracted = result
                else:
                    extracted = str(result)
            except Exception:
                extracted = str(result)
        extra["response"] = extracted 
        await self.build_trace_data(context, extra=extra, start_time=start_time, end_time=end_time)
        return result

 