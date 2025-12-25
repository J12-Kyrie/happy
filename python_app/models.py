from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Quote:
    text: str
    color: str
    category: str


@dataclass(frozen=True)
class Achievement:
    text: str
    color: str

