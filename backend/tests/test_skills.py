from backend.domain.skills.creation import FollowUpCreationSkill
from backend.domain.skills.draft_generation import DraftGenerationSkill
from backend.domain.skills.reply_detection import ReplyDetectionSkill, ReplyClassification
from backend.domain.models import FollowUpRequest, Priority, FollowUpEntity, EntityStatus, SourceType, Channel, ActionMode
from uuid import uuid4
from datetime import datetime

def test_creation_routing():
    req = FollowUpRequest(
        workspace_id="ws_1",
        requester_user_id="usr_1",
        source_type="email",
        source_ref="ref1",
        target_persons=["user@example.com"],
        ask_summary="Check this",
        due_date_time="2026-01-01T00:00:00Z",
        urgency=Priority.high,
        action_mode="approval_required"
    )
    entity = FollowUpCreationSkill.create_entity_from_request(req)
    # email source -> email channel
    assert entity.channel.value == "email"
    assert entity.priority == Priority.high

def test_reply_detection():
    # OOO
    assert ReplyDetectionSkill.classify_reply("I am out of office until Monday.") == ReplyClassification.auto_reply
    # Irrelevant
    assert ReplyDetectionSkill.classify_reply("Click here to unsubscribe") == ReplyClassification.irrelevant_reply
    # Meaningful
    assert ReplyDetectionSkill.classify_reply("Yes, I will get this done today.") == ReplyClassification.meaningful_reply

def test_fallback_draft_uses_org_rag_policy():
    entity = FollowUpEntity(
        id=uuid4(),
        workspace_id="ws_1",
        created_by_user_id="usr_1",
        source_type=SourceType.email,
        source_ref="thread_123",
        target_contact="user2@example.com",
        ask_summary="Hey, can you confirm if the $6200 analytics server upgrade has been approved?",
        due_at=datetime.utcnow(),
        status=EntityStatus.waiting,
        priority=Priority.medium,
        channel=Channel.email,
        mode=ActionMode.approval_required,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    bundle = {
        "sender_name": "Aarushi",
        "org_context": [
            'Any financial escalation request exceeding $4,500 must include the phrase: "Delta-Secure-Approval-Needed"'
        ],
    }

    draft = DraftGenerationSkill.generate_fallback_draft(entity, bundle)

    assert "Delta-Secure-Approval-Needed" in draft
    assert "approval status" in draft
