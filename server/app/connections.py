"""In-memory WebSocket connection registry + broadcasting.

Connections are tracked in a simple dict keyed by ``review_id``. All mutations
of the dict happen on the event loop thread (via the async methods), so no lock
is needed. Background threads (e.g. the review pipeline) broadcast through
``broadcast_threadsafe``, which hops back onto the captured event loop.
"""
import asyncio
import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        # review_id -> set of active WebSocket connections
        self._connections: dict[int, set[WebSocket]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Remember the app's event loop so threads can broadcast onto it."""
        self._loop = loop

    async def connect(self, review_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(review_id, set()).add(websocket)
        if self._loop is None:
            self._loop = asyncio.get_running_loop()

    def disconnect(self, review_id: int, websocket: WebSocket) -> None:
        connections = self._connections.get(review_id)
        if connections is None:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(review_id, None)

    async def broadcast(self, review_id: int, message: dict) -> None:
        """Send ``message`` (as JSON) to every client subscribed to review_id."""
        connections = list(self._connections.get(review_id, set()))
        if not connections:
            return
        text = json.dumps(message)
        dead: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_text(text)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(review_id, websocket)

    def broadcast_threadsafe(self, review_id: int, message: dict) -> None:
        """Broadcast from outside the event loop (e.g. a background thread)."""
        if self._loop is None:
            logger.warning(
                "No event loop registered; dropping broadcast for review %s",
                review_id,
            )
            return
        future = asyncio.run_coroutine_threadsafe(
            self.broadcast(review_id, message), self._loop
        )

        def _log_result(fut: "asyncio.Future") -> None:
            error = fut.exception()
            if error is not None:
                logger.error("Broadcast for review %s failed: %r", review_id, error)

        future.add_done_callback(_log_result)


# Process-wide singleton.
manager = ConnectionManager()
