"""PowerPresent 绘制底层：在 python-pptx 之上直接写 DrawingML。

python-pptx 自带的 API 表达不了半透明、渐变描边、发光、柔和阴影、异形轮廓，
而这些正是发布会风格页面的主要视觉语言。这里把它们收敛成一套简洁的画布接口，
产出的全部是 PowerPoint 原生形状和文本，打开后可以直接编辑。

坐标约定：整页是 1600 x 900 的虚拟像素画布（16:9），所有 x / y / w / h 都用这个单位，
方便直接对照 1600 x 900 的参考图量尺寸。字号仍然用磅（pt）；
在这块画布上，一个高 h 像素的汉字约等于 h * 0.6 磅。

颜色约定："#RRGGBB" 或 "#RRGGBBAA"（末两位是不透明度）。
渐变用 lin(角度, 颜色...) 与 rad(颜色...) 构造，颜色可写成 (位置0~1, 颜色)。
"""
from __future__ import annotations

from xml.sax.saxutils import escape

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from pptx.util import Emu

CANVAS_W, CANVAS_H = 1600, 900
EMU_PER_PX = 12192000 // CANVAS_W  # 整页宽 13.333 英寸

_NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
       'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
       'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')


def _emu(px: float) -> int:
    return int(round(px * EMU_PER_PX))


# ---------------------------------------------------------------- 颜色与填充

def _color(spec: str) -> str:
    spec = spec.lstrip("#")
    rgb, alpha = spec[:6].upper(), spec[6:8]
    if alpha and alpha.lower() != "ff":
        return f'<a:srgbClr val="{rgb}"><a:alpha val="{round(int(alpha, 16) / 255 * 100000)}"/></a:srgbClr>'
    return f'<a:srgbClr val="{rgb}"/>'


def lin(angle: float, *stops) -> dict:
    """线性渐变。angle 是颜色推进的方向：0 从左到右，90 从上到下。"""
    return {"kind": "lin", "angle": angle, "stops": _stops(stops)}


def rad(*stops, center=(0.5, 0.5)) -> dict:
    """径向渐变，从 center（相对位置）向外扩散。"""
    return {"kind": "rad", "center": center, "stops": _stops(stops)}


def _stops(stops):
    if all(isinstance(s, str) for s in stops):
        last = max(len(stops) - 1, 1)
        return [(i / last, s) for i, s in enumerate(stops)]
    return list(stops)


def _fill(spec) -> str:
    if spec is None:
        return "<a:noFill/>"
    if isinstance(spec, str):
        return f"<a:solidFill>{_color(spec)}</a:solidFill>"
    stops = "".join(f'<a:gs pos="{round(p * 100000)}">{_color(c)}</a:gs>' for p, c in spec["stops"])
    if spec["kind"] == "lin":
        direction = f'<a:lin ang="{round(spec["angle"] * 60000)}" scaled="0"/>'
    else:
        cx, cy = (round(v * 100000) for v in spec["center"])
        direction = (f'<a:path path="circle"><a:fillToRect l="{cx}" t="{cy}" '
                     f'r="{100000 - cx}" b="{100000 - cy}"/></a:path>')
    return f'<a:gradFill rotWithShape="1"><a:gsLst>{stops}</a:gsLst>{direction}</a:gradFill>'


def _line(color, width, dash, head, tail) -> str:
    if color is None:
        return "<a:ln><a:noFill/></a:ln>"
    parts = [_fill(color)]
    if dash:
        parts.append(f'<a:prstDash val="{dash}"/>')
    parts.append("<a:round/>")
    if head:
        parts.append(f'<a:headEnd type="{head}" w="lg" len="lg"/>')
    if tail:
        parts.append(f'<a:tailEnd type="{tail}" w="lg" len="lg"/>')
    return f'<a:ln w="{_emu(width)}" cap="flat">{"".join(parts)}</a:ln>'


def _effects(glow, shadow, soft=None) -> str:
    """glow=(颜色, 半径px)；shadow=(颜色, 模糊px, 偏移px, 方向角度)；soft=柔化边缘px。"""
    parts = []
    if glow:
        parts.append(f'<a:glow rad="{_emu(glow[1])}">{_color(glow[0])}</a:glow>')
    if shadow:
        color, blur, dist, angle = (list(shadow) + [0, 90])[:4]
        parts.append(f'<a:outerShdw blurRad="{_emu(blur)}" dist="{_emu(dist)}" dir="{round(angle * 60000)}" '
                     f'algn="ctr" rotWithShape="0">{_color(color)}</a:outerShdw>')
    if soft:
        parts.append(f'<a:softEdge rad="{_emu(soft)}"/>')
    return f"<a:effectLst>{''.join(parts)}</a:effectLst>" if parts else ""


# ---------------------------------------------------------------- 几何轮廓

def _preset(name: str, adj) -> str:
    guides = ""
    if adj is not None:
        values = adj if isinstance(adj, (list, tuple)) else [adj]
        names = ["adj"] if len(values) == 1 else [f"adj{i + 1}" for i in range(len(values))]
        guides = "".join(f'<a:gd name="{n}" fmla="val {round(v * 100000)}"/>' for n, v in zip(names, values))
    return f'<a:prstGeom prst="{name}"><a:avLst>{guides}</a:avLst></a:prstGeom>'


def _custom(commands, x0, y0, w, h) -> str:
    """把路径命令（绝对像素坐标）写成自定义几何。命令：M/L 点，C 三次贝塞尔，Z 闭合。"""
    def pt(x, y):
        return f'<a:pt x="{_emu(x - x0)}" y="{_emu(y - y0)}"/>'
    body = []
    for cmd in commands:
        op, v = cmd[0], cmd[1:]
        if op == "M":
            body.append(f"<a:moveTo>{pt(*v)}</a:moveTo>")
        elif op == "L":
            body.append(f"<a:lnTo>{pt(*v)}</a:lnTo>")
        elif op == "C":
            body.append(f"<a:cubicBezTo>{pt(v[0], v[1])}{pt(v[2], v[3])}{pt(v[4], v[5])}</a:cubicBezTo>")
        elif op == "Z":
            body.append("<a:close/>")
    return (f'<a:custGeom><a:avLst/><a:gdLst/><a:ahLst/><a:cxnLst/><a:rect l="0" t="0" r="r" b="b"/>'
            f'<a:pathLst><a:path w="{_emu(w)}" h="{_emu(h)}">{"".join(body)}</a:path></a:pathLst></a:custGeom>')


def polygon(points, closed=True):
    """把点列表转成路径命令。"""
    commands = [("M", *points[0])] + [("L", *p) for p in points[1:]]
    return commands + ([("Z",)] if closed else [])


# ---------------------------------------------------------------- 文本

DEFAULT_FONT = {"latin": "Microsoft YaHei", "ea": "微软雅黑"}


def _run(text: str, st: dict) -> str:
    attrs = f'lang="zh-CN" altLang="en-US" sz="{round(st["size"] * 100)}" b="{int(bool(st.get("bold")))}"'
    if st.get("italic"):
        attrs += ' i="1"'
    if st.get("spacing"):
        attrs += f' spc="{round(st["spacing"] * 100)}"'
    font = {**DEFAULT_FONT, **(st.get("font") or {})}
    inner = (_fill(st.get("color", "#FFFFFF")) + _effects(st.get("glow"), st.get("shadow"))
             + f'<a:latin typeface="{font["latin"]}"/><a:ea typeface="{font["ea"]}"/><a:cs typeface="{font["latin"]}"/>')
    return f"<a:r><a:rPr {attrs}>{inner}</a:rPr><a:t>{escape(text)}</a:t></a:r>"


def _text_body(text, st: dict) -> str:
    """text：字符串（\\n 分段）或段落列表；段落可以是字符串，也可以是 [片段, ...]，
    片段是字符串或 (字符串, 覆盖样式字典)，用来在一行里混用颜色、字重。"""
    paragraphs = text.split("\n") if isinstance(text, str) else text
    align = {"left": "l", "center": "ctr", "right": "r", "justify": "just"}[st.get("align", "left")]
    spacing = f'<a:lnSpc><a:spcPct val="{round(st.get("leading", 1.0) * 100000)}"/></a:lnSpc>'
    after = f'<a:spcAft><a:spcPts val="{round(st.get("para_gap", 0) * 100)}"/></a:spcAft>'
    out = []
    for para in paragraphs:
        runs = [para] if isinstance(para, str) else para
        xml = "".join(_run(r, st) if isinstance(r, str) else _run(r[0], {**st, **r[1]}) for r in runs)
        out.append(f'<a:p><a:pPr algn="{align}">{spacing}<a:spcBef><a:spcPts val="0"/></a:spcBef>{after}</a:pPr>{xml}</a:p>')
    anchor = {"top": "t", "middle": "ctr", "bottom": "b"}[st.get("valign", "middle")]
    pad = [_emu(v) for v in st.get("pad", (0, 0, 0, 0))]  # 左 上 右 下
    vertical = ' vert="eaVert"' if st.get("vertical") else ""
    wrap = "square" if st.get("wrap", True) else "none"
    return (f'<p:txBody {_NS}><a:bodyPr wrap="{wrap}" lIns="{pad[0]}" tIns="{pad[1]}" rIns="{pad[2]}" bIns="{pad[3]}" '
            f'anchor="{anchor}"{vertical} rtlCol="0"><a:noAutofit/></a:bodyPr><a:lstStyle/>{"".join(out)}</p:txBody>')


_TEXT_KEYS = {"size", "color", "bold", "italic", "spacing", "font", "align", "valign", "leading",
              "para_gap", "pad", "vertical", "wrap"}


# ---------------------------------------------------------------- 画布

class Deck:
    """一份 16:9 演示文稿。"""

    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = Emu(_emu(CANVAS_W)), Emu(_emu(CANVAS_H))

    def slide(self, background=None, name: str | None = None) -> "Slide":
        """新增一页。background 可以是颜色、渐变，或一张铺满整页的背景图路径。"""
        return Slide(self, background, name)

    def save(self, path) -> None:
        self.prs.save(str(path))


class Slide:
    def __init__(self, deck: Deck, background, name):
        self.slide = deck.prs.slides.add_slide(deck.prs.slide_layouts[6])  # 空白版式
        self._shapes = self.slide.shapes
        if isinstance(background, dict) or (isinstance(background, str) and background.startswith("#")):
            self.box(0, 0, CANVAS_W, CANVAS_H, fill=background, name="背景")
        elif background:
            self.image(background, 0, 0, CANVAS_W, CANVAS_H, name="背景图")
        if name:
            self.slide.name = name

    # ---- 形状 ----

    def box(self, x, y, w, h, geom="rect", adj=None, fill=None, line=None, line_width=1.0, dash=None,
            glow=None, shadow=None, soft=None, rotate=0, flip=False, text=None, name=None, **text_style):
        """画一个预设形状（rect、roundRect、ellipse、chevron、trapezoid、parallelogram、hexagon…）。
        adj 是该形状的调节值（0~1），例如 roundRect 的圆角比例。传 text 即在形状内写字。"""
        return self._add(x, y, w, h, _preset(geom, adj), fill, line, line_width, dash, None, None,
                         glow, shadow, soft, rotate, flip, text, name, text_style)

    def path(self, commands, fill=None, line=None, line_width=1.0, dash=None, head=None, tail=None,
             glow=None, shadow=None, soft=None, name=None):
        """画任意轮廓（异形边框、斜切卡片、曲线）。commands 见 polygon() 与 _custom()。"""
        xs = [v for c in commands for v in c[1::2]]
        ys = [v for c in commands for v in c[2::2]]
        x0, y0 = min(xs), min(ys)
        w, h = max(max(xs) - x0, 0.01), max(max(ys) - y0, 0.01)
        return self._add(x0, y0, w, h, _custom(commands, x0, y0, w, h), fill, line, line_width, dash,
                         head, tail, glow, shadow, soft, 0, False, None, name, {})

    def line(self, x1, y1, x2, y2, color="#FFFFFF", width=1.0, dash=None, head=None, tail=None, glow=None, name=None):
        """直线。head / tail 可取 triangle、arrow、oval 等箭头样式。"""
        return self.path([("M", x1, y1), ("L", x2, y2)], line=color, line_width=width, dash=dash,
                         head=head, tail=tail, glow=glow, name=name)

    def text(self, x, y, w, h, text, name=None, **text_style):
        """纯文本框。常用样式：size（磅）、color、bold、align、valign、leading、glow、shadow。"""
        return self.box(x, y, w, h, text=text, name=name, **text_style)

    def image(self, path, x, y, w, h, name=None, cover=False, geom=None, line=None, line_width=1.0):
        """放一张图片。cover=True 时等比放大并裁掉多余部分以铺满矩形（否则按给定宽高拉伸，
        调用方应自行保证比例）；geom 可取 "ellipse" 把图片裁成圆形；line 是边框颜色（#RRGGBB）。"""
        picture = self._shapes.add_picture(str(path), _emu(x), _emu(y), _emu(w), _emu(h))
        if cover:
            image_w, image_h = picture.image.size
            ratio = (image_w / image_h) / (w / h)
            if ratio > 1:
                picture.crop_left = picture.crop_right = (1 - 1 / ratio) / 2
            else:
                picture.crop_top = picture.crop_bottom = (1 - ratio) / 2
        if geom == "ellipse":
            picture.auto_shape_type = MSO_SHAPE.OVAL
        if line:
            picture.line.color.rgb = RGBColor.from_string(line.lstrip("#")[:6].upper())
            picture.line.width = Emu(_emu(line_width))
        if name:
            picture.name = name
        return picture

    # ---- 内部 ----

    def _add(self, x, y, w, h, geometry, fill, line, line_width, dash, head, tail,
             glow, shadow, soft, rotate, flip, text, name, text_style):
        unknown = set(text_style) - _TEXT_KEYS
        if unknown:
            raise TypeError(f"未知参数: {sorted(unknown)}")
        shape = self._shapes.add_shape(MSO_SHAPE.RECTANGLE, _emu(x), _emu(y), _emu(w), _emu(h))
        element = shape._element
        style = element.find(qn("p:style"))
        if style is not None:  # 去掉主题默认样式，避免带出默认的蓝色填充与描边
            element.remove(style)
        sp_pr = element.spPr
        for child in list(sp_pr):
            if child.tag != qn("a:xfrm"):
                sp_pr.remove(child)
        xfrm = sp_pr.find(qn("a:xfrm"))
        if rotate:
            xfrm.set("rot", str(round(rotate * 60000)))
        if flip:
            xfrm.set("flipH", "1")
        # 文字自身的发光/阴影写在文字上；形状没有填充和描边时，glow/shadow 归文字所有
        shape_has_ink = fill is not None or line is not None
        pieces = geometry + _fill(fill) + _line(line, line_width, dash, head, tail)
        if shape_has_ink:
            pieces += _effects(glow, shadow, soft)
        for node in etree.fromstring(f"<root {_NS}>{pieces}</root>"):
            sp_pr.append(node)
        old_body = element.find(qn("p:txBody"))
        if old_body is not None:
            element.remove(old_body)
        if text is not None:
            st = {"size": 18, **text_style}
            if not shape_has_ink:
                st.update(glow=glow, shadow=shadow)
            element.append(etree.fromstring(_text_body(text, st)))
        else:
            element.append(etree.fromstring(f"<p:txBody {_NS}><a:bodyPr/><a:lstStyle/><a:p/></p:txBody>"))
        if name:
            shape.name = name
        return shape
