"""SSE comment heartbeats so nginx does not drop a quiet AI stream."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import TypeVar

T = TypeVar("T")

SSE_HEARTBEAT_INTERVAL_SECONDS = 15.0
SSE_KEEPALIVE = ": keepalive\n\n"


async def iter_with_heartbeat(
    source: AsyncIterator[T],
    *,
    interval: float = SSE_HEARTBEAT_INTERVAL_SECONDS,
) -> AsyncIterator[T | str]:
    """Yield source items, inserting SSE comments when the source is quiet."""
    nxt = asyncio.create_task(source.__anext__())
    try:
        while True:
            done, _ = await asyncio.wait({nxt}, timeout=interval)
            if not done:
                yield SSE_KEEPALIVE
                continue
            try:
                item = nxt.result()
            except StopAsyncIteration:
                return
            yield item
            nxt = asyncio.create_task(source.__anext__())
    finally:
        if not nxt.done():
            nxt.cancel()
            try:
                await nxt
            except (asyncio.CancelledError, StopAsyncIteration):
                pass
