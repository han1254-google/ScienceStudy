"""
测试 ChatGPT / OpenAI 模型调用
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
)


def test_chat(prompt: str):
    print(f"\n{'='*60}")
    print(f"模型: {os.getenv('OPENAI_MODEL', 'gpt-4o')}")
    print(f"提示: {prompt}")
    print("=" * 60)

    # 非流式
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        messages=[{"role": "user", "content": prompt}],
    )
    print(f"\n【回复】\n{response.choices[0].message.content}")


def test_stream(prompt: str):
    print(f"\n{'='*60}")
    print("流式输出测试")
    print("=" * 60)

    stream = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )

    print("\n【流式回复】")
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end='', flush=True)
    print()


if __name__ == "__main__":
    test_chat("用一句话介绍你自己")
    test_stream("用Python写一个快速排序")
