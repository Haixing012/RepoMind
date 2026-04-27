from __future__ import annotations

import asyncio
from collections import defaultdict


class ProgressBroker:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict]]] = defaultdict(set)

    def subscribe(self, repository_id: str) -> asyncio.Queue[dict]:
        queue: asyncio.Queue[dict] = asyncio.Queue()
        self._subscribers[repository_id].add(queue)
        return queue

    def unsubscribe(self, repository_id: str, queue: asyncio.Queue[dict]) -> None:
        subscribers = self._subscribers.get(repository_id)
        if not subscribers:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._subscribers.pop(repository_id, None)

    async def publish(self, repository_id: str, payload: dict) -> None:
        for queue in list(self._subscribers.get(repository_id, set())):
            await queue.put(payload)


progress_broker = ProgressBroker()
