from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BatchRequest(BaseModel, Generic[T]):
    items: list[T]
