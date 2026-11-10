import asyncio
import json

from orchestrator.event_bus import bus
from shared.stream import StreamHub


def test_hub_replays_and_streams_events():
    async def go():
        hub = StreamHub()
        hub.attach()
        await bus.publish("ANOMALY_DETECTED", {"service": "cart", "incident_id": "i1"})
        gen = hub.listen(heartbeat_seconds=0.05)
        first = await gen.__anext__()          # retry hint
        replay = await gen.__anext__()         # replayed event
        await bus.publish("FIX_APPLIED", {"service": "cart", "incident_id": "i1"})
        live = await gen.__anext__()
        beat = await gen.__anext__()           # nothing else -> heartbeat
        await gen.aclose()
        return first, replay, live, beat, hub

    first, replay, live, beat, hub = asyncio.run(go())
    assert first.startswith("retry:")
    assert json.loads(replay.split("data: ")[1])["topic"] == "ANOMALY_DETECTED"
    assert json.loads(live.split("data: ")[1])["topic"] == "FIX_APPLIED"
    assert beat.startswith(": heartbeat")
    assert hub.client_count == 0
    bus._wildcard.clear()
