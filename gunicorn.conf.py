"""Gunicorn configuration for OYERA production deployments."""

import os
from pathlib import Path

_port = os.environ.get("PORT", "8000")
bind = os.environ.get(
    "GUNICORN_BIND",
    f"0.0.0.0:{_port}",
)
chdir = str(Path(__file__).resolve().parent / "src")

worker_class = "gthread"
workers = int(os.environ.get("GUNICORN_WORKERS", "2"))
threads = int(os.environ.get("GUNICORN_THREADS", "2"))

timeout = int(os.environ.get("GUNICORN_TIMEOUT", "60"))
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", "5"))

max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", "100"))

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
capture_output = True

# Gunicorn 25.1+ creates a runtime control socket by default. OYERA disables
# it unless an operator explicitly enables and secures the interface.
control_socket_disable = (
    os.environ.get(
        "GUNICORN_ENABLE_CONTROL_SOCKET",
        "false",
    )
    .strip()
    .lower()
    != "true"
)
control_socket = os.environ.get(
    "GUNICORN_CONTROL_SOCKET",
    "/tmp/oyera-gunicorn.ctl",
)
control_socket_mode = 0o600

preload_app = False
