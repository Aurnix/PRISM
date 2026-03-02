"""Abstract LLM backend interface with response and budget tracking.

Provides a swappable interface for LLM inference. Implementations include
AnthropicBackend (Claude API) and LocalInferenceBackend (OpenAI-compatible
API for vLLM/SGLang/llama.cpp on Mac Studio cluster).
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Standardized response from any LLM backend."""

    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    latency_ms: int = 0
    cached: bool = False


@dataclass
class TokenBudget:
    """Spend tracking and enforcement."""

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_calls: int = 0
    max_spend_usd: float = 100.0
    cost_per_1k_input: float = 0.003
    cost_per_1k_output: float = 0.015

    @property
    def estimated_cost(self) -> float:
        """Estimated cost in USD."""
        return (
            (self.total_input_tokens / 1000) * self.cost_per_1k_input
            + (self.total_output_tokens / 1000) * self.cost_per_1k_output
        )

    @property
    def budget_remaining(self) -> float:
        """Remaining budget in USD."""
        return self.max_spend_usd - self.estimated_cost

    def check_budget(self) -> bool:
        """Returns False if budget exhausted."""
        return self.estimated_cost < self.max_spend_usd

    def record(self, response: LLMResponse) -> None:
        """Record token usage from a response."""
        self.total_input_tokens += response.input_tokens
        self.total_output_tokens += response.output_tokens
        self.total_calls += 1

    def summary(self) -> str:
        """Human-readable usage summary."""
        return (
            f"API Calls: {self.total_calls} | "
            f"Input: {self.total_input_tokens:,} tokens | "
            f"Output: {self.total_output_tokens:,} tokens | "
            f"Est. Cost: ${self.estimated_cost:.4f}"
        )


class LLMBackend(ABC):
    """Abstract interface for LLM inference backends.

    Implementations: AnthropicBackend, LocalInferenceBackend.
    The Content Intelligence chain calls this interface — it never
    knows or cares which backend is answering.
    """

    @abstractmethod
    async def query(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        response_format: str = "json",
    ) -> Optional[LLMResponse]:
        """Send a prompt and get a response.

        Args:
            system_prompt: System-level instructions.
            user_prompt: The actual query content.
            max_tokens: Max output tokens.
            temperature: Sampling temperature (0.0 = deterministic).
            response_format: Expected format — "json" or "text".

        Returns:
            LLMResponse on success, None on failure after retries.
        """
        ...

    @abstractmethod
    def get_budget(self) -> TokenBudget:
        """Return current token usage and budget status."""
        ...

    async def query_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> Optional[dict]:
        """Send a prompt and parse the JSON response.

        Convenience method that wraps query() with JSON parsing.

        Returns:
            Parsed JSON dict, or None on failure.
        """
        response = await self.query(
            system_prompt,
            user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format="json",
        )
        if response is None:
            return None

        text = strip_code_fences(response.content)
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning("JSON parse failed: %s\nRaw: %s", e, text[:500])
            return None

    async def query_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> Optional[str]:
        """Send a prompt and return raw text.

        Convenience method that wraps query() for text responses.

        Returns:
            Raw text response, or None on failure.
        """
        response = await self.query(
            system_prompt,
            user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format="text",
        )
        return response.content if response else None


def strip_code_fences(text: str) -> str:
    """Remove markdown code fences from LLM response."""
    text = text.strip()
    pattern = r"^```(?:json)?\s*\n?(.*?)\n?\s*```$"
    match = re.match(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text
