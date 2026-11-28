from typing import TYPE_CHECKING

# FastAPI reads a dependency's signature at runtime
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from pipeline.database import session_scope

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield the request's session, as the `api` role `DATABASE_URL` names.

    One request is one transaction (see `session_scope`).
    """
    async with session_scope() as session:
        yield session
