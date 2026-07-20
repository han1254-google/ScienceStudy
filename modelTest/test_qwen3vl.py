"""
测试 Qwen3-VL-Plus 视觉模型
"""
import sys
import io
from openai import OpenAI
import os

# 设置 stdout 为 UTF-8，解决 Windows GBK 编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

API_KEY = "sk-ws-H.EHMYYLX.1KVB.MEUCIQDLLOse1XySwWKSBrqN6RLjduY21HqDLamcqo_KExWM6wIgLl4-j33RwaXmAyk6f2-KEX2GxUTJyRJDJZmv1m1_9NM"
os.environ["DASHSCOPE_API_KEY"] = API_KEY

# 初始化OpenAI客户端
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

reasoning_content = ""  # 定义完整思考过程
answer_content = ""     # 定义完整回复
is_answering = False    # 判断是否结束思考过程并开始回复
enable_thinking = True

# 创建聊天完成请求
completion = client.chat.completions.create(
    model="qwen3-vl-plus",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://img.alicdn.com/imgextra/i1/O1CN01gDEY8M1W114Hi3XcN_!!6000000002727-0-tps-1024-406.jpg"
                    },
                },
                {"type": "text", "text": "这道题怎么解答？"},
            ],
        },
    ],
    stream=True,
    extra_body={
        'enable_thinking': True,
        "thinking_budget": 81920
    },
)

if enable_thinking:
    print("\n" + "=" * 20 + "思考过程" + "=" * 20 + "\n")

for chunk in completion:
    # 如果chunk.choices为空，则打印usage
    if not chunk.choices:
        print("\nUsage:")
        print(chunk.usage)
    else:
        delta = chunk.choices[0].delta
        # 打印思考过程
        if hasattr(delta, 'reasoning_content') and delta.reasoning_content is not None:
            print(delta.reasoning_content, end='', flush=True)
            reasoning_content += delta.reasoning_content
        else:
            # 开始回复
            if delta.content != "" and not is_answering:
                print("\n" + "=" * 20 + "完整回复" + "=" * 20 + "\n")
                is_answering = True
            # 打印回复过程
            print(delta.content, end='', flush=True)
            answer_content += delta.content

print("\n")
