import logging
from abc import ABC, abstractmethod
from domain.models import FollowUpEntity

logger = logging.getLogger(__name__)


class BaseExecutor(ABC):
    """
    Abstract base that handles shared payload construction and logging.
    Subclasses override only platform-specific fields.
    """

    def __init__(self, entity: FollowUpEntity, content: str):
        self.entity = entity
        self.content = content

    @abstractmethod
    def _channel_label(self) -> str:
        """Return the platform name used in log messages."""

    @abstractmethod
    def _extra_fields(self) -> dict:
        """Return any platform-specific extra fields to merge into the payload."""

    def execute(self) -> dict:
        logger.info(
            f"Emitting execution_request for {self._channel_label().upper()} "
            f"to {self.entity.target_contact} for follow-up {self.entity.id}"
        )
        payload = {
            "draft_body": self.content,
            "target_contact": self.entity.target_contact,
            "channel": self.entity.channel.value,
            "metadata": {
                "follow_up_id": str(self.entity.id),
                "source_ref": self.entity.source_ref,
                "priority": self.entity.priority.value,
            },
        }
        payload.update(self._extra_fields())
        return payload


class EmailExecutor(BaseExecutor):
    def _channel_label(self) -> str:
        return "email"

    def _extra_fields(self) -> dict:
        # Email-specific: include subject hint derived from the ask summary
        return {
            "subject_hint": f"Follow-up: {self.entity.ask_summary[:60]}"
        }


class SlackExecutor(BaseExecutor):
    def _channel_label(self) -> str:
        return "slack"

    def _extra_fields(self) -> dict:
        # Slack-specific: include a formatted mention block
        return {
            "mention": f"Reminder for {self.entity.target_contact}"
        }


# ── Backward-compatible gateway shims ──────────────────────────────────────
# graph.py calls EmailExecutorGateway.send() and SlackExecutorGateway.send().
# These shims preserve that interface exactly — no caller changes needed.

class EmailExecutorGateway:
    @staticmethod
    def send(entity: FollowUpEntity, content: str) -> dict:
        return EmailExecutor(entity, content).execute()


class SlackExecutorGateway:
    @staticmethod
    def send(entity: FollowUpEntity, content: str) -> dict:
        return SlackExecutor(entity, content).execute()
