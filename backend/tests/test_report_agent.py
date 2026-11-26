import asyncio

from agents.report_agent import ReportAgent
from orchestrator.event_bus import bus
from shared.events import VALIDATION_RESULT


def test_result_for_an_incident_cleared_by_reset_is_not_logged(monkeypatch):
    cache = {"live": {"fault_type": "crash", "timeline": []}}
    agent = ReportAgent(cache)
    logged = []
    monkeypatch.setattr(agent, "log_incident", lambda **row: logged.append(row["service"]) or 1)

    def result(incident_id, service):
        return {"incident_id": incident_id, "service": service, "result": "RECOVERED", "mttr_seconds": 2.0}

    async def go():
        await bus.publish(VALIDATION_RESULT, result("live", "cart"))
        cache.clear()                                    # what the demo reset does
        await bus.publish(VALIDATION_RESULT, result("live", "auth"))

    asyncio.run(go())
    assert logged == ["cart"]
