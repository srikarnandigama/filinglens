"""Explicit pool lifecycle and transactional connections."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from psycopg.conninfo import conninfo_to_dict
from psycopg_pool import AsyncConnectionPool


def connection_options(url: str) -> dict[str, object]:
    options: dict[str, object] = {"connect_timeout": 15}
    if conninfo_to_dict(url).get("host") == "localhost":
        options["hostaddr"] = "127.0.0.1"
    return options


@asynccontextmanager
async def pool_for(url: str) -> AsyncIterator[AsyncConnectionPool]:
    pool = AsyncConnectionPool(
        url, open=False, min_size=1, max_size=4, kwargs=connection_options(url)
    )
    await pool.open()
    try:
        await pool.wait(timeout=30)
        yield pool
    finally:
        await pool.close()
