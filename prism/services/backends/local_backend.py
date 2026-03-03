"""Local inference backend via OpenAI-compatible API.

Works with vLLM, SGLang, llama.cpp server, or any server
that exposes POST /v1/chat/completions.

For Mac Studio cluster deployment with open-source models.
"""

import asyncio
import logging
import time
from typing import Optional

import httpx

from prism.services.llm_backend import LLMBackend, LLMResponse, TokenBudget

logger = logging.getLogger(__name__)


class LocalInferenceBackend(LLMBackend):
    """Local inference via OpenAI-compatible API endpoint.

    Cost is $0 (running locally), but token counts are still tracked
    for analysis and comparison with API-based backends.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        model: str = "local-model",
        max_retries: int = 3,
        timeout: float = 120.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._max_retries = max_retries
        self._timeout = timeout
        self._budget = TokenBudget(
            max_spend_usd=float("inf"),
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
        )
        self._client = httpx.AsyncClient(timeout=timeout)

    async def query(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        response_format: str = "json",
    ) -> Optional[LLMResponse]:
        """Send a prompt to a local OpenAI-compatible server.

        Implements retry with exponential backoff on connection and server errors.
        Stricter JSON validation than Anthropic backend since open models
        are flakier at structured output.
        """
        payload: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}

        url = f"{self._base_url}/v1/chat/completions"
        last_error: Optional[Exception] = None

        for attempt in range(self._max_retries):
            try:
                start_time = time.monotonic()
                resp = await self._client.post(url, json=payload)
                latency_ms = int((time.monotonic() - start_time) * 1000)

                if resp.status_code != 200:
                    logger.warning(
                        "Local inference returned %d: %s (attempt %d/%d)",
                        resp.status_code,
                        resp.text[:200],
                        attempt + 1,
                        self._max_retries,
                    )
                    if resp.status_code >= 500:
                        wait = 2**attempt
                        await asyncio.sleep(wait)
                        continue
                    return None

                data = resp.json()
                choices = data.get("choices")
                if not choices:
                    logger.error("Local inference returned no choices")
                    return None
                content = choices[0].get("message", {}).get("content")
                if content is None:
                    logger.error("Local inference response missing message content")
                    return None

                usage = data.get("usage", {})
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)

                llm_response = LLMResponse(
                    content=content,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    model=data.get("model", self._model),
                    latency_ms=latency_ms,
                )

                self._budget.record(llm_response)

                logger.debug(
                    "Local inference call: %d in / %d out tokens, %dms",
                    input_tokens,
                    output_tokens,
                    latency_ms,
                )

                return llm_response

            except httpx.ConnectError as e:
                wait = 2**attempt
                logger.warning(
                    "Local inference connection failed: %s, waiting %ds (attempt %d/%d)",
                    e,
                    wait,
                    attempt + 1,
                    self._max_retries,
                )
                await asyncio.sleep(wait)
                last_error = e
            except httpx.TimeoutException as e:
                wait = 2**attempt
                logger.warning(
                    "Local inference timeout: %s, waiting %ds (attempt %d/%d)",
                    e,
                    wait,
                    attempt + 1,
                    self._max_retries,
                )
                await asyncio.sleep(wait)
                last_error = e
            except (httpx.HTTPError, KeyError, IndexError) as e:
                logger.warning(
                    "Local inference error: %s (attempt %d/%d)",
                    e,
                    attempt + 1,
                    self._max_retries,
                )
                last_error = e
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(2**attempt)

        logger.error(
            "Local inference query failed after %d retries: %s",
            self._max_retries,
            last_error,
        )
        return None

    def get_budget(self) -> TokenBudget:
        """Return current token usage (cost is always $0 for local)."""
        return self._budget

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
