from __future__ import annotations

from decimal import Decimal


class Money:
    def __init__(self, value: Decimal) -> None:
        if value <= 0:
            raise ValueError("money must be positive")
        self.value = value

    def __float__(self) -> float:
        return float(self.value)
