from ..models import FollowUpEntity
from ..privacy import redact_context_bundle, redact_text


class DraftGenerationSkill:

    @staticmethod
    def generate_draft_prompt(entity: FollowUpEntity, bundle: dict) -> str:
        """
        Generates the prompt sent to the LLM (Gemini) via a single string call.
        Note: [SYSTEM] is not a real instruction boundary in the Gemini SDK —
        it is inline text only. True system instruction separation would require
        passing system_instruction= to GenerativeModel().
        """
        redacted_bundle = redact_context_bundle(bundle)
        semantic_list = redacted_bundle.get("semantic_context", [])
        recent_list = redacted_bundle.get("recent_context", [])
        org_list = redacted_bundle.get("org_context", [])

        # context_builder already extracts row['content'] strings, so these are list[str].
        semantic_formatted = "\n".join(semantic_list) if semantic_list else "No semantic context found."
        recent_formatted = "\n".join(recent_list) if recent_list else "No recent messages found."

        org_section = ""
        if org_list:
            org_formatted = "\n".join(org_list)
            org_section = f"\n[COMPANY KNOWLEDGE]\n{org_formatted}\n"

        # attempts_count = number of COMPLETED sends at the time this prompt is built.
        # graph.py increments attempts_count BEFORE calling generate_draft_prompt,
        # but only when status is already 'sent' or 'followed_up_1' (i.e. not the initial send).
        # So the values seen here are:
        #   0 → initial message (nothing sent yet)
        #   1 → first follow-up (initial was sent, no reply)
        #   2 → second and final follow-up before escalation
        if entity.attempts_count == 0:
            attempt_context = "This is the initial message. Be professional and clear."
        elif entity.attempts_count == 1:
            attempt_context = "This is the FIRST follow-up. The recipient has not replied to the initial message."
        elif entity.attempts_count == 2:
            attempt_context = "This is the SECOND AND FINAL follow-up before escalation. Add a slight sense of urgency."
        else:
            attempt_context = "This is a follow-up message."

        task_summary = redact_text(entity.ask_summary)
        recipient_rule = "- Use a neutral greeting such as 'Hi,' unless the conversation context provides a safe non-PII role label."
        sender_rule = "- End with 'Regards,' and do not invent or include a personal name."

        return f"""You are a professional follow-up assistant creating draft messages.

{attempt_context}

Perspective:
- Write as the connected mailbox owner who is following up with the recipient.
- The recipient/target is the person who owes the update; the app will send the message to the correct email thread.
- Never write as the recipient.
- Never answer the request on the recipient's behalf.
- If the original ask was a question, write a polite follow-up asking the recipient to answer or share status.

Rules:
- Return only the email body. Do not include Subject, To, From, Cc, Bcc, date, thread id, or any header line.
- Use this structure exactly: greeting, body, "Regards,", sender name.
- Do not add any new commitments.
- Ensure a polite tone appropriate for a {entity.priority.value} priority follow-up.
- Do not thank the sender for checking in unless the conversation context explicitly shows the target already replied with useful information.
- Do not claim that work is complete, nearing completion, approved, reviewed, or done unless the target already said so in the thread.
{recipient_rule}
{sender_rule}
{org_section}
[CONVERSATION CONTEXT]
{semantic_formatted}

[RECENT MESSAGES]
{recent_formatted}

[TASK]
{task_summary}"""

    @staticmethod
    def generate_fallback_draft(entity: FollowUpEntity, bundle: dict) -> str:
        """
        Deterministic fallback used when the AI provider is rate-limited.
        Keeps quota errors from becoming user-visible or sendable email bodies.
        """
        sender_name = bundle.get("sender_name") or ""
        recipient = entity.target_contact or "there"

        greeting = "Hi,"
        if recipient and "@" not in recipient:
            greeting = f"Hi {recipient},"

        if entity.attempts_count == 0:
            body = f"Just following up on this: {entity.ask_summary}. Please let me know when you get a chance."
        elif entity.attempts_count == 1:
            body = f"Just checking in again on this: {entity.ask_summary}. Please share an update when possible."
        else:
            body = f"Following up once more on this: {entity.ask_summary}. Please share a status update as soon as you can."

        signature = "Regards,"
        if sender_name:
            signature = f"{signature}\n{sender_name}"

        return f"{greeting}\n\n{body}\n\n{signature}"

    @staticmethod
    def validate_draft(draft_text: str) -> tuple[bool, str | None]:
        """
        Validates LLM output against guardrails before sending.
        Returns (True, None) if the draft is safe to send.
        Returns (False, reason) if rejected, so the caller can log why.

        Blocked keywords are intentionally narrow — 'legal' and 'finance' were
        removed because they appear in too many legitimate business follow-ups
        (e.g. 'send the legal review doc', 'finance team needs your report').
        Only block words that should genuinely never appear in an outbound message.
        """
        sensitive_keywords = ["termination", "salary", "investor"]
        text_lower = draft_text.lower()

        for kw in sensitive_keywords:
            if kw in text_lower:
                return False, f"Draft contains sensitive keyword: '{kw}'"

        return True, None
