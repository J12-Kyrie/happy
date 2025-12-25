from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Iterable, List, Sequence

from .models import Achievement, Quote


def _normalise_quote_entries(entries: Iterable[dict], category: str) -> List[Quote]:
    quotes: List[Quote] = []
    for item in entries:
        text = item.get("text")
        color = item.get("color", "#ffffff")
        if not text:
            continue
        quotes.append(Quote(text=text.strip(), color=color, category=category))
    return quotes


def _load_json(path: Path) -> Sequence:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        # 兼容 plan_detail.md 中提到的结构
        if "quotes" in data:
            return data["quotes"]
        if "greetings" in data:
            return data["greetings"]
        if "achievements" in data:
            return data["achievements"]
        return list(data.values())
    if isinstance(data, list):
        return data
    raise ValueError(f"Unsupported JSON structure in {path}")


def load_quotes(data_dir: Path) -> List[Quote]:
    mapping = {
        "text.json": "text",
        "book.json": "book",
    }

    categorised: dict[str, List[Quote]] = {"text": [], "book": []}
    for filename, category in mapping.items():
        path = data_dir / filename
        if not path.exists():
            continue
        entries = _load_json(path)
        quotes = _normalise_quote_entries(entries, category)
        # 不需要在这里处理优先级，让board.py从text_quotes中取
        categorised[category].extend(quotes)

    # 去重：同一分类下按文本去重，避免不同类型之间相互覆盖
    for category, quote_list in categorised.items():
        unique: dict[str, Quote] = {}
        for quote in quote_list:
            unique.setdefault(quote.text, quote)
        shuffled = list(unique.values())
        random.shuffle(shuffled)
        categorised[category] = shuffled

    ordered = categorised["text"] + categorised["book"]
    if not ordered:
        return []

    # 若存在其它类型（未来扩展），保持随机性
    remaining_categories = [
        quotes for key, quotes in categorised.items() if key not in {"text", "book"}
    ]
    for extra in remaining_categories:
        ordered.extend(extra)

    return ordered


def load_achievements(data_dir: Path) -> List[Achievement]:
    path = data_dir / "zanshang.json"
    if not path.exists():
        return []
    entries = _load_json(path)
    achievements = []
    for item in entries:
        if isinstance(item, dict):
            text = item.get("text")
            color = item.get("color", "#FFD580")
        else:
            text = str(item)
            color = "#FFD580"
        if not text:
            continue
        achievements.append(Achievement(text=text.strip(), color=color))

    if not achievements:
        achievements.append(
            Achievement(
                text="恭喜你达成收藏成就！继续保持这份热爱。",
                color="#FFD580",
            )
        )
    return achievements

