import operator
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from datetime import datetime, timedelta

from domain.models import FollowUpEntity, EntityStatus, ActionMode
from domain.state_machine import transition_state
from infrastructure.pgvector_ctx import PgVectorContextRepository
from infrastructure.gemini_llm import GeminiDraftingClient
from domain.skills.draft_generation import DraftGenerationSkill
from infrastructure.executors import EmailExecutorGateway, SlackExecutorGateway

class GraphState(TypedDict, total=False):
    entity: FollowUpEntity
    thread_summary: Optional[str]
    context_bundle: Optional[dict]
    route_action: str
    log_reason: Optional[str]
    log_payload: Optional[dict]

def check_due(state: GraphState):
    print(f"👉 LangGraph Node executing: check_due for {state['entity'].status}")
    entity = state["entity"]
    now = datetime.utcnow()
    action = "end"
    log_reason = state.get("log_reason")
    
    is_initial_due = (entity.status == EntityStatus.waiting and entity.due_at and entity.due_at.replace(tzinfo=None) <= now)
    is_followup_due = (entity.status in [EntityStatus.sent, EntityStatus.followed_up_1] and entity.next_follow_up_at and entity.next_follow_up_at.replace(tzinfo=None) <= now)
    
    if is_initial_due or is_followup_due:
        if not (entity.attempts_count >= 2 and entity.status == EntityStatus.followed_up_2):
            action = "get_context"
    elif entity.status == EntityStatus.awaiting_approval:
        action = "finalize_attempt"
    elif entity.status == EntityStatus.followed_up_2 and entity.next_follow_up_at and entity.next_follow_up_at.replace(tzinfo=None) <= now:
        action = "end"
        entity = transition_state(entity, EntityStatus.escalated)
        entity.next_follow_up_at = None
        log_reason = "Escalated after max attempts"
        
    return {"route_action": action, "entity": entity, "log_reason": log_reason}

def get_context(state: GraphState):
    entity = state["entity"]
    from .context_builder import get_context_bundle
    bundle = get_context_bundle(entity.id)
    return {"context_bundle": bundle}

def generate_draft(state: GraphState):
    entity = state["entity"]
    bundle = state.get("context_bundle", {})
    
    if entity.status in [EntityStatus.sent, EntityStatus.followed_up_1]:
        entity.attempts_count += 1
        
    thread_summary = bundle.get("thread_summary", "")
    # Approximate tokens (1 token ≈ 4 characters)
    thread_tokens = len(thread_summary) // 4
    if thread_tokens >= 6000:
        from .pgvector_ctx import PgVectorContextRepository
        search_result = PgVectorContextRepository.retrieve_thread_summary(
            source_ref=entity.source_ref,
            ask_summary=entity.ask_summary
        )
        bundle["thread_summary"] = search_result
        
    import json
    bundle_str = json.dumps(bundle, indent=2)
    prompt = DraftGenerationSkill.generate_draft_prompt(entity, bundle_str)
    draft_text = GeminiDraftingClient.generate_draft(prompt)
    
    entity = transition_state(entity, EntityStatus.draft_ready)
    entity.current_draft = draft_text
    
    return {"entity": entity, "log_reason": f"Draft generated (Attempt {entity.attempts_count})", "log_payload": {"draft": draft_text}}

def wait_for_approval(state: GraphState):
    entity = state["entity"]
    
    if entity.mode == ActionMode.auto_send:
        entity = transition_state(entity, EntityStatus.awaiting_approval)
        return {"entity": entity, "log_reason": f"Draft auto-approved by Mode C policy (Attempt {entity.attempts_count})", "log_payload": {"draft": entity.current_draft}}
    elif entity.mode == ActionMode.approval_required:
        return {"entity": entity, "log_reason": "Mode A policy: Draft requires manual approval. Pausing flow.", "log_payload": {"draft": entity.current_draft}}
    elif entity.mode == ActionMode.draft_only:
        return {"entity": entity, "log_reason": "Mode B policy: Draft generated for reference only. Pausing flow.", "log_payload": {"draft": entity.current_draft}}
        
    return {"entity": entity}

def finalize_attempt(state: GraphState):
    entity = state["entity"]
    send_text = entity.current_draft if entity.current_draft else f"Falling back to original ask: {entity.ask_summary}"
    
    if entity.channel.value == 'slack':
        execution_request = SlackExecutorGateway.send(entity, send_text)
    else:
        execution_request = EmailExecutorGateway.send(entity, send_text)
        
    if entity.attempts_count == 0:
        entity = transition_state(entity, EntityStatus.sent)
    elif entity.attempts_count == 1:
        entity = transition_state(entity, EntityStatus.followed_up_1)
    elif entity.attempts_count >= 2:
        entity = transition_state(entity, EntityStatus.followed_up_2)
        
    entity.last_sent_at = datetime.utcnow()
    return {"entity": entity, "log_payload": {"execution_request": execution_request}}

def schedule_next(state: GraphState):
    entity = state["entity"]
    entity.next_follow_up_at = datetime.utcnow() + timedelta(days=2) # Set next threshold to 2 days
    
    # Must preserve the log_payload generated by finalize_attempt so the scheduler writes it to the DB
    current_payload = state.get("log_payload", {})
    return {"entity": entity, "log_reason": f"Draft approved and successfully emitted execution_request (Status: {entity.status.value})", "log_payload": current_payload}

def route_after_check(state: GraphState):
    action = state.get("route_action")
    if action == "get_context":
        return "get_context"
    elif action == "finalize_attempt":
        return "finalize_attempt"
    else:
        return "end"

builder = StateGraph(GraphState)
builder.add_node("check_due", check_due)
builder.add_node("get_context", get_context)
builder.add_node("generate_draft", generate_draft)
builder.add_node("wait_for_approval", wait_for_approval)
builder.add_node("finalize_attempt", finalize_attempt)
builder.add_node("schedule_next", schedule_next)

builder.set_entry_point("check_due")
builder.add_conditional_edges("check_due", route_after_check, {
    "get_context": "get_context",
    "finalize_attempt": "finalize_attempt",
    "end": END
})
builder.add_edge("get_context", "generate_draft")
builder.add_edge("generate_draft", "wait_for_approval")
builder.add_edge("wait_for_approval", END)
builder.add_edge("finalize_attempt", "schedule_next")
builder.add_edge("schedule_next", END)

orchestrator = builder.compile()
