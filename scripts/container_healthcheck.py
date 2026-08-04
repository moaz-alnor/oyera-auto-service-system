"""Check OYERA liveness from inside its application container."""

from __future__ import annotations

import http.client
import os
import sys


def main() -> int:
    """Return zero only when the liveness endpoint is healthy."""
    host = os.environ.get(
        "DJANGO_HEALTHCHECK_HOST",
        "",
    ).strip()

    if not host:
        allowed_hosts = os.environ.get(
            "DJANGO_ALLOWED_HOSTS",
            "",
        )
        host = allowed_hosts.split(",", maxsplit=1)[0].strip()

    if not host:
        print(
            "DJANGO_HEALTHCHECK_HOST or DJANGO_ALLOWED_HOSTS is required.",
            file=sys.stderr,
        )
        return 1

    connection = http.client.HTTPConnection(
        "127.0.0.1",
        8000,
        timeout=5,
    )

    try:
        connection.request(
            "GET",
            "/health/live/",
            headers={
                "Host": host,
                "X-Forwarded-Proto": "https",
            },
        )
        response = connection.getresponse()
        response.read()
    except OSError as error:
        print(
            f"OYERA liveness request failed: {error}",
            file=sys.stderr,
        )
        return 1
    finally:
        connection.close()

    if response.status != 200:
        print(
            f"OYERA liveness returned unexpected status {response.status}.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
