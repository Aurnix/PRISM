"""PRISM services."""

import logging
from typing import Optional

from prism.services.llm_backend import LLMBackend

logger = logging.getLogger(__name__)


def get_llm_backend(backend_type: Optional[str] = None) -> LLMBackend:
    """Factory that returns the configured LLM backend.

    Args:
        backend_type: Override for backend type. If None, reads from config.

    Returns:
        Configured LLMBackend instance.
    """
    from prism.config import (
        ANTHROPIC_API_KEY,
        LLM_BACKEND,
        LLM_LOCAL_MODEL,
        LLM_LOCAL_URL,
        LLM_MAX_SPEND_USD,
        PRISM_MODEL,
    )

    backend = backend_type or LLM_BACKEND

    if backend == "local":
        from prism.services.backends.local_backend import LocalInferenceBackend

        return LocalInferenceBackend(
            base_url=LLM_LOCAL_URL,
            model=LLM_LOCAL_MODEL,
        )

    if backend == "anthropic":
        from prism.services.backends.anthropic_backend import AnthropicBackend

        return AnthropicBackend(
            api_key=ANTHROPIC_API_KEY,
            model=PRISM_MODEL,
            max_spend_usd=LLM_MAX_SPEND_USD,
        )

    if backend == "router":
        from prism.services.backends.anthropic_backend import AnthropicBackend
        from prism.services.backends.router import ModelRouter

        default = AnthropicBackend(
            api_key=ANTHROPIC_API_KEY,
            model=PRISM_MODEL,
            max_spend_usd=LLM_MAX_SPEND_USD,
        )
        return ModelRouter(default_backend=default)

    logger.warning("Unknown LLM_BACKEND '%s', falling back to anthropic", backend)
    from prism.services.backends.anthropic_backend import AnthropicBackend

    return AnthropicBackend(
        api_key=ANTHROPIC_API_KEY,
        model=PRISM_MODEL,
        max_spend_usd=LLM_MAX_SPEND_USD,
    )
