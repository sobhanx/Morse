"""Shim — Website models live in morse.models.

Legacy migration modules reference _generate_public_key / _generate_private_key
on this module; keep those callables importable.
"""

from morse.models.websites import (
    Website,
    WebsiteAgent,
    _generate_private_key,
    _generate_public_key,
)

__all__ = [
    "Website",
    "WebsiteAgent",
    "_generate_public_key",
    "_generate_private_key",
]
