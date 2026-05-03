from unittest.mock import patch

from backend.infrastructure.cohere_llm import CohereDraftingClient


def test_generate_draft_uses_cohere_chat_payload():
    with patch("backend.infrastructure.cohere_llm._post_json") as mock_post:
        mock_post.return_value = {
            "message": {
                "content": [
                    {"type": "text", "text": "Hi,\n\nFollowing up.\n\nRegards,"}
                ]
            }
        }

        draft = CohereDraftingClient.generate_draft("Prompt text")

    assert draft == "Hi,\n\nFollowing up.\n\nRegards,"
    path, payload = mock_post.call_args[0]
    assert path == "/v2/chat"
    assert payload["messages"][0]["content"] == "Prompt text"


def test_embedding_is_normalized_to_pgvector_dimension():
    with patch("backend.infrastructure.cohere_llm._post_json") as mock_post:
        mock_post.return_value = {
            "embeddings": {
                "float": [[float(i) for i in range(1024)]]
            }
        }

        embedding = CohereDraftingClient.get_embedding("server upgrade", input_type="search_query")

    assert len(embedding) == 768
    assert embedding[0] == 0.0
    assert embedding[-1] == 767.0
    path, payload = mock_post.call_args[0]
    assert path == "/v2/embed"
    assert payload["input_type"] == "search_query"
    assert payload["output_dimension"] == 1024
