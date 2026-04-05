import pytest
from uuid import uuid4
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.api.main import app
from backend.domain.models import FollowUpEntity, EntityStatus, SourceType, Channel, Priority, ActionMode, FollowUpEvent

client = TestClient(app)

def create_mock_entity(status, mode):
    return FollowUpEntity(
        id=uuid4(),
        workspace_id="ws_1",
        created_by_user_id="user_1",
        source_type=SourceType.email,
        source_ref="thread_1",
        target_contact="test@example.com",
        ask_summary="Discuss project",
        due_at=datetime.utcnow(),
        status=status,
        priority=Priority.low,
        channel=Channel.email,
        mode=mode,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        attempts_count=1
    )

def create_mock_event(reason_text):
    return FollowUpEvent(
        id=uuid4(),
        follow_up_id=uuid4(),
        event_type="test",
        payload={"reason": reason_text},
        created_at=datetime.utcnow()
    )

@patch('backend.api.controllers.followups.repo.get_events_for_followup')
@patch('backend.api.controllers.followups.repo.get_follow_up')
def test_explain_draft_generated(mock_get_follow_up, mock_get_events):
    mock_entity = create_mock_entity(EntityStatus.draft_ready, ActionMode.approval_required)
    mock_get_follow_up.return_value = mock_entity
    
    mock_get_events.return_value = [
        create_mock_event("due_time_reached for testing")
    ]
    
    response = client.get(f"/followups/{mock_entity.id}/explain")
    assert response.status_code == 200
    data = response.json()
    
    assert data["mode"] == "approval_required"
    assert data["attempt_number"] == 1
    assert "because due time was reached" in data["reason_triggered"]
    assert "Waiting for user to manually approve" in data["next_action"]


@patch('backend.api.controllers.followups.repo.get_events_for_followup')
@patch('backend.api.controllers.followups.repo.get_follow_up')
def test_explain_escalated(mock_get_follow_up, mock_get_events):
    mock_entity = create_mock_entity(EntityStatus.escalated, ActionMode.auto_send)
    mock_get_follow_up.return_value = mock_entity
    
    mock_get_events.return_value = [
        create_mock_event("Escalated after max attempts")
    ]
    
    response = client.get(f"/followups/{mock_entity.id}/explain")
    data = response.json()
    
    assert "Escalation happened because the maximum number" in data["reason_triggered"]
    assert "Terminal state." in data["next_action"]


@patch('backend.api.controllers.followups.repo.get_events_for_followup')
@patch('backend.api.controllers.followups.repo.get_follow_up')
def test_explain_paused_ooo(mock_get_follow_up, mock_get_events):
    mock_entity = create_mock_entity(EntityStatus.paused, ActionMode.auto_send)
    mock_get_follow_up.return_value = mock_entity
    
    mock_get_events.return_value = [
        create_mock_event("Paused follow-up due to OOO reply detected")
    ]
    
    response = client.get(f"/followups/{mock_entity.id}/explain")
    data = response.json()
    
    assert "Out of Office reply was detected" in data["reason_triggered"]
    assert "Paused. Requires manual intervention" in data["next_action"]
