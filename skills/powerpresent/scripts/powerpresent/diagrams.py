"""图示组件：用框、线、分层与真实图片表达复杂的技术内容。

画法只有两套，不得混用（理由见 references/design-system.md 第 10.3 节）：
- 2D 图示（本文件里除 iso_stack 之外的全部）：纯色填充、描边、同色系文字；不用渐变、半透明、阴影、光效。
- 2.5D 图示（iso_stack）：半透明的面、柔和的颜色、高对比的标签、有阴影和柔光；不描边。

工科汇报和产品技术介绍里，复杂内容优先画成图，而不是写成要点：
- 架构与分层：panorama（分层全景）、tiers（平台体系）、iso_stack（2.5D 层叠）、lanes（分区泳道）
- 运行链路与机制：Diagram（自由的框线图）、stages（分阶段流程）、cycle（闭环）、exchange（双向交互）
- 归类与组成：tree（分类树）、hub（中心辐射）
- 图片证据：gallery（图片组）、annotated（带标注的截图）、callout（结论横条）

这些方法通过 Page 调用，例如 page.panorama(...)、page.diagram()。
"""
from __future__ import annotations

import math

from PIL import Image

from .canvas import lin, polygon
from .layout import Rect, line_height, text_width



def _radius(r: Rect, pixels: float) -> float:
    """把圆角的像素值换算成 roundRect 需要的比例。"""
    return min(0.5, pixels / max(min(r.w, r.h), 1))


def _item(value, size: int):
    """把 "标题" 或 (标题, 说明, ...) 统一补齐成定长元组。"""
    items = (value,) if isinstance(value, str) else tuple(value)
    return items + (None,) * (size - len(items))


def _route(a: Rect, b: Rect, route: str, gap: float):
    """计算从 a 到 b 的折线路径。连线只沿水平与竖直方向走。"""
    overlap_x = min(a.right, b.right) - max(a.x, b.x)
    overlap_y = min(a.bottom, b.bottom) - max(a.y, b.y)
    if route == "auto":
        route = "h" if overlap_y > 8 else "v" if overlap_x > 8 else "hv"
    to_right, to_down = b.cx > a.cx, b.cy > a.cy
    x_out, x_in = (a.right + gap, b.x - gap) if to_right else (a.x - gap, b.right + gap)
    y_out, y_in = (a.bottom + gap, b.y - gap) if to_down else (a.y - gap, b.bottom + gap)
    if route == "h":
        y = (max(a.y, b.y) + min(a.bottom, b.bottom)) / 2 if overlap_y > 0 else a.cy
        return [(x_out, y), (x_in, y)]
    if route == "v":
        x = (max(a.x, b.x) + min(a.right, b.right)) / 2 if overlap_x > 0 else a.cx
        return [(x, y_out), (x, y_in)]
    if route == "hv":      # 先横后竖
        return [(x_out, a.cy), (b.cx, a.cy), (b.cx, y_in)]
    if route == "vh":      # 先竖后横
        return [(a.cx, y_out), (a.cx, b.cy), (x_in, b.cy)]
    if route == "hvh":     # 横 - 竖 - 横
        middle = (x_out + x_in) / 2
        return [(x_out, a.cy), (middle, a.cy), (middle, b.cy), (x_in, b.cy)]
    if route == "vhv":     # 竖 - 横 - 竖
        middle = (y_out + y_in) / 2
        return [(a.cx, y_out), (a.cx, middle), (b.cx, middle), (b.cx, y_in)]
    raise ValueError(f"未知的连线走法: {route}")


class Diagram:
    """自由的框线图：分组、节点、连线、图例。

    典型用法：先用 Rect 的 cols / rows 把区域切好，再往格子里放分组和节点，最后连线。

        d = page.diagram()
        left, core, right = page.area.cols([2, 5, 2])
        inner = d.group(core, "核心（本方）", tone="primary")
        a, b, c = d.row(inner.rows(3)[0], [("组装器", "拼上下文"), ("自检", "核对"), ("注册表", "取模型")])
        d.link(a, b); d.link(b, c)
    """

    def __init__(self, page):
        self.page, self.s, self.t = page, page.s, page.t

    def group(self, r: Rect, title=None, tone="plain", dashed=False) -> Rect:
        """画一个分组框，返回框内可用区域。dashed=True 表示逻辑上的范围而非实体模块。"""
        t, c = self.t, self.t.tone(tone)
        self.s.box(r.x, r.y, r.w, r.h, "roundRect", _radius(r, 12), fill=None if dashed else c["panel"],
                   line=c["line"] or t.link, line_width=1.3, dash="dash" if dashed else None, name="分组")
        if not title:
            return r.inset(14)
        head = line_height(t.size["small"] + 1.5) + 4
        if dashed:      # 虚线范围框的标题靠左，给从上方穿入的连线让出中间位置
            self.s.text(r.x + 14, r.y + 8, r.w - 28, head, self.page.line(title), name="分组标题",
                        **t.style("small", size=t.size["small"] + 1.5, color=t.text))
            return Rect(r.x + 14, r.y + 10 + head + 4, r.w - 28, r.h - head - 28)
        # 实体分组：标题做成一条实心的头带（取该色调里最深 / 最亮的那个颜色），让分区一眼可辨
        band = head + 12
        self.s.box(r.x, r.y, r.w, band, "round2SameRect", (min(0.5, 12 / band), 0), fill=t.strong_fill if tone == "plain" else c["text"], name="分组头带")
        self.s.text(r.x + 10, r.y, r.w - 20, band, self.page.line(title), align="center", name="分组标题",
                    **t.style("small", size=t.size["small"] + 1.5, color=t.strong_text if tone == "plain" else t.paper))
        return Rect(r.x + 14, r.y + band + 14, r.w - 28, r.h - band - 28)

    def node(self, r: Rect, title, sub=None, tone="plain", geom="roundRect", role=None) -> Rect:
        """画一个节点，返回它的矩形（用于连线）。sub 是一行小字说明。"""
        t, c = self.t, self.t.tone(tone)
        role = role or ("body" if r.h >= 58 and r.w >= 130 else "small")
        paragraphs = list(title.split("\n"))
        if sub:
            sub_size = t.size["small"] if role in ("h", "body") else t.size["caption"]
            paragraphs.append([(sub, {"size": sub_size, "color": c["sub"]})])
        self.s.box(r.x, r.y, r.w, r.h, geom, _radius(r, 8) if geom == "roundRect" else None, fill=c["fill"],
                   line=c["line"], line_width=1.3, text=paragraphs, align="center", leading=1.0, pad=(6, 0, 6, 0),
                   name="节点", **t.style(role, color=c["text"]))
        return r

    def row(self, r: Rect, items, tone="plain", gap=14) -> list[Rect]:
        """把一行等分成若干节点。items 的元素是 "标题" 或 (标题, 说明) 或 (标题, 说明, 色调)。"""
        cells = r.cols(len(items), gap)
        return [self.node(cell, title, sub, own or tone)
                for cell, (title, sub, own) in zip(cells, (_item(i, 3) for i in items))]

    def column(self, r: Rect, items, tone="plain", gap=12) -> list[Rect]:
        """把一列等分成若干节点。"""
        cells = r.rows(len(items), gap)
        return [self.node(cell, title, sub, own or tone)
                for cell, (title, sub, own) in zip(cells, (_item(i, 3) for i in items))]

    def link(self, a: Rect, b: Rect, label=None, route="auto", dashed=False, both=False, color=None, width=2.2,
             gap=4):
        """从 a 指向 b 的连线。route: auto / h / v / hv / vh / hvh / vhv（横竖走法）。
        dashed 表示异步、可选或事件；both 表示双向。"""
        points = _route(a, b, route, gap)
        self.s.path(polygon(points, closed=False), line=color or self.t.link, line_width=width,
                    dash="dash" if dashed else None, tail="triangle", head="triangle" if both else None, name="连线")
        if label:
            segments = list(zip(points, points[1:]))
            (x1, y1), (x2, y2) = max(segments, key=lambda seg: abs(seg[0][0] - seg[1][0]) + abs(seg[0][1] - seg[1][1]))
            size = self.t.size["caption"]
            w, h = text_width(label, size) + 12, line_height(size)
            style = self.t.style("caption", color=self.t.text_muted)
            if abs(x2 - x1) >= abs(y2 - y1):
                self.s.text((x1 + x2) / 2 - w / 2, y1 - h - 2, w, h, label, align="center", wrap=False, **style)
            else:
                self.s.text(x1 + 6, (y1 + y2) / 2 - h / 2, w, h, label, wrap=False, **style)
        return points

    def legend(self, r: Rect, items):
        """图例。items: [(色调, 含义), ...]；色调写 "dashed" 表示虚线。"""
        t, size, x = self.t, self.t.size["caption"], r.x
        h = line_height(size)
        for tone, label in items:
            if tone == "dashed":
                self.s.line(x, r.y + h / 2, x + 28, r.y + h / 2, t.link, 1.6, dash="dash")
            else:
                c = t.tone(tone)
                self.s.box(x, r.y + 2, 28, h - 4, "roundRect", 0.25, fill=c["fill"], line=c["line"], line_width=1.2)
            w = text_width(label, size) + 8
            self.s.text(x + 36, r.y, w, h, label, wrap=False, **t.style("caption", color=t.text_muted))
            x += 36 + w + 22


class DiagramMixin:
    """Page 的图示能力。"""

    def diagram(self) -> Diagram:
        return Diagram(self)

    # ---------------------------------------------------------------- 架构与分层

    def panorama(self, r: Rect, rows, split=(26, 54, 20)) -> list[Rect]:
        """分层全景图：每层一条横带，左边是层名，中间画这一层的内容，右边是这一层带来的价值。
        rows: [(层名, 副标题或 None, [右侧关键词...]), ...]，自上而下。
        返回每一层中间区域的 Rect，由调用方用 diagram()、gallery() 等往里画。"""
        t, out = self.t, []
        for band, (title, sub, keys) in zip(r.rows(len(rows), 14), rows):
            self.s.box(band.x, band.y, band.w, band.h, "roundRect", _radius(band, 10), fill=t.flat_fill,
                       line=t.flat_line, line_width=1.3, name="全景层")
            left, middle, right = Rect(band.x + 26, band.y + 12, band.w - 46, band.h - 24).cols(list(split), 22)
            block_w = left.right + 4 - band.x
            self.s.box(band.x, band.y, block_w, band.h, "roundRect", _radius(Rect(band.x, band.y, block_w, band.h), 10),
                       fill=t.strong_fill, name="层名色块")
            heading = [self.line(title, t.on_feature_highlight)[0]]
            if sub:
                heading.append([(sub, {"size": t.size["small"], "color": t.strong_muted})])
            self.s.text(left.x, left.y, left.w - 8, left.h, heading, valign="middle", leading=1.1, name="层名",
                        **t.style("h", color=t.strong_text))
            key_h = min((right.h - 6 * (len(keys) - 1)) / max(len(keys), 1), line_height(t.size["small"]) + 12)
            total = key_h * len(keys) + 6 * (len(keys) - 1)
            for index, key in enumerate(keys):
                hot = "**" in key
                tone = t.tone("warm" if hot else "muted")
                self.s.box(right.x, right.cy - total / 2 + index * (key_h + 6), right.w, key_h, "roundRect", 0.5,
                           fill=tone["fill"], line=tone["line"], line_width=1.2, text=key.replace("**", ""), align="center",
                           wrap=False, name="层价值", **t.style("small", color=tone["text"]))
            out.append(middle)
        return out

    def tiers(self, r: Rect, tiers) -> Rect:
        """平台体系图：自上而下的几层平台，每层一排单元和一个底座标签，左侧是层的归类。
        tiers: [(左侧归类, 底座标签, [单元...]), ...]，最下面一层是基础，用实心单元。"""
        t, d = self.t, Diagram(self)
        side, body = r.take_left(96, 14)
        bands = body.rows(len(tiers), 20)
        size = t.size["small"] + 1
        tab_h = line_height(size) + 12
        for index, (band, (side_label, base, cells)) in enumerate(zip(bands, tiers)):
            last = index == len(tiers) - 1
            plate = Rect(band.x, band.y, band.w, band.h - tab_h / 2)
            c = t.tone("primary")
            self.s.box(plate.x, plate.y, plate.w, plate.h, "roundRect", _radius(plate, 10), fill=c["panel"],
                       line=c["line"], line_width=1.2, name="平台层")
            inner = Rect(plate.x + 18, plate.y + 14, plate.w - 36, plate.h - 28 - tab_h / 2)
            d.row(inner, cells, tone="solid" if last else "plain", gap=10)
            w = text_width(base, size) + 56
            self.s.path(polygon([(band.cx - w / 2 - 16, band.bottom - tab_h), (band.cx + w / 2 + 16, band.bottom - tab_h),
                                 (band.cx + w / 2, band.bottom), (band.cx - w / 2, band.bottom)]),
                        fill=t.tone("solid")["fill"], line=t.tone("solid")["line"], line_width=1.2, name="底座标签")
            self.s.text(band.cx - w / 2, band.bottom - tab_h, w, tab_h, base, align="center", wrap=False,
                        **t.style("small", size=size, color=t.tone("solid")["text"]))
            self.s.text(side.x, band.y, side.w, band.h, side_label.split("\n"), align="center", valign="middle",
                        leading=1.05, name="层归类", **t.style("h", color=t.accent))
            if not last:
                self.s.box(side.cx - 10, band.bottom + 1, 20, 18, "upArrow", (0.5, 0.6), fill=t.mark, name="向上箭头")
        return r

    def iso_stack(self, r: Rect, layers) -> Rect:
        """2.5D 层叠图：几块悬浮的斜视平板自上而下叠放，右侧引出每层的说明。
        layers: [(层名, 说明), ...]，2～4 层，上层在前。
        这是 2.5D 图示，按 2.5D 的画法：半透明的面、不描边、有阴影和柔光，层名用高对比的标签。"""
        t, n, iso = self.t, len(layers), self.t.iso()
        w = min(r.w * 0.54, r.h / (0.57 + 0.47 * (n - 1)))
        h, thick = w * 0.5, w * 0.07
        step = h * 0.8 + thick
        cx = r.x + w / 2
        top = r.y + (r.h - (h + thick + step * (n - 1))) / 2
        size = t.size["small"] + 1.5
        for index in range(n - 1, -1, -1):      # 先画下层，上层压在上面
            name, note = layers[index]
            y = top + index * step
            mid = y + h / 2
            for side, face in ((-1, iso["left"]), (1, iso["right"])):
                self.s.path(polygon([(cx + side * w / 2, mid), (cx, y + h), (cx, y + h + thick),
                                     (cx + side * w / 2, mid + thick)]), fill=face,
                            shadow=iso["shadow"], name="平板侧面")
            self.s.path(polygon([(cx, y), (cx + w / 2, mid), (cx, y + h), (cx - w / 2, mid)]),
                        fill=lin(90, iso["tops"][min(index, 3)], iso["tops"][min(index + 1, 3)]), glow=iso["glow"],
                        name="平板顶面")
            label_w, label_h = text_width(name, size) + 40, line_height(size) + 12
            self.s.box(cx - label_w / 2, mid - label_h / 2, label_w, label_h, "roundRect", 0.5, fill=iso["label_fill"],
                       shadow=iso["label_shadow"], text=name, align="center", wrap=False, name="层名标签",
                       **t.style("small", size=size, color=iso["label_text"]))
            note_x = cx + w / 2 + 44
            self.s.line(cx + w / 2 + 6, mid, note_x - 10, mid, t.link, 1.2, dash="dash", name="引线")
            self.s.box(note_x - 11, mid - 5, 10, 10, "ellipse", fill=t.mark, name="引线端点")
            self.text(Rect(note_x + 6, mid - step / 2 + 6, r.right - note_x - 6, step - 12), note, valign="middle",
                      leading=1.12)
        return r

    def lanes(self, r: Rect, names) -> list[Rect]:
        """分区泳道：把一张大图按阶段或模块分成几条横带，每条左侧有竖排的名称。
        返回每条泳道内部的 Rect。名称不超过 6 个汉字。"""
        t, out, c = self.t, [], self.t.tone("primary")
        for band, name in zip(r.rows(len(names), 12), names):
            tab, body = band.take_left(40, 10)
            self.s.box(tab.x, tab.y, tab.w, tab.h, "roundRect", 0.2, fill=c["fill"], line=c["line"], line_width=1.2,
                       text=list(name), align="center", leading=0.95, name="泳道名", **t.style("small", color=c["text"]))
            self.s.box(body.x, body.y, body.w, body.h, "roundRect", _radius(body, 10), line=t.link, line_width=1.2,
                       dash="dash", name="泳道")
            out.append(body.inset(14, 12))
        return out

    # ---------------------------------------------------------------- 链路与机制

    def stages(self, r: Rect, names) -> list[Rect]:
        """分阶段流程：几个依次推进的阶段并排，底部一条箭头带写阶段名。
        返回每个阶段上方区域的 Rect，由调用方往里画该阶段的细节。"""
        t = self.t
        band_h = line_height(t.size["h"]) + 20
        columns = r.cols(len(names), 0)
        tints = t.stage_tints
        for index, column in enumerate(columns):
            self.s.box(column.x, column.y, column.w, column.h - band_h, fill=tints[min(index, 3)], name="阶段底")
        for index in range(len(names) - 1, -1, -1):       # 从右往左画，左边的箭头尖压在右边之上
            column = columns[index]
            self.s.box(column.x, column.bottom - band_h, column.w + (22 if index < len(names) - 1 else 0), band_h,
                       "homePlate", 0.32, fill=t.stage[min(index + (0 if len(names) > 3 else 1), 4)],
                       text=names[index], align="center", name="阶段名", **t.style("h", color="#FFFFFF", spacing=4))
        return [Rect(c.x + 18, c.y + 16, c.w - 36, c.h - band_h - 32) for c in columns]

    def cycle(self, r: Rect, center, steps) -> Rect:
        """闭环图：若干环节沿圆环顺时针循环，圆心写这个闭环围绕的对象。
        center: (名称, 说明)；steps: [(环节, 说明), ...]，3～6 个。"""
        t, n = self.t, len(steps)
        size_h, size_s = t.size["small"] + 1, t.size["caption"]
        label_h = line_height(size_h) + line_height(size_s)
        radius = min(r.h / 2 - label_h - 14, r.w * 0.2)
        cx, cy = r.cx, r.cy
        self.s.box(cx - radius, cy - radius, 2 * radius, 2 * radius, "ellipse",
                   line=t.ring, line_width=12,
                   name="环")
        core = radius * 0.58
        title, note = _item(center, 2)
        paragraphs = [title] + ([[(note, {"size": size_s, "color": t.tone("warm")["sub"]})]] if note else [])
        c = t.tone("warm")
        self.s.box(cx - core, cy - core, 2 * core, 2 * core, "ellipse", fill=c["fill"], line=c["line"], line_width=1.6,
                   text=paragraphs, align="center", leading=1.05, name="闭环对象", **t.style("h", color=c["text"]))
        for index, (name, sub) in enumerate(_item(s, 2) for s in steps):
            angle = -90 + index * 360 / n
            rad_ = math.radians(angle)
            x, y = cx + radius * math.cos(rad_), cy + radius * math.sin(rad_)
            number = t.tone("solid")
            self.s.box(x - 20, y - 20, 40, 40, "ellipse", fill=number["fill"], line=number["line"], line_width=1.5,
                       text=str(index + 1), align="center", name="环节序号", **t.style("small", color=number["text"]))
            middle = math.radians(angle + 180 / n)
            self.s.box(cx + radius * math.cos(middle) - 9, cy + radius * math.sin(middle) - 13, 18, 26, "chevron", 0.6,
                       fill=t.mark, rotate=angle + 180 / n + 90, name="方向")
            text = [name] + ([[(sub, {"size": size_s, "color": t.text_muted})]] if sub else [])
            style = t.style("small", size=size_h, leading=1.05)
            if math.cos(rad_) > 0.3:
                self.s.text(x + 30, y - label_h / 2, 260, label_h, text, wrap=False, **style)
            elif math.cos(rad_) < -0.3:
                self.s.text(x - 290, y - label_h / 2, 260, label_h, text, align="right", wrap=False, **style)
            elif math.sin(rad_) < 0:
                self.s.text(x - 160, y - 26 - label_h, 320, label_h, text, align="center", wrap=False, **style)
            else:
                self.s.text(x - 160, y + 26, 320, label_h, text, align="center", wrap=False, **style)
        return r

    def exchange(self, r: Rect, left, right, forward, backward) -> Rect:
        """双向交互：左右两个主体，中间一来一回两个箭头。
        left / right: (名称, [要点...], 定位标签或 None)；forward / backward 是箭头上的字。"""
        t = self.t
        a, middle, b = r.cols([5, 3, 5], 24)
        for cell, (title, items, tag) in ((a, _item(left, 3)), (b, _item(right, 3))):
            tag_h = line_height(t.size["small"]) + 14 if tag else 0
            self.card(Rect(cell.x, cell.y, cell.w, cell.h - tag_h / 2), title, items, tone="flat")
            if tag:
                w = text_width(tag, t.size["small"] + 1) + 48
                tone = t.tone("primary")
                self.s.box(cell.cx - w / 2, cell.bottom - tag_h, w, tag_h, "roundRect", 0.3, fill=tone["fill"],
                           line=tone["line"], line_width=1.3, text=tag, align="center", wrap=False, name="定位标签",
                           **t.style("small", size=t.size["small"] + 1, color=tone["text"]))
        arrow_h = min(64, r.h * 0.26)
        for geom, y, label in (("rightArrow", middle.cy - arrow_h - 8, forward), ("leftArrow", middle.cy + 8, backward)):
            self.s.box(middle.x, y, middle.w, arrow_h, geom, (0.56, 0.5), fill=t.mark, text=label, align="center",
                       name="交互箭头", **t.style("body", color=t.mark_text))
        return r

    # ---------------------------------------------------------------- 归类与组成

    def tree(self, r: Rect, root) -> Rect:
        """分类树：从左向右展开的层级，用来梳理研究现状、方法分类、功能组成。
        root: (名称, 说明或 None, [子节点...])；叶子可以写成 "名称" 或 (名称, 说明)。"""
        t, d = self.t, Diagram(self)

        def normalize(node):
            title, note, children = _item(node, 3)
            return title, note, [normalize(c) for c in (children or [])]

        def leaves(node):
            return sum(leaves(c) for c in node[2]) or 1

        def depth(node):
            return 1 + max((depth(c) for c in node[2]), default=0)

        tree = normalize(root)
        levels, total = depth(tree), leaves(tree)
        column_w = r.w / levels
        box_w = column_w - 46
        unit = r.h / total
        tones = ["solid", "primary", "plain", "plain"]

        def draw(node, level, y0):
            title, note, children = node
            span = leaves(node) * unit
            box_h = min(unit - 10, 70) if not children else min(span - 10, 64)
            box = Rect(r.x + level * column_w, y0 + span / 2 - box_h / 2, box_w, box_h)
            d.node(box, title, note, tones[min(level, 3)])
            y, centers = y0, []
            for child in children:
                child_box = draw(child, level + 1, y)
                centers.append(child_box.cy)
                y += leaves(child) * unit
            if children:
                trunk = box.right + 23
                self.s.line(box.right + 2, box.cy, trunk, box.cy, t.link, 1.4, name="树干")
                self.s.line(trunk, min(centers), trunk, max(centers), t.link, 1.4, name="树干")
                for center in centers:
                    self.s.line(trunk, center, box.right + 44, center, t.link, 1.4, name="分支")
            return box

        draw(tree, 0, r.y)
        return r

    def hub(self, r: Rect, center, spokes) -> Rect:
        """中心辐射图：中间是核心系统，四周是它的组成部分或应用方向，适合配实物图。
        center: (名称, 图片路径或 None)；spokes: [(名称, [说明...], 图片路径或 None), ...]，2～6 个，左右各半。"""
        t = self.t
        diameter = min(r.h * 0.66, r.w * 0.27)
        cx, cy = r.cx, r.cy
        title, image = _item(center, 2)
        size = t.size["h"]
        if image:
            self.s.image(image, cx - diameter / 2, cy - diameter / 2, diameter, diameter, cover=True, geom="ellipse",
                         line=t.tone("solid")["fill"], line_width=3, name="核心图片")
            lines = title.split("\n")
            w = max(text_width(line, size) for line in lines) + 44
            h = line_height(size) * len(lines) + 14
            core = t.tone("solid")
            self.s.box(cx - w / 2, cy + diameter / 2 - h * 0.8, w, h, "roundRect", 0.22, fill=core["fill"],
                       line=core["line"], line_width=1.3, text=lines, align="center", leading=1.0, wrap=False,
                       name="核心名称", **t.style("h", color=core["text"]))
        else:
            core = t.tone("solid")
            self.s.box(cx - diameter / 2, cy - diameter / 2, diameter, diameter, "ellipse", fill=core["fill"],
                       line=core["line"], line_width=1.5, text=title.split("\n"), align="center", leading=1.05,
                       name="核心", **t.style("h", size=size + 3, color=core["text"]))
        half = (len(spokes) + 1) // 2
        zone_w = (r.w - diameter) / 2 - 36
        for items, on_left in ((spokes[:half], True), (spokes[half:], False)):
            if not items:
                continue
            zone = Rect(r.x if on_left else r.right - zone_w, r.y, zone_w, r.h)
            for cell, (name, notes, picture) in zip(zone.rows(len(items), 18), (_item(i, 3) for i in items)):
                d_pic = min(cell.h, zone_w * 0.42) if picture else 0
                pic_x = (cell.right - d_pic) if on_left else cell.x
                target = (pic_x + d_pic / 2, cell.cy) if picture else ((cell.right if on_left else cell.x), cell.cy)
                if picture:
                    self.s.image(picture, pic_x, cell.cy - d_pic / 2, d_pic, d_pic, cover=True, geom="ellipse",
                                 line=t.frame, line_width=2, name="分支图片")
                text_w = cell.w - d_pic - (18 if picture else 0)
                text_x = cell.x if on_left else cell.x + d_pic + (18 if picture else 0)
                head_h = line_height(size) + 2
                body_h = line_height(t.size["small"]) * 1.12 * len(notes or [])
                y = cell.cy - (head_h + body_h) / 2
                align = "right" if on_left else "left"
                self.s.text(text_x, y, text_w, head_h, name, align=align, wrap=False, name="分支名称",
                            **t.style("h", color=t.accent))
                if notes:
                    self.s.text(text_x, y + head_h, text_w, body_h + 6, [f"· {n}" for n in notes], align=align,
                                valign="top", leading=1.12, name="分支说明", **t.style("small"))
                dx, dy = target[0] - cx, target[1] - cy
                length = math.hypot(dx, dy)
                ux, uy = dx / length, dy / length
                start, end = diameter / 2 + 10, length - d_pic / 2 - 12
                if end - start > 16:
                    self.s.line(cx + ux * start, cy + uy * start, cx + ux * end, cy + uy * end, t.mark, 2.6,
                                tail="triangle", name="辐射箭头")
        return r

    # ---------------------------------------------------------------- 图片证据

    def _picture(self, box: Rect, path, cover: bool):
        """放一张带细边框的图片：cover 裁切铺满，否则等比缩放后居中。返回图片实际占的矩形。"""
        if cover:
            self.s.image(path, box.x, box.y, box.w, box.h, cover=True, line=self.t.frame, line_width=1.2, name="图片")
            return box
        image = Image.open(path)
        scale = min(box.w / image.width, box.h / image.height)
        w, h = image.width * scale, image.height * scale
        placed = Rect(box.cx - w / 2, box.cy - h / 2, w, h)
        self.s.image(path, placed.x, placed.y, w, h, line=self.t.frame, line_width=1.2, name="图片")
        return placed

    def gallery(self, r: Rect, items, columns=None, cover=True) -> Rect:
        """图片组：真实截图、实拍、数据图成组摆放，每张下面一行说明。
        items: [(图片路径, 说明), ...]。数据图用 cover=False 保证不被裁切。"""
        t, n = self.t, len(items)
        columns = columns or (n if n <= 3 else math.ceil(n / 2))
        caption_h = line_height(t.size["small"]) + 8
        for cell, (path, caption) in zip(r.grid(columns, math.ceil(n / columns), 18), items):
            placed = self._picture(Rect(cell.x, cell.y, cell.w, cell.h - caption_h), path, cover)
            self.s.text(cell.x, placed.bottom + 4, cell.w, caption_h - 4, self.line(caption), align="center",
                        name="图片说明", **t.style("small"))
        return r

    def annotated(self, r: Rect, image_path, marks, ratio=0.62) -> Rect:
        """带标注的截图：左边是截图，图上用编号圆点标出要看的位置，右边逐条解释。
        marks: [(横向位置 0~1, 纵向位置 0~1, 说明), ...]，位置相对于截图本身。"""
        t = self.t
        left, right = r.cols([ratio, 1 - ratio], 28)
        placed = self._picture(left, image_path, cover=False)
        ink = t.mark_text

        def marker(x, y, number, d=30):
            self.s.box(x - d / 2, y - d / 2, d, d, "ellipse", fill=t.mark, line="#FFFFFF", line_width=1.6,
                       text=str(number), align="center", name="标注点",
                       **t.style("small", color=ink))

        row_h = min((right.h - 10 * (len(marks) - 1)) / len(marks), line_height(t.size["body"]) * 3.4)   # 说明卡片不随区域拉高
        total = row_h * len(marks) + 10 * (len(marks) - 1)
        rows = Rect(right.x, right.cy - total / 2, right.w, total).rows(len(marks), 10)
        for index, (cell, (fx, fy, note)) in enumerate(zip(rows, marks), 1):
            marker(placed.x + fx * placed.w, placed.y + fy * placed.h, index)
            self._panel(cell, tone="flat", name="标注说明")
            marker(cell.x + 30, cell.cy, index)
            self.s.text(cell.x + 58, cell.y, cell.w - 72, cell.h, self.line(note), leading=1.12, **t.style("body"))
        return r

    def callout(self, r: Rect, text) -> Rect:
        """结论横条：放在两组图片或图表之间，用一句话点明对照的结论，例如“速度提升 **1000 倍以上**”。"""
        t = self.t
        tone = t.tone("warm")
        self.s.box(r.x, r.y, r.w, r.h, "roundRect", _radius(r, 8), fill=tone["panel"], line=tone["line"], line_width=1.3,
                   name="结论横条")
        self.s.text(r.x, r.y, r.w, r.h, self.line(text), align="center", wrap=False,
                    **t.style("h", size=t.size["h"] + 2))
        return r
