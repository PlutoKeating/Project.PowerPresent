# PowerPresent

面向 Agent 的演示文稿构建 skill：一套设计系统、文案与叙事指南、可复用组件库、标准工作流，以及可直接编辑的 PPTX 输出。

适用于工科学术会议与研究汇报、答辩、产品发布与技术路演、科技企业介绍。

## 安装

### 用安装脚本

在解压后的 skill 目录或本仓库的 `skills/powerpresent/` 下执行：

```bash
# Claude Code：安装到 ~/.claude/skills/powerpresent
./install.sh --claude

# OpenCode：安装到 ~/.config/opencode/skills/powerpresent
./install.sh --opencode

# 安装到某个项目的 skills/ 下：<project>/skills/powerpresent
./install.sh --project /path/to/project

# 安装到任意 skills 目录：<dir>/powerpresent
./install.sh /path/to/skills
```

目标已存在时脚本会拒绝覆盖；确认要覆盖时加 `FORCE=1`：

```bash
FORCE=1 ./install.sh --claude
```

### 手动复制

把整个 `powerpresent/` 目录复制到目标 Agent 的 skills 目录即可。`SKILL.md` 是 Agent 的入口，`references/`、`scripts/`、`assets/` 必须一起复制。

## 依赖

在 skill 目录下安装：

```bash
python -m pip install -r requirements.txt
```

- Python 3.11+
- `python-pptx`、`Pillow`：生成与加工 PPTX / 底图
- `google-genai`（可选）：只有调用 `scripts/generate_image.py` 生成图片时需要，另需 `gcloud` 已登录并设置默认项目
- LibreOffice（`soffice`）与 poppler（`pdftoppm`）：把 PPTX 渲染成逐页预览，供自检
- 目标机器需要 Times New Roman、宋体、黑体；缺失时 PowerPoint / WPS 会做字体替换

## 快速开始

1. 让 Agent 先读 `SKILL.md`，再提供材料、听众、时长和使用场景。
2. 工作流会先定配色（`journal` 学术 / `ink` 商业）、底色（`light` / `dark`）、密度（`read` / `talk`）、底图，再写主旨句与标题提纲。
3. 每份稿子一个目录：`build.py`、`assets/`、`out/`。
4. 构建后逐页看 `out/preview/`；最终必须在 Microsoft PowerPoint 或 WPS 中人工确认，LibreOffice 预览只用于自检。

最小骨架见 `SKILL.md` 第 4 步。

## 目录

```text
SKILL.md                  Agent 入口：七步工作流与不可违反的规则
references/               设计系统、文案、叙事、组件使用手册
scripts/powerpresent/     绘制库与组件库
scripts/render_pptx.py    渲染逐页预览
scripts/make_backdrop.py  加工底图；拉丝配方见 design-system.md 第 9 节
scripts/generate_image.py 可选的图像生成脚本
assets/backdrops/         六种底图，各含两套配色、两种底色、内容页与封面页强度
VERSION                   当前版本
CHANGELOG.md              版本变更
LICENSE                   双许可证说明：代码 MIT，内容 CC BY-NC 4.0
LICENSE-CC-BY-NC-4.0.txt  CC BY-NC 4.0 完整法律条款
```

## 版本

当前版本见 `VERSION`，变更见 `CHANGELOG.md`。

## 许可

代码按 **MIT** 授权；文档、指南、幻灯片与视觉素材按 **CC BY-NC 4.0**（知识共享 署名—非商业性使用 4.0 国际）授权。完整条款见同目录 `LICENSE` 与 `LICENSE-CC-BY-NC-4.0.txt`。商业使用需另行取得授权。
