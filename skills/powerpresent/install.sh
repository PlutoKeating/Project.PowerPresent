#!/usr/bin/env sh
set -eu

NAME=powerpresent
SRC=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

usage() {
    cat <<'EOF'
用法:
  ./install.sh --claude                 安装到 ~/.claude/skills/powerpresent
  ./install.sh --opencode               安装到 ~/.config/opencode/skills/powerpresent
  ./install.sh --project <项目目录>      安装到 <项目目录>/skills/powerpresent
  ./install.sh <skills 目录>             安装到 <skills 目录>/powerpresent

环境变量:
  CLAUDE_SKILLS_DIR    覆盖 Claude 的 skills 目录
  OPENCODE_SKILLS_DIR  覆盖 OpenCode 的 skills 目录
  FORCE=1              覆盖已存在的安装
EOF
}

if [ "$#" -eq 0 ]; then
    usage
    exit 1
fi

case "$1" in
    -h|--help)
        usage
        exit 0
        ;;
    --claude)
        DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/$NAME"
        ;;
    --opencode)
        DEST="${OPENCODE_SKILLS_DIR:-$HOME/.config/opencode/skills}/$NAME"
        ;;
    --project)
        if [ "$#" -lt 2 ]; then
            echo "缺少项目目录。用法：./install.sh --project <项目目录>" >&2
            exit 1
        fi
        DEST="$2/skills/$NAME"
        ;;
    *)
        DEST="$1/$NAME"
        ;;
esac

mkdir -p "$(dirname "$DEST")"
DEST_DIR=$(CDPATH= cd -- "$(dirname "$DEST")" && pwd)
DEST="$DEST_DIR/$(basename "$DEST")"

case "$DEST" in
    "$SRC"|"$SRC"/*)
        echo "目标不能位于源目录内：$DEST" >&2
        exit 1
        ;;
esac

if [ -e "$DEST" ]; then
    if [ "${FORCE:-0}" != "1" ]; then
        echo "目标已存在：$DEST" >&2
        echo "确认覆盖请执行：FORCE=1 $0 $*" >&2
        exit 1
    fi
    rm -rf "$DEST"
fi

cp -R "$SRC/." "$DEST/"
find "$DEST" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find "$DEST" -name '.DS_Store' -delete 2>/dev/null || true
find "$DEST" -name '*.pyc' -delete 2>/dev/null || true

echo "已安装 PowerPresent 到：$DEST"
echo "下一步："
echo "  1. 安装依赖：python -m pip install -r \"$DEST/requirements.txt\""
echo "  2. 确认 LibreOffice（soffice）和 poppler（pdftoppm）可用"
echo "  3. 让 Agent 先读 \"$DEST/SKILL.md\"，再提供材料与场景"
