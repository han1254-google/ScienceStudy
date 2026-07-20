"""
全局配置 — 从 .env 文件加载，不硬编码 API Key
"""
import os
from pathlib import Path

# 加载 .env（项目根目录）
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

# Embedding（千问）
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_EMBED_MODEL = os.getenv("QWEN_EMBED_MODEL", "text-embedding-v4")

# LLM — 根据 LLM_PROVIDER 选择
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")  # deepseek / openai

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# 根据 provider 选择当前 LLM 配置
if LLM_PROVIDER == "openai":
    LLM_API_KEY = OPENAI_API_KEY or DEEPSEEK_API_KEY
    LLM_BASE_URL = OPENAI_BASE_URL
    LLM_MODEL = OPENAI_MODEL
else:
    LLM_API_KEY = DEEPSEEK_API_KEY
    LLM_BASE_URL = DEEPSEEK_BASE_URL
    LLM_MODEL = DEEPSEEK_MODEL
