import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GROQ_API_KEY", "test-key")

import pytest

from orchestrator.event_bus import bus


@pytest.fixture(autouse=True)
def clean_bus():
    """The bus is a process-wide singleton; isolate every test."""
    for _ in range(2):
        bus._subscribers.clear()
        bus._wildcard.clear()
        bus._event_log.clear()
        if _ == 0:
            yield


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _no_real_docker(monkeypatch):
    """Keep tests hermetic: never pick up a real container, even if Docker is running."""
    from services.docker_service import DockerService
    monkeypatch.setattr(DockerService, "is_available", lambda self: False)
