"""
Module 2: 图像分析 API 路由
├── 2.1 模板数据分析 (6 类实验): /experiments/{type}/analyze
├── 2.2 自定义数据分析: /custom/generate-code, /custom/execute-code
└── 2.3 AI 图像理解: /understand/image

日志: server/logs/app.log
"""
import os
import sys
import uuid
import time
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, List
from datetime import datetime

# ---- 文件 + 控制台日志配置 ----
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

_log_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

_root_logger = logging.getLogger()

# 文件 handler（同 literature.py 共享 app.log）
if not any(isinstance(h, RotatingFileHandler) for h in _root_logger.handlers):
    _fh = RotatingFileHandler(
        LOG_DIR / "app.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    _fh.setFormatter(_log_formatter)
    _root_logger.addHandler(_fh)

# 控制台 handler（避免重复添加）
if not any(isinstance(h, logging.StreamHandler) and hasattr(h, 'stream') and
           h.stream in (sys.stdout, sys.stderr) for h in _root_logger.handlers):
    _ch = logging.StreamHandler(sys.stdout)
    _ch.setFormatter(_log_formatter)
    _root_logger.addHandler(_ch)

_root_logger.setLevel(logging.INFO)

from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException
from pydantic import BaseModel

from services import cck8_service, edu_service, colony_service, wb_service, qpcr_service, ihc_service
from services.chart_generator import (
    make_chart_item, fig_to_base64, cck8_dose_curve, cck8_bar_chart,
    edu_bar_chart, colony_bar_chart, wb_bar_chart, wb_lane_plot,
    qpcr_bar_chart, ihc_bar_chart,
)
from services.code_executor import execute_code
from services.image_understanding import analyze_images as vision_analyze, _tif_to_png, get_image_info
from services.data_templates import get_template, list_templates

log = logging.getLogger("API.ImageAnalysis")
router = APIRouter()

TEMP_DIR = Path(__file__).parent.parent / "temp"
TEMP_DIR.mkdir(exist_ok=True)


# ============================================================
# 工具函数
# ============================================================

async def _save_upload(file: UploadFile, prefix: str = "") -> str:
    """保存上传文件到临时目录，返回文件路径"""
    ext = Path(file.filename).suffix if file.filename else ".tmp"
    name = f"{prefix}_{uuid.uuid4().hex[:8]}{ext}"
    path = TEMP_DIR / name
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    return str(path)


def _read_data_file(file_path: str):
    """读取 Excel/CSV/TXT 数据文件为 DataFrame"""
    import pandas as pd
    ext = Path(file_path).suffix.lower()
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(file_path)
    elif ext == ".csv":
        return pd.read_csv(file_path)
    elif ext == ".txt":
        return pd.read_csv(file_path, sep="\t")
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


async def _read_uploaded_images(files: list[UploadFile]) -> list[bytes]:
    """读取上传的图像文件为字节列表"""
    return [await file.read() for file in files]


def _cleanup(*paths: str):
    """清理临时文件"""
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except OSError:
            pass


# ============================================================
# 响应模型
# ============================================================

class ChartItem(BaseModel):
    chart_id: str
    title: str
    base64: str
    description: str = ""


class AnalysisResponse(BaseModel):
    success: bool = True
    experiment_type: str = ""
    data: dict = {}
    stats: dict = {}
    charts: list = []
    report: str = ""
    download_filename: str = ""


# ============================================================
# 模板查询
# ============================================================

@router.get("/templates")
async def get_templates():
    """获取所有实验类型的数据模板列表"""
    return {"templates": list_templates()}


@router.get("/templates/{experiment_type}")
async def get_experiment_template(experiment_type: str):
    """获取指定实验类型的数据模板详情"""
    try:
        return get_template(experiment_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================
# 2.1 模板数据分析 — CCK8
# ============================================================

@router.post("/experiments/cck8/analyze")
async def analyze_cck8(
    file: UploadFile = File(None, description="OD值数据 (.xlsx/.csv)"),
    fit_model: str = Form("4pl"),
    stat_method: str = Form("anova"),
    error_bar: str = Form("sem"),
):
    """CCK8 细胞增殖/毒性分析"""
    t0 = time.time()
    if not file:
        raise HTTPException(status_code=400, detail="请上传数据文件")
    path = ""
    try:
        path = await _save_upload(file, "cck8")
        df = _read_data_file(path)
        stats = cck8_service.analyze_cck8_data(df, fit_model, stat_method, error_bar)
        charts = []

        # 剂量-效应曲线
        if stats.get("has_dose_response") and stats.get("dose_response"):
            for dr in stats["dose_response"]:
                if dr["doses"] and len(dr["doses"]) >= 3:
                    chart = cck8_dose_curve(
                        [dr["doses"]], [dr["viabilities"]], [dr["errors"]],
                        [dr["group"]], stats.get("ic50", {}), fit_model,
                    )
                    charts.append(chart)

        # 柱状图
        groups = list(stats["group_stats"].keys())
        means = [stats["group_stats"][g]["viability"] for g in groups]
        errs = [stats["group_stats"][g]["od_std"] / max(stats["group_stats"][g]["od_mean"], 0.001) * stats["group_stats"][groups[0]]["viability"] for g in groups]
        p_vals = None
        if stats.get("statistics", {}).get("comparisons"):
            p_vals = [1.0]
            for comp in stats["statistics"]["comparisons"]:
                p_vals.append(comp.get("p_value", 1.0))

        chart = cck8_bar_chart(groups, means, errs, p_vals, error_bar)
        charts.append(chart)

        # 报告
        ic50_str = ", ".join(f"{k}={v}" for k, v in stats.get("ic50", {}).items()) or "N/A"
        report = f"""## CCK8 分析报告

**拟合模型**: {fit_model} | **统计方法**: {stat_method} | **误差棒**: {error_bar.upper()}

### 细胞活力
{chr(10).join(f"- **{g}**: {s['viability']:.1f}% (n={s['n']})" for g, s in stats['group_stats'].items())}

### IC50
{ic50_str}

### 统计结果
- 方法: {stats.get('statistics', {}).get('method', 'N/A')}
- p值: {stats.get('statistics', {}).get('p_value', 'N/A')}
"""

        log.info(f"[CCK8] done: {len(df)} rows ({time.time()-t0:.1f}s)")
        return {
            "success": True, "experiment_type": "cck8",
            "data": {"rows": len(df), "groups": groups},
            "stats": stats, "charts": charts, "report": report,
            "download_filename": f"cck8_analysis_{datetime.now():%Y%m%d_%H%M%S}",
        }
    except Exception as e:
        log.error(f"[CCK8] fail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _cleanup(path)


# ============================================================
# 2.1 模板数据分析 — EdU
# ============================================================

@router.post("/experiments/edu/analyze")
async def analyze_edu(
    files: list[UploadFile] = File(..., description="EdU 荧光图像"),
    edu_channel: str = Form("green"),
    nuclear_dye: str = Form("dapi"),
    threshold: float = Form(30.0),
):
    """EdU 细胞增殖图像分析"""
    t0 = time.time()
    try:
        images = await _read_uploaded_images(files)
        result = edu_service.analyze_edu_images(images, edu_channel, nuclear_dye, threshold)

        charts = []
        # 标注图
        for i, pi in enumerate(result["per_image"]):
            if pi.get("annotated_b64"):
                charts.append({
                    "chart_id": f"edu_annotated_{i+1}",
                    "title": f"EdU 分析图 {i+1} (阳性率={pi.get('positive_rate',0):.1f}%)",
                    "base64": pi["annotated_b64"],
                    "description": f"总核={pi.get('total_nuclei',0)}, EdU+={pi.get('edu_positive',0)}",
                })

        # 汇总柱状图
        if len(result["per_image"]) > 1:
            import matplotlib.pyplot as plt
            import numpy as np
            labels = [f"FOV {i+1}" for i in range(len(result["per_image"]))]
            rates = [r.get("positive_rate", 0) for r in result["per_image"]]
            fig, ax = plt.subplots(figsize=(5, 4))
            ax.bar(labels, rates, color="#1677ff")
            ax.set_ylabel("EdU Positive Rate (%)")
            ax.set_title("EdU Proliferation Summary")
            charts.append(make_chart_item("edu_summary", "EdU 阳性率汇总", fig))

        report = f"""## EdU 分析报告

**总视野数**: {len(files)}
**总细胞核**: {result['summary']['total_nuclei_sum']}
**EdU+ 细胞**: {result['summary']['total_positive_sum']}
**总体阳性率**: {result['summary']['overall_positive_rate']:.1f}%
**平均阳性率**: {result['summary']['mean_positive_rate']:.1f}% ± {result['summary']['std_positive_rate']:.1f}%

### 各视野统计
{chr(10).join(f"- FOV {i+1}: {pi.get('total_nuclei',0)} 核, {pi.get('edu_positive',0)} EdU+ ({pi.get('positive_rate',0):.1f}%)" for i, pi in enumerate(result['per_image']))}
"""

        log.info(f"[EdU] done: {len(files)} images ({time.time()-t0:.1f}s)")
        return {
            "success": True, "experiment_type": "edu",
            "data": {"image_count": len(files)},
            "stats": result["summary"], "charts": charts, "report": report,
            "download_filename": f"edu_analysis_{datetime.now():%Y%m%d_%H%M%S}",
        }
    except Exception as e:
        log.error(f"[EdU] fail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 2.1 模板数据分析 — 克隆形成
# ============================================================

@router.post("/experiments/colony/analyze")
async def analyze_colony(
    files: list[UploadFile] = File(..., description="克隆形成图像"),
    min_area: int = Form(50),
    roi_mode: str = Form("auto"),
):
    """细胞克隆形成分析"""
    t0 = time.time()
    try:
        images = await _read_uploaded_images(files)
        result = colony_service.analyze_colony_images(images, min_area, roi_mode)

        charts = []
        for i, pi in enumerate(result["per_image"]):
            if pi.get("annotated_b64"):
                charts.append({
                    "chart_id": f"colony_annotated_{i+1}",
                    "title": f"克隆标注 {i+1} (计数={pi.get('count',0)})",
                    "base64": pi["annotated_b64"],
                    "description": f"面积={pi.get('image_size','?')}",
                })

        # 汇总柱状图
        import matplotlib.pyplot as plt
        labels = [f"Img {i+1}" for i in range(len(result["per_image"]))]
        counts = [r.get("count", 0) for r in result["per_image"]]
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.bar(labels, counts, color="#1677ff")
        ax.set_ylabel("Colony Count")
        ax.set_title("Colony Formation Summary")
        charts.append(make_chart_item("colony_summary", "克隆计数汇总", fig))

        report = f"""## 克隆形成分析报告

**图像数**: {len(files)}
**总克隆数**: {result['summary']['total_colonies']}
**平均每图**: {result['summary']['mean_count']} ± {result['summary']['std_count']}
**平均克隆面积**: {result['summary']['mean_area']} px²
**面积范围**: {result['summary']['area_range']}

### 各图像统计
{chr(10).join(f"- 图像 {i+1}: {pi.get('count',0)} 个克隆" for i, pi in enumerate(result['per_image']))}
"""

        log.info(f"[Colony] done: {len(files)} images ({time.time()-t0:.1f}s)")
        return {
            "success": True, "experiment_type": "colony",
            "data": {"image_count": len(files)},
            "stats": result["summary"], "charts": charts, "report": report,
            "download_filename": f"colony_analysis_{datetime.now():%Y%m%d_%H%M%S}",
        }
    except Exception as e:
        log.error(f"[Colony] fail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 2.1 模板数据分析 — WB
# ============================================================

@router.post("/experiments/wb/analyze")
async def analyze_wb(
    file: UploadFile = File(..., description="WB 条带图像"),
    lanes: int = Form(6),
    background: str = Form("rolling"),
    housekeeping: str = Form("gapdh"),
):
    """Western Blot 条带定量分析"""
    t0 = time.time()
    try:
        img_bytes = await file.read()
        result = wb_service.analyze_wb_image(img_bytes, lanes, background, housekeeping)

        charts = []
        if result.get("annotated_b64"):
            charts.append({
                "chart_id": "wb_annotated", "title": "WB 泳道/条带标注",
                "base64": result["annotated_b64"],
                "description": f"检测到 {result['lane_count']} 个泳道, {result['total_bands']} 个条带",
            })

        # 泳道强度图
        if result.get("lane_profiles"):
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(6, 3))
            for i, profile in enumerate(result["lane_profiles"]):
                ax.plot(profile, label=f"Lane {i+1}", linewidth=1)
            ax.set_xlabel("Pixel Position (vertical)")
            ax.set_ylabel("Intensity")
            ax.legend(fontsize=7, frameon=False)
            ax.set_title("Lane Intensity Profiles")
            charts.append(make_chart_item("wb_profiles", "泳道强度分布", fig))

        report = f"""## WB 定量分析报告

**泳道数**: {result['lane_count']}
**检测条带数**: {result['total_bands']}
**内参**: {housekeeping}

### 各泳道条带
"""
        for ld in result.get("lanes", []):
            report += f"\n**泳道 {ld['index']}**: {len(ld.get('bands', []))} 个条带\n"
            for b in ld.get("bands", []):
                report += f"  - 位置 y={b['position']}: 灰度值={b['intensity']:.0f}, 面积={b['area']:.0f}\n"

        log.info(f"[WB] done: {time.time()-t0:.1f}s")
        return {
            "success": True, "experiment_type": "wb",
            "data": {"lanes": result["lane_count"], "bands": result["total_bands"]},
            "stats": result, "charts": charts, "report": report,
            "download_filename": f"wb_analysis_{datetime.now():%Y%m%d_%H%M%S}",
        }
    except Exception as e:
        log.error(f"[WB] fail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 2.1 模板数据分析 — qPCR
# ============================================================

@router.post("/experiments/qpcr/analyze")
async def analyze_qpcr(
    file: UploadFile = File(None, description="Ct 值数据 (.xlsx/.csv/.txt)"),
    housekeeping_genes: str = Form("GAPDH"),
    control_group: str = Form("Control"),
    method: str = Form("ddct"),
):
    """qPCR 结果分析"""
    t0 = time.time()
    if not file:
        raise HTTPException(status_code=400, detail="请上传数据文件")
    path = ""
    try:
        path = await _save_upload(file, "qpcr")
        df = _read_data_file(path)
        hk_list = [g.strip() for g in housekeeping_genes.split(",")]
        stats = qpcr_service.analyze_qpcr_data(df, hk_list, control_group, method)

        charts = []
        gene_summary = stats.get("gene_summary", [])
        if gene_summary:
            import matplotlib.pyplot as plt
            import numpy as np
            genes = sorted(set(g["gene"] for g in gene_summary))
            groups = sorted(set(g["group"] for g in gene_summary))

            fig, ax = plt.subplots(figsize=(6, 4))
            x = np.arange(len(genes))
            width = 0.8 / len(groups)
            for gi, group in enumerate(groups):
                values = []
                errors = []
                for gene in genes:
                    matches = [g for g in gene_summary if g["gene"] == gene and g["group"] == group]
                    if matches:
                        values.append(matches[0]["mean_fold_change"])
                        errors.append(matches[0].get("sem", 0))
                    else:
                        values.append(0)
                        errors.append(0)
                ax.bar(x + gi * width, values, width, yerr=errors, label=group, capsize=2)
            ax.set_xticks(x + width * (len(groups) - 1) / 2)
            ax.set_xticklabels(genes, rotation=30, ha="right")
            ax.set_ylabel("Relative Expression (2^(-ΔΔCt))")
            ax.axhline(1.0, color="red", linestyle="--", linewidth=0.6, alpha=0.3)
            ax.legend(frameon=False, fontsize=8)
            ax.set_title("qPCR Gene Expression")
            charts.append(make_chart_item("qpcr_bar", "mRNA 相对表达量", fig,
                                          f"内参: {','.join(hk_list)}, 对照: {control_group}"))

        report = f"""## qPCR 分析报告

**内参基因**: {', '.join(hk_list)}
**对照组**: {control_group}
**计算方法**: {method}

### 基因表达汇总
{chr(10).join(f"- **{gs['gene']}** ({gs['group']}): {gs['mean_fold_change']:.3f} ± {gs.get('sem',0):.3f}" for gs in gene_summary)}
"""

        log.info(f"[qPCR] done: {len(df)} rows ({time.time()-t0:.1f}s)")
        return {
            "success": True, "experiment_type": "qpcr",
            "data": {"rows": len(df), "genes": len(set(g["gene"] for g in gene_summary))},
            "stats": stats, "charts": charts, "report": report,
            "download_filename": f"qpcr_analysis_{datetime.now():%Y%m%d_%H%M%S}",
        }
    except Exception as e:
        log.error(f"[qPCR] fail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _cleanup(path)


# ============================================================
# 2.1 模板数据分析 — IHC
# ============================================================

@router.post("/experiments/ihc/analyze")
async def analyze_ihc(
    files: list[UploadFile] = File(..., description="IHC 染色图像"),
    stain_type: str = Form("dab-he"),
    dab_threshold: float = Form(50.0),
):
    """IHC 免疫组化图像分析"""
    t0 = time.time()
    try:
        images = await _read_uploaded_images(files)
        result = ihc_service.analyze_ihc_images(images, stain_type, dab_threshold)

        charts = []
        for i, pi in enumerate(result["per_image"]):
            if pi.get("annotated_b64"):
                charts.append({
                    "chart_id": f"ihc_overlay_{i+1}",
                    "title": f"IHC 分析叠加图 {i+1} (H-Score={pi.get('hscore',0):.1f})",
                    "base64": pi["annotated_b64"],
                    "description": f"阳性面积={pi.get('positive_area_ratio',0):.1f}%, AOD={pi.get('aod',0):.4f}",
                })

        # 汇总柱状图
        import matplotlib.pyplot as plt
        labels = [f"Img {i+1}" for i in range(len(result["per_image"]))]
        hscores = [r.get("hscore", 0) for r in result["per_image"]]
        pa_ratios = [r.get("positive_area_ratio", 0) for r in result["per_image"]]
        fig, axes = plt.subplots(1, 2, figsize=(8, 4))
        axes[0].bar(labels, hscores, color="#1677ff")
        axes[0].set_ylabel("H-Score")
        axes[0].set_title("H-Score")
        axes[1].bar(labels, pa_ratios, color="#52c41a")
        axes[1].set_ylabel("Positive Area (%)")
        axes[1].set_title("Positive Area Ratio")
        plt.tight_layout()
        charts.append(make_chart_item("ihc_summary", "IHC 定量汇总", fig))

        report = f"""## IHC 分析报告

**染色方式**: {stain_type}
**图像数**: {len(files)}
**平均 H-Score**: {result['summary']['mean_hscore']:.1f}
**平均阳性面积比**: {result['summary']['mean_positive_area_ratio']:.1f}%
**平均 AOD**: {result['summary']['mean_aod']:.4f}

### 各图像统计
{chr(10).join(f"- 图像 {i+1}: H-Score={pi.get('hscore',0):.1f}, 阳性面积={pi.get('positive_area_ratio',0):.1f}%, AOD={pi.get('aod',0):.4f}" for i, pi in enumerate(result['per_image']))}
"""

        log.info(f"[IHC] done: {len(files)} images ({time.time()-t0:.1f}s)")
        return {
            "success": True, "experiment_type": "ihc",
            "data": {"image_count": len(files)},
            "stats": result["summary"], "charts": charts, "report": report,
            "download_filename": f"ihc_analysis_{datetime.now():%Y%m%d_%H%M%S}",
        }
    except Exception as e:
        log.error(f"[IHC] fail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 2.2 自定义数据分析
# ============================================================

class GenerateCodeRequest(BaseModel):
    data_preview: list = []
    data_description: str = ""
    user_prompt: str = ""
    data_file_id: str = ""


class ExecuteCodeRequest(BaseModel):
    code: str
    data_file_id: str = ""


@router.post("/custom/generate-code")
async def custom_generate_code(
    file: UploadFile = File(...),
    user_prompt: str = Form(""),
):
    """
    AI 读取上传数据，自动生成 Python 分析代码。
    返回生成的代码和解释供用户查看和编辑。
    """
    t0 = time.time()
    path = ""
    try:
        path = await _save_upload(file, "custom")
        df = _read_data_file(path)

        # 数据摘要
        preview = df.head(10).to_dict(orient="records")
        columns = list(df.columns)
        dtypes = {col: str(df[col].dtype) for col in columns}
        shape = df.shape
        describe = df.describe().to_dict() if len(df.select_dtypes(include=["number"]).columns) > 0 else {}

        # 构建 LLM 提示
        from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
        from openai import OpenAI

        prompt = f"""你是生物信息学数据分析专家。用户上传了一个数据文件，请生成 Python 代码来分析这些数据。

## 数据信息
- 文件名: {file.filename}
- 形状: {shape[0]} 行 × {shape[1]} 列
- 列名及类型: {dtypes}
- 前 10 行预览:
```json
{preview}
```
- 数值列统计:
```json
{describe}
```

## 用户要求
{user_prompt or '请对数据进行分析，包括描述性统计、数据可视化、组间比较（如有分组），生成适当的图表'}

## 重要
变量 `df` 已经包含了用户上传的真实数据（pandas DataFrame），可以直接使用，不需要 pd.read_excel()。
不要写"假设df存在"之类的注释，df 就是真实数据。

## 要求
1. 直接使用 df 进行分析，不需要再次读取文件
2. 使用 numpy, pandas, scipy.stats, matplotlib, seaborn 进行分析和绘图
3. 自动检测数据类型（数值/分类），选择合适的分析方法
4. 如果有分组列，进行组间统计比较
5. 生成至少 1-2 张有意义的图表（折线图、柱状图、散点图、热力图等）
6. 每张图表用独立的 plt.figure() 创建，最后用 plt.show() 显示
7. 代码要完整可执行，包含必要的 import
8. 注释用中文
9. 严格只输出 Python 代码，不要任何 markdown 标记或解释文字"""

        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=120.0)

        # 首次生成
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是生物信息学数据分析Python代码生成专家。请严格只输出可执行的Python代码，不要任何代码块标记或解释。代码必须完整，以 plt.show() 结尾。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3, max_tokens=16000,
        )

        code = resp.choices[0].message.content.strip()
        finish_reason = resp.choices[0].finish_reason
        log.info(f"[Custom-Gen] first response: {len(code)} chars, finish_reason={finish_reason}")

        # 如果被截断，自动续写
        if finish_reason == "length":
            log.warning("[Custom-Gen] code truncated by token limit, requesting continuation...")
            continue_resp = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": "你是Python代码生成专家。请从上次截断的地方继续输出，不要重复已经输出的内容，不要加任何解释。"},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": code},
                    {"role": "user", "content": "上面的代码被截断了，请从截断处继续输出剩余的Python代码。不要重复已有代码，直接从截断的语句开始续写完整。确保代码以 plt.show() 结尾。"},
                ],
                temperature=0.3, max_tokens=8000,
            )
            continuation = continue_resp.choices[0].message.content.strip()
            code += "\n" + continuation
            log.info(f"[Custom-Gen] continued: +{len(continuation)} chars, total={len(code)} chars")

        if code.startswith("```python"):
            code = code.split("\n", 1)[1]
        if code.startswith("```"):
            code = code.split("\n", 1)[1]
        if code.endswith("```"):
            code = code[:-3]
        code = code.strip()

        # 检测截断：括号不匹配 / 最后一行不完整
        truncated = False
        open_parens = code.count("(") - code.count(")")
        open_brackets = code.count("[") - code.count("]")
        open_braces = code.count("{") - code.count("}")
        last_line = code.split("\n")[-1].strip() if code else ""
        ends_abruptly = last_line and not last_line.endswith((".", ")", "]", "}", '"', "'", " "))
        if open_parens > 0 or open_brackets > 0 or open_braces > 0 or ends_abruptly:
            truncated = True
            log.warning(f"[Custom-Gen] code may be truncated: parens={open_parens}, brackets={open_brackets}, braces={open_braces}, last_line='{last_line[:60]}'")

        # 尝试语法检查
        try:
            compile(code, "<generated>", "exec")
        except SyntaxError as e:
            log.warning(f"[Custom-Gen] syntax error in generated code: {e}")
            truncated = True

        # 保存数据文件 ID 供后续执行
        data_file_id = str(path)

        log.info(f"[Custom-Gen] done: {len(code)} chars, truncated={truncated} ({time.time()-t0:.1f}s)")
        return {
            "success": True,
            "generated_code": code,
            "language": "python",
            "truncated": truncated,
            "explanation": (
                f"根据数据 ({shape[0]}行×{shape[1]}列) 生成的Python分析代码。"
                f"列: {', '.join(columns[:8])}{'...' if len(columns)>8 else ''}。"
                + ("⚠️ 代码可能不完整，请检查后手动补全。" if truncated else "代码将在服务器端执行，生成的图表将显示在页面上。")
            ),
            "data_file_id": data_file_id,
            "data_preview": preview,
            "columns": columns,
            "shape": list(shape),
        }
    except Exception as e:
        log.error(f"[Custom-Gen] fail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    # 注意：不清理文件，因为后续需要用于执行


@router.post("/custom/execute-code")
async def custom_execute_code(req: ExecuteCodeRequest):
    """
    执行用户/AI生成的 Python 代码（沙盒子进程）。
    返回 stdout/stderr 和生成的图表。
    """
    t0 = time.time()
    log.info(f"[Custom-Exec] executing code ({len(req.code)} chars)")
    try:
        data_path = req.data_file_id
        if data_path and not os.path.exists(data_path):
            data_path = ""

        result = execute_code(req.code, data_path, timeout=30)

        log.info(f"[Custom-Exec] done: success={result['success']}, charts={len(result['charts'])} ({time.time()-t0:.1f}s)")
        return result
    except Exception as e:
        log.error(f"[Custom-Exec] fail: {e}", exc_info=True)
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "charts": [],
            "error": str(e),
            "exit_code": -1,
        }


# ============================================================
# 2.3 AI 图像理解
# ============================================================

@router.post("/understand/image")
async def understand_image(
    file: UploadFile = File(..., description="待分析的图像 (.tif/.jpg/.png)"),
    prompt: str = Form("请详细分析这张科研图像"),
    description: str = Form(""),
    analysis_type: str = Form("general"),
):
    """
    AI 视觉图像分析。
    支持 TIF（自动转PNG）、JPG、PNG。调用 Vision LLM 进行图像理解。
    """
    t0 = time.time()
    try:
        img_bytes = await file.read()
        filename = file.filename or "image.png"

        # TIF → PNG 转换
        ext = filename.lower().split(".")[-1] if "." in filename else "png"
        if ext in ("tif", "tiff"):
            processed = _tif_to_png(img_bytes)
        else:
            processed = img_bytes

        # 图像信息
        try:
            from PIL import Image
            import io as io_mod
            pil_img = Image.open(io_mod.BytesIO(processed))
            img_info = {"width": pil_img.width, "height": pil_img.height,
                        "mode": pil_img.mode, "original_format": ext.upper()}
        except Exception:
            img_info = {"width": 0, "height": 0, "mode": "unknown", "original_format": ext.upper()}

        # 构建完整提示
        full_prompt = prompt
        if description:
            full_prompt = f"用户补充说明: {description}\n\n{prompt}"

        if analysis_type != "general":
            type_hints = {
                "microscopy": "这是一张显微镜图像。请关注染色类型、细胞/组织形态、放大倍数等。",
                "ihc": "这是免疫组化(IHC)染色图像。请关注阳性染色分布、强度、组织定位。",
                "wb": "这是Western Blot图像。请识别条带位置、分析条带形态和背景水平。",
            }
            full_prompt = type_hints.get(analysis_type, "") + "\n\n" + full_prompt

        # 调用视觉模型
        result = vision_analyze(
            images=[processed],
            prompt=full_prompt,
            filenames=[filename],
            analysis_type=analysis_type,
        )

        log.info(f"[Vision] done: model={result.get('model_used')}, chars={len(result.get('analysis',''))} ({time.time()-t0:.1f}s)")

        return {
            "success": result.get("success", True),
            "analysis": result.get("analysis", ""),
            "model_used": result.get("model_used", ""),
            "image_info": img_info,
            "filename": filename,
            "error": result.get("error", ""),
        }
    except Exception as e:
        log.error(f"[Vision] fail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 2.x 保留兼容旧端点
# ============================================================

@router.post("/cck8/analyze")
async def analyze_cck8_legacy(
    file: UploadFile = File(None),
    fit_model: str = Query("4pl"),
    stat_method: str = Query("anova"),
    error_bar: str = Query("sem"),
):
    """（兼容旧版）CCK8 分析 — 转发到新端点"""
    return await analyze_cck8(file=file, fit_model=fit_model, stat_method=stat_method, error_bar=error_bar)


@router.post("/edu/analyze")
async def analyze_edu_legacy(
    files: list[UploadFile] = File(...),
    edu_channel: str = Query("green"),
    nuclear_dye: str = Query("dapi"),
    threshold: float = Query(30.0),
):
    """（兼容旧版）EdU 分析"""
    return await analyze_edu(files=files, edu_channel=edu_channel, nuclear_dye=nuclear_dye, threshold=threshold)


@router.post("/colony/analyze")
async def analyze_colony_legacy(
    files: list[UploadFile] = File(...),
    min_area: int = Query(50),
    min_cells: int = Query(50),
    roi_mode: str = Query("auto"),
):
    """（兼容旧版）克隆形成分析"""
    return await analyze_colony(files=files, min_area=min_area, roi_mode=roi_mode)


@router.post("/wb/analyze")
async def analyze_wb_legacy(
    file: UploadFile = File(...),
    lanes: int = Query(6),
    background: str = Query("rolling"),
    housekeeping: str = Query("gapdh"),
    target_proteins: str = Query(""),
):
    """（兼容旧版）WB 定量分析"""
    return await analyze_wb(file=file, lanes=lanes, background=background, housekeeping=housekeeping)


@router.post("/qpcr/analyze")
async def analyze_qpcr_legacy(
    file: UploadFile = File(None),
    housekeeping_genes: str = Query("GAPDH"),
    control_group: str = Query("Control"),
    method: str = Query("ddct"),
):
    """（兼容旧版）qPCR 分析"""
    return await analyze_qpcr(file=file, housekeeping_genes=housekeeping_genes, control_group=control_group, method=method)


@router.post("/ihc/analyze")
async def analyze_ihc_legacy(
    files: list[UploadFile] = File(...),
    stain_type: str = Query("dab-he"),
    metrics: str = Query("positive,hscore"),
    dab_threshold: float = Query(50.0),
):
    """（兼容旧版）IHC 分析"""
    return await analyze_ihc(files=files, stain_type=stain_type, dab_threshold=dab_threshold)
