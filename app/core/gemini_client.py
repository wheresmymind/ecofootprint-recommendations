# app/core/gemini_client.py
import google.generativeai as genai
from .config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash') # Or specify a newer model if available
    logger.info("Gemini client configured successfully.")
except Exception as e:
    logger.error(f"Failed to configure Gemini client: {e}")
    model = None # Ensure model is None if config fails

async def generate_text_from_gemini(prompt: str) -> str | None:
    if not model:
        logger.error("Gemini model not initialized. Cannot generate text.")
        return None
    try:
        response = await model.generate_content_async(prompt) # Use async version
        # Basic safety check (can be expanded)
        if not response.candidates or not response.candidates[0].content.parts:
             logger.warning(f"Gemini response emight be blocked or empty. Response: {response}")
             # Check prompt feedback for block reasons
             if response.prompt_feedback and response.prompt_feedback.block_reason:
                 return f"Blocked: {response.prompt_feedback.block_reason_message}"
             return "Could not generate recommendations due to content policy or empty response."

        return response.text
    except Exception as e:
        logger.error(f"Error generating content with Gemini: {e}")
        # Consider specific error types if needed (e.g., API key errors)
        return f"Error communicating with Gemini: {e}"