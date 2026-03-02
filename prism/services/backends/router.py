"""Model router for mixed-model strategies.

Routes requests to different backends based on task type.
Example: Haiku/small model for extraction, Sonnet/large for synthesis.
"""

import logging
from typing import Optional

from prism.services.llm_backend import LLMBackend, LLMResponse, TokenBudget

logger = logging.getLogger(__name__)


class ModelRouter(LLMBackend):
    """Routes LLM requests to different backends based on task type.

    Example configuration:
        routes = {
            "extraction": haiku_backend,      # Stage 1 extraction (cheap)
            "synthesis": sonnet_backend,       # Stages 2-4 (needs reasoning)
            "activation": sonnet_backend,      # Angle generation
        }

    Callers pass task_type as a keyword argument to route to the
    appropriate backend. Unmatched task types go to the default backend.
    """

    def __init__(
        self,
        default_backend: LLMBackend,
        routes: Optional[dict[str, LLMBackend]] = None,
    ) -> None:
        self._default = default_backend
        self._routes = routes or {}

    async def query(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        response_format: str = "json",
        task_type: Optional[str] = None,
    ) -> Optional[LLMResponse]:
        """Route the query to the appropriate backend.

        Args:
            system_prompt: System-level instructions.
            user_prompt: The actual query content.
            max_tokens: Max output tokens.
            temperature: Sampling temperature.
            response_format: "json" or "text".
            task_type: Optional routing key to select backend.

        Returns:
            LLMResponse from the selected backend.
        """
        backend = self._routes.get(task_type, self._default) if task_type else self._default

        logger.debug(
            "Routing task_type=%s to %s",
            task_type or "default",
            type(backend).__name__,
        )

        return await backend.query(
            system_prompt,
            user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
        )

    def get_budget(self) -> TokenBudget:
        """Return aggregated budget from default backend.

        For detailed per-backend budgets, access backends directly
        through the routes dict.
        """
        return self._default.get_budget()

    def get_all_budgets(self) -> dict[str, TokenBudget]:
        """Return budgets from all backends for detailed reporting."""
        budgets: dict[str, TokenBudget] = {"default": self._default.get_budget()}
        seen_backends: set[int] = {id(self._default)}
        for task_type, backend in self._routes.items():
            if id(backend) not in seen_backends:
                budgets[task_type] = backend.get_budget()
                seen_backends.add(id(backend))
        return budgets
