import json
import logging
import os
from typing import Any

from app.config import settings
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class GeminiClientWrapper:
    """
    Wrapper around Google's latest google-genai SDK.
    Initializes Client using environment variables (GEMINI_API_KEY).
    """

    def __init__(self):
        self._client: genai.Client | None = None

    def get_client(self) -> genai.Client:
        if self._client is None:
            api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
            if not api_key:
                logger.warning("GEMINI_API_KEY environment variable is not set!")
            self._client = genai.Client(api_key=api_key)
        return self._client

    async def generate_response(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.2
    ) -> str:
        """Generates text response using Google GenAI SDK."""
        try:
            client = self.get_client()
            config = types.GenerateContentConfig(
                temperature=temperature,
                system_instruction=system_instruction
            )
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=config
            )
            return response.text or ""
        except Exception as e:
            logger.error(f"Gemini API invocation error: {e}")
            raise RuntimeError(f"Gemini GenAI Error: {str(e)}")

    async def generate_json(
        self,
        prompt: str,
        system_instruction: str | None = None
    ) -> dict[str, Any]:
        """Generates structured JSON output using response_mime_type="application/json"."""
        try:
            client = self.get_client()
            config = types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                system_instruction=system_instruction
            )
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=config
            )
            text_content = response.text or "{}"
            return json.loads(text_content)
        except Exception as e:
            logger.error(f"Gemini JSON generation error: {e}")
            # Return fallback dictionary
            return {"error": str(e)}


gemini_client = GeminiClientWrapper()
