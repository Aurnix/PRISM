"""Claude API wrapper with structured output, retry, and cost tracking."""

import asyncio
import json
import logging
import re
from typing import Optional

import anthropic

from prism.config import (
    ANTHROPIC_API_KEY,
    LLM_COST_PER_1K_INPUT,
    LLM_COST_PER_1K_OUTPUT,
    PRISM_MODEL,
)

logger = logging.getLogger(__name__)


class TokenUsage:
    """Tracks cumulative token usage and cost."""

    def __init__(self) -> None:
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.total_calls: int = 0

    @property
    def estimated_cost(self) -> float:
        """Estimated cost in USD."""
        input_cost = (self.total_input_tokens / 1000) * LLM_COST_PER_1K_INPUT
        output_cost = (self.total_output_tokens / 1000) * LLM_COST_PER_1K_OUTPUT
        return input_cost + output_cost

    def add(self, input_tokens: int, output_tokens: int) -> None:
        """Record a new API call."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_calls += 1

    def summary(self) -> str:
        """Human-readable usage summary."""
        return (
            f"API Calls: {self.total_calls} | "
            f"Input: {self.total_input_tokens:,} tokens | "
            f"Output: {self.total_output_tokens:,} tokens | "
            f"Est. Cost: ${self.estimated_cost:.4f}"
        )


class LLMService:
    """Claude API service with retry logic and cost tracking."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = api_key or ANTHROPIC_API_KEY
        self.model = model or PRISM_MODEL
        self.usage = TokenUsage()

        if not self.api_key:
            logger.warning("No ANTHROPIC_API_KEY set. LLM calls will fail.")
            self._client = None
        else:
            self._client = anthropic.Anthropic(api_key=self.api_key)

    async def query_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        retries: int = 3,
    ) -> Optional[dict]:
        """Send a prompt and parse the JSON response.

        Args:
            system_prompt: System message with instructions.
            user_prompt: User message with content to analyze.
            max_tokens: Maximum output tokens.
            retries: Number of retry attempts.

        Returns:
            Parsed JSON dict, or None on failure.
        """
        if not self._client:
            logger.error("No API client available (missing API key)")
            return None

        last_error = None
        for attempt in range(retries):
            try:
                response = await asyncio.to_thread(
                    self._client.messages.create,
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )

                # Track usage
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                self.usage.add(input_tokens, output_tokens)

                logger.debug(
                    "LLM call: %d input, %d output tokens",
                    input_tokens,
                    output_tokens,
                )

                # Extract text
                raw_text = response.content[0].text

                # Strip markdown code fences
                raw_text = _strip_code_fences(raw_text)

                # Parse JSON
                try:
                    return json.loads(raw_text)
                except json.JSONDecodeError as e:
                    logger.warning(
                        "JSON parse failed (attempt %d): %s\nRaw: %s",
                        attempt + 1, e, raw_text[:500],
                    )
                    if attempt < retries - 1:
                        await asyncio.sleep(1 * (attempt + 1))
                    last_error = e

            except anthropic.RateLimitError:
                wait = 2 ** attempt
                logger.warning("Rate limited, waiting %ds (attempt %d)", wait, attempt + 1)
                await asyncio.sleep(wait)
            except anthropic.APIError as e:
                wait = 2 ** attempt
                logger.warning("API error: %s, waiting %ds (attempt %d)", e, wait, attempt + 1)
                await asyncio.sleep(wait)
                last_error = e

        logger.error("LLM query failed after %d retries: %s", retries, last_error)
        return None

    async def query_text(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        retries: int = 3,
    ) -> Optional[str]:
        """Send a prompt and return raw text response.

        Args:
            system_prompt: System message with instructions.
            user_prompt: User message.
            max_tokens: Maximum output tokens.
            retries: Number of retry attempts.

        Returns:
            Raw text response, or None on failure.
        """
        if not self._client:
            logger.error("No API client available (missing API key)")
            return None

        for attempt in range(retries):
            try:
                response = await asyncio.to_thread(
                    self._client.messages.create,
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )

                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                self.usage.add(input_tokens, output_tokens)

                return response.content[0].text

            except anthropic.RateLimitError:
                wait = 2 ** attempt
                logger.warning("Rate limited, waiting %ds", wait)
                await asyncio.sleep(wait)
            except anthropic.APIError as e:
                wait = 2 ** attempt
                logger.warning("API error: %s, waiting %ds", e, wait)
                await asyncio.sleep(wait)

        logger.error("LLM text query failed after %d retries", retries)
        return None


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences from LLM response."""
    # Remove ```json ... ``` or ``` ... ```
    text = text.strip()
    pattern = r"^```(?:json)?\s*\n?(.*?)\n?\s*```$"
    match = re.match(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text
