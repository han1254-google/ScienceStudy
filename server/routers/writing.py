"""
AI 写作相关 API 路由
"""
from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()


@router.post("/generate")
async def generate_text(
    section: str = Query(..., description="写作章节: background/objectives/methods/introduction/results/discussion"),
    context: str = Query("", description="上下文/已有内容"),
    language: str = Query("zh", description="语言: zh/en"),
):
    """
    AI 生成文本 — 根据上下文生成标书/论文章节
    TODO: 接入 LLM API
    """
    return {
        "section": section,
        "generated_text": "",
        "message": f"AI 生成 {section} 功能将通过 LLM API 实现",
    }


@router.post("/polish")
async def polish_text(
    text: str = Query(..., description="待润色的文本"),
    target: str = Query("polish", description="操作: polish/translate-zh2en/translate-en2zh/expand/shorten"),
):
    """
    AI 润色/翻译
    """
    return {
        "original_length": len(text),
        "polished_text": "",
        "message": f"AI {target} 功能将通过 LLM API 实现",
    }


@router.post("/generate-abstract")
async def generate_abstract(
    background: str = Query(""),
    methods: str = Query(""),
    results: str = Query(""),
    conclusions: str = Query(""),
    language: str = Query("en", description="语言: zh/en"),
):
    """
    根据各部分内容生成结构化摘要
    """
    return {
        "abstract": "",
        "message": "摘要生成功能将通过 LLM API 实现",
    }


@router.post("/generate-figure-legend")
async def generate_figure_legend(
    figure_data: dict = None,
):
    """
    根据图表数据生成 Figure Legend
    """
    return {
        "legend": "",
        "message": "图注生成功能将通过 LLM API 实现",
    }
