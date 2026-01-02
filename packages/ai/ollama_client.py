"""Ollama LLM client for local inference.

Provides async interface to Ollama for:
- Text generation and completion
- Structured output parsing
- Batch processing with rate limiting
"""

import asyncio
import json
import os
from typing import Any, TypeVar

import aiohttp
import structlog
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger()

# Default Ollama settings
DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2:8b"
DEFAULT_TIMEOUT = 120  # seconds

T = TypeVar("T", bound=BaseModel)


class OllamaClient:
    """Async client for Ollama API."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize Ollama client.

        Args:
            base_url: Ollama server URL (default: http://localhost:11434)
            model: Default model to use (default: llama3.2:8b)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", DEFAULT_BASE_URL)
        self.model = model or os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
        self.timeout = timeout
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def is_available(self) -> bool:
        """Check if Ollama server is available."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/tags") as response:
                return response.status == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """List available models."""
        session = await self._get_session()
        async with session.get(f"{self.base_url}/api/tags") as response:
            if response.status != 200:
                return []
            data = await response.json()
            return [m["name"] for m in data.get("models", [])]

    @retry(
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
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
        """Generate text completion.

        Args:
            prompt: The prompt to complete
            model: Model to use (overrides default)
            system: System prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        session = await self._get_session()

        payload: dict[str, Any] = {
            "model": model or self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if system:
            payload["system"] = system

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        logger.debug("ollama_generate", model=payload["model"], prompt_len=len(prompt))

        async with session.post(
            f"{self.base_url}/api/generate",
            json=payload,
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"Ollama error: {error_text}")

            data = await response.json()
            return data.get("response", "")

    async def generate_json(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Generate JSON output.

        Args:
            prompt: Prompt requesting JSON output
            model: Model to use
            system: System prompt
            temperature: Lower temperature for more consistent JSON

        Returns:
            Parsed JSON dict
        """
        # Add JSON instruction to prompt
        json_prompt = f"{prompt}\n\nRespond with valid JSON only, no other text."

        response = await self.generate(
            json_prompt,
            model=model,
            system=system,
            temperature=temperature,
        )

        # Try to extract JSON from response
        response = response.strip()

        # Handle markdown code blocks
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        try:
            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            logger.warning("json_parse_failed", error=str(e), response=response[:200])
            raise ValueError(f"Failed to parse JSON: {e}")

    async def generate_structured(
        self,
        prompt: str,
        output_model: type[T],
        *,
        model: str | None = None,
        system: str | None = None,
    ) -> T:
        """Generate structured output matching a Pydantic model.

        Args:
            prompt: The prompt
            output_model: Pydantic model class for output
            model: LLM model to use
            system: System prompt

        Returns:
            Parsed and validated Pydantic model instance
        """
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
        )

        return output_model.model_validate(json_response)

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Chat completion with message history.

        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": "..."}
            model: Model to use
            temperature: Sampling temperature

        Returns:
            Assistant response
        """
        session = await self._get_session()

        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        async with session.post(
            f"{self.base_url}/api/chat",
            json=payload,
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"Ollama error: {error_text}")

            data = await response.json()
            return data.get("message", {}).get("content", "")


# Global client instance
ollama_client = OllamaClient()
