import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4
from datetime import datetime
from backend.domain.models import FollowUpEntity, EntityStatus, SourceType, Channel, Priority, ActionMode
from backend.infrastructure.scheduler import Scheduler

@pytest.fixture
def mock_repo():
    repo = MagicMock()
    # Create an entity that is currently "sent"
    entity = FollowUpEntity(
        id=uuid4(),
        workspace_id="test_ws",
        created_by_user_id="user1",
        source_type=SourceType.email,
        source_ref="thread_456",
        target_contact="test@example.com",
        ask_summary="Check status",
        due_at=datetime.utcnow(),
        status=EntityStatus.sent,
        priority=Priority.medium,
        channel=Channel.email,
        mode=ActionMode.auto_send,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        last_sent_at=datetime.utcnow()
    )
    repo.get_by_status.return_value = [entity]
    return repo

@patch('backend.infrastructure.reply_detector.check_for_reply')
@patch('backend.infrastructure.graph.orchestrator.invoke')
def test_scheduler_pauses_on_ooo(mock_invoke, mock_check, mock_repo):
    mock_check.return_value = {"reply_detected": True, "reply_type": "ooo"}
    
    scheduler = Scheduler(repo=mock_repo)
    scheduler.tick()
    
    # Entity should be paused
    entity = mock_repo.save_follow_up.call_args[0][0]
    assert entity.status == EntityStatus.paused
    # Orchestrator should not be called
    mock_invoke.assert_not_called()

@patch('backend.infrastructure.reply_detector.check_for_reply')
@patch('backend.infrastructure.graph.orchestrator.invoke')
def test_scheduler_closes_on_normal_reply(mock_invoke, mock_check, mock_repo):
    mock_check.return_value = {"reply_detected": True, "reply_type": "normal"}
    
    scheduler = Scheduler(repo=mock_repo)
    scheduler.tick()
    
    # Entity should be closed
    entity = mock_repo.save_follow_up.call_args[0][0]
    assert entity.status == EntityStatus.closed
    # Orchestrator should not be called
    mock_invoke.assert_not_called()

@patch('backend.infrastructure.reply_detector.check_for_reply')
@patch('backend.infrastructure.graph.orchestrator.invoke')
def test_scheduler_proceeds_if_no_reply(mock_invoke, mock_check, mock_repo):
    mock_check.return_value = {"reply_detected": False, "reply_type": "normal"}
    mock_invoke.return_value = {"entity": mock_repo.get_by_status()[0]}
    
    scheduler = Scheduler(repo=mock_repo)
    scheduler.tick()
    
    # Orchestrator SHOULD be called since no reply was detected
    mock_invoke.assert_called_once()
