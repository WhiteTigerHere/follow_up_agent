from fastapi import APIRouter, HTTPException
from ...domain.models import IngestThreadRequest
from ...infrastructure.gemini_llm import GeminiDraftingClient
from ...infrastructure.pgvector_ctx import PgVectorContextRepository

router = APIRouter(prefix="/ingest", tags=["ingestion"])

@router.post("/thread")
def ingest_thread(request: IngestThreadRequest):
    try:
        if not request.messages:
            return {"status": "success", "thread_id": request.thread_id, "messages_stored": 0, "message": "No messages provided"}
            
        # 1. Convert messages to dicts for the LLM summarizer
        msg_dicts = [{"author": m.author, "text": m.text} for m in request.messages]
        
        # 2. Ask Gemini for an overall summary of the thread
        summary = GeminiDraftingClient.summarize_thread(msg_dicts)
        
        # 3. Store the overarching summary with pgvector, scoped to thread_id
        summary_text = f"THREAD SUMMARY:\n{summary}"
        PgVectorContextRepository.store_document(request.thread_id, summary_text)
        
        # 4. Store each individual message with pgvector, scoped to thread_id
        for m in request.messages:
            msg_text = f"Message from {m.author}:\n{m.text}"
            PgVectorContextRepository.store_document(request.thread_id, msg_text)
            
        return {"status": "success", "thread_id": request.thread_id, "messages_stored": len(request.messages)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
