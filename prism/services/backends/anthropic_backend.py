"""Anthropic Claude API backend.

Refactored from the Phase 0 services/llm.py into the LLMBackend interface.
Uses true async via anthropic.AsyncAnthropic (no asyncio.to_thread).
"""

import asyncio
import logging
import time
from typing import Optional

import anthropic

from prism.services.llm_backend import LLMBackend, LLMResponse, TokenBudget

logger = logging.getLogger(__name__)


class AnthropicBackend(LLMBackend):
    """Claude API backend via Anthropic SDK.

    Core logic from Phase 0 (retry, budget tracking) preserved.
    Now uses AsyncAnthropic for true async.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        max_retries: int = 3,
        max_spend_usd: float = 100.0,
    ) -> None:
        from prism.config import ANTHROPIC_API_KEY, PRISM_MODEL

        self._api_key = api_key or ANTHROPIC_API_KEY
        self._model = model if model != "claude-sonnet-4-20250514" else PRISM_MODEL
        self._max_retries = max_retries
        self._budget = TokenBudget(max_spend_usd=max_spend_usd)

        if not self._api_key:
            logger.warning("No ANTHROPIC_API_KEY set. LLM calls will fail.")
            self._client: Optional[anthropic.AsyncAnthropic] = None
        else:
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key)

    async def query(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        response_format: str = "json",
    ) -> Optional[LLMResponse]:
        """Send a prompt to Claude and get a response.

        Implements retry with exponential backoff on rate limit and API errors.
        Checks budget before each call.
        """
        if not self._client:
            logger.error("No API client available (missing API key)")
            return None

        if not self._budget.check_budget():
            logger.error(
                "Budget exhausted (spent $%.4f of $%.2f limit)",
                self._budget.estimated_cost,
                self._budget.max_spend_usd,
            )
            return None

        last_error: Optional[Exception] = None
        for attempt in range(self._max_retries):
            try:
                start_time = time.monotonic()
                response = await self._client.messages.create(
                    model=self._model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                latency_ms = int((time.monotonic() - start_time) * 1000)

                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens

                if not response.content or not hasattr(response.content[0], "text"):
                    logger.error("Empty or non-text response from Anthropic")
                    return None
                content = response.content[0].text

                llm_response = LLMResponse(
                    content=content,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    model=self._model,
                    latency_ms=latency_ms,
                )

                self._budget.record(llm_response)

                logger.debug(
                    "Anthropic call: %d in / %d out tokens, %dms",
                    input_tokens,
                    output_tokens,
                    latency_ms,
                )

                return llm_response

            except anthropic.RateLimitError:
                wait = 2**attempt
                logger.warning(
                    "Rate limited, waiting %ds (attempt %d/%d)",
                    wait,
                    attempt + 1,
                    self._max_retries,
                )
                await asyncio.sleep(wait)
            except anthropic.APIError as e:
                wait = 2**attempt
                logger.warning(
                    "API error: %s, waiting %ds (attempt %d/%d)",
                    e,
                    wait,
                    attempt + 1,
                    self._max_retries,
                )
                await asyncio.sleep(wait)
                last_error = e

        logger.error(
            "Anthropic query failed after %d retries: %s",
            self._max_retries,
            last_error,
        )
        return None

    def get_budget(self) -> TokenBudget:
        """Return current token usage and budget status."""
        return self._budget
