"""Shim — websocket routes live in morse.routing."""

from morse.routing import websocket_urlpatterns  # noqa: F401

__all__ = ["websocket_urlpatterns"]
