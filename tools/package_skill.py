#!/usr/bin/env python3
"""构建 PowerPresent 发布包。

产物（dist/，不入库）：
  powerpresent-skill-v<版本>.zip   只含 skill 本体，可直接安装到其他项目
  powerpresent-demo-v<版本>.zip    skill + 可运行的示例，用于展示与回归
  SHA256SUMS                       两个 zip 的校验和

用法:
    python tools/package_skill.py
"""
import hashlib
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/powerpresent"
EXAMPLES = ROOT / "examples"
DIST = ROOT / "dist"

IGNORED_DIRS = {"__pycache__", ".pytest_cache"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
IGNORED_NAMES = {".DS_Store"}


def read_version():
    version = (SKILL / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit(f"VERSION 格式不对：{version!r}")
    return version


def iter_files(root):
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        relative = path.relative_to(root)
        if any(part in IGNORED_DIRS for part in relative.parts):
            continue
        if path.suffix in IGNORED_SUFFIXES or path.name in IGNORED_NAMES:
            continue
        yield path


def add_tree(archive, root, prefix):
    for path in iter_files(root):
        arcname = (Path(prefix) / path.relative_to(root)).as_posix()
        archive.write(path, arcname)


def check_skill():
    required = [
        "SKILL.md",
        "README.md",
        "VERSION",
        "CHANGELOG.md",
        "LICENSE",
        "LICENSE-CC-BY-NC-4.0.txt",
        "requirements.txt",
        "install.sh",
        "references/design-system.md",
        "references/copywriting.md",
        "references/narrative.md",
        "references/components.md",
        "scripts/powerpresent/__init__.py",
        "scripts/render_pptx.py",
        "scripts/make_backdrop.py",
        "assets/backdrops/wafer/journal-light-cover.jpg",
    ]
    missing = [name for name in required if not (SKILL / name).exists()]
    if missing:
        raise SystemExit("skill 缺少文件：\n  " + "\n  ".join(missing))


def demo_readme(version):
    return f"""# PowerPresent {version} 示例包

这个包包含完整的 skill 和可运行示例，用于查看效果与回归验证。

- `skills/powerpresent/`：skill 本体，安装说明见其中的 `README.md`
- `examples/demo/`：完全虚构的《云杉计划》示例（4 份模板 × 11 页）

## 运行

```bash
python -m pip install -r skills/powerpresent/requirements.txt

python examples/demo/build.py
```

另需 LibreOffice（`soffice`）和 poppler（`pdftoppm`）才能生成预览。预览只用于自检，
最终观感请在 Microsoft PowerPoint 或 WPS 中确认。

## 只装 skill

如果只需要 skill，用同目录下的 `powerpresent-skill-v{version}.zip`，它不含示例。
"""


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    check_skill()
    version = read_version()
    DIST.mkdir(exist_ok=True)
    for old in DIST.glob(f"powerpresent-*-v{version}.zip"):
        old.unlink()

    skill_zip = DIST / f"powerpresent-skill-v{version}.zip"
    with zipfile.ZipFile(skill_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        add_tree(archive, SKILL, "powerpresent")

    demo_zip = DIST / f"powerpresent-demo-v{version}.zip"
    demo_root = f"powerpresent-demo-v{version}"
    with zipfile.ZipFile(demo_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        add_tree(archive, SKILL, f"{demo_root}/skills/powerpresent")
        add_tree(archive, EXAMPLES, f"{demo_root}/examples")
        archive.writestr(f"{demo_root}/README.md", demo_readme(version))

    checksums = DIST / "SHA256SUMS"
    checksums.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in (skill_zip, demo_zip)),
        encoding="utf-8",
    )

    for path in (skill_zip, demo_zip, checksums):
        print(f"{path.relative_to(ROOT)}  {path.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
