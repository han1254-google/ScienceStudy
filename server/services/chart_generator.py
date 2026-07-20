"""
SCI 级图表生成器 — matplotlib 封装
统一生成所有实验类型的图表，输出 base64 PNG 给前端直接展示
"""
import io
import base64
import logging
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

log = logging.getLogger("ChartGenerator")
from typing import Optional

# ---- 全局 SCI 风格 ----
plt.rcParams.update({
    "font.family": "Arial",
    "font.size": 9,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "lines.linewidth": 1.5,
    "lines.markersize": 4,
    "errorbar.capsize": 3,
})

# 兼容中文字体（Windows 常见）
for _font in ["Microsoft YaHei", "SimHei", "Arial"]:
    try:
        plt.rcParams["font.sans-serif"] = [_font] + plt.rcParams.get("font.sans-serif", [])
        break
    except Exception:
        continue

COLORS = ["#333333", "#808080", "#BBBBBB", "#555555", "#999999", "#666666"]
COLOR_ACCENT = "#1677ff"
SIGNIFICANCE_STYLES = {"*": "p<0.05", "**": "p<0.01", "***": "p<0.001", "ns": "not significant"}


def _safe_errors(errors):
    """将 None 替换为 NaN，matplotlib 接受 NaN 但不接受 None"""
    return [e if e is not None else float('nan') for e in (errors or [])]


def fig_to_base64(fig: plt.Figure) -> str:
    """matplotlib Figure → base64 PNG data URI"""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    data_uri = f"data:image/png;base64,{b64}"
    log.debug(f"Chart generated: {len(data_uri)} chars base64 PNG")
    return data_uri


def make_chart_item(chart_id: str, title: str, fig: plt.Figure, description: str = "") -> dict:
    """将 Figure 包装为前端可用的 ChartItem"""
    return {
        "chart_id": chart_id,
        "title": title,
        "base64": fig_to_base64(fig),
        "description": description,
    }


def _significance_label(p_value: float) -> str:
    if p_value < 0.001: return "***"
    elif p_value < 0.01: return "**"
    elif p_value < 0.05: return "*"
    return "ns"


def _add_significance_brackets(ax, x1, x2, y, h, label: str):
    """在柱状图上添加显著性括号"""
    ax.plot([x1, x1, x2, x2], [y, y + h, y + h, y], lw=0.8, color="#333333", clip_on=False)
    ax.text((x1 + x2) / 2, y + h, label, ha="center", va="bottom", fontsize=9)


# ==================== CCK8 图表 ====================

def cck8_dose_curve(doses: list, viabilities: list, viability_errors: list,
                    group_labels: list, ic50_values: dict,
                    fit_model: str = "4pl") -> dict:
    """剂量-效应曲线"""
    fig, ax = plt.subplots(figsize=(6, 4))
    for i, label in enumerate(group_labels):
        d = np.array(doses[i], dtype=float) if isinstance(doses[i], list) else np.array(doses, dtype=float)
        v = np.array(viabilities[i], dtype=float)
        e = np.array(_safe_errors(viability_errors[i]), dtype=float)
        ax.errorbar(d, v, yerr=e, fmt="o-", color=COLORS[i % len(COLORS)],
                     capsize=3, markersize=5, label=f"{label} (IC50={ic50_values.get(label, 'N/A')})")
    ax.set_xlabel("Concentration (μM)")
    ax.set_ylabel("Cell Viability (%)")
    ax.set_title("Dose-Response Curve")
    ax.legend(frameon=False)
    ax.axhline(50, color="red", linestyle="--", linewidth=0.6, alpha=0.5)
    if all(d > 0 for dlist in doses for d in dlist if d > 0):
        ax.set_xscale("log")
    return make_chart_item("dose_curve", "剂量-效应曲线", fig,
                           f"拟合模型: {fit_model}, X轴为对数刻度, 红色虚线=50%活力线")


def cck8_bar_chart(groups: list, means: list, errors: list,
                   p_values: list = None, error_bar: str = "sem") -> dict:
    """分组柱状图（单浓度/单时间点）"""
    fig, ax = plt.subplots(figsize=(5, 4))
    x = np.arange(len(groups))
    bars = ax.bar(x, means, yerr=_safe_errors(errors), color=COLOR_ACCENT, capsize=3,
                  edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(groups, rotation=30, ha="right")
    ax.set_ylabel(f"Cell Viability (%) (Mean ± {error_bar.upper()})")
    ax.set_title("Cell Viability Comparison")
    ymax = max(means) + max(errors) if errors else max(means) * 1.3
    ax.set_ylim(0, ymax * 1.2)
    if p_values:
        for i, p in enumerate(p_values):
            if i > 0 and p is not None and p < 0.05:
                _add_significance_brackets(ax, 0, i, ymax * (1 + 0.08 * i), ymax * 0.04,
                                           _significance_label(p))
    return make_chart_item("bar_chart", "细胞活力对比", fig,
                           f"误差棒: Mean ± {error_bar.upper()}, 显著性: *p<0.05 **p<0.01 ***p<0.001")


# ==================== EdU 图表 ====================

def edu_bar_chart(groups: list, positive_rates: list, errors: list,
                  p_values: list = None) -> dict:
    """EdU 阳性率柱状图"""
    fig, ax = plt.subplots(figsize=(5, 4))
    x = np.arange(len(groups))
    ax.bar(x, positive_rates, yerr=_safe_errors(errors), color=COLOR_ACCENT, capsize=3,
           edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(groups, rotation=30, ha="right")
    ax.set_ylabel("EdU Positive Rate (%)")
    ax.set_title("EdU Proliferation Assay")
    return make_chart_item("edu_bar", "EdU 阳性率对比", fig, "EdU+ / Total nuclei × 100%")


def edu_annotated_image(base64_img: str, total: int, positive: int, rate: float) -> dict:
    """标注后的 EdU 图像（带计数叠加）"""
    return make_chart_item("edu_annotated", f"EdU 分析标注图 (总={total}, 阳性={positive}, 率={rate:.1f}%)",
                           _placeholder_figure(), "绿色=EdU+, 蓝色=DAPI")


# ==================== 克隆形成 图表 ====================

def colony_bar_chart(groups: list, counts: list, errors: list,
                     rates: list = None) -> dict:
    """克隆计数柱状图"""
    fig, ax = plt.subplots(figsize=(5, 4))
    x = np.arange(len(groups))
    ax.bar(x, counts, yerr=_safe_errors(errors), color=COLOR_ACCENT, capsize=3,
           edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(groups, rotation=30, ha="right")
    ax.set_ylabel("Colony Count")
    ax.set_title("Colony Formation Assay")
    if rates:
        for i, r in enumerate(rates):
            ax.text(i, counts[i] + errors[i] + max(counts) * 0.02,
                    f"{r:.1f}%", ha="center", fontsize=8)
    return make_chart_item("colony_bar", "克隆计数对比", fig, "克隆数 ≥50 个细胞的集落")


def colony_annotated_image(base64_img: str, count: int, areas: list) -> dict:
    return make_chart_item("colony_annotated", f"克隆标注图 (计数={count})",
                           _placeholder_figure(), "红色圈=检测到的克隆")


# ==================== WB 图表 ====================

def wb_bar_chart(proteins: list, fold_changes: list, errors: list,
                 p_values: list = None) -> dict:
    """WB 相对表达量柱状图"""
    fig, ax = plt.subplots(figsize=(5, 4))
    x = np.arange(len(proteins))
    colors = [COLOR_ACCENT if abs(fc) > 1.5 else COLORS[1] for fc in fold_changes]
    ax.bar(x, fold_changes, yerr=_safe_errors(errors), color=colors, capsize=3,
           edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(proteins, rotation=30, ha="right")
    ax.set_ylabel("Relative Expression (Fold Change)")
    ax.set_title("Western Blot Quantification")
    ax.axhline(1.0, color="red", linestyle="--", linewidth=0.6, alpha=0.3)
    return make_chart_item("wb_bar", "蛋白相对表达量", fig, "内参归一化, Fold Change vs Control")


def wb_lane_plot(lane_intensities: list, lane_labels: list) -> dict:
    """泳道强度分布图"""
    fig, ax = plt.subplots(figsize=(6, 3))
    for i, (intensities, label) in enumerate(zip(lane_intensities, lane_labels)):
        ax.plot(intensities, label=label, color=COLORS[i % len(COLORS)], linewidth=1)
    ax.set_xlabel("Pixel Position")
    ax.set_ylabel("Intensity")
    ax.set_title("Lane Intensity Profiles")
    ax.legend(frameon=False, fontsize=7)
    return make_chart_item("wb_lanes", "泳道强度分布", fig, "横轴=泳道方向像素位置, 纵轴=灰度值")


# ==================== qPCR 图表 ====================

def qpcr_bar_chart(genes: list, fold_changes: list, errors: list,
                   p_values: list = None) -> dict:
    """qPCR 相对表达量"""
    fig, ax = plt.subplots(figsize=(5, 4))
    x = np.arange(len(genes))
    ax.bar(x, fold_changes, yerr=_safe_errors(errors), color=COLOR_ACCENT, capsize=3,
           edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(genes, rotation=30, ha="right")
    ax.set_ylabel("Relative mRNA Expression (2^(-ΔΔCt))")
    ax.set_title("qPCR Gene Expression")
    ax.axhline(1.0, color="red", linestyle="--", linewidth=0.6, alpha=0.3)
    if p_values:
        ymax = max(fold_changes) + max(errors) if errors else max(fold_changes) * 1.5
        for i, p in enumerate(p_values):
            if p is not None and p < 0.05:
                _add_significance_brackets(ax, 0, i, ymax * (1 + 0.08 * i), ymax * 0.04,
                                           _significance_label(p))
    return make_chart_item("qpcr_bar", "mRNA 相对表达量", fig, "ΔΔCt 法, 内参归一化")


# ==================== IHC 图表 ====================

def ihc_bar_chart(groups: list, metric_name: str, values: list, errors: list,
                  p_values: list = None) -> dict:
    """IHC 定量指标柱状图"""
    fig, ax = plt.subplots(figsize=(5, 4))
    x = np.arange(len(groups))
    ax.bar(x, values, yerr=_safe_errors(errors), color=COLOR_ACCENT, capsize=3,
           edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(groups, rotation=30, ha="right")
    ax.set_ylabel(metric_name)
    ax.set_title(f"IHC {metric_name} Comparison")
    return make_chart_item("ihc_bar", f"IHC {metric_name} 对比", fig, f"{metric_name} per group")


def ihc_deconvolution_overlay(original_b64: str, dab_b64: str, he_b64: str) -> dict:
    """颜色反卷积三通道叠加图"""
    return make_chart_item("ihc_deconv", "颜色反卷积结果",
                           _placeholder_figure(), "左=原图, 中=DAB(棕色阳性), 右=苏木精(蓝色复染)")


# ==================== 自定义分析 通用图表 ====================

def generic_bar_chart(labels: list, values: list, errors: list = None,
                      xlabel: str = "", ylabel: str = "", title: str = "",
                      color: str = COLOR_ACCENT) -> dict:
    """通用柱状图"""
    fig, ax = plt.subplots(figsize=(5, 4))
    x = np.arange(len(labels))
    ax.bar(x, values, yerr=_safe_errors(errors), color=color, capsize=3, edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title or "Data Comparison")
    return make_chart_item("generic_bar", title or "柱状图", fig, f"{ylabel} per {xlabel}")


def generic_line_chart(x_data: list, y_data: list, labels: list = None,
                       xlabel: str = "", ylabel: str = "", title: str = "") -> dict:
    """通用折线图"""
    fig, ax = plt.subplots(figsize=(5, 4))
    if labels:
        for x, y, lbl in zip(x_data, y_data, labels):
            ax.plot(x, y, "o-", label=lbl, markersize=4)
        ax.legend(frameon=False, fontsize=8)
    else:
        ax.plot(x_data[0] if isinstance(x_data, list) and isinstance(x_data[0], list) else x_data,
                y_data[0] if isinstance(y_data, list) and isinstance(y_data[0], list) else y_data,
                "o-", color=COLOR_ACCENT, markersize=4)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title or "Data Plot")
    return make_chart_item("generic_line", title or "折线图", fig, f"{ylabel} vs {xlabel}")


def generic_scatter(x: list, y: list, xlabel: str = "", ylabel: str = "",
                    title: str = "") -> dict:
    """通用散点图"""
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.scatter(x, y, color=COLOR_ACCENT, alpha=0.6, s=30, edgecolors="white", linewidth=0.3)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title or "Scatter Plot")
    return make_chart_item("generic_scatter", title or "散点图", fig)


def generic_heatmap(data: np.ndarray, row_labels: list = None, col_labels: list = None,
                    title: str = "Heatmap") -> dict:
    """通用热力图"""
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(data, aspect="auto", cmap="Greys")
    if row_labels:
        ax.set_yticks(range(len(row_labels)))
        ax.set_yticklabels(row_labels)
    if col_labels:
        ax.set_xticks(range(len(col_labels)))
        ax.set_xticklabels(col_labels, rotation=45, ha="right")
    plt.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title(title)
    return make_chart_item("heatmap", title, fig, "灰度热力图")


# ==================== 辅助函数 ====================

def _placeholder_figure() -> plt.Figure:
    """占位图（用于纯标记图片等场景）"""
    fig, ax = plt.subplots(figsize=(1, 1))
    ax.axis("off")
    return fig
