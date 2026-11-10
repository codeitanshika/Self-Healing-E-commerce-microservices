import asyncio

from orchestrator.event_bus import bus


def test_publish_reaches_every_subscriber():
    seen = []

    async def a(p):
        seen.append(("a", p["x"]))

    async def b(p):
        seen.append(("b", p["x"]))

    bus.subscribe("T", a)
    bus.subscribe("T", b)
    asyncio.run(bus.publish("T", {"x": 1}))
    assert sorted(seen) == [("a", 1), ("b", 1)]


def test_publish_without_subscribers_is_a_noop():
    asyncio.run(bus.publish("NOBODY", {"service": "x"}))  # must not raise


def test_payload_is_stamped_and_logged():
    payload = {"service": "cart"}
    asyncio.run(bus.publish("T", payload))
    assert payload["_topic"] == "T"
    assert "_published_at" in payload
    assert bus.get_recent_events(1)[0]["topic"] == "T"


def test_event_log_is_bounded():
    for i in range(bus._max_log_size + 25):
        asyncio.run(bus.publish("T", {"i": i}))
    assert len(bus._event_log) == bus._max_log_size
    assert bus.get_recent_events(1)[0]["payload"]["i"] == bus._max_log_size + 24


def test_subscriber_count():
    async def h(p):
        pass

    bus.subscribe("A", h)
    bus.subscribe("A", h)
    assert bus.get_subscriber_count() == {"A": 2}
