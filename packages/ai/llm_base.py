from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    """Protocol for LLM clients."""

    async def is_available(self) -> bool:
        """Check if LLM service is available."""
        ...

    async def close(self) -> None:
        """Close client resources."""
        ...

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
        ...

    async def generate_json(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Generate JSON output."""
        ...

    async def generate_structured(
        self,
        prompt: str,
        output_model: type[T],
        *,
        model: str | None = None,
        system: str | None = None,
    ) -> T:
        """Generate structured output matching a Pydantic model."""
        ...
