"""PRISM data access — DAL factory and data loading."""

import logging

from prism.data.dal import DataAccessLayer

logger = logging.getLogger(__name__)


def get_dal(session=None) -> DataAccessLayer:
    """Factory that returns the appropriate DAL based on config.

    If DATABASE_URL is set, returns DatabaseDAL. Otherwise FixtureDAL.

    Args:
        session: Optional async session. If provided, used for DatabaseDAL.
    """
    from prism.config import DATABASE_URL

    if DATABASE_URL:
        from prism.data.database_dal import DatabaseDAL
        if session is None:
            raise RuntimeError(
                "DatabaseDAL requires a session. Use get_dal(session=session) "
                "or use the FastAPI dependency injection."
            )
        return DatabaseDAL(session)

    from prism.data.fixture_dal import FixtureDAL
    return FixtureDAL()
