"""PowerPresent 组件库：页面框架与内容组件。

用法骨架：

    kit = Kit(surface="dark", density="read", footer="项目名 · 2026-11", sections=["背景", "方法", "结果"])
    kit.cover("一句话主标题", subtitle="副标题", meta=["汇报人", "单位"])
    page = kit.content("这一页的结论写成一句完整的话", lead="补一句背景或限定", section=0)
    left, right = page.area.cols([3, 2])
    page.card(left, "小标题", ["要点一，**关键词**会被强调", "要点二"])
    page.stat(right, "87%", "指标名称", note="对比基准或来源")
    kit.save("out.pptx")

文字里用 **双星号** 包住的片段会按强调色显示；每页强调不超过三处。
组件不会自动缩字：文字放不下说明内容太多，应当删字或拆页，而不是调小字号。
"""
from __future__ import annotations

import pathlib
import re

from PIL import Image
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.util import Emu, Pt

from .canvas import CANVAS_H, CANVAS_W, Deck, _emu, lin, polygon
from .diagrams import DiagramMixin
from .layout import Rect, line_height, px, text_width
from .theme import CONTENT, DEFAULT_PALETTE, FONT_BODY, GAP, MARGIN, PAD, RADIUS, Theme



BACKDROPS = pathlib.Path(__file__).resolve().parents[2] / "assets/backdrops"


class Kit:
    """一份演示文稿：统一的主题、页眉章节索引、页脚与页码。"""

    def __init__(self, surface="dark", density="read", footer="", sections=(), logo=None, palette=DEFAULT_PALETTE,
                 backdrop="wafer"):
        self.deck = Deck()
        self.theme = Theme(surface, density, palette)
        self.backdrop = backdrop      # 底图母题名（assets/backdrops/ 下的目录名），默认芯片版图；None 表示只用纯色渐变
        self.footer, self.sections, self.logo = footer, list(sections), logo
        self.page_no = 0
        self.warnings: list[str] = []

    def save(self, path) -> None:
        """保存并打印构建时发现的问题（例如页标题超过一行）。这些问题必须改掉，不能忽略。"""
        self.deck.save(path)
        for line in self.warnings:
            print("需要修改:", line)

    def _new(self, kind: str, name: str) -> "Page":
        self.page_no += 1
        background = self.theme.background(kind)
        if self.backdrop:
            variant = "content" if kind == "content" else "cover"
            background = BACKDROPS / self.backdrop / f"{self.theme.palette}-{self.theme.surface}-{variant}.jpg"
        slide = self.deck.slide(background, name=name)
        page = Page(self, slide)
        return page

    # ---------------------------------------------------------------- 页面框架

    def cover(self, title, subtitle=None, kicker=None, meta=(), image=None) -> "Page":
        """封面。title 最多两行（用 \\n 换行）；kicker 是场合或栏目名；meta 是署名、单位、日期等。
        image 是一张整幅的封面图（可选）；不给时右侧是一块主色色块。"""
        page, t = self._new("cover", "封面"), self.theme
        s = page.s
        lines = title.count("\n") + 1
        top = 330 - (lines - 1) * 45
        if image:      # 整幅图片做封面：左侧压一层由深到透明的蒙版，保证文字可读
            s.image(image, 0, 0, CANVAS_W, CANVAS_H, cover=True, name="封面图")
            s.box(0, 0, CANVAS_W, CANVAS_H, fill=lin(0, "#0A1220D0", "#0A122000"), name="封面蒙版")
            ink, soft, kick = "#FFFFFF", "#E3E8EF", "#FFFFFF"
        else:
            s.box(1120, 0, CANVAS_W - 1120, CANVAS_H, fill=t.feature_fill, name="封面色块")
            s.box(1120, 0, 10, CANVAS_H, fill=t.mark, name="封面色条")
            ink, soft, kick = t.title, t.text_muted, t.accent
        if kicker:
            s.text(MARGIN + 20, 150, 900, 30, kicker, **t.style("kicker", color=kick, spacing=3))
        s.text(MARGIN + 20, top, 960, 90 * lines, title, valign="middle", leading=0.95, name="主标题",
               **t.style("cover", color=ink))
        y = top + 90 * lines + 22
        if subtitle:
            s.text(MARGIN + 20, y, 900, 80, subtitle, valign="top", leading=1.05, name="副标题",
                   **t.style("lead", size=t.size["lead"] + 3, color=soft))
        if meta:
            s.box(MARGIN + 20, 712, 64, 3, fill=t.mark if not image else "#F0A04B", name="署名分隔")
            s.text(MARGIN + 20, 728, 1000, 90, list(meta), valign="top", leading=1.1, name="署名",
                   **t.style("small", size=t.size["small"] + 1.5, color=ink if image else t.text))
        page._logo(1420, 60)
        return page

    def section(self, index: int, title=None, points=()) -> "Page":
        """章节过渡页。index 是 sections 里的下标；points 是这一章要讲的 2～4 个小节。"""
        page, t = self._new("section", "章节页"), self.theme
        s = page.s
        title = title or self.sections[index]
        panel = 700
        s.box(0, 0, panel, CANVAS_H, fill=t.strong_fill, name="章节色块")
        s.box(panel, 0, 10, CANVAS_H, fill=t.mark, name="章节色条")
        s.text(MARGIN + 20, 250, 500, 150, f"{index + 1:02d}", name="章节序号",
               **t.style("stat", size=110, color=t.on_feature_highlight))
        s.text(MARGIN + 26, 412, 500, 30, f"PART {index + 1}", **t.style("kicker", color=t.strong_muted, spacing=4))
        s.text(MARGIN + 20, 452, panel - MARGIN - 40, 80, title, name="章节标题", **t.style("section", color=t.strong_text))
        top = CANVAS_H / 2 - len(points) * 36
        for i, point in enumerate(points):
            y = top + i * 72
            s.box(panel + 90, y + 6, 40, 40, "ellipse", fill=t.mark, text=str(i + 1), align="center",
                  **t.style("body", color=t.mark_text))
            s.text(panel + 150, y, CANVAS_W - panel - 150 - MARGIN, 52, point, name="小节", **t.style("lead", size=t.size["lead"] + 2))
            if i < len(points) - 1:
                s.box(panel + 150, y + 62, CANVAS_W - panel - 150 - MARGIN, 1.2, fill=t.rule)
        return page

    def content(self, title, lead=None, section=None) -> "Page":
        """内容页。title 写成一句完整的结论；lead 是一行补充；section 是当前所在章节的下标。"""
        page, t = self._new("content", "内容页"), self.theme
        s = page.s
        if section is not None and self.sections:
            page._tabs(section)
        s.box(MARGIN, 74, CANVAS_W - 2 * MARGIN, 1.2, fill=t.rule, name="页眉线")
        s.box(MARGIN, 72, 96, 5, fill=t.mark, name="页眉强调段")
        for label, text, role in (("页标题", title, "title"), ("导语", lead or "", "lead")):
            if text_width(text, t.size[role]) > CANVAS_W - 2 * MARGIN:
                self.warnings.append(f"第 {self.page_no} 页{label}超过一行，请改短：{text}")
        s.text(MARGIN, 94, CANVAS_W - 2 * MARGIN, 64, title, wrap=False, name="页标题",
               **t.style("title", color=t.title))
        if lead:
            s.text(MARGIN, 156, CANVAS_W - 2 * MARGIN, 34, lead, wrap=False, name="导语",
                   **t.style("lead", color=t.text_muted))
        s.box(0, 850, CANVAS_W, 50, fill=t.band_fill, name="页脚带")
        s.text(MARGIN, 850, 1000, 50, self.footer, name="页脚", **t.style("footer", color=t.band_text))
        s.box(CANVAS_W - MARGIN - 54, 850, 54, 50, fill=t.mark, text=str(self.page_no), align="center", name="页码",
              **t.style("footer", size=t.size["footer"] + 2, color=t.mark_text))
        return page

    def closing(self, message, points=(), contact=None) -> "Page":
        """结尾页：把全篇收束成一句话，外加最多三条要带走的结论；不要只写“谢谢”。"""
        page, t = self._new("cover", "结尾页"), self.theme
        s = page.s
        lines = message.count("\n") + 1
        s.text(MARGIN + 20, 190, 1100, 78 * lines, message, valign="middle", leading=0.98,
               name="收束句", **t.style("section", color=t.title))
        y = 190 + 78 * lines + 46
        for i, point in enumerate(points):
            s.box(MARGIN + 22, y + i * 58 + 20, 14, 14, fill=t.mark)
            s.text(MARGIN + 44, y + i * 58, 1000, 54, page.line(point), name="结论", **t.style("lead"))
        s.box(0, 760, CANVAS_W, 140, fill=t.strong_fill, name="结尾色带")
        s.box(0, 754, CANVAS_W, 8, fill=t.mark, name="结尾色条")
        if contact:
            s.text(MARGIN + 20, 760, 1200, 140, contact, name="联系方式", **t.style("lead", color=t.strong_text))
        return page


class Page(DiagramMixin):
    """一页幻灯片。area 是可以放内容的区域；组件方法都接收一个 Rect。图示类组件见 diagrams.py。"""

    def __init__(self, kit: Kit, slide):
        self.kit, self.s, self.t = kit, slide, kit.theme
        self.area = Rect(*CONTENT)

    # ---------------------------------------------------------------- 文字工具

    def rich(self, text, color=None):
        """把含 **强调** 标记的字符串转成片段列表。"""
        if not isinstance(text, str):
            return text
        parts = re.split(r"\*\*(.+?)\*\*", text)
        return [[(p, {"color": color or self.t.highlight}) if i % 2 else p for i, p in enumerate(parts) if p]][0]

    def line(self, text, color=None):
        """单段文字（可含 **强调**），转成可直接交给画布的段落列表。"""
        return [self.rich(text, color)]

    def text(self, r: Rect, text, role="body", **style):
        """在矩形里写一段文字。role 决定字号与字体，见 theme.SIZES。"""
        paragraphs = [text] if isinstance(text, str) else text
        merged = {"valign": "top", **self.t.style(role), **style}
        return self.s.text(r.x, r.y, r.w, r.h, [self.rich(p) for p in paragraphs], **merged)

    def bullets(self, r: Rect, items, role="body", marker="■", **style):
        """要点列表。每条前面有一个强调色的小方块。"""
        size = style.get("size", self.t.size[role])
        color_of_marker = style.pop("marker_color", self.t.mark)
        paragraphs = [[(f"{marker}  ", {"color": color_of_marker, "size": size * 0.55}), *self.rich(item)] for item in items]
        merged = {"valign": "top", "leading": 1.12, "para_gap": size * 0.45, **self.t.style(role), **style}
        return self.s.text(r.x, r.y, r.w, r.h, paragraphs, **merged)

    def notes(self, text: str):
        """写入这一页的演讲者备注：讲稿、数字口径、出处细节都放这里。"""
        self.s.slide.notes_slide.notes_text_frame.text = text
        return self

    # ---------------------------------------------------------------- 框架内部件

    def _logo(self, x, y):
        if self.kit.logo:
            image = Image.open(self.kit.logo)
            h = 44
            self.s.image(self.kit.logo, x, y, h * image.width / image.height, h, name="标识")

    def _tabs(self, current: int):
        """页眉右侧的章节索引：当前章节实心高亮，其余淡显。"""
        t, s = self.t, self.s
        size = t.size["tab"]
        widths = [text_width(name, size) + 30 for name in self.kit.sections]
        x = CANVAS_W - MARGIN - sum(widths) - 8 * (len(widths) - 1)
        for i, (name, w) in enumerate(zip(self.kit.sections, widths)):
            on = i == current
            s.box(x, 32, w, 28, "roundRect", 0.5, fill=t.strong_fill if on else None,
                  line=None if on else t.rule, line_width=1, text=name, align="center", wrap=False,
                  name="章节索引", **t.style("tab", color=t.strong_text if on else t.text_muted))
            x += w + 8

    def _panel(self, r: Rect, tone="default", name="卡片"):
        t = self.t
        if tone == "strong":
            return self.s.box(r.x, r.y, r.w, r.h, "roundRect", RADIUS * min(1, 200 / min(r.w, r.h)),
                              fill=t.feature_fill, shadow=t.card_shadow, name=name)
        if tone == "flat":      # 2D 图示里的容器：纯色、描边、无阴影
            return self.s.box(r.x, r.y, r.w, r.h, "roundRect", RADIUS * min(1, 200 / min(r.w, r.h)), fill=t.flat_fill,
                              line=t.flat_line, line_width=1.3, name=name)
        fill = t.quiet_fill if tone == "quiet" else t.card_fill
        return self.s.box(r.x, r.y, r.w, r.h, "roundRect", RADIUS * min(1, 200 / min(r.w, r.h)), fill=fill,
                          line=t.card_line, line_width=1, shadow=None if tone == "quiet" else t.card_shadow, name=name)

    # ---------------------------------------------------------------- 内容组件

    def panel(self, r: Rect, pad: float = 26) -> Rect:
        """图示面板：一块带柔和投影的圆角浅色底，把示意图、图表托起来，和页面背景分开。返回面板内的可用区域。"""
        self._panel(r, "default", name="图示面板")
        return r.inset(pad)

    def takeaway(self, text) -> Rect:
        """页面底部的结论条：全页最想让人记住的一句话。返回它上方剩余的内容区。"""
        t = self.t
        bar, rest = self.area.take_bottom(58)
        self.s.box(bar.x, bar.y, bar.w, bar.h, "roundRect", 0.18, fill=t.feature_fill, name="结论条")
        self.s.box(bar.x + 22, bar.y + bar.h / 2 - 7, 14, 14, fill=t.mark, name="结论标记")
        self.s.text(bar.x + 50, bar.y, bar.w - 74, bar.h, self.line(text, t.on_feature_highlight), wrap=False,
                    name="结论", **t.style("lead", color=t.feature_text))
        self.area = rest
        return rest

    def card(self, r: Rect, title=None, body=None, tone="default", number=None):
        """卡片：小标题加正文。body 是字符串（一段话）或列表（要点）。
        tone: default（标题是一条反色头带）/ quiet（次要：淡底、无头带）/ strong（重点：整张反色）/
        flat（2D 图示里的容器：同 default，但无阴影）。"""
        t = self.t
        self._panel(r, tone)
        strong, banded = tone == "strong", tone in ("default", "flat") and bool(title)
        inner = r.inset(PAD)
        if title:
            head_h = line_height(t.size["h"]) + 6
            title_color = t.strong_text if strong else (t.head_text if banded else t.accent)
            if banded:
                band_h = head_h + 22
                radius = RADIUS * min(1, 200 / min(r.w, r.h)) * min(r.w, r.h) / min(r.w, band_h)
                self.s.box(r.x, r.y, r.w, band_h, "round2SameRect", (min(radius, 0.5), 0), fill=t.head_fill, name="卡片头带")
                inner = Rect(inner.x, r.y + 11, inner.w, r.bottom - PAD - r.y - 11)
            x = inner.x
            if number is not None:
                self.s.box(x, inner.y + 2, 30, 30, "ellipse", fill=t.mark, text=str(number), align="center",
                           **t.style("small", color=t.mark_text))
                x += 42
            self.s.text(x, inner.y, inner.right - x, head_h, self.line(title, t.on_feature_highlight if strong else None),
                        valign="middle", name="卡片标题", **t.style("h", color=title_color))
            gap = 26 if banded else 10
            inner = Rect(inner.x, inner.y + head_h + gap, inner.w, inner.h - head_h - gap)
        if body:
            color = t.strong_text if strong else t.text
            highlight = t.on_feature_highlight if strong else None
            if isinstance(body, str):
                self.s.text(inner.x, inner.y, inner.w, inner.h, self.line(body, highlight), valign="top", leading=1.15,
                            **t.style("body", color=color))
            else:
                paragraphs = [[("■  ", {"color": t.mark, "size": t.size["body"] * 0.55}), *self.rich(item, highlight)]
                              for item in body]
                self.s.text(inner.x, inner.y, inner.w, inner.h, paragraphs, valign="top", leading=1.12,
                            para_gap=t.size["body"] * 0.45, **t.style("body", color=color))
        return r

    def stat(self, r: Rect, value, label, note=None, tone="default"):
        """数据块：一个大数字、它是什么、一行对比基准或来源。
        tone: default（普通卡片，顶部一小段强调色）/ strong（反色块，一页最多一个，用来突出最要紧的那个数）。"""
        t = self.t
        strong = tone == "strong"
        self._panel(r, "strong" if strong else "default")
        if not strong:
            self.s.box(r.x + PAD, r.y, 56, 6, fill=t.mark, name="数据色条")
        inner = r.inset(PAD)
        value_h = line_height(t.size["stat"]) * 0.92
        top = inner.y + max(0, (inner.h - value_h - line_height(t.size["body"]) * (2 if note else 1) - 8) / 2)
        self.s.text(inner.x, top, inner.w, value_h, value, align="center", wrap=False, name="数据",
                    **t.style("stat", color=t.on_feature_highlight if strong else t.primary))
        self.s.text(inner.x, top + value_h + 2, inner.w, line_height(t.size["body"]),
                    self.line(label, t.on_feature_highlight if strong else None), align="center", name="数据说明",
                    **t.style("body", color=t.strong_text if strong else t.text))
        if note:
            self.s.text(inner.x, top + value_h + 4 + line_height(t.size["body"]), inner.w, line_height(t.size["small"]),
                        note, align="center", name="数据备注",
                        **t.style("small", color=t.strong_muted if strong else t.text_muted))
        return r

    def steps(self, r: Rect, items):
        """横向步骤流程。items: [(标题, 说明), ...]，2～5 步，之间用箭头连接。"""
        t = self.t
        arrow = 44
        w = (r.w - arrow * (len(items) - 1)) / len(items)
        for i, (title, note) in enumerate(items):
            cell = Rect(r.x + i * (w + arrow), r.y, w, r.h)
            self.card(cell, title, note, tone="flat", number=i + 1)
            if i < len(items) - 1:
                self.s.box(cell.right + arrow / 2 - 10, cell.cy - 17, 20, 34, "chevron", 0.6, fill=t.mark, name="箭头")
        return r

    def matrix(self, r: Rect, columns):
        """分列清单。columns: [(列标题, [单元格, ...]), ...]，每列的单元格数应相同。"""
        t = self.t
        head_h = line_height(t.size["h"]) + 8
        rows = max(len(cells) for _, cells in columns)
        for col, (header, cells) in zip(r.cols(len(columns)), columns):
            self.s.box(col.x, col.y, col.w, head_h + 6, "roundRect", 0.16, fill=t.strong_fill, text=header, align="center",
                       name="列标题", **t.style("h", color=t.strong_text))
            body = Rect(col.x, col.y + head_h + 18, col.w, col.h - head_h - 18)
            for cell, label in zip(body.rows(rows, 10), cells):
                self._panel(cell, tone="flat", name="单元格")
                self.s.text(cell.x + 10, cell.y, cell.w - 20, cell.h, self.line(label), align="center",
                            **t.style("body"))
        return r

    def pills(self, r: Rect, labels, align="left"):
        """一排标签。"""
        t = self.t
        size = t.size["small"]
        widths = [text_width(label, size) + 34 for label in labels]
        total = sum(widths) + 10 * (len(widths) - 1)
        x = r.x if align == "left" else (r.cx - total / 2 if align == "center" else r.right - total)
        h = line_height(size) + 12
        for label, w in zip(labels, widths):
            self.s.box(x, r.y, w, h, "roundRect", 0.5, fill=t.chip_fill, text=label, align="center", wrap=False,
                       name="标签", **t.style("small", color=t.chip_text))
            x += w + 10
        return Rect(r.x, r.y, r.w, h)

    def table(self, r: Rect, header, rows, widths=None, highlight_row=None):
        """表格。header 是表头，rows 是二维列表；widths 是各列宽度比例；highlight_row 高亮某一行（下标）。"""
        t = self.t
        widths = widths or [1] * len(header)
        row_h = min(r.h / (len(rows) + 1), line_height(t.size["body"]) * 2.1)
        columns = Rect(r.x, r.y, r.w, row_h).cols(widths, 0)
        for cell, label in zip(columns, header):
            self.s.box(cell.x, r.y, cell.w, row_h, fill=t.strong_fill, text=label, align="center",
                       name="表头", **t.style("body", color=t.strong_text))
        for i, row in enumerate(rows):
            y = r.y + (i + 1) * row_h
            hot = i == highlight_row
            fill = (t.chip_fill if hot else (t.quiet_fill if i % 2 == 0 else None))
            self.s.box(r.x, y, r.w, row_h, fill=fill, name="表格行")
            self.s.box(r.x, y + row_h - 1, r.w, 1, fill=t.rule, name="行线")
            for j, (cell, label) in enumerate(zip(columns, row)):
                self.s.text(cell.x + 12, y, cell.w - 24, row_h, self.line(str(label)),
                            align="left" if j == 0 else "center",
                            **t.style("body", color=t.highlight if hot and j > 0 else t.text))
        return Rect(r.x, r.y, r.w, row_h * (len(rows) + 1))

    def stack(self, r: Rect, layers):
        """分层架构：自上而下的梯形层叠板。layers: [(层名, [模块, ...]), ...]，上层在前。
        这是 2.5D 图示（带透视的板），按 2.5D 的画法：半透明的面、不描边、有阴影和柔光，文字高对比。"""
        t, iso = self.t, self.t.iso()
        gap, inset, thick = 16, 34, 9
        heights = [1.0 if not cells else 1.7 for _, cells in layers]
        unit = (r.h - (gap + thick) * (len(layers) - 1) - thick) / sum(heights)
        y = r.y
        for i, ((name, cells), weight) in enumerate(zip(layers, heights)):
            h = unit * weight
            top = iso["tops"][min(i, 3)]
            self.s.path(polygon([(r.x, y + h), (r.right, y + h), (r.right - 5, y + h + thick), (r.x + 5, y + h + thick)]),
                        fill=iso["right"], shadow=iso["shadow"], name="层板厚度")
            self.s.path(polygon([(r.x + inset, y), (r.right - inset, y), (r.right, y + h), (r.x, y + h)]),
                        fill=lin(90, top, iso["tops"][min(i + 1, 3)]), glow=iso["glow"], name="层板")
            head_h = line_height(t.size["h"]) + 4
            head_y = y + (8 if cells else (h - head_h) / 2)
            self.s.text(r.x + inset, head_y, r.w - 2 * inset, head_h, self.line(name), align="center", name="层名",
                        **t.style("h", color=iso["face_text"]))
            if cells:
                body = Rect(r.x + inset + 24, head_y + head_h + 6, r.w - 2 * inset - 48, y + h - head_y - head_h - 18)
                for cell, label in zip(body.cols(len(cells), 14), cells):
                    self.s.box(cell.x, cell.y, cell.w, cell.h, "roundRect", 0.14, fill=iso["cell"],
                               shadow=iso["label_shadow"], text=label, align="center", name="模块",
                               **t.style("small", color=iso["cell_text"]))
            y += h + gap + thick
        return r

    def nodes(self, r: Rect, labels):
        """圆形节点流程：适合 4～6 个字数很少的环节。"""
        t = self.t
        d = min(r.h, (r.w - 50 * (len(labels) - 1)) / len(labels))
        step = (r.w - d) / max(len(labels) - 1, 1)
        for i, label in enumerate(labels):
            cx = r.x + d / 2 + i * step
            tone = t.tone("primary")
            self.s.box(cx - d / 2, r.cy - d / 2, d, d, "ellipse", fill=tone["fill"], line=tone["line"], line_width=2,
                       text=label, align="center", leading=0.95, wrap=False, name="节点",
                       **t.style("h", color=tone["text"]))
            if i < len(labels) - 1:
                self.s.box(cx + step / 2 - 10, r.cy - 16, 20, 32, "chevron", 0.6, fill=t.mark, name="箭头")
        return r

    def timeline(self, r: Rect, events):
        """时间线。events: [(时间, 事件说明), ...]，3～6 个。"""
        t = self.t
        axis_y = r.y + line_height(t.size["h"]) + 22
        self.s.box(r.x, axis_y - 1, r.w, 2, fill=t.flat_line, name="时间轴")
        for cell, (when, what) in zip(r.cols(len(events), GAP), events):
            pill_w = text_width(when, t.size["h"]) + 40
            self.s.box(cell.cx - pill_w / 2, r.y, pill_w, line_height(t.size["h"]) + 6, "roundRect", 0.5, fill=t.mark,
                       text=when, align="center", wrap=False, name="时间", **t.style("h", color=t.mark_text))
            self.s.box(cell.cx - 8, axis_y - 8, 16, 16, "ellipse", fill=t.flat_fill, line=t.mark, line_width=3.5, name="时间点")
            self.text(Rect(cell.x, axis_y + 24, cell.w, r.bottom - axis_y - 24), what, align="center", leading=1.12)
        return r

    def compare(self, r: Rect, left, right, labels=("现状", "改进后")):
        """左右对比。left / right: (标题, 要点列表)。左侧淡显，右侧为主。"""
        t = self.t
        a, b = r.cols(2, 76)
        for cell, (title, body), tone, label in ((a, left, "quiet", labels[0]), (b, right, "default", labels[1])):
            self.card(Rect(cell.x, cell.y + 20, cell.w, cell.h - 20), title, body, tone=tone)
            w = text_width(label, t.size["small"]) + 30
            hot = tone == "default"
            self.s.box(cell.right - PAD - w, cell.y + 4, w, 32, "roundRect", 0.5, fill=t.mark if hot else t.quiet_fill,
                       line=None if hot else t.card_line, line_width=1, text=label, align="center", wrap=False,
                       name="对比标签", **t.style("small", color=t.mark_text if hot else t.text_muted))
        self.s.box(r.cx - 16, r.cy - 8, 32, 36, "chevron", 0.6, fill=t.mark, name="对比箭头")
        return r

    def spotlight(self, r: Rect, heading, items):
        """无框要点块：标题加两三行说明，底部一条两端上翘的异形托线。适合竖向排三块。"""
        t = self.t
        head_h = line_height(t.size["h"] + 3)
        self.s.text(r.x, r.y, r.w, head_h, heading, align="center", shadow=t.text_shadow, name="要点标题",
                    **t.style("h", size=t.size["h"] + 3, color=t.text if t.dark else t.title))
        self.s.box(r.cx - 28, r.y + head_h + 2, 56, 4, fill=t.mark, name="要点色段")
        self.text(Rect(r.x + r.w * 0.06, r.y + head_h + 14, r.w * 0.88, r.h - head_h - 48), [f"•  {i}" for i in items],
                  role="small", align="center", leading=1.15)
        base, wing = r.bottom - 4, min(30, r.h * 0.18)
        line = t.accent
        self.s.path([("M", r.x, base - wing), ("L", r.x + r.w * 0.22, base - 12), ("L", r.x + r.w * 0.26, base),
                     ("L", r.x + r.w * 0.74, base), ("L", r.x + r.w * 0.78, base - 12), ("L", r.right, base - wing)],
                    line=lin(0, line + "00", line + "CC", line, line + "CC", line + "00"), line_width=1.8,
                    name="托线")
        return r

    def quote(self, r: Rect, text, by=None):
        """引用：一句原话加出处。"""
        t = self.t
        self.s.text(r.x, r.y - 20, 90, 110, "“", name="引号", **t.style("stat", size=96, color=t.mark))
        self.text(Rect(r.x + 84, r.y + 14, r.w - 84, r.h - 60), text, role="lead", size=t.size["lead"] + 4, leading=1.2)
        if by:
            self.s.text(r.x + 84, r.bottom - 36, r.w - 84, 32, f"—— {by}", align="right",
                        **t.style("small", color=t.text_muted))
        return r

    def figure(self, r: Rect, image_path, caption=None, source=None):
        """图片：等比缩放后在矩形内居中，下方是图注与来源。"""
        t = self.t
        cap_h = (line_height(t.size["caption"]) + 6) * (bool(caption) + bool(source))
        box = Rect(r.x, r.y, r.w, r.h - cap_h)
        image = Image.open(image_path)
        scale = min(box.w / image.width, box.h / image.height)
        w, h = image.width * scale, image.height * scale
        x, y = box.cx - w / 2, box.cy - h / 2
        self.s.image(image_path, x, y, w, h, name="图片")
        self.s.box(x, y, w, h, line=t.card_line, line_width=1, name="图片边框")
        y = box.bottom + 6
        for line, color in ((caption, t.text), (source, t.text_muted)):
            if line:
                self.s.text(r.x, y, r.w, line_height(t.size["caption"]), line, align="center",
                            **t.style("caption", color=color))
                y += line_height(t.size["caption"]) + 4
        return r

    def chart(self, r: Rect, categories, series, kind="bar", number_format="General", title=None):
        """原生图表（在 PowerPoint 里可以直接改数据）。series: {系列名: [数值, ...]}。
        kind: bar（柱状）/ hbar（横向条形，类别名较长时用）/ line（折线）。"""
        t = self.t
        if title:
            head, r = r.take_top(line_height(t.size["small"]) + 4, 6)
            self.s.text(head.x, head.y, head.w, head.h, title, **t.style("small", color=t.text_muted))
        if kind == "hbar":      # 条形图从下往上排，倒序后第一个类别才在最上面
            categories = list(reversed(categories))
            series = {name: list(reversed(values)) for name, values in series.items()}
        data = CategoryChartData()
        data.categories = categories
        for name, values in series.items():
            data.add_series(name, values)
        chart_type = {"bar": XL_CHART_TYPE.COLUMN_CLUSTERED, "hbar": XL_CHART_TYPE.BAR_CLUSTERED}.get(kind, XL_CHART_TYPE.LINE_MARKERS)
        bars = kind in ("bar", "hbar")
        frame = self.s._shapes.add_chart(chart_type, Emu(_emu(r.x)), Emu(_emu(r.y)), Emu(_emu(r.w)), Emu(_emu(r.h)), data)
        chart = frame.chart
        ink = RGBColor.from_string(t.text.lstrip("#")[:6])
        muted = RGBColor.from_string(t.text_muted.lstrip("#")[:6])
        chart.font.size, chart.font.name, chart.font.color.rgb = Pt(t.size["caption"] + 1), FONT_BODY["latin"], ink
        chart.has_title = False      # 标题由页面文字给出，不用图表自带的标题
        chart.has_legend = len(series) > 1
        if chart.has_legend:
            chart.legend.position, chart.legend.include_in_layout = XL_LEGEND_POSITION.TOP, False
        value_axis, category_axis = chart.value_axis, chart.category_axis
        value_axis.has_major_gridlines = True
        value_axis.major_gridlines.format.line.color.rgb = RGBColor.from_string(t.rule.lstrip("#")[:6])
        value_axis.major_gridlines.format.line.width = Pt(0.6)
        value_axis.format.line.fill.background()
        category_axis.format.line.color.rgb = muted
        value_axis.tick_labels.font.color.rgb = category_axis.tick_labels.font.color.rgb = muted
        plot = chart.plots[0]
        if bars:
            plot.gap_width = 60
            plot.has_data_labels = True
            plot.data_labels.number_format, plot.data_labels.number_format_is_linked = number_format, False
            plot.data_labels.font.size, plot.data_labels.font.color.rgb = Pt(t.size["caption"] + 1), ink
        for item, color in zip(plot.series, t.series):
            rgb = RGBColor.from_string(color.lstrip("#"))
            if bars:
                item.format.fill.solid()
                item.format.fill.fore_color.rgb = rgb
            else:
                item.format.line.color.rgb, item.format.line.width = rgb, Pt(2.2)
                item.marker.format.fill.solid()
                item.marker.format.fill.fore_color.rgb = rgb
                item.smooth = False
        return frame
