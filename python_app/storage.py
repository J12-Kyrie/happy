from __future__ import annotations

import json
from pathlib import Path
from typing import Set


class FavoriteStorage:
    """收藏状态管理（默认仅运行期有效，不持久化到磁盘）。"""

    def __init__(self, filename: str = ".jtter_favorites.json", persist: bool = False) -> None:
        self.persist = persist
        self.path = Path.home() / filename if persist else None
        if self.persist and self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Set[str]:
        if not self.persist or self.path is None:
            return set()
        if not self.path.exists():
            return set()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return {str(item) for item in data}
        except Exception:
            return set()
        finally:
            try:
                self.path.unlink()
            except Exception:
                pass
        return set()

    def save(self, favorites: Set[str]) -> None:
        if not self.persist or self.path is None:
            return
        try:
            self.path.write_text(
                json.dumps(sorted(favorites), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

