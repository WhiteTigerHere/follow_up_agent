from ..models import FollowUpEntity


class DraftGenerationSkill:

    @staticmethod
    def generate_draft_prompt(entity: FollowUpEntity, bundle: dict) -> str:
        """
        Generates the prompt sent to the LLM (Gemini) via a single string call.
        Note: [SYSTEM] is not a real instruction boundary in the Gemini SDK —
        it is inline text only. True system instruction separation would require
        passing system_instruction= to GenerativeModel().
        """
        semantic_list = bundle.get("semantic_context", [])
        recent_list = bundle.get("recent_context", [])
        org_list = bundle.get("org_context", [])

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

        sender_name = bundle.get("sender_name") or ""
        recipient_contact = entity.target_contact or ""

        recipient_rule = (
            f"- Address the recipient as '{recipient_contact}'."
            if recipient_contact and "@" not in recipient_contact
            else "- Do not address the recipient by name (only their email address is known)."
        )
        sender_rule = (
            f"- Sign off with the name: {sender_name}."
            if sender_name
            else "- Do not include a sign-off name placeholder."
        )

        return f"""You are a professional follow-up assistant creating draft messages.

{attempt_context}

Rules:
- Do not add any new commitments.
- Ensure a polite tone appropriate for a {entity.priority.value} priority follow-up.
{recipient_rule}
{sender_rule}
{org_section}
[CONVERSATION CONTEXT]
{semantic_formatted}

[RECENT MESSAGES]
{recent_formatted}

[TASK]
{entity.ask_summary}"""

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
