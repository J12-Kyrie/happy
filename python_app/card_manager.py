from __future__ import annotations

import random

from dataclasses import dataclass
from typing import List

from PySide6.QtCore import QRect, QSize

from .card_widget import QuoteCard


@dataclass
class CardSlot:
    widget: QuoteCard
    rect: QRect


class CardManager:
    def __init__(self, container, margin: int = 32) -> None:
        self.container = container
        self.margin = margin
        self.viewport_size = QSize(1280, 720)
        self.cards: List[CardSlot] = []
        self.max_cards = 90

    def set_viewport_size(self, size: QSize) -> None:
        self.viewport_size = size
        for slot in self.cards:
            rect = self._random_rect(slot.rect.size())
            slot.rect = rect
            slot.widget.setGeometry(rect)
            slot.widget.raise_()

    def _random_rect(self, size: QSize) -> QRect:
        width = max(size.width(), 240)
        height = max(size.height(), 150)
        available_width = max(0, self.viewport_size.width() - width - self.margin * 2)
        available_height = max(0, self.viewport_size.height() - height - self.margin * 2)
        x = self.margin + (random.randint(0, available_width) if available_width > 0 else 0)
        y = self.margin + (random.randint(0, available_height) if available_height > 0 else 0)
        return QRect(x, y, width, height)

    def add_card(self, card: QuoteCard) -> None:
        size_hint = card.sizeHint()
        width_variation = random.randint(-18, 22)
        height_variation = random.randint(-24, 26)
        adjusted_size = QSize(
            max(260, size_hint.width() + width_variation),
            max(170, size_hint.height() + height_variation),
        )
        rect = self._random_rect(adjusted_size)

        card.setParent(self.container)
        card.setGeometry(rect)
        card.show()
        card.raise_()
        card.fade_in()

        slot = CardSlot(widget=card, rect=rect)
        self.cards.append(slot)

        if len(self.cards) > self.max_cards:
            self._remove_oldest()

    def _remove_oldest(self) -> None:
        if not self.cards:
            return
        slot = self.cards.pop(0)

        def _on_finished() -> None:
            slot.widget.deleteLater()

        slot.widget.fade_out(_on_finished)

    def fade_out_all(self, callback=None) -> None:
        """淡出所有卡片"""
        if not self.cards:
            if callback:
                callback()
            return

        for slot in self.cards:
            slot.widget.fade_out(slot.widget.deleteLater)

        self.cards = []
        if callback:
            import PySide6.QtCore
            PySide6.QtCore.QTimer.singleShot(1600, callback)

