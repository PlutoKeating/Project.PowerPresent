"""把手工拍摄的幻灯片照片做透视矫正，得到正视的 16:9 画面，供人工并排比对。

用法:
    python rectify_photo.py [--ref-width 1400] -- <照片> <输出.png> x1,y1 x2,y2 x3,y3 x4,y4

四个点依次是幻灯片画面的 左上、右上、右下、左下 角，坐标可以落在照片之外
（照片没拍全时，按版式推断出界外的角点）。--ref-width 表示这些坐标是在
多宽的缩略图上量的，脚本会自动换算到原图尺寸。角点可能是负数，所以位置参数前要加 "--"。
"""
import argparse

from PIL import Image, ImageOps

OUT_W, OUT_H = 1600, 900


def solve(matrix, vector):
    """高斯消元解线性方程组（规模只有 8x8，不值得为此引入 numpy）。"""
    n = len(vector)
    rows = [list(map(float, matrix[i])) + [float(vector[i])] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(rows[r][col]))
        rows[col], rows[pivot] = rows[pivot], rows[col]
        for r in range(n):
            if r != col:
                factor = rows[r][col] / rows[col][col]
                rows[r] = [a - factor * b for a, b in zip(rows[r], rows[col])]
    return [rows[i][n] / rows[i][i] for i in range(n)]


def perspective_coefficients(output_points, source_points):
    """求 Pillow PERSPECTIVE 变换需要的 8 个系数：输出坐标 -> 原图坐标。"""
    matrix, vector = [], []
    for (ox, oy), (sx, sy) in zip(output_points, source_points):
        matrix.append([ox, oy, 1, 0, 0, 0, -sx * ox, -sx * oy])
        matrix.append([0, 0, 0, ox, oy, 1, -sy * ox, -sy * oy])
        vector += [sx, sy]
    return solve(matrix, vector)


def rectify(photo_path, corners, ref_width=None):
    image = ImageOps.exif_transpose(Image.open(photo_path)).convert("RGB")
    scale = image.width / ref_width if ref_width else 1.0
    source = [(x * scale, y * scale) for x, y in corners]
    target = [(0, 0), (OUT_W, 0), (OUT_W, OUT_H), (0, OUT_H)]
    coefficients = perspective_coefficients(target, source)
    return image.transform((OUT_W, OUT_H), Image.Transform.PERSPECTIVE, coefficients,
                           Image.Resampling.BICUBIC, fillcolor=(40, 40, 40))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("photo")
    parser.add_argument("output")
    parser.add_argument("corners", nargs=4, help="x,y 形式的四个角点：左上 右上 右下 左下")
    parser.add_argument("--ref-width", type=float, default=None)
    args = parser.parse_args()
    points = [tuple(float(v) for v in c.split(",")) for c in args.corners]
    rectify(args.photo, points, args.ref_width).save(args.output)
