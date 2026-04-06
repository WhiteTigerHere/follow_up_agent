import os
import google.generativeai as genai
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path)

# Configured for drafting texts
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", "dummy_key"))

class GeminiDraftingClient:
    @staticmethod
    def generate_draft(prompt: str) -> str:
        """
        Calls Gemini strictly only to draft text, not for entity tracking or routing decisions.
        """
        
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating draft: {str(e)}"

    @staticmethod
    def summarize_thread(messages: list[dict]) -> str:
        """
        Calls Gemini to create a concise summary of the provided thread messages.
        """
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            formatted = "\n".join([f"{m['author']}: {m['text']}" for m in messages])
            prompt = f"Please provide a concise, high-level summary of the following message thread:\n\n{formatted}"
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating summary: {str(e)}"
            