"""LLM Client Factory.

Manages creation of LLM clients based on configuration.
"""

import os
from typing import Literal

from packages.ai.gemini_client import GeminiClient
from packages.ai.groq_client import GroqClient
from packages.ai.llm_base import LLMClient
from packages.ai.ollama_client import OllamaClient

ProviderType = Literal["ollama", "groq", "gemini"]

_client_instance: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get the configured LLM client instance.

    Returns:
        LLMClient: The active LLM client
    """
    global _client_instance

    if _client_instance is None:
        provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        
        if provider == "groq":
            _client_instance = GroqClient()
        elif provider == "gemini":
            _client_instance = GeminiClient()
        else:
            _client_instance = OllamaClient()

    return _client_instance


async def close_client() -> None:
    """Close the active LLM client."""
    global _client_instance
    if _client_instance:
        await _client_instance.close()
        _client_instance = None
