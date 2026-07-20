"""
测试千问 (Qwen) 模型调用
"""
import os
from openai import OpenAI

# API Key
API_KEY = "sk-ws-H.EHMYYLX.1KVB.MEUCIQDLLOse1XySwWKSBrqN6RLjduY21HqDLamcqo_KExWM6wIgLl4-j33RwaXmAyk6f2-KEX2GxUTJyRJDJZmv1m1_9NM"
BASE_URL = "https://dashscope.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1"
MODEL = "qwen3.7-plus"

# 设置环境变量
os.environ["DASHSCOPE_API_KEY"] = API_KEY


def test_simple_question():
    """测试简单问答"""
    print("=" * 50)
    print("测试 1: 简单问答")
    print("=" * 50)

    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url=BASE_URL,
    )

    response = client.responses.create(
        model=MODEL,
        input="9.9和9.11哪个大？",
        extra_body={
            "enable_thinking": True  # 启用思考模式
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


def test_with_custom_prompt(prompt: str):
    """测试自定义提示词"""
    print("=" * 50)
    print(f"测试: {prompt[:50]}...")
    print("=" * 50)

    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url=BASE_URL,
    )

    response = client.responses.create(
        model=MODEL,
        input=prompt,
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


def test_streaming():
    """测试流式输出"""
    print("=" * 50)
    print("测试: 流式输出")
    print("=" * 50)

    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url=BASE_URL,
    )

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "请用Python写一个快速排序算法"}
        ],
        stream=True,
        stream_options={"include_usage": True}
    )

    reasoning_content = ""
    answer_content = ""
    is_answering = False

    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        # 处理思考过程
        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
            reasoning_content += delta.reasoning_content
        # 处理正式回复
        if delta.content:
            if not is_answering:
                if reasoning_content:
                    print("【推理过程】")
                    print(reasoning_content[:500])
                    print()
                print("【最终答案】")
                is_answering = True
            print(delta.content, end="", flush=True)

    if answer_content:
        print()
    print("\n")


if __name__ == "__main__":
    print("开始测试千问模型调用...\n")

    try:
        # 测试 1: 简单问答
        test_simple_question()
    except Exception as e:
        print(f"测试 1 失败: {e}\n")

    try:
        # 测试 2: 自定义提示词
        test_with_custom_prompt("请介绍一下机器学习的基本分类")
    except Exception as e:
        print(f"测试 2 失败: {e}\n")

    try:
        # 测试 3: 流式输出
        test_streaming()
    except Exception as e:
        print(f"测试 3 失败: {e}\n")

    print("所有测试完成!")
