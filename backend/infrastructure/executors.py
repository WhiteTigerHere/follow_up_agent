import logging
from ..domain.models import FollowUpEntity

logger = logging.getLogger(__name__)

class EmailExecutorGateway:
    @staticmethod
    def send(entity: FollowUpEntity, content: str) -> dict:
        """
        Emits an execution_request instead of sending.
        """
        logger.info(f"Emitting execution_request for EMAIL to {entity.target_contact} for follow-up {entity.id}")
        return {
            "draft_body": content,
            "target_contact": entity.target_contact,
            "channel": entity.channel.value,
            "metadata": {
                "follow_up_id": str(entity.id),
                "source_ref": entity.source_ref,
                "priority": entity.priority.value
            }
        }

class SlackExecutorGateway:
    @staticmethod
    def send(entity: FollowUpEntity, content: str) -> dict:
        """
        Emits an execution_request instead of sending.
        """
        logger.info(f"Emitting execution_request for SLACK to {entity.target_contact} for follow-up {entity.id}")
        return {
            "draft_body": content,
            "target_contact": entity.target_contact,
            "channel": entity.channel.value,
            "metadata": {
                "follow_up_id": str(entity.id),
                "source_ref": entity.source_ref,
                "priority": entity.priority.value
            }
        }
