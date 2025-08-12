import threading
import queue
import requests
import time
import os
from typing import Optional, Dict
from .base import TraceAdapter


class ContexaTraceAdapter(TraceAdapter):
    """
    Trace adapter that buffers and sends trace data to Contexa in a background thread.
    Endpoint: https://api.contexaai.com/v1/trace/ingest

    Required headers:
      - X-API-KEY: from `api_key` or env `CONTEXA_API_KEY`
      - X-Server-ID: from `server_id` or env `CONTEXA_SERVER_ID`
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        server_id: Optional[str] = None,
        buffer_size: int = 1000,
        flush_interval: float = 1.0,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        daemon: bool = True,
    ):
        self.api_url = os.getenv("CONTEXA_API_URL", "https://api.contexaai.com/v1/trace/ingest")
        self.api_key = api_key or os.getenv("CONTEXA_API_KEY")
        self.server_id = server_id or os.getenv("CONTEXA_SERVER_ID")

        if not self.api_key:
            raise ValueError("Missing API key. Pass `api_key` or set CONTEXA_API_KEY env var.")
        if not self.server_id:
            raise ValueError("Missing server ID. Pass `server_id` or set CONTEXA_SERVER_ID env var.")

        self.headers = {
            "X-API-KEY": self.api_key,
            "X-Server-ID": self.server_id,
            "Content-Type": "application/json"
        }

        self.buffer = queue.Queue(maxsize=buffer_size)
        self.flush_interval = flush_interval
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._stop_event = threading.Event()

        self._worker = threading.Thread(target=self._worker_fn, daemon=daemon)
        self._worker.start()

    def export(self, trace_data: Dict):
        """Add a trace event to the buffer (non-blocking)."""
        try:
            self.buffer.put_nowait(trace_data)
        except queue.Full:
            print("[ContexaTraceAdapter] Buffer full — dropping event.")

    def _worker_fn(self):
        while not self._stop_event.is_set():
            try:
                event = self.buffer.get(timeout=self.flush_interval)
                self._send_event_with_retry(event)
                self.buffer.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[ContexaTraceAdapter] Worker thread error: {e}")

    def _send_event_with_retry(self, event: Dict):
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(self.api_url, json=event, headers=self.headers, timeout=5)
                if 200 <= response.status_code < 300:
                    return
                else:
                    print(f"[ContexaTraceAdapter] Server error ({response.status_code}): {response.text}")
            except requests.RequestException as e:
                print(f"[ContexaTraceAdapter] Send failed (attempt {attempt}): {e}")
            time.sleep(self.retry_delay)
        print("[ContexaTraceAdapter] Max retries reached — event dropped.")

    def flush(self, timeout: Optional[float] = None):
        """
        Block until all buffered events are sent or timeout is reached.
        """
        start_time = time.time()
        while not self.buffer.empty():
            if timeout and (time.time() - start_time) > timeout:
                print("[ContexaTraceAdapter] Flush timeout reached.")
                break
            time.sleep(0.1)

    def shutdown(self, wait: bool = True, timeout: Optional[float] = None):
        """
        Signal worker to stop and optionally wait for it.
        """
        self._stop_event.set()
        if wait:
            self._worker.join(timeout)
            if self._worker.is_alive():
                print("[ContexaTraceAdapter] Worker did not shut down cleanly.")
