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


def test_wildcard_observer_sees_all_topics_and_cannot_break_pipeline():
    seen = []

    async def observer(topic, payload):
        seen.append(topic)

    async def bad_observer(topic, payload):
        raise RuntimeError("boom")

    delivered = []

    async def real(p):
        delivered.append(p["x"])

    bus.subscribe("A", real)
    bus.subscribe_all(bad_observer)
    bus.subscribe_all(observer)
    asyncio.run(bus.publish("A", {"x": 1}))
    asyncio.run(bus.publish("B", {"x": 2}))
    assert seen == ["A", "B"]
    assert delivered == [1]
    bus.unsubscribe_all(observer)
    bus.unsubscribe_all(bad_observer)
