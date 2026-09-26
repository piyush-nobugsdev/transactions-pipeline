from __future__ import annotations

from typing import Protocol


class Storage(Protocol):
    async def upload(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
    ) -> None: ...

    async def download(self, *, key: str) -> bytes: ...

    async def delete(self, *, key: str) -> None: ...

    async def exists(self, *, key: str) -> bool: ...
