"""
scenarios.py
============
Scripted multi-fault scenarios — the "chaos" side of the project.

Single faults prove the loop works; scenarios prove it holds up when several
things break at once (concurrent incidents) or when one failure drags others
down (cascades). Each step is (service, fault, delay_seconds_after_previous).

A "cascade" here is scripted, not an emergent dependency model: the upstream
fault is injected first and the downstream symptoms follow after a delay,
which is how an upstream outage typically shows up to the services behind it.
"""
import asyncio

SCENARIOS: dict[str, dict] = {
    "flash-sale": {
        "title": "Flash-sale surge",
        "blurb": "Payment crashes while cart slows and auth throws errors, all at once",
        "kind": "concurrent",
        "steps": [("payment", "crash", 0), ("cart", "slow", 0), ("auth", "error", 0)],
    },
    "slow-burn": {
        "title": "Slow burn",
        "blurb": "Inventory leaks memory as notification dies",
        "kind": "concurrent",
        "steps": [("inventory", "memory", 0), ("notification", "crash", 0)],
    },
    "checkout-cascade": {
        "title": "Checkout cascade",
        "blurb": "Auth crashes; cart then payment degrade as their login calls fail",
        "kind": "cascade",
        "steps": [("auth", "crash", 0), ("cart", "error", 3), ("payment", "error", 3)],
    },
    "everything-breaks": {
        "title": "Everything breaks",
        "blurb": "One fault in every service simultaneously: the worst case for the pipeline",
        "kind": "stress",
        "steps": [("auth", "crash", 0), ("cart", "slow", 0), ("payment", "error", 0),
                  ("inventory", "memory", 0), ("notification", "crash", 0)],
    },
}


def list_scenarios() -> list[dict]:
    return [
        {"id": sid, "title": s["title"], "blurb": s["blurb"], "kind": s["kind"],
         "steps": [{"service": sv, "fault": f, "delay": d} for sv, f, d in s["steps"]]}
        for sid, s in SCENARIOS.items()
    ]


def valid_steps(manager, scenario_id: str) -> list[tuple]:
    """Steps that target services actually registered right now."""
    return [st for st in SCENARIOS[scenario_id]["steps"] if st[0] in manager.services]


async def run_scenario(manager, scenario_id: str) -> list[dict]:
    """Inject every step (respecting delays). Returns the injection results."""
    if scenario_id not in SCENARIOS:
        raise KeyError(scenario_id)
    results = []
    for service, fault, delay in valid_steps(manager, scenario_id):
        if delay:
            await asyncio.sleep(delay)
        results.append(await asyncio.to_thread(manager.inject_fault, service, fault))
    return results
