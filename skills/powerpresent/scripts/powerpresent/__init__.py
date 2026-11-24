"""PowerPresent：可编辑 PPTX 的绘制库与组件库。"""
from .canvas import CANVAS_H, CANVAS_W, Deck, Slide, lin, polygon, rad
from .components import Kit, Page
from .layout import Rect
from .theme import DEFAULT_PALETTE, PALETTES, Theme

__all__ = ["CANVAS_H", "CANVAS_W", "Deck", "Kit", "DEFAULT_PALETTE", "PALETTES", "Page", "Rect", "Slide", "Theme", "lin", "polygon", "rad"]
