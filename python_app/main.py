from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication, QMainWindow

try:  # 支持作为脚本直接运行
    from .board import QuoteBoard
    from .data_loader import load_quotes, load_achievements
except ImportError:  # pragma: no cover - 仅在脚本模式下使用
    if __package__ in (None, ""):
        package_dir = Path(__file__).resolve().parent
        project_root = package_dir.parent
        if str(project_root) not in sys.path:
            sys.path.append(str(project_root))
        from python_app.board import QuoteBoard  # type: ignore[no-redef]
        from python_app.data_loader import load_quotes, load_achievements  # type: ignore[no-redef]
    else:
        raise


class MainWindow(QMainWindow):
    def __init__(self, board: QuoteBoard) -> None:
        super().__init__()
        self.board = board
        self._started = False
        self.setCentralWidget(board)
        self.setWindowTitle("温馨金句 - Python 版")
        self.setStyleSheet("background-color: #f7f5f3;")
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if not self._started:
            self._started = True
            QTimer.singleShot(100, self.board.start)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.isAutoRepeat():
            return
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.close()
        elif key == Qt.Key.Key_Space:
            self.board.toggle_pause()
        elif key == Qt.Key.Key_F:
            self.board.favorite_current()
        elif key == Qt.Key.Key_D:
            self.board.toggle_distraction_free()
        else:
            super().keyPressEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("温馨金句")

    # 尝试载入项目自带字体（若存在）
    fonts_dir = Path(__file__).resolve().parent.parent / "assets" / "fonts"
    if fonts_dir.exists():
        for font_path in fonts_dir.glob("*.ttf"):
            QFontDatabase.addApplicationFont(str(font_path))

    data_dir = Path(__file__).resolve().parent.parent / "data"
    quotes = load_quotes(data_dir)
    if not quotes:
        raise RuntimeError("未在 data 目录中找到金句数据")
    compliments = load_achievements(data_dir)
    board = QuoteBoard(quotes, compliments)

    window = MainWindow(board)
    window.showFullScreen()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

