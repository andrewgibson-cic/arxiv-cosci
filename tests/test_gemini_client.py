"""Tests for GeminiClient."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from packages.ai.gemini_client import GeminiClient


class TestModel(BaseModel):
    name: str
    value: int


@pytest.fixture
def mock_genai():
    with patch("packages.ai.gemini_client.genai") as mock:
        yield mock


@pytest.fixture
def client():
    return GeminiClient(api_key="fake-key")


@pytest.mark.asyncio
async def test_is_available_true(mock_genai, client):
    """Test availability check returns True when API works."""
    mock_genai.list_models.return_value = ["model1"]
    assert await client.is_available() is True


@pytest.mark.asyncio
async def test_is_available_false(mock_genai, client):
    """Test availability check returns False on error."""
    mock_genai.list_models.side_effect = Exception("API Error")
    assert await client.is_available() is False


@pytest.mark.asyncio
async def test_generate_text(mock_genai, client):
    """Test simple text generation."""
    mock_response = AsyncMock()
    mock_response.text = "Generated text"
    
    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(return_value=mock_response)
    mock_genai.GenerativeModel.return_value = mock_model

    result = await client.generate("Prompt")
    
    assert result == "Generated text"
    mock_model.generate_content_async.assert_called_once()


@pytest.mark.asyncio
async def test_generate_json(mock_genai, client):
    """Test JSON generation."""
    expected_data = {"key": "value"}
    mock_response = AsyncMock()
    mock_response.text = json.dumps(expected_data)
    
    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(return_value=mock_response)
    mock_genai.GenerativeModel.return_value = mock_model

    result = await client.generate_json("Prompt")
    
    assert result == expected_data


@pytest.mark.asyncio
async def test_generate_structured(mock_genai, client):
    """Test structured Pydantic output."""
    expected_data = {"name": "test", "value": 42}
    mock_response = AsyncMock()
    mock_response.text = json.dumps(expected_data)
    
    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(return_value=mock_response)
    mock_genai.GenerativeModel.return_value = mock_model

    result = await client.generate_structured("Prompt", TestModel)
    
    assert isinstance(result, TestModel)
    assert result.name == "test"
    assert result.value == 42
    
    # Check that schema was passed to config
    # Since we are mocking genai, GenerationConfig is a mock.
    # We should check how it was initialized or check the arguments passed to generate_content_async.
    
    # Verify GenerationConfig was created with correct params
    mock_genai.types.GenerationConfig.assert_called_with(
        temperature=0.2,
        response_mime_type="application/json",
        response_schema=TestModel,
    )
