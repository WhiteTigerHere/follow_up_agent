from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any
from uuid import UUID
from datetime import datetime

from domain.models import FollowUpRequest, FollowUpEntity, EntityStatus, FollowUpEvent
from domain.skills.creation import FollowUpCreationSkill
from domain.skills.approval import FollowUpApprovalSkill
from infrastructure.supabase_repo import SupabaseRepository
from api.dependencies import get_current_user

router = APIRouter(prefix="/followups", tags=["followups"])
repo = SupabaseRepository()

@router.post("/create", response_model=FollowUpEntity)
def create_followup(request: FollowUpRequest, current_user = Depends(get_current_user)):
    """
    Creates a new Follow-up Request.
    """
    try:
        request.requester_user_id = current_user.id
        entity = FollowUpCreationSkill.create_entity_from_request(request)
        
        # Transition from created to waiting so it becomes "pending" and active in the system
        from domain.state_machine import transition_state
        entity = transition_state(entity, EntityStatus.waiting)
        
        saved_entity = repo.save_follow_up(entity)
        return saved_entity
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create follow-up: {str(e)}")

@router.post("/{id}/approve", response_model=FollowUpEntity)
def approve_draft(id: UUID):
    """
    Approves a draft generated for a follow-up.
    """
    entity = repo.get_follow_up(id)
    if not entity:
        raise HTTPException(status_code=404, detail="Follow-up not found")
        
    try:
        updated_entity = FollowUpApprovalSkill.approve_draft(entity)
        return repo.save_follow_up(updated_entity)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{id}/close", response_model=FollowUpEntity)
def close_followup(id: UUID):
    """
    Manually closes a follow-up.
    """
    entity = repo.get_follow_up(id)
    if not entity:
        raise HTTPException(status_code=404, detail="Follow-up not found")
        
    updated_entity = FollowUpApprovalSkill.close_follow_up(entity)
    return repo.save_follow_up(updated_entity)

class ModifyDraftRequest(BaseModel):
    new_text: str

@router.post("/{id}/modify", response_model=FollowUpEntity)
def modify_draft(id: UUID, req: ModifyDraftRequest):
    """Modifies the draft text for a given follow up draft."""
    entity = repo.get_follow_up(id)
    if not entity or entity.status != EntityStatus.draft_ready:
        raise HTTPException(status_code=400, detail="Follow-up not found or not in draft_ready state")
        
    updated_entity = FollowUpApprovalSkill.modify_draft(entity, req.new_text)
    repo.save_follow_up(updated_entity)
    
    from uuid import uuid4
    repo.log_event(FollowUpEvent(
        id=uuid4(),
        follow_up_id=id,
        event_type="draft_modified",
        payload={"reason": "User manually edited draft", "channel": entity.channel.value},
        created_at=datetime.utcnow()
    ))
    return updated_entity

class RescheduleRequest(BaseModel):
    new_time: datetime

@router.post("/{id}/reschedule", response_model=FollowUpEntity)
def reschedule_followup(id: UUID, req: RescheduleRequest):
    """Reschedules the next follow_up_at time manually."""
    entity = repo.get_follow_up(id)
    if not entity:
        raise HTTPException(status_code=404, detail="Follow-up not found")
        
    entity.next_follow_up_at = req.new_time
    entity.updated_at = datetime.utcnow()
    repo.save_follow_up(entity)
    
    from uuid import uuid4
    repo.log_event(FollowUpEvent(
        id=uuid4(),
        follow_up_id=id,
        event_type="rescheduled",
        payload={"reason": f"User manually rescheduled to {req.new_time.isoformat()}"},
        created_at=datetime.utcnow()
    ))
    return entity

@router.post("/{id}/reject", response_model=FollowUpEntity)
def reject_draft(id: UUID):
    """Rejects a draft and resets the scheduler."""
    entity = repo.get_follow_up(id)
    if not entity or entity.status != EntityStatus.draft_ready:
        raise HTTPException(status_code=400, detail="Follow-up not found or not in draft_ready state")
        
    updated_entity = FollowUpApprovalSkill.reject_draft(entity)
    return repo.save_follow_up(updated_entity)

@router.get("/active", response_model=List[FollowUpEntity])
def get_active(current_user = Depends(get_current_user)):
    """Returns all follow-ups not closed and not escalated."""
    return repo.get_by_status([
        EntityStatus.created, EntityStatus.waiting, EntityStatus.draft_ready, 
        EntityStatus.awaiting_approval, EntityStatus.sent, 
        EntityStatus.followed_up_1, EntityStatus.followed_up_2
    ], user_id=current_user.id)

@router.get("/pending", response_model=List[FollowUpEntity])
def get_pending(current_user = Depends(get_current_user)):
    """Returns active, not yet sent but valid follow-ups (draft_ready, awaiting_approval, waiting)."""
    return repo.get_by_status([EntityStatus.waiting, EntityStatus.draft_ready, EntityStatus.awaiting_approval], user_id=current_user.id)

@router.get("/overdue", response_model=List[FollowUpEntity])
def get_overdue(current_user = Depends(get_current_user)):
    """Returns follow-ups that passed due_at and are still pending/active."""
    active = repo.get_by_status([EntityStatus.waiting, EntityStatus.draft_ready], user_id=current_user.id)
    now = datetime.utcnow()
    # Replace timezoneinfo to ensure proper comparison
    return [e for e in active if e.due_at.replace(tzinfo=None) < now]

@router.get("/report")
def get_report(current_user = Depends(get_current_user)):
    """Weekly/overall block report."""
    escalated = repo.get_by_status([EntityStatus.escalated], user_id=current_user.id)
    pending = repo.get_by_status([EntityStatus.waiting, EntityStatus.draft_ready, EntityStatus.awaiting_approval], user_id=current_user.id)
    
    return {
        "escalations": [e.model_dump(mode='json') for e in escalated],
        "blocking_you_summary": f"You have {len(pending)} pending items blocking your workflow."
    }

@router.post("/batch_overdue")
def batch_overdue():
    """Endpoint to trigger actions on overdue items (used conditionally by UI/Scheduler)."""
    return {"message": "Batch overdue process triggered"}

@router.get("/{id}/explain")
def explain_followup(id: UUID):
    """
    Explainability requirement. Exposes what is pending, who owes it, due date, why triggered, what happens next.
    """
    entity = repo.get_follow_up(id)
    if not entity:
        raise HTTPException(status_code=404, detail="Follow-up not found")
        
    events = repo.get_events_for_followup(id)
    sorted_events = sorted(events, key=lambda e: e.created_at)
    
    # Calculate reason_triggered safely from the most recent event logs
    reason_triggered = f"Source: {entity.source_type.value}, Reference: {entity.source_ref}"
    if sorted_events:
        latest_event = sorted_events[-1]
        payload = latest_event.payload
        if isinstance(payload, dict) and "reason" in payload:
            reason = payload["reason"]
            if "due_time_reached" in reason or "Draft generated" in reason:
                reason_triggered = "Draft was generated because due time was reached and no reply was received."
            elif "Escalated" in reason:
                reason_triggered = "Escalation happened because the maximum number of follow-up attempts was exhausted."
            elif "OOO" in reason:
                reason_triggered = "Follow-up was closed because an Out of Office reply was detected."
            elif "normal reply" in reason:
                reason_triggered = "Follow-up was closed because a normal reply was received."
            else:
                reason_triggered = reason
                
    # Calculate next_action based on status and action mode
    next_action = "Will transition to next appropriate state."
    if entity.status == EntityStatus.draft_ready:
        if entity.mode.value == "approval_required":
            next_action = "Waiting for user to manually approve or modify the draft before sending."
        elif entity.mode.value == "draft_only":
            next_action = "Draft is kept for reference only and will not be auto-sent."
        else: # auto_send
            next_action = "Draft is scheduled for auto-sending and will progress shortly."
    elif entity.status in [EntityStatus.waiting, EntityStatus.sent, EntityStatus.followed_up_1]:
        next_action = "Monitoring thread for replies and waiting for the next due time."
    elif entity.status == EntityStatus.awaiting_approval:
        next_action = "Draft is automatically progressing through the graph safely and will be sent shortly."
    elif entity.status in [EntityStatus.escalated, EntityStatus.closed]:
        next_action = "Terminal state. No further actions will be taken automatically."
    
    return {
        "what_is_pending": entity.ask_summary,
        "who_owes_it": entity.target_contact,
        "due_date": entity.due_at,
        "mode": entity.mode.value,
        "attempt_number": entity.attempts_count,
        "reason_triggered": reason_triggered,
        "status": entity.status.value,
        "next_action": next_action,
        "timeline": [e.model_dump(mode='json') for e in sorted_events]
    }
