"""Real-time Server-Sent Events (SSE) streaming broker for incident state and agent activities."""

import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from src.observability.logging import get_logger

logger = get_logger(__name__)


class EventBroker:
    """In-memory pub/sub broker distributing real-time SSE events to connected web clients."""

    def __init__(self, history_buffer_size: int = 50) -> None:
        self._subscribers: dict[str, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)
        self._history: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._history_buffer_size = history_buffer_size
        self._lock = asyncio.Lock()

    async def publish(
        self,
        incident_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """Publishes an event to all active subscribers of the given incident."""
        event_record = {
            "event": event_type,
            "data": payload,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        async with self._lock:
            # Store in history buffer
            hist = self._history[incident_id]
            hist.append(event_record)
            if len(hist) > self._history_buffer_size:
                hist.pop(0)

            # Broadcast to queues
            queues = self._subscribers[incident_id]
            for q in queues:
                await q.put(event_record)

        logger.debug(
            f"Published SSE event [{event_type}] for incident [{incident_id}] to {len(queues)} listener(s)"
        )

    async def subscribe(
        self,
        incident_id: str,
    ) -> AsyncGenerator[dict[str, str], None]:
        """Subscribes a client to the incident event stream, replaying recent history."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        async with self._lock:
            # Replay recent history
            for past_event in self._history.get(incident_id, []):
                await queue.put(past_event)
            self._subscribers[incident_id].append(queue)

        try:
            while True:
                record = await queue.get()
                yield {
                    "event": record["event"],
                    "data": json.dumps(record["data"]),
                }
                # Check for termination events
                if record["event"] in ["resolved", "failed", "escalated"]:
                    break
        finally:
            async with self._lock:
                if queue in self._subscribers[incident_id]:
                    self._subscribers[incident_id].remove(queue)
                if not self._subscribers[incident_id]:
                    self._subscribers.pop(incident_id, None)


# Global event broker singleton
default_event_broker = EventBroker()
