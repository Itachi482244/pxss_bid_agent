"""Pytest-wide setup.

Keeps the structured request/task access logs (emitted by the observability
middleware and ``observed_task``) out of the pytest output by defaulting the
log level to ``WARNING`` for the test session. This must run before
``app.core.config`` is imported anywhere, so it lives at module import time in
the root test conftest. Set ``LOG_LEVEL`` explicitly in the environment to
override (e.g. ``LOG_LEVEL=INFO`` when debugging a test).
"""

import os

os.environ.setdefault("LOG_LEVEL", "WARNING")
