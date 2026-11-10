import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GROQ_API_KEY", "test-key")

import pytest

from orchestrator.event_bus import bus


@pytest.fixture(autouse=True)
def clean_bus():
    """The bus is a process-wide singleton; isolate every test."""
    bus._subscribers.clear()
    bus._event_log.clear()
    yield
    bus._subscribers.clear()
    bus._event_log.clear()
