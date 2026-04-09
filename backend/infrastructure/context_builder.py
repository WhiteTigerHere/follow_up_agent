import logging
from uuid import UUID
from infrastructure.supabase_repo import SupabaseRepository, supabase

logger = logging.getLogger(__name__)

def get_context_bundle(follow_up_id: UUID) -> dict:
    """
    Deterministically fetches structured context before RAG. 
    Does not use vector embeddings.
    """
    repo = SupabaseRepository()
    entity = repo.get_follow_up(follow_up_id)
    if not entity:
        logger.error(f"Cannot build context bundle: entity {follow_up_id} not found.")
        return {}
        
    # Lightweight summary generated from latest messages (scoped strictly to source_ref)
    # Relational lookup only, No RAG.
    try:
        response = supabase.table('document_embeddings').select('content').eq('source_ref', entity.source_ref).order('id', desc=True).limit(5).execute()
        raw_messages = [row['content'] for row in response.data] if response.data else []
        thread_summary = "\n\n".join(raw_messages) if raw_messages else "No pre-stored summary found."
    except Exception as e:
        logger.error(f"Error fetching lightweight thread summary: {e}")
        thread_summary = "Error retrieving thread history."
        
    bundle = {
        "ask_summary": entity.ask_summary,
        "target_contact": entity.target_contact,
        "attempt_number": entity.attempts_count,
        "last_sent_at": entity.last_sent_at.isoformat() if entity.last_sent_at else None,
        "thread_summary": thread_summary,
        "metadata": {
            "source_type": entity.source_type.value,
            "source_ref": entity.source_ref,
            "priority": entity.priority.value
        }
    }
    return bundle
