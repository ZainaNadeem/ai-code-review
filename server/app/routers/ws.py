import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.connections import manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/reviews/{review_id}")
async def review_updates(websocket: WebSocket, review_id: int) -> None:
    """Subscribe a client to status updates for a single review.

    The connection is held open until the client disconnects; clients receive
    a JSON message when the review completes. Inbound messages are ignored.
    """
    await manager.connect(review_id, websocket)
    try:
        while True:
            # We don't expect client messages; this keeps the socket open and
            # surfaces the disconnect.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(review_id, websocket)
    except Exception:
        logger.exception("WebSocket error for review %s", review_id)
        manager.disconnect(review_id, websocket)
