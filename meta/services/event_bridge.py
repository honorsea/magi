"""
MAGI Meta Layer — Thread → Async Event Bridge.

SimPy runs in a background thread. This bridge lets that thread
push events into the asyncio event loop without blocking.
"""

import asyncio
import time
from typing import Any, Dict, Optional


class EventBridge:
    """
    Thread-safe bridge between a SimPy simulation thread and an asyncio queue.

    Usage (from simulation thread):
        bridge.emit("task_record", {"workstation": "CW", ...})

    Usage (from async code):
        async for event in bridge.stream():
            await websocket.send_json(event)
    """

    def __init__(self, sim_id: str, loop: asyncio.AbstractEventLoop):
        self.sim_id = sim_id
        self._loop = loop
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=2000)
        self._closed = False

    def emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Called from the simulation thread.
        Thread-safe: uses run_coroutine_threadsafe to push into the asyncio queue.
        Drops the event silently if the queue is full (prevents backpressure blocking the sim).
        """
        if self._closed:
            return
        envelope = {
            "type":      event_type,
            "sim_id":    self.sim_id,
            "data":      data,
            "timestamp": time.time(),
        }
        try:
            asyncio.run_coroutine_threadsafe(
                self._queue.put(envelope), self._loop
            ).result(timeout=0.05)  # 50ms timeout; drop if async loop is busy
        except Exception:
            pass  # Never block the simulation thread

    def close(self) -> None:
        """Signal that no more events will be emitted."""
        self._closed = True
        # Push a sentinel so any waiting consumer exits
        try:
            asyncio.run_coroutine_threadsafe(
                self._queue.put({"type": "_sentinel", "sim_id": self.sim_id}),
                self._loop,
            )
        except Exception:
            pass

    async def stream(self):
        """Async generator yielding events until the bridge is closed."""
        while True:
            event = await self._queue.get()
            if event.get("type") == "_sentinel":
                return
            yield event

    async def drain_to_list(self) -> list:
        """Drain all currently queued events without blocking."""
        events = []
        while not self._queue.empty():
            try:
                events.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return [e for e in events if e.get("type") != "_sentinel"]
