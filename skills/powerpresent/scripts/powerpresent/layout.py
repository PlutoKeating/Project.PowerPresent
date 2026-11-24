"""版面网格：用矩形切分代替手算坐标。

所有组件都接收一个 Rect。先从页面的内容区出发，按列、按行、按比例切出若干矩形，
再把组件放进去，这样间距和对齐天然一致。
"""
from __future__ import annotations

from dataclasses import dataclass

from .theme import GAP


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    def inset(self, dx: float, dy: float | None = None) -> "Rect":
        dy = dx if dy is None else dy
        return Rect(self.x + dx, self.y + dy, self.w - 2 * dx, self.h - 2 * dy)

    def cols(self, spec=2, gap: float = GAP) -> list["Rect"]:
        """切成若干列。spec 是列数，或各列的宽度比例，例如 [2, 1]。"""
        ratios = [1] * spec if isinstance(spec, int) else list(spec)
        usable = self.w - gap * (len(ratios) - 1)
        out, x = [], self.x
        for r in ratios:
            w = usable * r / sum(ratios)
            out.append(Rect(x, self.y, w, self.h))
            x += w + gap
        return out

    def rows(self, spec=2, gap: float = GAP) -> list["Rect"]:
        """切成若干行。spec 是行数，或各行的高度比例。"""
        ratios = [1] * spec if isinstance(spec, int) else list(spec)
        usable = self.h - gap * (len(ratios) - 1)
        out, y = [], self.y
        for r in ratios:
            h = usable * r / sum(ratios)
            out.append(Rect(self.x, y, self.w, h))
            y += h + gap
        return out

    def grid(self, columns: int, rows: int, gap: float = GAP) -> list["Rect"]:
        """切成 columns x rows 的格子，按行优先返回。"""
        return [cell for row in self.rows(rows, gap) for cell in row.cols(columns, gap)]

    def take_top(self, h: float, gap: float = GAP) -> tuple["Rect", "Rect"]:
        """从顶部切下高 h 的一条，返回 (这一条, 剩余部分)。"""
        return Rect(self.x, self.y, self.w, h), Rect(self.x, self.y + h + gap, self.w, self.h - h - gap)

    def take_bottom(self, h: float, gap: float = GAP) -> tuple["Rect", "Rect"]:
        return Rect(self.x, self.bottom - h, self.w, h), Rect(self.x, self.y, self.w, self.h - h - gap)

    def take_left(self, w: float, gap: float = GAP) -> tuple["Rect", "Rect"]:
        return Rect(self.x, self.y, w, self.h), Rect(self.x + w + gap, self.y, self.w - w - gap, self.h)


# ---------------------------------------------------------------- 文字度量

def px(size_pt: float) -> float:
    """字号（磅）对应的汉字宽高（画布像素）。"""
    return size_pt / 0.6


def line_height(size_pt: float, leading: float = 1.0) -> float:
    return px(size_pt) * 1.3 * leading


def text_width(text: str, size_pt: float) -> float:
    """粗略估算一行文字的宽度：汉字与全角标点按一个字宽，其余按半个多一点。"""
    plain = text.replace("**", "")
    return sum(px(size_pt) * (1.0 if ord(ch) > 0x2E7F else 0.52) for ch in plain)
