import re
from datetime import datetime

def check_for_reply(thread_id: str, last_sent_at: datetime) -> dict:
    """
    Checks if a reply has been received in the given thread after `last_sent_at`.
    For this mock implementation, we simulate checks. In a real application, 
    this would query an email API (like Gmail/Graph API) restricted to `thread_id`.
    
    Returns:
        {"reply_detected": bool, "reply_type": "normal" | "ooo"}
    """
    # Pseudo-implementation or mock hook.
    # In a real impl, we'd fetch messages and inspect their content using classify_reply_type.
    # For now, we simulate finding no reply by default.
    # Tests will mock this function to verify scheduler behavior.
    return {
        "reply_detected": False,
        "reply_type": "normal"
    }

def classify_reply_type(message_body: str) -> str:
    """
    Basic string matching to detect OOO (Out of Office) replies.
    Does NOT use NLP/Intent classification, adhering to strict rules.
    """
    ooo_patterns = [
        r"(?i)\booo\b",
        r"(?i)out of office",
        r"(?i)auto-reply",
        r"(?i)automated reply",
        r"(?i)vacation responder"
    ]
    for pattern in ooo_patterns:
        if re.search(pattern, message_body):
            return "ooo"
    return "normal"
