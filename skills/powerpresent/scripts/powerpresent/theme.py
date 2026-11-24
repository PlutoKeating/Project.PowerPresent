"""PowerPresent 设计令牌：唯一的一套配色、字体与字号，分深色底与浅色底两种用法。

所有组件只从这里取值，不在别处写死颜色或字号；要改视觉，改这一个文件。
规则说明与取舍理由见 references/design-system.md。
"""
from __future__ import annotations

from .canvas import lin
from .color import oklch, to_oklch

# ------------------------------------------------------------------ 配色
# 配色不凭感觉挑，按三条规则生成（依据见 references/design-system.md 第 2 节）：
#   1. 主色、强调色、图示色相、图表系列色，取自公开发表的色盲友好色卡（Paul Tol、Okabe-Ito）。
#   2. 其余颜色在感知均匀的 OKLCH 空间里派生：同一组标签固定明度 L 与彩度 C、只换色相 H。
#   3. 中性色（纸、面、线、墨）成一个体系，至多带极低的色偏；深色底单独取值，不靠反色。

PALETTES = {
    # journal 期刊蓝与赭黄（学术场景首选）：主色、强调色、第三色即 Paul Tol 的 high-contrast 三色；图示色相与图表系列取 Tol bright。
    "journal": {
        "light": {"paper": "#F5F7F9", "surface": "#EAEDF1", "line": "#D0D5D9", "ink": "#171D26", "muted": "#636A71",
                  "primary": "#004488", "accent": "#DDAA33", "emphasis": "#BB5566"},
        "dark": {"paper": "#0E141D", "surface": "#171F28", "line": "#2F3640", "ink": "#FFFFFF", "muted": "#DDE2E8",
                 "primary": "#71A8E8", "accent": "#E5B650", "emphasis": "#E5B650",
                 "block": "#1F5FA8", "block_text": "#F5F7F9"},     # 深色底上的色块：中等明度的蓝，比背景亮、比文字暗
        "hues": {"primary": 251, "accent": 145, "warm": 95, "alert": 17, "cyan": 215, "purple": 350},
        "series": ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377"],
    },
    # ink 墨与朱（商业场景首选）：纯灰的中性色，没有彩色主色，全稿只有一个朱色强调；图示色相与图表系列取 Okabe-Ito。
    "ink": {
        "light": {"paper": "#F7F7F7", "surface": "#EBEBEB", "line": "#D1D1D1", "ink": "#161616", "muted": "#636363",
                  "primary": "#161616", "accent": "#D55E00", "emphasis": "#B14A00"},
        "dark": {"paper": "#0F0F0F", "surface": "#1B1B1B", "line": "#333333", "ink": "#FFFFFF", "muted": "#E0E0E0",
                 "primary": "#E8E8E8", "accent": "#F27636", "emphasis": "#F27636"},
        "hues": {"primary": 245, "accent": 165, "warm": 75, "alert": 40, "cyan": 235, "purple": 350},
        "series": ["#0072B2", "#D55E00", "#009E73", "#E69F00", "#56B4E9", "#CC79A7"],
    },
}
DEFAULT_PALETTE = "journal"

# 2D 图示标签的取值规则：同一组标签的 (L, C) 固定，只换色相。依次是 填充 / 描边 / 文字 / 副文字 / 分组底色。
TAG_RULE = {
    "light": {"fill": (0.955, 0.028), "line": (0.74, 0.085), "text": (0.42, 0.10), "sub": (0.54, 0.07), "panel": (0.978, 0.014)},
    # 深色底：彩色卡片要足够亮才不发闷；副文字不是强调色，一律用接近纯白
    "dark": {"fill": (0.40, 0.085), "line": (0.66, 0.12), "text": (0.92, 0.075), "sub": (0.97, 0.012), "panel": (0.25, 0.035)},
}


# ------------------------------------------------------------------ 字体
# 西文与数字一律 Times New Roman；汉字：大标题用不加粗的黑体，其余一律加粗的宋体。

FONT_TITLE = {"latin": "Times New Roman", "ea": "黑体"}
FONT_BODY = {"latin": "Times New Roman", "ea": "宋体"}

# ------------------------------------------------------------------ 版面（1600 x 900 画布）

MARGIN = 80                       # 左右页边
CONTENT = (80, 206, 1440, 600)    # 内容区 x, y, w, h：标题区之下、页脚之上
GAP = 24                          # 模块之间的标准间距
PAD = 22                          # 卡片内边距
RADIUS = 0.08                     # 卡片圆角（相对短边的比例）

# ------------------------------------------------------------------ 字号（磅）
# 两档文字密度：talk = 演讲档（少字大字），read = 阅读档（页面自解释）

SIZES = {
    "talk": {"cover": 46, "section": 40, "title": 30, "lead": 18, "h": 21, "body": 18, "small": 14,
             "caption": 12, "stat": 48, "kicker": 12, "tab": 11.5, "footer": 10.5},
    "read": {"cover": 44, "section": 38, "title": 28, "lead": 16.5, "h": 18.5, "body": 15, "small": 12.5,
             "caption": 11, "stat": 42, "kicker": 11.5, "tab": 11, "footer": 10.5},
}
TITLE_ROLES = {"cover", "section", "title", "stat"}   # 这些角色用标题字体（黑体、不加粗）


class Theme:
    """一套配色在某种底色（dark / light）与某档密度（talk / read）下的全部取值。"""

    def __init__(self, surface: str = "dark", density: str = "read", palette: str = DEFAULT_PALETTE):
        if surface not in ("dark", "light") or density not in SIZES:
            raise ValueError("surface 取 dark / light，density 取 talk / read")
        self.surface, self.density, self.palette = surface, density, palette
        self.dark = d = surface == "dark"
        self.size = SIZES[density]
        spec = PALETTES[palette]
        p = spec[surface]
        self._hues, self._rule = spec["hues"], TAG_RULE[surface]
        _, self._nc, self._nh = to_oklch(p["line"])              # 中性色的彩度与色相（极低的色偏）
        _, self._pc, _ = to_oklch(spec["light"]["primary"])      # 主色的彩度：决定色阶有多“蓝”
        self._ph = spec["hues"]["primary"]

        # 中性色与文字
        self.paper, self.text, self.text_muted = p["paper"], p["ink"], p["muted"]
        self.rule = p["line"]
        self.card_line = self._neutral(0.80) if not d else self._neutral(0.40)
        self.quiet_fill = p["surface"]
        # 卡片要和页面背景拉开明度：浅色底的卡片接近白、背景略灰；深色底的卡片明显亮于背景
        self.card_fill = self._neutral(0.995) if not d else self._neutral(0.285)
        self.card_shadow = (p["ink"] + "1C", 22, 6, 90) if not d else ("#00000050", 20, 6, 90)
        self.flat_fill, self.flat_line = self.card_fill, self._neutral(0.66 if not d else 0.50)
        self.link, self.frame = self._neutral(0.45 if not d else 0.68), self._neutral(0.74 if not d else 0.42)

        # 主色与强调色
        self.primary = self.accent = p["primary"]                  # accent：结构性强调（章节标记、小标题、序号、箭头）
        # 标题用比主色更深、更沉的颜色（深色底用白），细体的黑体才压得住
        self.title = (oklch(0.27, self._pc * 0.7, self._ph) if self._pc > 0.02 else p["ink"]) if not d else p["ink"]
        # 卡片的标题头带：主色的浅色调，而不是实心主色。实心色块留给每页一两处重点
        self.head_fill = oklch(0.915, self._pc * 0.30, self._ph) if not d else oklch(0.36, self._pc * 0.55, self._ph)
        self.head_text = self.title
        self.highlight = p["emphasis"]                             # highlight：正文里最要紧的那几个字
        self.mark = p["accent"]                                    # mark：强调色本身，只用于小面积的图形与大数字
        self.on_highlight = p["paper"]
        self.positive, self.negative = self._hue("accent", "text"), self._hue("alert", "text")
        # 反色块：浅色底上是深色块，深色底上是亮色块。全稿靠它拉开明暗层次，避免整页一个亮度。
        self.strong_fill = self.feature_fill = p.get("block", p["primary"])
        self.strong_text = self.feature_text = p.get("block_text", p["paper"])
        block_is_dark = to_oklch(self.strong_fill)[0] < 0.6
        self.strong_muted = oklch(0.82 if block_is_dark else 0.36, self._nc, self._nh)   # 反色块上的次要文字
        self.on_feature_highlight = spec["dark"]["accent"] if block_is_dark else spec["light"]["emphasis"]
        # 页脚带每页都出现：色块本身很亮时（如 ink 深色底的近白色块）改用一条比背景略亮的灰带，避免每页底部一道白
        self.band_fill = self.strong_fill if block_is_dark else self._neutral(0.32)
        self.band_text = self.strong_text if block_is_dark else p["ink"]
        self.mark_text = spec["light"]["ink"]                      # 压在强调色块上的字
        primary_tag = self.tone("primary")
        self.chip_fill, self.chip_text = primary_tag["fill"], primary_tag["text"]

        # 色阶：同一色相上等距的明度阶梯
        chroma = self._pc
        self.ramp = [oklch(L, chroma * k, self._ph) for L, k in
                     (((0.93, .30), (0.88, .42), (0.83, .54), (0.78, .66), (0.73, .78)) if not d
                      else ((0.42, .62), (0.37, .58), (0.32, .54), (0.27, .50), (0.22, .46)))]
        self.stage = [oklch(L, chroma * 0.85, self._ph) for L in
                      ((0.52, 0.45, 0.38, 0.31, 0.24) if not d else (0.56, 0.50, 0.44, 0.38, 0.32))]
        self.stage_tints = [oklch(L, chroma * 0.12, self._ph) for L in
                            ((0.972, 0.955, 0.938, 0.921) if not d else (0.195, 0.22, 0.245, 0.27))]
        self.ring = oklch(0.86 if not d else 0.40, chroma * 0.4, self._ph)
        self.series = spec["series"]
        # 页面框架不使用发光与文字投影：光效只留给 2.5D 图示
        self.title_glow = self.strong_glow = self.text_shadow = None

    def _neutral(self, L: float) -> str:
        return oklch(L, self._nc, self._nh)

    def _hue(self, name: str, part: str) -> str:
        L, C = self._rule[part]
        return oklch(L, C, self._hues[name])

    # ---------------------------------------------------------------- 背景

    def background(self, kind: str = "content") -> dict:
        """页面背景：同色相、明度差很小的斜向渐变（原生填充，不用图片）。"""
        L, C, H = to_oklch(self.paper)
        return lin(45, self.paper, oklch(L + (0.035 if self.dark else -0.04), C, H))

    # ---------------------------------------------------------------- 2D 图示的语义色调

    def tone(self, name: str = "plain") -> dict:
        """2D 图示的色调：纯色填充 + 同色系描边 + 同色系文字，不用渐变、阴影和光效。
        plain 常规；primary 本方 / 主体；solid 核心；accent 流程中的动作；warm 数据与存储；
        alert 问题与风险；muted 外部或次要；另有 cyan、purple 两个备用色相。
        除 plain / solid / muted 外，各色调的明度与彩度完全相同，只有色相不同。"""
        if name == "plain":
            return {"fill": self.flat_fill, "line": self.flat_line, "text": self.text, "sub": self.text_muted,
                    "panel": self._neutral(self._rule["panel"][0])}
        if name == "muted":
            tone = {part: self._neutral(L) for part, (L, _) in self._rule.items()}
            if self.dark:      # 深色底上非强调的文字一律亮白
                tone["text"] = tone["sub"] = self.text
            return tone
        if name == "solid":
            return {"fill": self.feature_fill, "line": self._neutral(0.30 if not self.dark else 0.62),
                    "text": self.feature_text, "sub": self.feature_text, "panel": self._hue("primary", "panel")}
        return {part: self._hue(name, part) for part in self._rule}

    # ---------------------------------------------------------------- 2.5D 图示

    def iso(self) -> dict:
        """2.5D / 3D 图示的取值：半透明的面、柔和的颜色、高对比的标签、有阴影和柔光、不描边。"""
        chroma, hue, d = self._pc, self._ph, self.dark
        levels = (0.62, 0.55, 0.48, 0.41) if d else (0.90, 0.84, 0.78, 0.72)
        tops = [oklch(L, chroma * (0.55 if d else 0.42), hue) + ("C0" if d else "D0") for L in levels]
        side = oklch(0.34 if d else 0.56, chroma * 0.6, hue)
        return {"tops": tops, "left": oklch(0.42 if d else 0.66, chroma * 0.6, hue) + "E6", "right": side + "E6",
                "cell": ("#FFFFFF30" if d else "#FFFFFFE0"), "cell_text": self.text if not d else "#FFFFFF",
                "face_text": "#FFFFFF" if d else self.text,
                "glow": (oklch(0.80, chroma * 0.5, hue) + ("40" if d else "70"), 9),
                "shadow": ("#00000066", 16, 9, 90) if d else (self.text + "2E", 16, 9, 90),
                "label_fill": self.text, "label_text": self.paper,
                "label_shadow": ("#00000055", 7, 3, 90) if d else (self.text + "33", 7, 3, 90)}

    # ---------------------------------------------------------------- 文字样式

    def style(self, role: str, **overrides) -> dict:
        """某个文字角色的完整样式。role 取 SIZES 里的键。"""
        is_title = role in TITLE_ROLES
        base = {"size": self.size[role], "font": FONT_TITLE if is_title else FONT_BODY, "bold": not is_title,
                "color": self.text}
        return {**base, **overrides}
