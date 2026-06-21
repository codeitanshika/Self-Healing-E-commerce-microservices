"""
test_retry.py
=============
TEMPORARY test script — proves the Orchestrator's retry loop works.

We don't want to wait for a real STILL_BROKEN to randomly happen,
so we directly call the Orchestrator's retry-handling method
with a fake STILL_BROKEN payload and watch it dispatch a retry.

Delete this file after you've confirmed the retry logic works —
it's a test tool, not part of the actual system.
"""

import asyncio
import time
import uuid

from orchestrator.orchestrator import Orchestrator
from orchestrator.event_bus import bus
from shared.events import FIX_REQUEST


async def main():
    orch = Orchestrator()

    # manually subscribe a "spy" to FIX_REQUEST so we can see what
    # fix the orchestrator chooses on retry
    async def spy(payload):
        print(f"\n👀 SPY saw FIX_REQUEST: {payload}")

    bus.subscribe(FIX_REQUEST, spy)

    # simulate an incident that already went through diagnosis
    incident_id = str(uuid.uuid4())[:8]
    orch.incident_cache[incident_id] = {
        "service": "cart",
        "fault_type": "slow",
        "detected_at": time.time(),
        "retry_count": 0,
        "root_cause": "cpu_overload",   # primary fix = reduce_load, retry fix = restart
        "fix_applied": "reduce_load",
    }

    print(f"--- Simulating incident {incident_id}: first fix FAILED (STILL_BROKEN) ---")
    await orch.on_validation_result({
        "service": "cart",
        "incident_id": incident_id,
        "result": "STILL_BROKEN",
        "mttr_seconds": 12.0,
    })

    print(f"\nretry_count is now: {orch.incident_cache[incident_id]['retry_count']}")

    print(f"\n--- Simulating incident {incident_id}: SECOND fix also FAILED ---")
    await orch.on_validation_result({
        "service": "cart",
        "incident_id": incident_id,
        "result": "STILL_BROKEN",
        "mttr_seconds": 25.0,
    })

    print(f"\nretry_count is now: {orch.incident_cache[incident_id]['retry_count']}")

    print(f"\n--- Simulating incident {incident_id}: THIRD failure → should ESCALATE ---")
    await orch.on_validation_result({
        "service": "cart",
        "incident_id": incident_id,
        "result": "STILL_BROKEN",
        "mttr_seconds": 40.0,
    })


if __name__ == "__main__":
    asyncio.run(main())