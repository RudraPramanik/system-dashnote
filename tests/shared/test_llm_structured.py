"""Unit tests for shared.llm structured completion — no live API calls."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import litellm
import pytest
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from shared.llm.structured import (
    StructuredLLMParseError,
    acompletion_structured,
    extract_json_blob,
    parse_structured_response,
)


class TagSchema(BaseModel):
    tags: list[str] = Field(max_length=5)


def test_extract_json_blob_plain():
    raw = '{"tags": ["quantum", "physics"]}'
    assert extract_json_blob(raw) == raw


def test_extract_json_blob_markdown_fence():
    raw = '```json\n{"tags": ["ai"]}\n```'
    assert extract_json_blob(raw) == '{"tags": ["ai"]}'


def test_extract_json_blob_preamble():
    raw = 'Here is the JSON:\n{"tags": ["lab"]}'
    assert extract_json_blob(raw) == '{"tags": ["lab"]}'


def test_parse_structured_response_valid():
    raw = '{"tags": ["note", "test"]}'
    result = parse_structured_response(raw, TagSchema)
    assert result.tags == ["note", "test"]


def test_parse_structured_response_salvage_markdown():
    raw = '```json\n{"tags": ["salvaged"]}\n```'
    result = parse_structured_response(raw, TagSchema)
    assert result.tags == ["salvaged"]


def test_parse_structured_response_truncated_raises():
    raw = '{"tags": ["incomplete'
    with pytest.raises(StructuredLLMParseError):
        parse_structured_response(raw, TagSchema)


def _mock_response(content: str) -> AsyncMock:
    mock = AsyncMock()
    mock.choices = [AsyncMock(message=AsyncMock(content=content))]
    return mock


@pytest.mark.asyncio
async def test_acompletion_structured_valid_json():
    with patch(
        "shared.llm.structured.acompletion_with_fallback",
        new_callable=AsyncMock,
        return_value=_mock_response('{"tags": ["valid"]}'),
    ):
        result = await acompletion_structured(
            messages=[{"role": "user", "content": "test"}],
            schema=TagSchema,
            max_tokens=64,
        )
    assert result.tags == ["valid"]


@pytest.mark.asyncio
async def test_acompletion_structured_markdown_salvage():
    with patch(
        "shared.llm.structured.acompletion_with_fallback",
        new_callable=AsyncMock,
        return_value=_mock_response('```json\n{"tags": ["md"]}\n```'),
    ):
        result = await acompletion_structured(
            messages=[{"role": "user", "content": "test"}],
            schema=TagSchema,
            max_tokens=64,
        )
    assert result.tags == ["md"]


@pytest.mark.asyncio
async def test_acompletion_structured_preamble_salvage():
    with patch(
        "shared.llm.structured.acompletion_with_fallback",
        new_callable=AsyncMock,
        return_value=_mock_response('Here is the JSON: {"tags": ["pre"]}'),
    ):
        result = await acompletion_structured(
            messages=[{"role": "user", "content": "test"}],
            schema=TagSchema,
            max_tokens=64,
        )
    assert result.tags == ["pre"]


@pytest.mark.asyncio
async def test_acompletion_structured_truncated_raises():
    with patch(
        "shared.llm.structured.acompletion_with_fallback",
        new_callable=AsyncMock,
        return_value=_mock_response('{"tags": ["bad'),
    ):
        with pytest.raises(StructuredLLMParseError):
            await acompletion_structured(
                messages=[{"role": "user", "content": "test"}],
                schema=TagSchema,
                max_tokens=64,
            )


@pytest.mark.asyncio
async def test_acompletion_structured_retries_then_succeeds():
    call_count = 0

    async def side_effect(**_kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise litellm.exceptions.ServiceUnavailableError(
                message="503",
                llm_provider="test",
                model="test",
            )
        return _mock_response('{"tags": ["retry"]}')

    with patch(
        "shared.llm.structured.acompletion_with_fallback",
        new_callable=AsyncMock,
        side_effect=side_effect,
    ):
        result = await acompletion_structured(
            messages=[{"role": "user", "content": "test"}],
            schema=TagSchema,
            max_tokens=64,
        )

    assert result.tags == ["retry"]
    assert call_count == 2
