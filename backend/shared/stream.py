"""
stream.py
=========
Fan-out of event-bus traffic to browser clients over Server-Sent Events.

Each connected dashboard gets its own bounded asyncio.Queue. The hub is
registered on the bus as a wildcard *observer*, so streaming can never
slow down or break the healing pipeline: a slow client simply drops its
oldest messages.
"""
import asyncio
import json
import time
from collections import deque

from orchestrator.event_bus import bus

# Fields that are bulky or internal; the browser doesn't need them.
_DROP_KEYS = {"_topic", "_published_at"}
REPLAY_SIZE = 40
CLIENT_QUEUE_SIZE = 200


def _clean(payload: dict) -> dict:
    return {k: v for k, v in payload.items() if k not in _DROP_KEYS}


class StreamHub:
    def __init__(self):
        self._clients: set[asyncio.Queue] = set()
        self._recent: deque = deque(maxlen=REPLAY_SIZE)
        self._seq = 0

    @property
    def client_count(self) -> int:
        return len(self._clients)

    def attach(self):
        """Start observing the bus (idempotent)."""
        if self.observe not in bus._wildcard:
            bus.subscribe_all(self.observe)

    async def observe(self, topic: str, payload: dict):
        self._seq += 1
        message = {
            "seq": self._seq,
            "topic": topic,
            "service": payload.get("service", ""),
            "incident_id": payload.get("incident_id"),
            "ts": time.time(),
            "data": _clean(payload),
        }
        self._recent.append(message)
        for queue in list(self._clients):
            if queue.full():
                try:
                    queue.get_nowait()  # drop the oldest for slow clients
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(message)

    def recent(self, limit: int = REPLAY_SIZE) -> list[dict]:
        return list(self._recent)[-limit:]

    async def listen(self, heartbeat_seconds: float = 15.0):
        """Async generator yielding SSE-formatted strings for one client."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=CLIENT_QUEUE_SIZE)
        self._clients.add(queue)
        try:
            yield "retry: 3000\n\n"
            for message in self.recent():
                yield self.format(message)
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), heartbeat_seconds)
                    yield self.format(message)
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            self._clients.discard(queue)

    @staticmethod
    def format(message: dict) -> str:
        body = json.dumps(message, default=str)
        return f"id: {message['seq']}\nevent: pipeline\ndata: {body}\n\n"


hub = StreamHub()
