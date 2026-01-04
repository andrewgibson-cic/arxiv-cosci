"""Gemini LLM client.

Provides async interface to Google's Gemini API.
"""

import json
import os
from typing import Any, TypeVar

import google.generativeai as genai
import structlog
from google.api_core import exceptions as google_exceptions
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from packages.ai.llm_base import LLMClient

logger = structlog.get_logger()

# Default Gemini settings
DEFAULT_MODEL = "gemini-1.5-flash"
DEFAULT_TIMEOUT = 60  # seconds

T = TypeVar("T", bound=BaseModel)


class GeminiClient(LLMClient):
    """Async client for Google Gemini API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize Gemini client.

        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            model: Default model to use (default: gemini-1.5-flash)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        self.timeout = timeout
        self._configured = False

    def _configure(self) -> None:
        """Configure the Gemini API library."""
        if not self._configured:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY not found")
            genai.configure(api_key=self.api_key)
            self._configured = True

    async def close(self) -> None:
        """Close client resources.
        
        The Google library manages its own connection pool, so explicitly
        closing it isn't strictly necessary for individual requests,
        but we implement the protocol method for consistency.
        """
        pass

    async def is_available(self) -> bool:
        """Check if Gemini service is available."""
        if not self.api_key:
            return False
        try:
            self._configure()
            # Simple list models call to check connectivity
            list(genai.list_models(page_size=1))
            return True
        except Exception:
            return False

    @retry(
        retry=retry_if_exception_type(
            (
                google_exceptions.ResourceExhausted,  # Rate limit (429)
                google_exceptions.ServiceUnavailable,  # 503
                google_exceptions.DeadlineExceeded,   # Timeout
                google_exceptions.InternalServerError, # 500
            )
        ),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
    )
    async def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """Generate text completion."""
        self._configure()
        
        target_model = model or self.model_name
        
        # Configure generation config
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        try:
            # Create model instance
            # Note: Gemini puts system instructions in the model constructor
            generative_model = genai.GenerativeModel(
                model_name=target_model,
                system_instruction=system,
            )

            # Generate content (async)
            response = await generative_model.generate_content_async(
                prompt,
                generation_config=generation_config,
            )
            
            return response.text
            
        except ValueError as e:
            # Often happens if blocked by safety filters
            logger.warning("gemini_blocked", error=str(e))
            return ""
        except Exception as e:
            logger.error("gemini_generate_failed", error=str(e))
            raise

    async def generate_json(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Generate JSON output."""
        self._configure()
        target_model = model or self.model_name

        # Gemini supports native JSON mode
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json",
        )

        try:
            generative_model = genai.GenerativeModel(
                model_name=target_model,
                system_instruction=system,
            )

            response = await generative_model.generate_content_async(
                prompt,
                generation_config=generation_config,
            )
            
            return json.loads(response.text)
            
        except Exception as e:
            logger.error("gemini_json_failed", error=str(e))
            raise

    async def generate_structured(
        self,
        prompt: str,
        output_model: type[T],
        *,
        model: str | None = None,
        system: str | None = None,
    ) -> T:
        """Generate structured output matching a Pydantic model."""
        self._configure()
        target_model = model or self.model_name
        
        # Gemini allows passing the Pydantic schema directly!
        # This is very robust.
        
        generation_config = genai.types.GenerationConfig(
            temperature=0.2, # Low temp for structure
            response_mime_type="application/json",
            response_schema=output_model,
        )

        try:
            generative_model = genai.GenerativeModel(
                model_name=target_model,
                system_instruction=system,
            )

            response = await generative_model.generate_content_async(
                prompt,
                generation_config=generation_config,
            )
            
            # The response text should be valid JSON matching the schema
            return output_model.model_validate_json(response.text)
            
        except Exception as e:
            logger.error("gemini_structured_failed", error=str(e))
            raise
