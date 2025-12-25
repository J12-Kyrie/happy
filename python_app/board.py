from __future__ import annotations

import random
from collections import deque
from typing import Deque, List, Optional

import math

from PySide6.QtCore import QPointF, QRect, Qt, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QFont, QPainter, QPixmap, QColor, QPen, QPainterPath
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .card_manager import CardManager
from .card_widget import QuoteCard
from .effects import SnowEffect, FireworksOverlay
from .models import Quote, Achievement


class SplashOverlay(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
            "  stop:0 #eef6fb, stop:1 #f3b8d9);"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label = QLabel("正在为你生成暖冬提醒…")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Source Han Sans", 28, QFont.Weight.Medium))
        self.label.setStyleSheet("color: #2c3e50;")
        layout.addWidget(self.label)

    def start(self, duration_ms: int, finished_callback) -> None:
        self.show()
        QTimer.singleShot(duration_ms, finished_callback)


class CloverEmojiOverlay(QWidget):
    """显示🍀emoji的覆盖层，带淡入效果"""
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._opacity = 0.0
        self._visible = False
        self.animation: Optional[QPropertyAnimation] = None
        self.hide()

    def get_opacity(self) -> float:
        return self._opacity

    def set_opacity(self, value: float) -> None:
        self._opacity = max(0.0, min(1.0, value))
        self.update()

    opacity = Property(float, get_opacity, set_opacity)

    def show_emoji(self) -> None:
        """淡入显示emoji"""
        self._visible = True
        self.show()
        self.raise_()
        
        if self.animation:
            self.animation.stop()
        
        self.animation = QPropertyAnimation(self, b"opacity")
        self.animation.setDuration(1500)  # 1.5秒淡入
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation.start()

    def hide_emoji(self) -> None:
        """淡出隐藏emoji"""
        if self.animation:
            self.animation.stop()
        
        self.animation = QPropertyAnimation(self, b"opacity")
        self.animation.setDuration(500)  # 0.5秒淡出
        self.animation.setStartValue(self._opacity)
        self.animation.setEndValue(0.0)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation.finished.connect(self._on_fade_out_finished)
        self.animation.start()

    def _on_fade_out_finished(self) -> None:
        self._visible = False
        self.hide()

    def emoji_visible(self) -> bool:
        return self._visible

    def paintEvent(self, event) -> None:  # type: ignore[override]
        if self._opacity <= 0.0:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        # 设置透明度
        painter.setOpacity(self._opacity)
        
        rect = self.rect()
        # 使用与轮廓相同的边距
        margin_x = rect.width() * 0.05
        margin_y = rect.height() * 0.05
        emoji_width = rect.width() - margin_x * 2
        emoji_height = rect.height() - margin_y * 2
        
        if emoji_width <= 0 or emoji_height <= 0:
            return
        
        # 计算emoji字体大小（基于可用区域）
        font_size = int(min(emoji_width, emoji_height) * 0.8)
        font = QFont("Apple Color Emoji", font_size)
        painter.setFont(font)
        
        # 保存画笔状态
        painter.save()
        
        # 移动到中心点
        center_x = rect.center().x()
        center_y = rect.center().y()
        painter.translate(center_x, center_y)
        
        # 逆时针旋转30度（负数表示逆时针）
        painter.rotate(-30)
        
        # 绘制🍀emoji居中（相对于旋转后的坐标系）
        emoji_rect = QRect(
            int(-emoji_width / 2),
            int(-emoji_height / 2),
            int(emoji_width),
            int(emoji_height)
        )
        painter.drawText(emoji_rect, Qt.AlignmentFlag.AlignCenter, "🍀")
        
        # 恢复画笔状态
        painter.restore()


class QuoteBoard(QWidget):
    def __init__(
        self,
        quotes: List[Quote],
        compliments: Optional[List[Achievement]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        
        # 背景透明度属性（用于动画）
        self._background_opacity = 1.0

        text_quotes = [quote for quote in quotes if quote.category == "text"]
        book_quotes = [quote for quote in quotes if quote.category == "book"]
        others = [quote for quote in quotes if quote.category not in {"text", "book"}]

        self.intro_quote: Optional[Quote] = text_quotes.pop(0) if text_quotes else None

        self.text_quotes: Deque[Quote] = deque(text_quotes)
        self.text_count = len(self.text_quotes)
        self.text_shown = 0
        self.text_finished = self.text_count == 0
        self.text_interval_ms = 800

        self.book_quotes: Deque[Quote] = deque(book_quotes)
        self.book_total = len(self.book_quotes)
        self.book_interval_ms = 1200
        self.book_shown = 0
        self.books_finished = self.book_total == 0
        self.book_grid_positions: List[QRect] = []
        self.book_grid_index = 0
        self.book_cards: List[QuoteCard] = []
        self.book_max_visible = 3
        self.book_batch_count = 0

        self.other_quotes: Deque[Quote] = deque(others)
        self.compliments = compliments or []

        if not self.text_finished:
            self.card_phase: str = "text"
        elif self.book_total:
            self.card_phase = "book"
        elif self.other_quotes:
            self.card_phase = "other"
        else:
            self.card_phase = "idle"

        self.cards_container = QWidget(self)
        self.cards_container.setObjectName("cardsContainer")
        self.cards_container.setMouseTracking(True)
        # 设置透明背景，否则会遮挡背景图
        self.cards_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.cards_container.setStyleSheet("background: transparent;")
        
        print(f"初始化: book_total={self.book_total}, books_finished={self.books_finished}")
        print(f"cards_container 是否透明: {self.cards_container.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)}")

        self.card_manager = CardManager(self.cards_container)

        self.snow_effect = SnowEffect(self)
        self.snow_effect.lower()
        # 确保雪花效果透明，不遮挡背景
        self.snow_effect.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.snow_effect.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.fireworks_overlays: List[FireworksOverlay] = [FireworksOverlay(self) for _ in range(18)]
        for overlay in self.fireworks_overlays:
            overlay.lower()

        self.heart_firework_colors = [
            QColor("#ff6b6b"),
            QColor("#ffd93d"),
            QColor("#6bc5ff"),
            QColor("#a38bff"),
            QColor("#6bff95"),
            QColor("#ff9ff3"),
            QColor("#ff6ec7"),
            QColor("#54a0ff"),
            QColor("#ffbe76"),
            QColor("#ff7979"),
        ]

        self.splash = SplashOverlay(self)

        self.paused = False
        self.distraction_free = False
        self.hover_card: Optional[QuoteCard] = None
        self.intro_card: Optional[QuoteCard] = None
        self.intro_timer: Optional[QTimer] = None
        self.intro_full_text = ""
        self.intro_index = 0

        self.compliment_timer: Optional[QTimer] = None
        self.compliment_full_text = ""
        self.compliment_char_index = 0

        self.background_color = QColor("#f7f5f3")
        # 默认背景图（text.json阶段）
        self.default_background = QPixmap(
            "/Users/kyrie/Desktop/happy/ChatGPT Image Nov 1, 2025, 12_47_46 PM.png"
        )
        # 烟花阶段的背景图（迪士尼城堡）
        self.fireworks_background = QPixmap(
            "/Users/kyrie/Desktop/happy/Gemini_Generated_Image_q0r36jq0r36jq0r3.png"
        )
        if self.fireworks_background.isNull():
            print("警告: 迪士尼城堡背景图 加载失败")
        else:
            print(f"迪士尼城堡背景图 加载成功，尺寸: {self.fireworks_background.width()}x{self.fireworks_background.height()}")
        
        # book.json阶段的背景图（圣诞主题）
        self.book_background = QPixmap(
            "/Users/kyrie/Desktop/happy/WechatIMG407.jpg"
        )
        if self.book_background.isNull():
            print("警告: WechatIMG407.jpg 加载失败")
        else:
            print(f"WechatIMG407.jpg 加载成功，尺寸: {self.book_background.width()}x{self.book_background.height()}")
        
        self.background_pixmap = self.default_background

        self.card_timer = QTimer(self)
        self.card_timer.setSingleShot(True)
        self.card_timer.timeout.connect(self._on_card_timer)

        self.compliment_label = QLabel("", self)
        self.compliment_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.compliment_label.setStyleSheet(
            "background: rgba(0, 0, 0, 0.42);"
            "color: #ffffff;"
            "padding: 14px 28px;"
            "border-radius: 18px;"
            "letter-spacing: 1px;"
        )
        self.compliment_label.setFont(QFont("Source Han Sans", 26, QFont.Weight.DemiBold))
        self.compliment_label.hide()

        self.heart_fireworks_timer = QTimer(self)
        self.heart_fireworks_timer.setSingleShot(True)
        self.heart_fireworks_timer.timeout.connect(self._run_heart_fireworks_cycle)
        self.heart_fireworks_limit = len(compliments) if compliments else 3
        self.heart_fireworks_count = 0
        self.heart_fireworks_interval_ms = 2000  # 保留作为最小间隔，实际使用动态计算
        self.compliment_char_interval_ms = 120  # 每个字符显示的间隔时间（毫秒）
        self.compliment_index = 0
        self.post_heart_pending = False
        self.current_compliment_text = ""  # 当前显示的祝福语文本，用于计算显示时间
        
        self._last_paint_phase = ""  # 记录上次绘制的阶段，避免重复日志
        
        # 背景图淡入动画相关
        self.background_opacity = 1.0  # 背景图透明度
        self.background_fade_animation: Optional[QPropertyAnimation] = None

        # 🍀展示时长（毫秒）
        self.emoji_show_ms = 2000

        self.clover_overlay = CloverEmojiOverlay(self)
        self.clover_overlay.hide()

        self.heart_fade_ms = 1600
    
    def get_background_opacity(self) -> float:
        return self._background_opacity
    
    def set_background_opacity(self, value: float) -> None:
        self._background_opacity = max(0.0, min(1.0, value))
        self.update()
    
    background_opacity = Property(float, get_background_opacity, set_background_opacity)

    def start(self) -> None:
        self.splash.setGeometry(self.rect())
        self.splash.start(3000, self._after_splash)

    # region 生命周期
    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        rect = self.rect()
        self.cards_container.setGeometry(rect)
        self.snow_effect.setGeometry(rect)
        self.splash.setGeometry(rect)
        for overlay in self.fireworks_overlays:
            overlay.setGeometry(rect)
        self.clover_overlay.setGeometry(rect)
        self.card_manager.set_viewport_size(rect.size())
        if self.compliment_label.isVisible():
            self.compliment_label.adjustSize()
            target_y = rect.center().y() + int(rect.height() * 0.30)
            self.compliment_label.move(
                rect.center().x() - self.compliment_label.width() // 2,
                target_y,
            )

    # endregion

    # region 启动流程
    def _after_splash(self) -> None:
        self.splash.hide()
        self._show_intro_card()

    def _show_intro_card(self) -> None:
        quote = self._intro_quote()
        self.intro_card = QuoteCard(quote)
        self.intro_card.setParent(self)
        self.intro_card.content_label.setText("")
        size = self.intro_card.sizeHint()
        width = max(420, size.width())
        height = max(260, size.height())
        self.intro_card.resize(width, height)
        center = self.rect().center()
        self.intro_card.move(center.x() - width // 2, center.y() - height // 2)
        self.intro_card.show()
        self.intro_card.fade_in()

        self.intro_full_text = quote.text
        self.intro_index = 0
        self.intro_timer = QTimer(self)
        self.intro_timer.timeout.connect(self._typewriter_step)
        self.intro_timer.start(60)
        QTimer.singleShot(5200, self._finish_intro)

    def _intro_quote(self) -> Quote:
        # 固定返回"听听音乐，让大脑放松一下。"
        fixed_text = "听听音乐，让大脑放松一下。"
        
        # 如果intro_quote已设置且是目标文本，使用它
        if self.intro_quote is not None and self.intro_quote.text == fixed_text:
            quote = self.intro_quote
            self.intro_quote = None
            return quote
        
        # 从text_quotes中查找目标文本
        for idx, quote in enumerate(self.text_quotes):
            if quote.text == fixed_text:
                return self.text_quotes[idx]
        
        # 如果没找到，创建一个
        return Quote(text=fixed_text, color="#E6E6FA", category="text")

    def _typewriter_step(self) -> None:
        if not self.intro_card:
            return
        self.intro_index += 1
        text = self.intro_full_text[: self.intro_index]
        self.intro_card.content_label.setText(text)
        if self.intro_index >= len(self.intro_full_text):
            if self.intro_timer:
                self.intro_timer.stop()

    def _finish_intro(self) -> None:
        if self.intro_timer:
            self.intro_timer.stop()
        if not self.intro_card:
            self._start_card_loop()
            return

        def _after_fade():
            if self.intro_card:
                self.intro_card.deleteLater()
            self.intro_card = None
            self._start_card_loop()

        self.intro_card.fade_out(_after_fade)

    # endregion

    def _start_card_loop(self) -> None:
        if not self.text_finished:
            self.card_phase = "text"
            self._schedule_next_card()
        else:
            self._start_regular_loop()

    def _start_regular_loop(self) -> None:
        if self.card_phase in {"post_fireworks"}:
            return
        if self.card_phase != "text" and not self.text_finished:
            self.card_phase = "text"
        elif self.card_phase != "book" and self.book_total and not self.books_finished:
            self.card_phase = "book"
        elif self.card_phase != "other" and (not self.book_total or self.books_finished) and self.other_quotes:
            self.card_phase = "other"
        elif not self.other_quotes and (self.books_finished or not self.book_total) and self.text_finished:
            self.card_phase = "idle"
            return
        self._schedule_next_card()

    def _init_book_grid(self) -> None:
        """初始化 book 卡片的网格布局（右半部分）"""
        print(f"[_init_book_grid] 调用，book_quotes={len(self.book_quotes)}")
        if not self.book_quotes:
            print("[_init_book_grid] book_quotes 为空，返回")
            return

        rect = self.cards_container.rect()
        print(f"[_init_book_grid] 容器尺寸: {rect.width()}x{rect.height()}")
        if rect.width() <= 0 or rect.height() <= 0:
            print("[_init_book_grid] 容器尺寸无效，返回")
            return

        start_x = rect.width() * 0.5
        margin = 30
        card_width = 320
        card_height = 200

        cols = 1
        rows = 3

        available_width = rect.width() - start_x - margin * 2
        available_height = rect.height() - margin * 2

        spacing_x = (available_width - card_width * cols) / (cols + 1) if cols > 0 else 0
        spacing_y = (available_height - card_height * rows) / (rows + 1) if rows > 0 else 0

        self.book_grid_positions = []
        for row in range(rows):
            for col in range(cols):
                x = int(start_x + margin + spacing_x * (col + 1) + card_width * col)
                y = int(margin + spacing_y * (row + 1) + card_height * row)
                self.book_grid_positions.append(QRect(x, y, card_width, card_height))

        print(f"[_init_book_grid] 生成了 {len(self.book_grid_positions)} 个网格位置")
        if self.book_grid_positions:
            print(f"[_init_book_grid] 第一个位置: {self.book_grid_positions[0]}")

    def _after_text_fade_out(self) -> None:
        """text 淡出后，切换背景并开始下一阶段"""
        print("[_after_text_fade_out] text 淡出完成")
        if self.book_total and not self.books_finished:
            print(f"[_after_text_fade_out] 切换到 book 阶段，book_total={self.book_total}")
            self.card_phase = "book"
            self.background_pixmap = self.book_background
            self.set_background_opacity(1.0)
            self.update()
            self._init_book_grid()
            QTimer.singleShot(500, self._schedule_next_card)
        else:
            self._start_fireworks_phase()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self.background_color)
        
        if not self.background_pixmap.isNull():
            # post_fireworks/book/other阶段使用全屏背景图
            if self.card_phase in ("post_fireworks", "book", "other"):
                # 只在阶段切换时打印日志
                if self._last_paint_phase != self.card_phase:
                    print(f"[paintEvent] 阶段切换: {self._last_paint_phase} -> {self.card_phase}")
                    print(f"[paintEvent] 窗口尺寸={self.size()}, pixmap尺寸={self.background_pixmap.size()}")
                    self._last_paint_phase = self.card_phase
                
                # 按比例缩放至全屏
                scaled = self.background_pixmap.scaled(
                    self.size(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
                # 居中裁剪
                x = (self.width() - scaled.width()) // 2
                y = (self.height() - scaled.height()) // 2
                painter.save()
                painter.setOpacity(self._background_opacity)
                painter.drawPixmap(x, y, scaled)
                painter.restore()
            else:
                # text阶段使用底部小图
                available_height = int(self.height() * 0.32)
                if available_height > 0:
                    scaled = self.background_pixmap.scaledToHeight(
                        available_height, Qt.TransformationMode.SmoothTransformation
                    )
                    margin_x = int(self.width() * 0.05)
                    margin_y = int(self.height() * 0.05)
                    x = margin_x
                    y = self.height() - scaled.height() - margin_y
                    painter.save()
                    painter.setOpacity(self._background_opacity)
                    painter.drawPixmap(x, y, scaled)
                    painter.restore()
        super().paintEvent(event)

    def _start_fireworks_phase(self) -> None:
        print("开始烟花阶段，切换到城堡背景")
        self.card_phase = "post_fireworks"
        self.post_heart_pending = True
        self.heart_fireworks_count = 0
        self.compliment_index = 0

        self.background_pixmap = self.fireworks_background
        self.set_background_opacity(1.0)
        self.update()
        QTimer.singleShot(500, self._start_heart_fireworks)

    def _start_heart_fireworks(self) -> None:
        if not self.fireworks_overlays:
            return
        print("开始播放烟花，切换到迪士尼城堡背景图")
        # 切换到烟花背景图
        self.background_pixmap = self.fireworks_background
        # 确保背景是完全不变暗的
        self.set_background_opacity(1.0)
        self.update()
        self.heart_fireworks_count = 0
        self._run_heart_fireworks_cycle()

    def _fade_to_fireworks_background(self) -> None:
        """先淡入迪士尼背景，结束后再启动烟花。"""
        self.background_pixmap = self.fireworks_background
        # 从0到1做淡入
        if self.background_fade_animation and self.background_fade_animation.state() == QPropertyAnimation.Running:
            self.background_fade_animation.stop()
        self.set_background_opacity(0.0)
        self.background_fade_animation = QPropertyAnimation(self, b"background_opacity")
        self.background_fade_animation.setDuration(1000)
        self.background_fade_animation.setStartValue(0.0)
        self.background_fade_animation.setEndValue(1.0)
        self.background_fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.background_fade_animation.finished.connect(self._after_background_fade_in)
        self.background_fade_animation.start()

    def _after_background_fade_in(self) -> None:
        """背景淡入后停顿2s再播放烟花。"""
        self.set_background_opacity(1.0)
        QTimer.singleShot(2000, self._start_heart_fireworks)

    def _fade_out_emoji_and_cards(self) -> None:
        """让🍀和 text 一起淡出。"""
        # 隐藏🍀（已有0.5s淡出动画）
        self.clover_overlay.hide_emoji()
        # 淡出所有心形卡片
        self._dismiss_heart_cards()

    def _stop_heart_fireworks(self) -> None:
        if self.heart_fireworks_timer.isActive():
            self.heart_fireworks_timer.stop()
        self.heart_fireworks_count = self.heart_fireworks_limit
        for overlay in self.fireworks_overlays:
            overlay.hide()
        self.compliment_label.hide()

    def _run_heart_fireworks_cycle(self) -> None:
        self._show_compliment()
        self._heart_fireworks_burst()
        self.heart_fireworks_count += 1
        self.set_background_opacity(1.0)
        print(f"烟花轮次: {self.heart_fireworks_count}/{self.heart_fireworks_limit}")
        
        # 动态计算间隔时间：确保上一轮祝福语完全显示
        # 计算时间 = 字符数 × 字符间隔时间 + 额外停留时间（让用户有时间阅读）
        if self.current_compliment_text:
            text_length = len(self.current_compliment_text)
            typing_duration = text_length * self.compliment_char_interval_ms
            # 额外停留时间：根据文本长度动态调整，最少1秒，最多3秒
            extra_display_time = min(3000, max(1000, text_length * 20))
            dynamic_interval = typing_duration + extra_display_time
        else:
            dynamic_interval = self.heart_fireworks_interval_ms
        
        if self.heart_fireworks_count < self.heart_fireworks_limit:
            print(f"下一条祝福语将在 {dynamic_interval}ms 后显示（文本长度: {len(self.current_compliment_text) if self.current_compliment_text else 0} 字符）")
            self.heart_fireworks_timer.start(dynamic_interval)
        else:
            print(f"所有 zanshang.json 内容显示完成，等待 {dynamic_interval}ms 后切换阶段")
            self.heart_fireworks_timer.stop()
            QTimer.singleShot(dynamic_interval, self._after_heart_fireworks_complete)

    def _heart_fireworks_burst(self) -> None:
        if not self.fireworks_overlays:
            return
        rect = self.rect()
        if rect.isEmpty():
            return

        total = len(self.fireworks_overlays)
        for index, overlay in enumerate(self.fireworks_overlays):
            color = self.heart_firework_colors[index % len(self.heart_firework_colors)]

            target_x = rect.width() * random.uniform(0.15, 0.85)
            target_y = rect.height() * random.uniform(0.15, 0.45)
            position = QPointF(target_x, target_y)

            overlay.setGeometry(rect)
            overlay.raise_()
            overlay.trigger(color, position, simultaneous=True, bursts=1, particle_count=90, launch_from_bottom=True)

    def _show_compliment(self) -> None:
        if not self.compliments:
            self.compliment_label.hide()
            return
        if self.compliment_index >= len(self.compliments):
            self.compliment_label.hide()
            return
        compliment = self.compliments[self.compliment_index]
        self.compliment_index += 1

        self.compliment_full_text = compliment.text
        self.current_compliment_text = compliment.text  # 保存当前祝福语文本，用于计算显示时间
        self.compliment_char_index = 0
        self.compliment_label.setText("")

        rect = self.rect()
        target_y = rect.center().y() + int(rect.height() * 0.30)
        self.compliment_label.move(
            rect.center().x() - 400,
            target_y,
        )
        self.compliment_label.setMinimumWidth(800)
        self.compliment_label.raise_()
        self.compliment_label.show()

        if self.compliment_timer:
            self.compliment_timer.stop()
        self.compliment_timer = QTimer(self)
        self.compliment_timer.timeout.connect(self._compliment_typewriter_step)
        self.compliment_timer.start(self.compliment_char_interval_ms)

    def _compliment_typewriter_step(self) -> None:
        if self.compliment_char_index < len(self.compliment_full_text):
            self.compliment_char_index += 1
            text = self.compliment_full_text[:self.compliment_char_index]
            self.compliment_label.setText(text)
        else:
            if self.compliment_timer:
                self.compliment_timer.stop()

    def _after_heart_fireworks_complete(self) -> None:
        if not self.post_heart_pending:
            return
        self.post_heart_pending = False
        if self.compliment_timer:
            self.compliment_timer.stop()
        self.compliment_label.hide()

        print(f"烟花结束 - other_quotes: {len(self.other_quotes)}")

        if self.other_quotes:
            self.card_phase = "other"
        else:
            self.card_phase = "idle"
        self._start_regular_loop()

    def _schedule_next_card(self) -> None:
        if self.paused or self.card_phase in {"idle", "post_fireworks"}:
            return
        if self.card_timer.isActive():
            return
        interval = self._next_interval()
        if interval is None:
            return
        self.card_timer.start(interval)

    def _next_interval(self) -> Optional[int]:
        if self.card_phase == "text":
            if self.text_quotes:
                return self.text_interval_ms
            return None
        if self.card_phase == "book":
            if self.book_quotes:
                return self.book_interval_ms
            return None
        if self.card_phase == "other":
            if self.other_quotes:
                return random.randint(2400, 3200)
        return None

    def _on_card_timer(self) -> None:
        self.card_timer.stop()
        if self.paused or self.card_phase not in {"text", "book", "other"}:
            return
        self._add_new_card()
        self._schedule_next_card()

    def _next_quote(self) -> Quote:
        if self.card_phase == "text" and self.text_quotes:
            self.text_shown += 1
            return self.text_quotes.popleft()
        if self.card_phase == "book" and self.book_quotes:
            self.book_shown += 1
            return self.book_quotes.popleft()
        if self.card_phase == "other" and self.other_quotes:
            return self.other_quotes.popleft()
        raise RuntimeError("没有可用的金句数据")

    def _add_new_card(self) -> None:
        quote = self._next_quote()
        card = QuoteCard(quote)
        card.hovered.connect(self._on_card_hovered)
        card.unhovered.connect(self._on_card_unhovered)

        if quote.category == "text":
            self.card_manager.add_card(card)
            if not self.text_quotes and not self.text_finished:
                self.text_finished = True
                print("text 完成，淡出所有卡片")
                self.card_manager.fade_out_all(self._after_text_fade_out)
                return
        elif quote.category == "book":
            print(f"[_add_new_card] 添加 book 卡片，当前显示={len(self.book_cards)}, batch_count={self.book_batch_count}")
            if self.book_grid_positions:
                card.setParent(self.cards_container)

                if self.book_batch_count >= self.book_max_visible:
                    print(f"[_add_new_card] 批次已满({self.book_batch_count}张)，清空所有卡片")
                    self._clear_book_batch()
                    self.book_batch_count = 0

                position_index = self.book_batch_count
                base_rect = self.book_grid_positions[position_index]
                size_hint = card.sizeHint()
                actual_width = max(size_hint.width(), base_rect.width())
                actual_height = max(size_hint.height(), base_rect.height())
                adjusted_rect = QRect(base_rect.x(), base_rect.y(), actual_width, actual_height)
                card.setGeometry(adjusted_rect)
                print(f"[_add_new_card] 卡片定位到网格位置[{position_index}]")

                self.book_cards.append(card)
                self.book_batch_count += 1

                card.show()
                card.raise_()
                card.fade_in()

                print(f"[_add_new_card] book 卡片已添加，当前 book_cards 数量: {len(self.book_cards)}")
            else:
                print(f"[_add_new_card] 警告：网格位置未初始化")
            if not self.book_quotes and not self.books_finished:
                self.books_finished = True
                print("book 完成，淡出所有卡片")
                self._fade_out_book_cards()
                return
        else:
            self.card_manager.add_card(card)

        if self.card_phase not in {"idle", "post_fireworks"}:
            self._schedule_next_card()

    def _clear_book_batch(self) -> None:
        """清空当前批次的 book 卡片"""
        if not self.book_cards:
            return
        print(f"[_clear_book_batch] 清空 {len(self.book_cards)} 张卡片")
        for card in self.book_cards:
            card.fade_out(card.deleteLater)
        self.book_cards = []

    def _fade_out_book_cards(self) -> None:
        """淡出所有 book 卡片"""
        if not self.book_cards:
            self._after_book_fade_out()
            return

        for card in self.book_cards:
            card.fade_out(card.deleteLater)

        self.book_cards = []
        QTimer.singleShot(1600, self._after_book_fade_out)

    def _after_book_fade_out(self) -> None:
        """book 卡片淡出后，切换背景并开始烟花"""
        print("book 卡片淡出完成，切换到城堡背景，准备烟花")
        self._start_fireworks_phase()

    # region 互动状态
    def _on_card_hovered(self, card: QuoteCard) -> None:
        self.hover_card = card

    def _on_card_unhovered(self, card: QuoteCard) -> None:
        if self.hover_card is card:
            self.hover_card = None

    def favorite_current(self) -> None:
        pass

    # endregion

    # region 控制逻辑
    def toggle_pause(self) -> None:
        self.paused = not self.paused
        if self.paused:
            if self.card_timer.isActive():
                self.card_timer.stop()
            self.snow_effect.pause()
            if self.heart_fireworks_timer and self.heart_fireworks_timer.isActive():
                self.heart_fireworks_timer.stop()
            if self.compliment_timer and self.compliment_timer.isActive():
                self.compliment_timer.stop()
            self.compliment_label.hide()
        else:
            self.snow_effect.resume()
            if self.card_phase not in {"idle", "post_fireworks"}:
                self._schedule_next_card()
            if (
                self.post_heart_pending
                and self.heart_fireworks_count < self.heart_fireworks_limit
                and not self.heart_fireworks_timer.isActive()
            ):
                self.heart_fireworks_timer.start(self.heart_fireworks_interval_ms)

    def toggle_distraction_free(self) -> None:
        self.distraction_free = not self.distraction_free
        self.cards_container.setVisible(not self.distraction_free)
        if not self.distraction_free:
            if self.post_heart_pending and self.heart_fireworks_count < self.heart_fireworks_limit:
                self.compliment_label.show()

    # endregion

