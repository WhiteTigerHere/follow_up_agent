import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from bs4 import BeautifulSoup

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """Returns an authorized Gmail API service instance."""
    creds = None
    if os.path.exists('backend/token.json'):
        creds = Credentials.from_authorized_user_file('backend/token.json', SCOPES)
    elif os.path.exists('token.json'): # Fallback path
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            try:
                creds.refresh(Request())
                token_path = 'backend/token.json' if os.path.exists('backend/token.json') else 'token.json'
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                raise Exception(f"Failed to refresh Google API credentials: {e}. Please run `python setup_gmail.py` first.")
        else:
            raise Exception("Invalid or missing Google API credentials. Please run `python setup_gmail.py` first.")
        
    service = build('gmail', 'v1', credentials=creds)
    return service

def _get_body_from_payload(payload):
    """
    Recursively extracts the plain text or HTML body from a Gmail message payload.
    """
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8')
            elif part['mimeType'] == 'text/html':
                data = part['body'].get('data')
                if data:
                    html_content = base64.urlsafe_b64decode(data).decode('utf-8')
                    # Fallback to HTML if plain text not found, strip tags using BS4
                    return BeautifulSoup(html_content, "html.parser").get_text()
            elif 'parts' in part:
                # Nested parts (e.g. multipart/related inside multipart/alternative)
                res = _get_body_from_payload(part)
                if res:
                    return res
    else:
        # Sometimes there's no parts, just the body directly
        if payload.get('mimeType') == 'text/plain' or payload.get('mimeType') == 'text/html':
            data = payload['body'].get('data')
            if data:
                 text = base64.urlsafe_b64decode(data).decode('utf-8')
                 if payload.get('mimeType') == 'text/html':
                     text = BeautifulSoup(text, "html.parser").get_text()
                 return text
                 
    return ""

_THREAD_ID_CACHE = {}

def find_thread_id_by_query(query: str):
    """
    Searches Gmail for a thread matching the given query (e.g. subject)
    and returns its thread ID. If not found, returns None.
    """
    if query in _THREAD_ID_CACHE:
        return _THREAD_ID_CACHE[query]

    service = get_gmail_service()
    results = service.users().threads().list(userId='me', q=query).execute()
    threads = results.get('threads', [])
    if threads:
         _THREAD_ID_CACHE[query] = threads[0]['id']
         return threads[0]['id']
    return None

def get_thread_messages(thread_id_or_subject: str):
    """
    Given a Gmail thread_id or subject, fetches the thread and returns a list of messages.
    Returns: [{"id": msg_id, "author": sender, "text": body_text, "date": int_ms, "internalDate": string}]
    """
    import re
    if not re.match(r"^[0-9a-fA-F]{15,20}$", thread_id_or_subject):
        actual_thread_id = find_thread_id_by_query(thread_id_or_subject)
        if not actual_thread_id:
            raise ValueError(f"Could not find any Gmail thread matching: {thread_id_or_subject}")
    else:
        actual_thread_id = thread_id_or_subject

    service = get_gmail_service()
    thread = service.users().threads().get(userId='me', id=actual_thread_id).execute()
    messages_data = thread.get('messages', [])
    
    parsed_messages = []
    
    for msg in messages_data:
        # Extract headers
        headers = msg['payload'].get('headers', [])
        sender = "Unknown"
        for h in headers:
            if h['name'] == 'From':
                sender = h['value']
                break
                
        # Extract body
        body_text = _get_body_from_payload(msg['payload'])
        if not body_text:
            body_text = msg.get('snippet', '')
            
        parsed_messages.append({
            "id": msg['id'],
            "author": sender,
            "text": body_text,
            "internalDate": msg['internalDate']
        })
        
    return parsed_messages

def check_new_replies_since(thread_id: str, since_ms: int, my_email_address=""):
    """
    Checks if there are new messages in a thread after since_ms.
    Returns a dictionary indicating if a reply was detected and from whom.
    """
    try:
        messages = get_thread_messages(thread_id)
    except Exception as e:
        print(f"Error fetching thread {thread_id}: {e}")
        return {"reply_detected": False, "reply_type": "normal"}

    new_messages = [m for m in messages if int(m['internalDate']) > since_ms]
    
    if not new_messages:
        return {"reply_detected": False, "reply_type": "normal"}
        
    # Check if any new message is from someone ELSE (not me)
    # If the user provides my_email_address, we use it to filter out self-replies
    # Otherwise, we just assume any new message is a reply
    if my_email_address:
         new_replies = [m for m in new_messages if my_email_address.lower() not in m['author'].lower()]
         if not new_replies:
              # Only got messages from myself, so no external reply
              return {"reply_detected": False, "reply_type": "normal"}
         else:
              # For simplicity, pass the first external reply to the classifier
              msg_text = new_replies[0]['text']
    else:
         msg_text = new_messages[0]['text']

    from .reply_detector import classify_reply_type
    reply_type = classify_reply_type(msg_text)

    return {
        "reply_detected": True,
        "reply_type": reply_type
    }
