"""把一张灰度纹理图加工成各套配色、各种底色下的页面底图。

用法:
    python make_backdrop.py <灰度纹理.png> <母题名> [--gain 1.0] [--uniform] [--recipe default|brushed]

做法（依据见 references/design-system.md 第 9 节）：纹理不直接当底图用，而是
去色 -> 只取它相对于底色的明暗起伏 -> 按很低的比例叠到该配色的纸面色上 -> 内容页再用蒙版让它集中在右侧与边角 ->
最后加一层细颗粒。这样底图的颜色一定落在配色之内，对比度可控。

`--recipe brushed` 是拉丝金属的专用预处理：先中值去斑，再沿拉丝方向平滑、垂直粗化，
最后锐化线条。配合 `--gain 4.2` 生成当前使用的 `brushed` 底图。
每个母题输出 8 张图到 assets/backdrops/<母题名>/：<配色>-<底色>-<content|cover>.jpg
"""
import argparse
import pathlib
import sys

from PIL import Image, ImageChops, ImageFilter, ImageStat

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from powerpresent.color import oklch, to_oklch  # noqa: E402
from powerpresent.theme import PALETTES  # noqa: E402

SIZE = (1920, 1080)
OUT = pathlib.Path(__file__).resolve().parents[1] / "assets/backdrops"
# 纹理叠加的强度（向纹理色混合的最大比例）：内容页与封面页分别取值
STRENGTH = {("light", "content"): 0.16, ("light", "cover"): 0.30, ("dark", "content"): 0.10, ("dark", "cover"): 0.20}
GRAIN = {"light": 0.022, "dark": 0.016}


def _rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def _base(paper, dark):
    """页面的底色渐变：与主题里的背景一致（同色相、明度差很小的斜向渐变）。"""
    L, C, H = to_oklch(paper)
    other = oklch(L + (0.035 if dark else -0.04), C, H)
    ramp = Image.blend(Image.linear_gradient("L").rotate(90, expand=True).resize(SIZE), Image.linear_gradient("L").resize(SIZE), 0.5)
    return Image.composite(Image.new("RGB", SIZE, _rgb(other)), Image.new("RGB", SIZE, _rgb(paper)), ramp)


def _fade():
    """内容页的蒙版：左上与中部几乎没有纹理，向右侧和右下角逐渐显现，正文区保持干净。"""
    horizontal = Image.linear_gradient("L").rotate(90, expand=True).resize(SIZE)          # 左暗右亮
    vertical = Image.linear_gradient("L").resize(SIZE)                                    # 上暗下亮
    mask = ImageChops.add(horizontal.point(lambda v: max(0, v - 70) * 1.25), vertical.point(lambda v: max(0, v - 150) * 1.1))
    return mask.point(lambda v: min(255, int(v))).filter(ImageFilter.GaussianBlur(60))


def _smooth_along_lines(image, factor):
    """沿水平方向降采样再放大：抹掉短促的噪点，保留连续的横向拉丝。"""
    width, height = image.size
    return image.resize((max(1, width // factor), height), Image.Resampling.LANCZOS).resize(SIZE, Image.Resampling.LANCZOS)


def _coarsen_lines(image, factor):
    """垂直方向降采样再放大：把 1px 的细线合并成更粗的横向条纹。"""
    width, height = image.size
    return image.resize((width, max(1, height // factor)), Image.Resampling.LANCZOS).resize(SIZE, Image.Resampling.LANCZOS)


def _recipe(image, recipe):
    if recipe == "brushed":
        image = image.filter(ImageFilter.MedianFilter(5))
        image = _smooth_along_lines(image, 12)
        image = _coarsen_lines(image, 2)
        image = image.filter(ImageFilter.UnsharpMask(radius=1.0, percent=190, threshold=2))
    return image


def make(texture_path, name, gain=1.0, uniform=False, recipe="default"):
    texture = Image.open(texture_path).convert("L").resize(SIZE, Image.Resampling.LANCZOS)
    texture = _recipe(texture, recipe)
    median = ImageStat.Stat(texture).median[0]
    lighter = texture.point(lambda v: min(255, max(0, v - median) * 3.2 * gain))          # 比底色亮的部分：线条、亮面
    darker = texture.point(lambda v: min(255, max(0, median - v) * 3.2 * gain))           # 比底色暗的部分
    detail = ImageChops.lighter(lighter, darker)
    fade = _fade()
    target = OUT / name
    target.mkdir(parents=True, exist_ok=True)
    for palette, spec in PALETTES.items():
        for surface in ("light", "dark"):
            dark = surface == "dark"
            paper = spec[surface]["paper"]
            ink = spec["dark"]["primary"] if dark else spec["light"]["primary"]           # 纹理的颜色：该配色的主色
            for kind in ("content", "cover"):
                mask = detail if (kind == "cover" or uniform) else ImageChops.multiply(detail, fade)
                mask = mask.point(lambda v, k=STRENGTH[(surface, kind)]: int(v * k))
                image = Image.composite(Image.new("RGB", SIZE, _rgb(ink)), _base(paper, dark), mask)
                noise = Image.effect_noise(SIZE, 40).point(lambda v: min(255, max(0, (v - 128) * 2 + 128)))
                grain = Image.merge("RGB", (noise, noise, noise))
                image = Image.blend(image, ImageChops.overlay(image, grain), GRAIN[surface] * 8)
                image.save(target / f"{palette}-{surface}-{kind}.jpg", quality=84)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("texture")
    parser.add_argument("name")
    parser.add_argument("--gain", type=float, default=1.0)
    parser.add_argument("--uniform", action="store_true", help="内容页也整幅均匀铺开（只适合颗粒、纸纹这类没有图形的纹理）")
    parser.add_argument("--recipe", choices=("default", "brushed"), default="default", help="纹理预处理配方：brushed 为粗拉丝专用")
    args = parser.parse_args()
    print(make(args.texture, args.name, args.gain, args.uniform, args.recipe))
