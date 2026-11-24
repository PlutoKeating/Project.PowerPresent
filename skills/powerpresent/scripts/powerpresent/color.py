"""感知均匀色彩空间 OKLCH 的换算工具。

配色不在 RGB 或 HSL 里凭感觉挑，而是在 OKLCH 里按规则生成：
L 是感知明度（0～1），C 是彩度（0 为灰，常用到 0.2 左右），H 是色相角（0～360）。
在这个空间里，L 相同的颜色看起来一样亮，C 相同的颜色看起来一样鲜艳，
所以“同一组标签取相同的 L 和 C、只变 H”就能得到天然协调的一组颜色。

换算公式取自 Björn Ottosson 的 OKLab 定义。
"""
from __future__ import annotations

import math


def _to_linear(v: float) -> float:
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _to_gamma(v: float) -> float:
    return 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055


def _oklab_to_linear_rgb(L: float, a: float, b: float) -> tuple[float, float, float]:
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
            -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
            -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)


def oklch(L: float, C: float, H: float) -> str:
    """OKLCH -> "#RRGGBB"。超出 sRGB 色域时保持明度与色相不变、逐步降低彩度，直到落回色域内。"""
    L = min(max(L, 0.0), 1.0)
    low, high = 0.0, C
    rgb = None
    for step in range(24):
        chroma = high if step == 0 else (low + high) / 2
        a, b = chroma * math.cos(math.radians(H)), chroma * math.sin(math.radians(H))
        candidate = _oklab_to_linear_rgb(L, a, b)
        if all(-1e-4 <= v <= 1 + 1e-4 for v in candidate):
            rgb = candidate
            if step == 0:
                break
            low = chroma
        else:
            high = chroma
    if rgb is None:
        rgb = _oklab_to_linear_rgb(L, 0, 0)
    return "#" + "".join(f"{round(min(max(_to_gamma(min(max(v, 0), 1)), 0), 1) * 255):02X}" for v in rgb)


def to_oklch(color: str) -> tuple[float, float, float]:
    """"#RRGGBB" -> (L, C, H)。"""
    color = color.lstrip("#")
    r, g, b = (_to_linear(int(color[i:i + 2], 16) / 255) for i in (0, 2, 4))
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b2 = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return L, math.hypot(a, b2), math.degrees(math.atan2(b2, a)) % 360


def mix(a: str, b: str, t: float) -> str:
    """两个颜色在 OKLab 空间里按比例混合：t=0 得到 a，t=1 得到 b。比在 RGB 里混合更不容易发灰。"""
    la, ca, ha = to_oklch(a)
    lb, cb, hb = to_oklch(b)
    ax, ay = ca * math.cos(math.radians(ha)), ca * math.sin(math.radians(ha))
    bx, by = cb * math.cos(math.radians(hb)), cb * math.sin(math.radians(hb))
    x, y = ax + (bx - ax) * t, ay + (by - ay) * t
    return oklch(la + (lb - la) * t, math.hypot(x, y), math.degrees(math.atan2(y, x)) % 360)


def contrast(a: str, b: str) -> float:
    """WCAG 对比度。"""
    def luminance(color):
        color = color.lstrip("#")
        r, g, b_ = (_to_linear(int(color[i:i + 2], 16) / 255) for i in (0, 2, 4))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b_
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)
