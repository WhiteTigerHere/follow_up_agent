import pytest
from unittest.mock import patch
from backend.infrastructure.graph import generate_draft
from backend.domain.models import FollowUpEntity, EntityStatus, Priority, SourceType, Channel, ActionMode
import uuid
from datetime import datetime

@pytest.fixture
def sample_entity():
    return FollowUpEntity(
        id=uuid.uuid4(),
        workspace_id="test_ws",
        created_by_user_id="user1",
        source_type=SourceType.email,
        source_ref="thread_123",
        target_contact="test@example.com",
        ask_summary="Check status",
        due_at=datetime.utcnow(),
        status=EntityStatus.waiting,
        priority=Priority.medium,
        channel=Channel.email,
        mode=ActionMode.auto_send,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

@patch('backend.infrastructure.graph.GeminiDraftingClient.generate_draft', return_value="Draft Text")
@patch('backend.infrastructure.graph.PgVectorContextRepository.retrieve_thread_summary', return_value="Vector Summary")
def test_generate_draft_short_context(mock_retrieve, mock_gemini, sample_entity):
    state = {
        "entity": sample_entity,
        "context_bundle": {
            "thread_summary": "Short context."
        }
    }
    
    result = generate_draft(state)
    
    print("\n\n--- Short Context RAG Flow ---")
    print(f"1. State Passed to LLM: {mock_gemini.call_args[0][0]}")
    print(f"2. Resulting Entity Status: {result['entity'].status}")
    print("------------------------------\n")
    
    assert result["entity"].status == EntityStatus.draft_ready
    mock_retrieve.assert_not_called()
    assert "Short context." in mock_gemini.call_args[0][0]

@patch('backend.infrastructure.graph.GeminiDraftingClient.generate_draft', return_value="Draft Text")
@patch('backend.infrastructure.graph.PgVectorContextRepository.retrieve_thread_summary', return_value="Vector Summary")
def test_generate_draft_long_context(mock_retrieve, mock_gemini, sample_entity):
    # 25,000 chars roughly = 6250 tokens
    long_summary = "A" * 25000
    state = {
        "entity": sample_entity,
        "context_bundle": {
            "thread_summary": long_summary
        }
    }
    
    result = generate_draft(state)
    
    print("\n\n--- Long Context RAG Flow ---")
    print(f"1. Context too long, retrieved fallback from PgVector")
    print(f"2. State Passed to LLM (First 300 chars): {mock_gemini.call_args[0][0][:300]}...\n")
    print(f"3. Resulting Entity Status: {result['entity'].status}")
    print("-----------------------------\n")

    assert result["entity"].status == EntityStatus.draft_ready
    mock_retrieve.assert_called_once_with(source_ref="thread_123", ask_summary="Check status")
    assert "Vector Summary" in mock_gemini.call_args[0][0]
