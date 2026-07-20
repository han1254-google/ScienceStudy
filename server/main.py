"""
科研智能助手 — 后端服务
FastAPI 入口，涵盖文献检索、图像分析、AI 写作、图表导出等 API
"""
import json
import math
import sys
import logging
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

# ---- 确保控制台日志（在 router 导入前设置，避免被 clear() 误删） ----
_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S"
))
_console_handler.setLevel(logging.DEBUG)
logging.getLogger().addHandler(_console_handler)
logging.getLogger().setLevel(logging.INFO)

from routers import literature, image_analysis, writing, export


def _sanitize_json(obj):
    """递归清洗 NaN/Inf/numpy 类型 → JSON 安全值"""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj): return None
        return obj
    if isinstance(obj, (np.floating,)):
        return None if np.isnan(obj) or np.isinf(obj) else float(obj)
    if isinstance(obj, (np.integer,)): return int(obj)
    if isinstance(obj, (np.bool_,)): return bool(obj)
    if isinstance(obj, np.ndarray): return _sanitize_json(obj.tolist())
    if isinstance(obj, dict):
        return {k: _sanitize_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_json(i) for i in obj]
    return obj


class SafeJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(_sanitize_json(content), ensure_ascii=False).encode("utf-8")


app = FastAPI(
    title="科研智能助手 API",
    description="ScienceStudy — AI-assisted scientific research platform",
    version="0.1.0",
    default_response_class=SafeJSONResponse,
)

# CORS 中间件（允许前端跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(literature.router, prefix="/api/literature", tags=["文献检索"])
app.include_router(image_analysis.router, prefix="/api/image-analysis", tags=["图像分析"])
app.include_router(writing.router, prefix="/api/writing", tags=["AI 写作"])
app.include_router(export.router, prefix="/api/export", tags=["导出"])


@app.get("/")
async def root():
    return {"message": "科研智能助手 API 服务运行中", "version": "0.1.0"}


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
