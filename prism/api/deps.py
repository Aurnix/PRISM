"""FastAPI dependency injection — DB session, auth, LLM backend."""

import logging
from typing import AsyncGenerator

from fastapi import Depends, Header, HTTPException

from prism.config import API_KEYS
from prism.data.dal import DataAccessLayer
from prism.data.database_dal import DatabaseDAL
from prism.data.fixture_dal import FixtureDAL
from prism.services.llm_backend import LLMBackend

logger = logging.getLogger(__name__)


async def get_dal_dep() -> AsyncGenerator[DataAccessLayer, None]:
    """Yield a DAL instance. Uses DB if configured, else fixtures."""
    from prism.config import DATABASE_URL

    if DATABASE_URL:
        from prism.db.session import get_session_factory
        factory = get_session_factory()
        async with factory() as session:
            yield DatabaseDAL(session)
    else:
        yield FixtureDAL()


async def get_llm_dep() -> LLMBackend:
    """Return the configured LLM backend."""
    from prism.services import get_llm_backend
    return get_llm_backend()


async def verify_api_key(x_api_key: str = Header(default="")) -> str:
    """Verify X-API-Key header. Skip if no API keys configured."""
    if not API_KEYS:
        return "no-auth"
    if x_api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
