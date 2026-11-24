"""把 PPTX 渲染成逐页 PNG，供肉眼检查。

用法:
    python render_pptx.py <输入.pptx> <输出目录> [--width 1600]

依赖本机的 LibreOffice（soffice）与 poppler（pdftoppm）。
注意：这是 LibreOffice 的渲染结果，发光、渐变、字体与 PowerPoint / WPS 会有细微差异，
最终观感仍要在目标软件里人工确认。
"""
import argparse
import pathlib
import shutil
import subprocess
import tempfile


def render(pptx_path, out_dir, width=1600):
    pptx_path, out_dir = pathlib.Path(pptx_path).resolve(), pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp) / "deck.pptx"  # 用纯英文文件名，避开 soffice 对特殊字符路径的问题
        shutil.copy(pptx_path, work)
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", tmp, str(work)],
                       check=True, capture_output=True, timeout=600)
        subprocess.run(["pdftoppm", "-png", "-scale-to-x", str(width), "-scale-to-y", "-1",
                        str(pathlib.Path(tmp) / "deck.pdf"), str(pathlib.Path(tmp) / "page")], check=True)
        pages = sorted(pathlib.Path(tmp).glob("page-*.png"))
        results = []
        for index, page in enumerate(pages, 1):
            target = out_dir / f"{pptx_path.stem}-{index:02d}.png"
            shutil.move(page, target)
            results.append(target)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pptx")
    parser.add_argument("out_dir")
    parser.add_argument("--width", type=int, default=1600)
    args = parser.parse_args()
    for path in render(args.pptx, args.out_dir, args.width):
        print(path)
