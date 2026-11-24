"""端到端示例：一个完全虚构的分布式传感网络项目《云杉计划》。

所有项目名、场景、数字、站点和结论均为虚构，仅用于展示 PowerPresent 的
版式、组件与配色，不对应任何真实项目或原始汇报稿。

用法:
    python examples/demo/build.py
输出: examples/demo/out/demo-<配色>-<底色>.pptx 与 out/preview/ 下的预览图
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / "skills/powerpresent/scripts"))

from PIL import Image  # noqa: E402
from powerpresent import Kit  # noqa: E402
from render_pptx import render  # noqa: E402

SECTIONS = ["问题", "方案", "验证"]


def build(palette, surface):
    kit = Kit(palette=palette, surface=surface, density="read", footer="云杉计划 · 完全虚构示例 · 2026-11",
              sections=SECTIONS, backdrop="wafer")

    # 1 封面
    kit.cover("让每一台边缘设备都被看见",
              subtitle="云杉计划：面向分布式传感网络的低功耗监测系统",
              kicker="示例项目", meta=["完全虚构", "2026 年 11 月"])

    # 2 章节：问题
    kit.section(0, points=["覆盖广了，异常反而更难被及时发现", "把判断放到边缘，只上报结论"])

    # 3 问题
    page = kit.content("问题：设备越多，异常越难在第一时间被发现", section=0)
    area = page.takeaway("数据在路上堵住，告警在平台排队，现场只能靠人巡")
    items = [
        ("上报量大", ["全量数据回传，带宽和存储先被占满", "历史数据还要额外归档", "跨站点汇总更慢"]),
        ("响应慢", ["平台排队判断，异常发现总是晚一步", "高峰期延迟更明显", "异常定位仍然靠人工"]),
        ("维护贵", ["每次调整阈值都要到现场改设备", "版本回退也没有记录", "规则分散在每台设备"]),
    ]
    for index, (cell, (title, body)) in enumerate(zip(area.cols(3, 30), items), 1):
        page.card(cell, title, body, number=index)

    # 4 原则
    page = kit.content("原则：把判断放到边缘，只上报结论", section=0)
    area = page.takeaway("**本地聚合、边缘判断、只传结论**：让带宽用在异常上，而不是用在日常数据上")
    steps = [
        ("本地聚合", "把高频采样压成分钟级摘要"),
        ("边缘判断", "按现场阈值先做一次筛选"),
        ("只传结论", "正常数据留本地，异常才上报"),
    ]
    for index, (cell, (title, body)) in enumerate(zip(area.cols(3, 34), steps), 1):
        page.card(cell, title, body, number=index)

    # 5 架构
    page = kit.content("架构：感知、边缘、平台三层", section=1)
    top, mid, low = page.panorama(page.area, [
        ("1. 感知层", "温度、振动、电流", ["低功耗", "自描述", "即插即用"]),
        ("2. 边缘层", "采集、聚合、判断", ["本地缓存", "阈值判断", "**只传结论**"]),
        ("3. 平台层", "设备、告警、审计", ["统一看板", "分级告警", "操作留痕"]),
    ])
    d = page.diagram()
    a, b, c = top.cols([1, 1, 1], 18)
    d.node(a, "传感器 A", "温度 / 振动", tone="muted")
    d.node(b, "采集网关", "分钟级聚合", tone="primary")
    d.node(c, "现场规则", "阈值可下发", tone="warm")
    ca, cb, cc = mid.cols([1, 1, 1], 18)
    d.node(ca, "本地缓存", "断网不丢数", tone="muted")
    d.node(cb, "异常判断", "正常留本地", tone="solid")
    d.node(cc, "上报队列", "只发结论", tone="warm")
    la, lb, lc = low.cols([1, 1, 1], 18)
    d.node(la, "设备台账", "型号 / 位置", tone="muted")
    d.node(lb, "告警中心", "分级通知", tone="primary")
    d.node(lc, "审计日志", "操作可追溯", tone="warm")

    # 6 运行链路
    page = kit.content("运行链路：采集 → 聚合 → 判断 → 上报", section=1)
    legend, area = page.area.take_bottom(26, 14)
    d = page.diagram()
    left, core, right = area.cols([5, 11, 5], 44)
    g1 = d.group(left, "现场", tone="muted")
    sensors = d.column(g1, [("温度", "低频采样"), ("振动", "高频采样"), ("电流", "阈值采样")], gap=10)
    g2 = d.group(core, "边缘网关", tone="primary")
    r1, r2, r3 = g2.rows([4, 4, 4], 18)
    collect, agg, judge = d.row(r1, ["采集", "聚合", "判断"], gap=24)
    cache, queue = d.row(r2, [("本地缓存", "保留 7 天", "muted"), ("上报队列", "只发结论", "warm")], gap=24)
    rule = d.node(r3, "规则与版本", "阈值随策略下发，变更留痕", tone="solid")
    g3 = d.group(right, "平台", tone="muted")
    platform = d.column(g3, [("设备台账", "位置与型号"), ("告警中心", "分级通知"), ("审计日志", "操作留痕")], gap=10)
    d.link(sensors[0], collect, route="h"); d.link(sensors[1], collect, route="h"); d.link(sensors[2], collect, route="h")
    d.link(collect, agg); d.link(agg, judge); d.link(judge, queue, route="v")
    d.link(queue, platform[1], route="h")
    d.link(rule, judge, route="v", dashed=True)
    d.legend(legend, [("primary", "边缘主路径"), ("warm", "异步或缓存"), ("muted", "现场与平台"), ("dashed", "策略下发")])

    # 7 对比
    page = kit.content("集中式与边缘式：同样的覆盖，不同的上报量", section=1)
    page.compare(page.area,
                 ("集中式", ["全量数据回传", "平台统一判断", "带宽和存储压力大"]),
                 ("边缘式", ["本地聚合", "边缘先判断", "**只传结论与异常**"]),
                 labels=("现状", "改进后"))

    # 8 数据
    page = kit.content("示例数据：上报量降了一个数量级", section=2)
    top, bottom = page.area.rows([2, 5], 20)
    stats = [("12 万", "日均上报条数", "集中式 · 示例数据"), ("0.8 s", "平均响应", "边缘式 · 示例数据"), ("3 个", "试点站点", "仅用于版式演示")]
    for cell, (value, label, note) in zip(top.cols(3, 24), stats):
        page.stat(cell, value, label, note)
    page.chart(bottom, ["试点 A", "试点 B", "试点 C"],
               {"集中式（万条/日）": [12, 15, 11], "边缘式（万条/日）": [1.4, 1.6, 1.2]},
               title="示例数据：每日上报量（仅用于版式演示）")

    # 9 路线
    page = kit.content("路线：先试点，再扩展，最后平台化", section=2)
    top, bottom = page.area.rows([3, 2], 24)
    page.timeline(top, [
        ("Q1", "3 个站点试点，验证采集与上报"),
        ("Q2", "扩展到 30 个站点，补齐断网缓存"),
        ("Q3", "统一平台上线，接入告警与审计"),
        ("Q4", "开放接口，支持第三方设备接入"),
    ])
    page.card(bottom, "推进原则", ["每一阶段都保留回退路径", "试点数据不达标就不扩展", "平台化之前先统一设备台账"])

    # 10 风险
    page = kit.content("风险与应对：先把最坏情况写出来", section=2)
    risks = [
        ("现场网络不稳定", "本地缓存 7 天；恢复后按顺序补传"),
        ("传感器漂移", "周期校准；异常值单独标记，不直接告警"),
        ("告警疲劳", "分级阈值；同一设备 10 分钟内合并通知"),
    ]
    for index, (cell, (title, body)) in enumerate(zip(page.area.cols(3, 30), risks), 1):
        page.card(cell, title, body, number=index)

    # 11 结尾
    kit.closing("先让一台设备可靠，\n再让一千台设备协同。",
                points=["所有项目名、数字与场景均为虚构", "所有文字、形状、图表可在 PowerPoint 中编辑", "示例数据只用于展示版式，不代表真实项目"],
                contact="示例联系方式：name@example.com")
    return kit


if __name__ == "__main__":
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    for palette, surface in (("journal", "light"), ("journal", "dark"), ("ink", "light"), ("ink", "dark")):
        target = out / f"demo-{palette}-{surface}.pptx"
        build(palette, surface).save(target)
        for path in render(target, out / "preview", width=1280):
            Image.open(path).convert("RGB").save(path.with_suffix(".jpg"), quality=86)
            path.unlink()
            print(path.with_suffix(".jpg"))
