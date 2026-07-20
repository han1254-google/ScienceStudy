"""
使用千问 qwen3.7-plus 模型分析图片
"""
import os
import base64
from openai import OpenAI

API_KEY = "sk-ws-H.EHMYYLX.1KVB.MEUCIQDLLOse1XySwWKSBrqN6RLjduY21HqDLamcqo_KExWM6wIgLl4-j33RwaXmAyk6f2-KEX2GxUTJyRJDJZmv1m1_9NM"
BASE_URL = "https://dashscope.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1"
MODEL = "qwen3.7-plus"
os.environ["DASHSCOPE_API_KEY"] = API_KEY

IMAGE_PATH = os.path.join(os.path.dirname(__file__), "test_image.png")


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_image(image_path: str, prompt: str):
    print("=" * 60)
    print(f"模型: {MODEL}")
    print(f"图片: {image_path}")
    print(f"提示词: {prompt}")
    print("=" * 60)

    base64_image = encode_image(image_path)

    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url=BASE_URL,
    )

    # 使用 responses.create，传图片
    response = client.responses.create(
        model=MODEL,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{base64_image}"
                    },
                    {
                        "type": "input_text",
                        "text": prompt
                    }
                ]
            }
        ],
        extra_body={
            "enable_thinking": True
        }
    )

    for item in response.output:
        if item.type == "reasoning":
            print("【推理过程】")
            for summary in item.summary:
                print(summary.text[:500])
            print()
        elif item.type == "message":
            print("【最终答案】")
            print(item.content[0].text)

    print()
    return response


if __name__ == "__main__":
    prompts = [
        "请详细描述这张图片的内容，包括画面中的主要元素、颜色、布局等",
        "这张图片中如果有文字，请识别并提取文字内容",
        "请分析这张图片可能传达的主题、情感或意图",
    ]

    for i, prompt in enumerate(prompts, 1):
        print(f"\n--- 第 {i} 轮分析 ---")
        try:
            analyze_image(IMAGE_PATH, prompt)
        except Exception as e:
            print(f"分析失败: {e}")

    print("所有分析完成!")
