"""Shared notification provider interface for inbox alerts."""

from abc import ABC, abstractmethod


class NotificationProvider(ABC):
    """
    Base class for outbound notification channels.

    Future providers (Slack, WhatsApp, Email) should implement ``send``
    and return True on success / False on soft failure.
    """

    name: str = "base"

    @abstractmethod
    def send(self, message: str) -> bool:
        """Deliver ``message``. Must not raise for expected config/network failures."""
