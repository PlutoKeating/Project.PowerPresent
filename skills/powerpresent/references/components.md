# 组件使用手册

组件库在 `scripts/powerpresent/`，产出的文字、形状、图表都是 PowerPoint 原生对象，可直接编辑。每个组件在两套配色、深浅底色下的实际样子见 `examples/demo/out/preview/`（JPEG）；完整的调用示例见 `examples/demo/build.py`。

## 目录

1 最小示例 · 2 Kit：一份稿子 · 3 四种页面 · 4 用 Rect 切分版面 · 5 内容组件一览 · 6 图示组件 · 7 内容该用哪个组件 · 8 文字标记与备注 · 9 组件不够用时 · 10 构建与检查

## 1. 最小示例

```python
import sys
sys.path.insert(0, "skills/powerpresent/scripts")
from powerpresent import Kit

kit = Kit(palette="journal", surface="light", density="read", footer="项目名 · 2026-11",
          sections=["问题", "方法", "结果", "结论"])

kit.cover("主标题一句话", subtitle="副标题补充对象与范围", kicker="会议或场合名称", meta=["汇报人", "单位 · 日期"])
kit.section(0, points=["小节一", "小节二"])

page = kit.content("页标题写成一句完整的结论", lead="一行导语：限定条件或背景", section=0)
area = page.takeaway("这一页最想让人记住的一句话")     # 先放结论条，拿到剩余区域
left, right = area.cols([3, 2])
page.card(left, "小标题", ["要点一，**关键词**会被强调", "要点二"])
page.stat(right, "87%", "指标名称", note="对比基准或来源")
page.notes("这一页的讲稿与数字口径")

kit.closing("全篇收束成的一句话", points=["结论一", "结论二"], contact="联系方式")
kit.save("out/deck.pptx")
```

## 2. Kit：一份稿子

`Kit(palette, surface, density, footer, sections, logo, backdrop)`

| 参数 | 取值 | 说明 |
|---|---|---|
| `palette` | `"journal"` / `"ink"` | 配色：学术场景用 `journal`，商业场景用 `ink`。见 `design-system.md` 第 2 节 |
| `backdrop` | `"wafer"`（默认）、`"brushed"`、`"blueprint"`、`"dots"`、`"contour"`、`"hairline"` 或 `None` | 底图母题，见 `design-system.md` 第 9 节 |
| `surface` | `"dark"` / `"light"` | 底色，全稿统一。怎么选见 `design-system.md` 第 3 节 |
| `density` | `"talk"` / `"read"` | 文字密度档，决定全部字号 |
| `footer` | 字符串 | 页脚左侧的“稿名 · 日期” |
| `sections` | 字符串列表 | 章节名，3～5 个，每个不超过 6 个汉字；决定页眉章节索引 |
| `logo` | 图片路径或 `None` | 只显示在封面右上角 |

## 3. 四种页面

| 方法 | 参数 | 返回 |
|---|---|---|
| `kit.cover(title, subtitle, kicker, meta, image)` | `title` 最多两行（`\n` 换行）；`meta` 是署名行列表；`image` 是可选的整幅封面图 | `Page` |
| `kit.section(index, title, points)` | `index` 是章节下标；`points` 是本章 2～4 个小节 | `Page` |
| `kit.content(title, lead, section)` | `title` 一行内的结论句；`section` 是所在章节下标 | `Page`，其 `area` 是内容区 |
| `kit.closing(message, points, contact)` | `message` 最多两行；`points` 最多三条 | `Page` |

## 4. 用 Rect 切分版面

`page.area` 是内容区（一个 `Rect`）。所有组件的第一个参数都是 `Rect`。**不要手写坐标**，用下面的方法从 `page.area` 切：

| 方法 | 作用 | 例子 |
|---|---|---|
| `r.cols(n)` / `r.cols([3, 2])` | 切成等宽列，或按比例切列 | `left, right = area.cols([3, 2])` |
| `r.rows(n)` / `r.rows([2, 3])` | 切成行 | `top, bottom = area.rows([2, 3])` |
| `r.grid(列数, 行数)` | 切成格子，按行优先返回 | `cells = area.grid(3, 2)` |
| `r.take_top(h)` / `take_bottom(h)` / `take_left(w)` | 切下固定尺寸的一条，返回 `(这一条, 剩余)` | `tags, rest = area.take_top(44)` |
| `r.inset(d)` | 四周向内缩 | |

默认间距是 24。内容少时不要把组件铺满整个 `area`：先用 `rows` 切出合适高度的一块，其余留白。

## 5. 内容组件一览

| 组件 | 调用 | 用来表达 |
|---|---|---|
| 结论条 | `area = page.takeaway(text)` | 这一页的一句话结论。固定在内容区底部，返回上方剩余区域，所以**最先调用** |
| 卡片 | `page.card(r, title, body, tone, number)` | 一个观点加两三条支撑。`body` 传字符串是一段话，传列表是要点。带标题时顶部是一条浅色调的头带。`tone`: `default` / `quiet`（次要）/ `strong`（重点，一页最多一张）/ `flat`（示意图里的容器：纯色、描边、无阴影） |
| 数据块 | `page.stat(r, value, label, note, tone)` | 一个大数字、它是什么、对比基准。默认是白卡片；`tone="strong"` 为实心反色块，一页最多一个 |
| 步骤流程 | `page.steps(r, [(标题, 说明), ...])` | 2～5 个有先后的步骤 |
| 分列清单 | `page.matrix(r, [(列标题, [单元格...]), ...])` | 几个并列类别各自包含什么 |
| 表格 | `page.table(r, header, rows, widths, highlight_row)` | 需要查数的明细；`highlight_row` 高亮结论所在行 |
| 左右对比 | `page.compare(r, (标题, 要点), (标题, 要点), labels)` | 改进前后、方案 A 与 B |
| 分层架构 | `page.stack(r, [(层名, [模块...]), ...])` | 上层依赖下层的系统结构，上层在前。梯形层叠板，按 2.5D 画法 |
| 圆形节点 | `page.nodes(r, [标签...])` | 4～6 个字数很少的环节 |
| 时间线 | `page.timeline(r, [(时间, 事件), ...])` | 3～6 个时间节点 |
| 托线要点块 | `page.spotlight(r, heading, items)` | 放在图旁边的无框解读，通常竖排三块 |
| 标签 | `page.pills(r, [标签...], align)` | 分类、适用范围、状态 |
| 引用 | `page.quote(r, text, by)` | 一句原话加出处 |
| 原生图表 | `page.chart(r, categories, {系列名: [数值...]}, kind, number_format, title)` | 柱状图 `bar`、横向条形图 `hbar`（类别名长时用）或折线图 `line`，数据可在 PowerPoint 里改 |
| 图片 | `page.figure(r, image_path, caption, source)` | 等比缩放的图片加图注与来源 |
| 文字 | `page.text(r, text, role)` / `page.bullets(r, items)` | 不需要容器的说明文字或要点 |
| 图示面板 | `inner = page.panel(r)` | 一块带投影的圆角浅色底，示意图和图表画在它里面；返回面板内的区域 |

`role` 可取 `title`、`lead`、`h`、`body`、`small`、`caption` 等，对应 `design-system.md` 第 5 节的字号角色。

## 6. 图示组件

表达架构、链路、机制和图片证据的组件，在 `scripts/powerpresent/diagrams.py`。选型与画图规则见 `design-system.md` 第 10 节，其中第 10.3 节规定了 2D 与 2.5D 两套画法（组件已内置，不要另加阴影、渐变或光效）；每个组件的完整示例见 `examples/demo/build.py`。

### 6.1 成型图示

| 组件 | 调用 | 说明 |
|---|---|---|
| 分层全景 | `mids = page.panorama(r, [(层名, 副标题, [价值关键词...]), ...])` | 返回每层中间区域的 `Rect`，再往里画框线图或放图片 |
| 平台体系 | `page.tiers(r, [(左侧归类, 底座标签, [单元...]), ...])` | 自上而下，最下一层为基础，用实心单元 |
| 2.5D 层叠 | `page.iso_stack(r, [(层名, 说明), ...])` | 2～4 层，上层在前 |
| 分阶段流程 | `areas = page.stages(r, [阶段名...])` | 返回每个阶段内部的 `Rect`，再往里画细节 |
| 分区泳道 | `areas = page.lanes(r, [名称...])` | 返回每条泳道内部的 `Rect` |
| 闭环 | `page.cycle(r, (对象, 说明), [(环节, 说明), ...])` | 3～6 个环节，顺时针 |
| 双向交互 | `page.exchange(r, (名称, [要点], 标签), (名称, [要点], 标签), 去向, 回向)` | 两个主体一来一回 |
| 分类树 | `page.tree(r, (名称, 说明, [子节点...]))` | 从左向右展开；叶子写成 `(名称, 说明)` |
| 中心辐射 | `page.hub(r, (名称, 图片), [(名称, [说明...], 图片), ...])` | 2～6 个分支，左右各半；图片可为 `None` |
| 图片组 | `page.gallery(r, [(图片, 说明), ...], columns, cover)` | 数据图用 `cover=False` 不裁切 |
| 带标注的截图 | `page.annotated(r, 图片, [(横向 0~1, 纵向 0~1, 说明), ...])` | 图上编号圆点，右侧逐条解释 |
| 结论横条 | `page.callout(r, text)` | 放在两组图之间，一句话点明差别 |

### 6.2 自由框线图

成型图示覆盖不了的结构，用 `page.diagram()` 自己搭：**先切格子，再放分组和节点，最后连线**。

```python
d = page.diagram()
legend, area = page.area.take_bottom(26, 14)
left, core, right = area.cols([5, 11, 5], 44)          # 区与区之间留 44，给连线走

g = d.group(core, "核心（本方）", tone="primary")       # 分组框，返回框内区域
top, bottom = g.rows([1, 1], 22)
a, b, c = d.row(top, [("组装器", "拼上下文"), ("自检", "回答前核对"), ("注册表", "取模型")], gap=28)
store = d.node(bottom, "数据与审计日志", "每次写入留一条记录", tone="warm")

d.link(a, b); d.link(b, c)                             # 同一行：自动走水平线
d.link(c, store, "写回", route="v")                     # 上下：竖直线，可带两三个字的标注
d.legend(legend, [("primary", "本方模块"), ("warm", "数据"), ("dashed", "可选路径")])
```

| 方法 | 作用 |
|---|---|
| `d.group(r, title, tone, dashed)` | 分组框，返回框内可用区域；`dashed=True` 表示逻辑范围 |
| `d.node(r, title, sub, tone)` | 一个节点，返回它的 `Rect` 供连线使用 |
| `d.row(r, items, tone, gap)` / `d.column(...)` | 把一行或一列等分成若干节点；元素是 `"标题"`、`(标题, 说明)` 或 `(标题, 说明, 色调)` |
| `d.link(a, b, label, route, dashed, both)` | 连线。`route`: `auto`、`h`、`v`、`hv`（先横后竖）、`vh`、`hvh`、`vhv` |
| `d.legend(r, [(色调, 含义), ...])` | 图例；色调写 `"dashed"` 表示虚线 |

色调取值与含义：`plain`、`primary`、`solid`、`accent`、`warm`、`alert`、`muted`（另有备用的 `cyan`、`purple`），见 `design-system.md` 第 10.2 节。

连线的注意点：需要连线的两个框之间至少留 22 的间距；连线会从框的边缘中点出发，所以要连的两个框应当在同一行或同一列上对齐，否则用 `hvh` / `vhv` 走折线；渲染后检查有没有线穿过别的框或压到文字，有就调整格子而不是硬连。

## 7. 内容该用哪个组件

| 你要说的是 | 用 |
|---|---|
| “结果是多少”——一到四个关键数字 | 数据块并排 |
| “比别人好多少”——多个对象在同一指标上的比较 | 原生柱状图，旁边一张卡片写怎么读 |
| “随时间怎么变” | 折线图；只有几个里程碑时用时间线 |
| “分几步做” | 步骤流程；环节名很短且多于四个时用圆形节点 |
| “由哪几部分组成” | 并列关系用分列清单；有上下依赖用分层架构；要讲清每层价值用分层全景 |
| “系统怎么运转、数据怎么流动” | 自由框线图；有反馈用闭环图；分阶段用阶段流程 |
| “真实效果是什么样” | 截图对照、带标注的截图、图片组 |
| “以前怎样、现在怎样” | 左右对比 |
| “三个并列的理由或特点” | 三张卡片并排 |
| “完整的实验数据” | 表格，高亮结论行；超过 6 行放附录 |
| “一张图就是证据” | 图片占内容区大半，旁边或下方一句结论 |
| 一句必须记住的话 | 结论条；如果它就是全页内容，考虑用章节页或结尾页的大字形式 |

技术内容优先选图示和图片类组件，卡片与要点用来写结论和解读。一页通常放 1～2 种组件，最多 3 种。组件种类越多，页面越像拼盘。

## 8. 文字标记与备注

- 任何组件的文字里，`**双星号**` 包住的片段显示为内容强调色。每页最多三处。
- `page.notes(text)` 写入演讲者备注。演讲档的每个内容页都要写讲稿；数字口径、出处细节也记在这里。
- 组件不会自动换小字号，也不会截断文字。渲染后发现溢出，按顺序处理：删字 → 减少条目 → 换组件 → 拆成两页。

## 9. 组件不够用时

成型图示和自由框线图都表达不了的内容（专用的原理图、实验装置示意），用底层画布直接画，但必须遵守设计系统：

```python
from powerpresent import lin
t, s = page.t, page.s          # 主题与底层画布
r = page.area
s.box(r.x, r.y, 300, 120, "roundRect", 0.1, fill=t.flat_fill, line=t.flat_line,
      text="文字", align="center", **t.style("body"))
s.line(r.x + 300, r.y + 60, r.x + 380, r.y + 60, t.accent, 1.5, tail="triangle")
```

- 颜色只从 `page.t`（主题）取：容器用 `t.flat_fill` / `t.flat_line`，彩色标签用 `t.tone(色调)`，连线用 `t.link`；字体与字号只用 `t.style(角色)`。不写十六进制色值。
- 坐标从 `page.area` 推算，不越出内容区。
- `s.box`（预设形状）、`s.path`（任意轮廓）、`s.line`、`s.text`、`s.image` 的参数见 `scripts/powerpresent/canvas.py` 的说明。
- 同一种图示在两页以上出现时，把它写成新组件加进 `components.py`，并在本手册和组件总览里补上。

## 10. 构建与检查

```bash
python examples/demo/build.py                                     # 重建示例（改了主题或组件后必须跑）
python skills/powerpresent/scripts/render_pptx.py out/deck.pptx out/preview   # 渲染成逐页 PNG
```

渲染后**逐页打开图片看**，按 `design-system.md` 第 13 节的清单检查。预览用的是 LibreOffice，字间距和发光效果与 PowerPoint、WPS 有出入，最终以后两者为准。
