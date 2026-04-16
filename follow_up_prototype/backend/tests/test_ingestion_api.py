import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.api.main import app

client = TestClient(app)

@patch('backend.api.controllers.ingestion.GeminiDraftingClient.summarize_thread')
@patch('backend.api.controllers.ingestion.PgVectorContextRepository.store_document')
def test_ingest_thread_success(mock_store_document, mock_summarize_thread):
    # Arrange: Mock the DB and LLM tools
    mock_summarize_thread.return_value = "Mocked summary of the discussion."
    
    payload = {
        "thread_id": "target_thread_999",
        "messages": [
            {"author": "Alice", "text": "Can we schedule a call?"},
            {"author": "Bob", "text": "Yes, tomorrow at 10 AM works."}
        ]
    }
    
    # Act: Hit the ingestion endpoint
    response = client.post("/ingest/thread", json=payload)
    
    # Assert Http code and payload
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["thread_id"] == "target_thread_999"
    assert data["messages_stored"] == 2
    
    # Assert Internal Triggers
    mock_summarize_thread.assert_called_once()
    
    # Should store precisely 3 vectors (1 summary + 2 separate messages)
    assert mock_store_document.call_count == 3
    
    # Constraint Check: Guarantee that EVERY database write was strictly scoped to 'target_thread_999'
    for call in mock_store_document.call_args_list:
        args, kwargs = call
        assert args[0] == "target_thread_999"


def test_ingest_thread_missing_data():
    # Arrange invalid payload (missing messages array)
    invalid_payload = {
        "thread_id": "target_thread_999"
    }
    
    # Act
    response = client.post("/ingest/thread", json=invalid_payload)
    
    # Assert Pydantic kicks in and rejects the missing schema automatically
    assert response.status_code == 422 
