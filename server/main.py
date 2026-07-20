"""
科研智能助手 — 后端服务
FastAPI 入口，涵盖文献检索、图像分析、AI 写作、图表导出等 API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import literature, image_analysis, writing, export

app = FastAPI(
    title="科研智能助手 API",
    description="ScienceStudy — AI-assisted scientific research platform",
    version="0.1.0",
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
