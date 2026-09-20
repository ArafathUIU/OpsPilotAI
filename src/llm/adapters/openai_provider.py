"""OpenAI-compatible LLM provider adapter using async HTTP client."""

import json
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from src.core.config import get_settings
from src.llm.provider import LLMProvider, LLMResponse, TokenUsage
from src.observability.logging import get_logger

logger = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)
settings = get_settings()


class OpenAICompatibleProvider(LLMProvider):
    """Adapter for OpenAI, Azure, Groq, and local OpenAI-compatible endpoints."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o",
        provider_name: str = "openai",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.provider_name = provider_name
        self.timeout_seconds = timeout_seconds

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: str,
        response_model: type[T],
        temperature: float = 0.1,
    ) -> LLMResponse[T]:
        start_time = time.perf_counter()
        schema_json = json.dumps(response_model.model_json_schema())
        augmented_system = (
            f"{system_prompt}\n\n"
            f"You MUST respond ONLY with a valid JSON object strictly matching this JSON Schema:\n"
            f"{schema_json}\n"
            f"Do not include any conversational preamble, explanation, or markdown formatting outside the JSON."
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": augmented_system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions", headers=headers, json=payload
            )
            resp.raise_for_status()
            data = resp.json()

        raw_text = data["choices"][0]["message"]["content"]
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Parse and validate with Pydantic
        try:
            parsed_dict = json.loads(raw_text)
            parsed_obj = response_model.model_validate(parsed_dict)
        except (json.JSONDecodeError, ValidationError) as err:
            logger.warning(
                f"Raw LLM output failed schema validation: {err}. Attempting raw repair."
            )
            raise

        usage_data = data.get("usage", {})
        prompt_tokens = usage_data.get("prompt_tokens", 0)
        completion_tokens = usage_data.get("completion_tokens", 0)
        total_tokens = usage_data.get("total_tokens", prompt_tokens + completion_tokens)

        # Approximate pricing ($2.50 / 1M in, $10.00 / 1M out for GPT-4o)
        cost = (prompt_tokens * 0.0000025) + (completion_tokens * 0.000010)

        return LLMResponse(
            parsed=parsed_obj,
            raw_content=raw_text,
            usage=TokenUsage(
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=round(cost, 6),
            ),
            provider=self.provider_name,
            model=self.model,
            latency_ms=latency_ms,
        )
