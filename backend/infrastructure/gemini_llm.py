import os
import google.generativeai as genai
from dotenv import load_dotenv
from domain.privacy import redact_messages, redact_text

env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path, override=True)

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

def _configure_gemini():
    load_dotenv(dotenv_path=env_path, override=True)
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY", "dummy_key"))

class GeminiDraftingClient:
    @staticmethod
    def generate_draft(prompt: str) -> str:
        """
        Calls Gemini strictly to generate draft text. 
        Does not ask LLM for entity tracking or routing decisions.
        """
        try:
            _configure_gemini()
            model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL", DEFAULT_MODEL))
            response = model.generate_content(redact_text(prompt))
            return response.text
        except Exception as e:
            raise RuntimeError(f"Gemini draft generation failed: {e}") from e

    @staticmethod
    def summarize_thread(messages: list[dict]) -> str:
        """
        Calls Gemini to create a concise summary of the provided thread messages.
        """
        try:
            _configure_gemini()
            model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL", DEFAULT_MODEL))
            safe_messages = redact_messages(messages)
            formatted = "\n".join([f"{m['author']}: {m['text']}" for m in safe_messages])
            prompt = f"Please provide a concise, high-level summary of the following message thread:\n\n{formatted}"
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return "Summary unavailable because the AI provider could not be reached or quota was exceeded."
            
