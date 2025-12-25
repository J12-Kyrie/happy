from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt, Signal, QSize
from PySide6.QtGui import (
    QColor,
    QEnterEvent,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPaintEvent,
)
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .models import Quote


class QuoteCard(QWidget):
    hovered = Signal(object)
    unhovered = Signal(object)

    def __init__(self, quote: Quote, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.quote = quote
        self._hover = False
        self.mode = "program" if quote.category == "text" else "letter"
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(False)
        self.setObjectName("quoteCard")
        self.setStyleSheet(self._build_stylesheet())
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        self._opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self._opacity_animation.setDuration(600)
        self._opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._finished_callback = None

        self.layout = QVBoxLayout(self)
        if self.mode == "program":
            self._build_program_layout()
        else:
            self._build_letter_layout()

    def _build_program_layout(self) -> None:
        self.layout.setContentsMargins(24, 12, 24, 22)
        self.layout.setSpacing(14)

        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 0, 0, 0)
        title_bar.setSpacing(10)

        self.window_icon = QLabel("⏰")
        self.window_icon.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        self.window_icon.setStyleSheet("color: #d0652f; background: transparent;")
        self.window_icon.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.window_title = QLabel("暖冬提醒")
        self.window_title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.DemiBold))
        self.window_title.setStyleSheet("color: #7a3d22; background: transparent;")
        self.window_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        title_bar.addWidget(self.window_icon)
        title_bar.addWidget(self.window_title)
        title_bar.addStretch()

        self.close_label = QLabel("✕")
        self.close_label.setFont(QFont("Microsoft YaHei", 10))
        self.close_label.setStyleSheet("color: #b17a5b; background: transparent;")
        title_bar.addWidget(self.close_label)

        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 2, 0, 0)
        content_row.setSpacing(0)
        content_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.setSpacing(8)

        self.content_label = QLabel(self.quote.text)
        self.content_label.setWordWrap(True)
        self.content_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.content_label.setFont(QFont("Microsoft YaHei", 13))
        self.content_label.setStyleSheet(
            "color: #6b3a29; background: transparent; line-height: 1.65;"
        )

        text_column.addWidget(self.content_label)
        text_column.addStretch()

        content_row.addLayout(text_column)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 12, 0, 0)
        button_row.addStretch()

        self.button_label = QLabel("确定")
        self.button_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.button_label.setFont(QFont("Microsoft YaHei", 11))
        self.button_label.setFixedSize(92, 34)
        self.button_label.setStyleSheet(
            "color: #5a2e1d; background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            " stop:0 #fff6ec, stop:1 #f0d7b3);"
            "border: 1px solid #d4a574; border-radius: 4px;"
        )

        button_row.addWidget(self.button_label)

        self.layout.addLayout(title_bar)
        self.layout.addLayout(content_row)
        self.layout.addLayout(button_row)

    def _build_letter_layout(self) -> None:
        self.layout.setContentsMargins(34, 30, 34, 36)
        self.layout.setSpacing(20)

        self.header_label = QLabel("To Jtter:")
        header_font = QFont("STKaiti", 22, QFont.Weight.DemiBold)
        self.header_label.setFont(header_font)
        self.header_label.setStyleSheet("color: #8c6b54; background: transparent;")

        self.content_label = QLabel(self.quote.text)
        self.content_label.setWordWrap(True)
        self.content_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.content_label.setFont(QFont("Songti SC", 22))
        self.content_label.setStyleSheet(
            "color: #2c2c2c; background: transparent; line-height: 1.8;"
        )

        self.signature_label = QLabel("Kyrie")
        signature_font = QFont("STKaiti", 22, QFont.Weight.Medium)
        self.signature_label.setFont(signature_font)
        self.signature_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.signature_label.setStyleSheet("color: #8c6b54; background: transparent;")

        self.layout.addWidget(self.header_label)
        self.layout.addWidget(self.content_label)
        self.layout.addStretch()
        self.layout.addWidget(self.signature_label)

    # region 动画控制
    def fade_in(self) -> None:
        self.opacity_effect.setOpacity(0.0)
        self._opacity_animation.stop()
        self._opacity_animation.setStartValue(0.0)
        self._opacity_animation.setEndValue(1.0)
        self._opacity_animation.start()

    def fade_out(self, finished_callback=None) -> None:
        self._opacity_animation.stop()
        if self._finished_callback is not None:
            try:
                self._opacity_animation.finished.disconnect(self._finished_callback)
            except (TypeError, RuntimeError):
                pass
            self._finished_callback = None
        if finished_callback:
            self._opacity_animation.finished.connect(finished_callback)
            self._finished_callback = finished_callback
        self._opacity_animation.setStartValue(self.opacity_effect.opacity())
        self._opacity_animation.setEndValue(0.0)
        self._opacity_animation.start()

    # endregion

    def enterEvent(self, event: QEnterEvent) -> None:  # type: ignore[override]
        self._hover = True
        self.hovered.emit(self)
        return super().enterEvent(event)

    def leaveEvent(self, event: QEnterEvent) -> None:  # type: ignore[override]
        self._hover = False
        self.unhovered.emit(self)
        return super().leaveEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        if self.mode == "program":
            border_color = QColor("#e3b383")
            painter.setPen(border_color)
            painter.setBrush(QColor("#fff6ef"))
            painter.drawRoundedRect(rect.adjusted(0, 0, -1, -1), 9, 9)

            title_height = 40
            title_rect = QRect(rect.left() + 1, rect.top() + 1, rect.width() - 2, title_height)
            gradient = QLinearGradient(title_rect.topLeft(), title_rect.bottomLeft())
            gradient.setColorAt(0.0, QColor("#ffe9d7"))
            gradient.setColorAt(1.0, QColor("#ffd3b0"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(gradient)
            painter.drawRoundedRect(title_rect, 8, 8)
            painter.drawRect(title_rect.adjusted(0, 8, 0, 0))

            body_rect = QRect(
                rect.left() + 1,
                title_rect.bottom(),
                rect.width() - 2,
                rect.height() - title_height - 2,
            )
            painter.setBrush(QColor("#fffdf9"))
            painter.drawRect(body_rect)

            if self._hover:
                hover_overlay = QColor(255, 248, 236, 120)
                painter.setBrush(hover_overlay)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(rect.adjusted(0, 0, -1, -1), 9, 9)
        else:
            paper = QColor("#fffaf0")
            paper.setAlpha(235)
            painter.setBrush(paper)
            border_color = QColor(self.quote.color)
            border_color.setAlpha(160)
            painter.setPen(border_color)
            painter.drawRoundedRect(rect.adjusted(0, 0, -1, -1), 20, 20)

            painter.setPen(QColor(0, 0, 0, 28))
            for offset in range(60, rect.height(), 48):
                y = rect.top() + offset
                if y >= rect.bottom() - 24:
                    break
                painter.drawLine(rect.left() + 26, y, rect.right() - 26, y)

            if self._hover:
                hover_overlay = QColor(255, 255, 255, 100)
                painter.setBrush(hover_overlay)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(rect, 20, 20)

        super().paintEvent(event)

    def _build_stylesheet(self) -> str:
        return (
            "#quoteCard {"
            "  background: transparent;"
            "  border-radius: 12px;"
            "}"
        )

    def _calculate_size(self, content: Optional[str] = None) -> QSize:
        text = (content if content is not None else self.quote.text).strip()
        if not text:
            text = " "

        margins = self.layout.contentsMargins()
        metrics = QFontMetrics(self.content_label.font())

        length = len(text)
        if self.mode == "program":
            if length <= 60:
                target_width = 420
            elif length <= 120:
                target_width = 500
            else:
                target_width = 580
        else:
            if length <= 60:
                target_width = 440
            elif length <= 120:
                target_width = 520
            else:
                target_width = 600

        available_width = max(160, target_width - margins.left() - margins.right())
        bounding_height = metrics.boundingRect(
            0,
            0,
            available_width,
            0,
            Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft,
            text,
        ).height()

        spacing_total = self.layout.spacing()
        if self.mode == "program":
            header_height = max(self.window_title.sizeHint().height(), 20)
            button_height = self.button_label.sizeHint().height()
            base_height = (
                margins.top()
                + header_height
                + spacing_total
                + bounding_height
                + spacing_total
                + button_height
                + margins.bottom()
            )
            min_height = 180
        else:
            header_height = self.header_label.sizeHint().height()
            signature_height = self.signature_label.sizeHint().height()
            base_height = (
                margins.top()
                + header_height
                + spacing_total
                + bounding_height
                + spacing_total
                + signature_height
                + margins.bottom()
            )
            min_height = 240

        total_height = max(min_height, base_height)
        return QSize(target_width, total_height)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return self._calculate_size()

    def minimumSizeHint(self) -> QSize:  # type: ignore[override]
        return self._calculate_size()

