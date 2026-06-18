"""
event_bus.py
============
Our custom lightweight event bus — the heart of the multi-agent system.

This replaces Solace Agent Mesh with ~50 lines of Python.

HOW IT WORKS:
- Agents "subscribe" to a topic with a function (handler)
- When something "publishes" to that topic, ALL subscribed
  handlers are called automatically with the payload
- Handlers run concurrently (asyncio.gather) so no agent
  blocks another

EXAMPLE FLOW:
  Monitor Agent publishes ANOMALY_DETECTED
       → Orchestrator's handler wakes up automatically
       → Orchestrator publishes DIAGNOSE_REQUEST
       → Diagnosis Agent's handler wakes up automatically
       → ... and so on

Nobody calls anybody directly. They just shout into the bus
and whoever is listening reacts. This is "loose coupling" —
the Monitor Agent doesn't even know the Orchestrator exists.
"""

import asyncio
from collections import defaultdict
from datetime import datetime


class EventBus:
    """
    Async publish/subscribe event bus.
    One shared instance is used by the entire application.
    """

    def __init__(self):
        # topic -> list of async handler functions
        self._subscribers: dict[str, list] = defaultdict(list)

        # keep a log of recent events for debugging + dashboard
        self._event_log: list[dict] = []
        self._max_log_size = 100    # keep last 100 events in memory

    # ────────────────────────────────────────────────────────────
    # SUBSCRIBE
    # ────────────────────────────────────────────────────────────

    def subscribe(self, topic: str, handler):
        """
        Register a handler function for a topic.
        The handler MUST be an async function (async def).

        Called once at startup by each agent:
        bus.subscribe(ANOMALY_DETECTED, orchestrator.on_anomaly)
        """
        self._subscribers[topic].append(handler)
        print(f"[EventBus] subscribed: {handler.__name__} → {topic}")

    # ────────────────────────────────────────────────────────────
    # PUBLISH
    # ────────────────────────────────────────────────────────────

    async def publish(self, topic: str, payload: dict):
        """
        Publish an event to all subscribers of a topic.
        All handlers are called concurrently via asyncio.gather.

        If no one is subscribed to this topic, nothing happens
        (no error — events can be published before subscribers exist).
        """
        # Always add topic and timestamp to every payload
        payload["_topic"] = topic
        payload["_published_at"] = datetime.now().isoformat()

        # Log the event
        self._log_event(topic, payload)

        # Print so you can see events firing in the terminal
        print(f"[EventBus] 📢 {topic} → {payload.get('service', '')}")

        # Get all handlers for this topic
        handlers = self._subscribers.get(topic, [])

        if not handlers:
            print(f"[EventBus] ⚠️  No subscribers for {topic}")
            return

        # Call all handlers concurrently
        await asyncio.gather(*[handler(payload) for handler in handlers])

    # ────────────────────────────────────────────────────────────
    # EVENT LOG (for dashboard debugging)
    # ────────────────────────────────────────────────────────────

    def _log_event(self, topic: str, payload: dict):
        """Keep a rolling log of the last 100 events."""
        self._event_log.append({
            "topic":     topic,
            "service":   payload.get("service", ""),
            "timestamp": datetime.now().isoformat(),
            "payload":   payload,
        })
        # trim to max size
        if len(self._event_log) > self._max_log_size:
            self._event_log = self._event_log[-self._max_log_size:]

    def get_recent_events(self, limit: int = 20) -> list:
        """
        Returns the most recent events.
        The dashboard uses this for the debug panel.
        """
        return self._event_log[-limit:]

    def get_subscriber_count(self) -> dict:
        """
        Returns how many handlers are subscribed to each topic.
        Useful for debugging — if count is 0, nobody is listening.
        """
        return {topic: len(handlers)
                for topic, handlers in self._subscribers.items()}


# ── Single shared instance ───────────────────────────────────────
# Every agent imports THIS instance — they all share the same bus.
# This is the "singleton" pattern.
bus = EventBus()