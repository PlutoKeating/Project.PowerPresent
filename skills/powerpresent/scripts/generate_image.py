"""调用 Vertex AI 上的 Gemini 图像模型生成背景图或插画素材。

用法:
    python generate_image.py "<提示词>" <输出.png> [--model 模型名] [--aspect 16:9] [--size 2K] [--ref 参考图 ...]

前提：本机 gcloud 已登录且设置了默认项目（或设置环境变量 GOOGLE_CLOUD_PROJECT）。
提示词会发送到外部服务，不要写入任何个人信息或未公开的项目内容。
"""
import argparse
import os
import pathlib
import subprocess

from google import genai
from google.genai import types

DEFAULT_MODEL = "gemini-nano-banana-2.1"


def _project() -> str:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        project = subprocess.run(["gcloud", "config", "get-value", "project"],
                                 capture_output=True, text=True, check=True).stdout.strip()
    os.environ.setdefault("GOOGLE_CLOUD_QUOTA_PROJECT", project)  # 本地凭据调用 Vertex 需要配额项目
    return project


def generate(prompt, output, model=DEFAULT_MODEL, aspect="16:9", size="2K", references=()):
    client = genai.Client(vertexai=True, project=_project(), location="global")
    contents = [types.Part.from_bytes(data=pathlib.Path(r).read_bytes(), mime_type="image/png") for r in references]
    contents.append(prompt)
    response = client.models.generate_content(
        model=model, contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio=aspect, image_size=size)))
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            pathlib.Path(output).parent.mkdir(parents=True, exist_ok=True)
            pathlib.Path(output).write_bytes(part.inline_data.data)
            return output
    raise RuntimeError(f"模型没有返回图片: {response}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("prompt")
    parser.add_argument("output")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--aspect", default="16:9")
    parser.add_argument("--size", default="2K")
    parser.add_argument("--ref", nargs="*", default=[])
    args = parser.parse_args()
    print(generate(args.prompt, args.output, args.model, args.aspect, args.size, args.ref))
