"""Groq LLM client.

Provides async interface to Groq API.
"""

import json
import os
from typing import Any, TypeVar

import structlog
from groq import AsyncGroq
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from packages.ai.llm_base import LLMClient

logger = structlog.get_logger()

# Default Groq settings
DEFAULT_MODEL = "llama3-8b-8192"
DEFAULT_TIMEOUT = 30  # seconds

T = TypeVar("T", bound=BaseModel)


class GroqClient(LLMClient):
    """Async client for Groq API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize Groq client.

        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env var)
            model: Default model to use (default: llama3-8b-8192)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model or os.getenv("GROQ_MODEL", DEFAULT_MODEL)
        self.timeout = timeout
        self._client: AsyncGroq | None = None

    def _get_client(self) -> AsyncGroq:
        """Get or create Groq client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("GROQ_API_KEY not found")
            self._client = AsyncGroq(
                api_key=self.api_key,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close client resources."""
        if self._client:
            await self._client.close()

    async def is_available(self) -> bool:
        """Check if Groq service is available."""
        if not self.api_key:
            return False
        try:
            client = self._get_client()
            # Simple list models call to check connectivity
            await client.models.list()
            return True
        except Exception:
            return False

    @retry(
        retry=retry_if_exception_type(Exception),  # Catch-all for network/API errors
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
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
        client = self._get_client()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            chat_completion = await client.chat.completions.create(
                messages=messages,
                model=model or self.model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return chat_completion.choices[0].message.content or ""
        except Exception as e:
            logger.error("groq_generate_failed", error=str(e))
            raise

    async def generate_json(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Generate JSON output using JSON mode."""
        client = self._get_client()

        # Ensure prompt asks for JSON (Groq requires "json" in prompt for json_object mode)
        json_prompt = f"{prompt}\n\nRespond with valid JSON only."
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": json_prompt})

        try:
            chat_completion = await client.chat.completions.create(
                messages=messages,
                model=model or self.model,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            content = chat_completion.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception as e:
            logger.error("groq_json_failed", error=str(e))
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
        # Get JSON schema from model
        schema = output_model.model_json_schema()
        schema_str = json.dumps(schema, indent=2)

        structured_prompt = f"""{prompt}

Output must be valid JSON matching this schema:
{schema_str}

Respond with JSON only."""

        json_response = await self.generate_json(
            structured_prompt,
            model=model,
            system=system,
            temperature=0.3, # Lower temp for structure
        )

        return output_model.model_validate(json_response)
