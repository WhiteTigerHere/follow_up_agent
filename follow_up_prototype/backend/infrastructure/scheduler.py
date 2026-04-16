import time
import logging
from domain.models import FollowUpEntity, EntityStatus, FollowUpEvent, ActionMode
from domain.state_machine import transition_state
from infrastructure.supabase_repo import SupabaseRepository
from uuid import uuid4
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class Scheduler:
    """
    Drives time-based transitions without LLMs.
    Runs on a 60-second tick in a separate process or thread.
    """
    def __init__(self, repo=SupabaseRepository):
        self.repo = repo
        
    def tick(self):
        """
        Executes one cycle of the scheduler.
        """
        logger.info("Scheduler tick started.")
        # Load active follow-ups. In a real system we'd limit by due_at < now() and status in (...)
        active_statuses = [
            EntityStatus.sent, 
            EntityStatus.followed_up_1, 
            EntityStatus.followed_up_2,
            EntityStatus.waiting,
            EntityStatus.awaiting_approval
        ]
        
        entities = self.repo.get_by_status(active_statuses)
        now = datetime.utcnow()
        
        from .graph import orchestrator
        from .reply_detector import check_for_reply

        for entity in entities:
            if entity.last_sent_at and entity.status in [EntityStatus.sent, EntityStatus.followed_up_1, EntityStatus.followed_up_2]:
                reply_info = check_for_reply(entity.source_ref, entity.last_sent_at)
                if reply_info.get("reply_detected"):
                    if reply_info.get("reply_type") == "ooo":
                        # OOO reply: close the loop rather than pausing (paused state removed)
                        entity = transition_state(entity, EntityStatus.closed)
                        self.save_and_log(entity, f"Closed follow-up due to OOO reply detected in thread: {entity.source_ref}")
                        continue
                    else:
                        entity = transition_state(entity, EntityStatus.closed)
                        self.save_and_log(entity, f"Closed follow-up due to normal reply detected in thread: {entity.source_ref}")
                        continue
            
            is_initial_due = (entity.status == EntityStatus.waiting and entity.due_at and entity.due_at.replace(tzinfo=None) <= now)
            is_followup_due = (entity.status in [EntityStatus.sent, EntityStatus.followed_up_1] and entity.next_follow_up_at and entity.next_follow_up_at.replace(tzinfo=None) <= now)
            
            if is_initial_due or is_followup_due:
                # Log explicitly as requested: { reason: "due_time_reached", action: "generate_draft" }
                self.save_and_log(entity, reason="due_time_reached", extra_payload={"action": "generate_draft"})
            
            initial_status = entity.status
            try:
                result = orchestrator.invoke({
                    "entity": entity,
                    "thread_summary": None,
                    "route_action": "none",
                    "log_reason": None,
                    "log_payload": None
                })
                
                final_entity = result["entity"]
                log_reason = result.get("log_reason")
                
                if log_reason:
                    self.save_and_log(final_entity, log_reason, result.get("log_payload"))
                elif initial_status != final_entity.status:
                    self.save_and_log(final_entity, f"State changed to {final_entity.status.value}")
                    
            except Exception as e:
                logger.error(f"Error orchestrating entity {entity.id}: {e}")

    def save_and_log(self, entity: FollowUpEntity, reason: str, extra_payload: dict = None):
        self.repo.save_follow_up(entity)
        payload = {"reason": reason, "channel": entity.channel.value}
        if extra_payload:
            payload.update(extra_payload)
            
        event = FollowUpEvent(
            id=uuid4(),
            follow_up_id=entity.id,
            event_type=f"transition_{entity.status.value}",
            payload=payload,
            created_at=datetime.utcnow()
        )
        self.repo.log_event(event)

    def run_continuously(self):
        while True:
            try:
                self.tick()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            time.sleep(60)
