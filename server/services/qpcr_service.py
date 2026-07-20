"""
qPCR 数据分析服务
- 解析多仪器格式 (Bio-Rad/ABI/Roche)
- ΔΔCt 计算 → 相对表达量 (2^(-ΔΔCt))
- 统计学检验
"""
import logging
import numpy as np
import pandas as pd
from scipy import stats

log = logging.getLogger("QPCR")


def _to_native(obj):
    """递归转换 numpy 类型为 Python 原生类型，处理 NaN/Inf"""
    import numpy as np
    if isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        if np.isnan(obj) or np.isinf(obj): return None
        return float(obj)
    elif isinstance(obj, (np.bool_,)):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, float) and (obj != obj or obj in (float('inf'), float('-inf'))):
        return None
    elif isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_to_native(i) for i in obj]
    return obj
from typing import Optional


def analyze_qpcr_data(
    df: pd.DataFrame,
    housekeeping_genes: list[str],
    control_group: str = "Control",
    method: str = "ddct",
) -> dict:
    """
    完整的 qPCR ΔΔCt 分析流程。

    期望列: ['sample', 'gene', 'ct_value']，可选: ['group', 'replicate']

    Returns:
        {
            "ct_table": [...],
            "delta_ct": [...],
            "mean_delta_ct": [...],
            "delta_delta_ct": [...],
            "fold_change": [...],
            "statistics": {...},
            "gene_summary": [...],
        }
    """
    # 自动检测列名
    log.info(f"Analyzing qPCR data: {len(df)} rows, columns={list(df.columns)}")
    df = _normalize_columns(df)
    log.info(f"Normalized columns: {list(df.columns)}, samples={df['sample'].nunique() if 'sample' in df.columns else '?'}")

    # 分组：按 sample + gene 取平均 Ct (处理技术重复)
    grouped = df.groupby(["sample", "gene"], as_index=False).agg(
        ct_mean=("ct_value", "mean"),
        ct_std=("ct_value", "std"),
        ct_count=("ct_value", "count"),
    )

    # 获取分组信息
    sample_groups = {}
    if "group" in df.columns:
        sample_groups = df.groupby("sample")["group"].first().to_dict()

    samples = sorted(grouped["sample"].unique())
    genes = sorted(g for g in grouped["gene"].unique() if g not in housekeeping_genes)

    # 取内参 Ct 均值 — 按 group 聚合（而非按 sample，因为 sample 包含基因名）
    hk_data = grouped[grouped["gene"].isin(housekeeping_genes)]

    # 构建 group -> replicate -> hk Ct 的映射
    # 更简单的方式：计算每个 sample 的内参均值（该 sample 中所有内参基因的平均 Ct）
    hk_means_by_sample = hk_data.groupby("sample")["ct_mean"].mean().to_dict()

    if not hk_means_by_sample:
        raise ValueError(f"未找到内参基因 {housekeeping_genes}。请检查数据中基因名称是否匹配。")

    # 构建 replicate_key -> hk_ct 的映射（用 group+replicate 作为通用键）
    # 从 hk samples 提取 group 和 replicate 以建立映射
    hk_by_group_rep = {}
    for hk_sample, hk_ct in hk_means_by_sample.items():
        # sample 格式: gene_group_replicate → 去掉 gene 得到 group_replicate
        group_name = sample_groups.get(hk_sample, "")
        rep = ""
        if "replicate" in df.columns:
            rep_info = df[df["sample"] == hk_sample]
            if len(rep_info) > 0:
                rep = str(rep_info["replicate"].iloc[0])
        key = f"{group_name}_{rep}"
        hk_by_group_rep[key] = hk_ct

    # 如果 hk_by_group_rep 为空，回退到按 group 聚合
    if not hk_by_group_rep:
        # 合并 df 获取 hk 数据的 group 信息
        hk_with_groups = hk_data.merge(df[["sample", "group"]].drop_duplicates(), on="sample", how="left")
        hk_means = hk_with_groups.groupby("group")["ct_mean"].mean().to_dict()
    else:
        # 提取 group-level 的内参均值
        hk_means = {}
        for key, ct in hk_by_group_rep.items():
            group = key.rsplit("_", 1)[0] if "_" in key else key
            hk_means.setdefault(group, []).append(ct)
        hk_means = {g: sum(cts) / len(cts) for g, cts in hk_means.items()}

    if not hk_means:
        raise ValueError(f"无法计算内参基因 {housekeeping_genes} 的 Ct 均值。")

    # 计算 ΔCt = Ct_target - Ct_housekeeping (按组匹配内参)
    delta_ct_records = []
    for _, row in grouped.iterrows():
        gene = row["gene"]
        sample = row["sample"]
        if gene in housekeeping_genes:
            continue
        group = sample_groups.get(sample, sample)
        hk = hk_means.get(group)
        if hk is None:
            continue
        delta_ct_records.append({
            "sample": sample,
            "gene": gene,
            "ct_target": round(row["ct_mean"], 3),
            "ct_housekeeping": round(hk, 3),
            "delta_ct": round(row["ct_mean"] - hk, 3),
            "group": sample_groups.get(sample, sample),
        })

    delta_ct_df = pd.DataFrame(delta_ct_records)

    # 对照组平均 ΔCt
    control_mask = delta_ct_df["group"].str.contains(control_group, case=False, na=False)
    if not control_mask.any():
        # 尝试精确匹配
        control_mask = delta_ct_df["group"] == control_group
    if not control_mask.any():
        # 使用第一个 group 作为对照
        control_mask = delta_ct_df["group"] == delta_ct_df["group"].iloc[0]

    control_mean_dct = delta_ct_df[control_mask].groupby("gene")["delta_ct"].mean().to_dict()

    # 计算 ΔΔCt 和 Fold Change
    results = []
    for _, row in delta_ct_df.iterrows():
        gene = row["gene"]
        mean_control_dct = control_mean_dct.get(gene, 0)
        ddct = row["delta_ct"] - mean_control_dct
        if method == "ddct":
            fc = 2 ** (-ddct)
        else:
            fc = np.power(2, -ddct)  # Pfaffl 简化（需扩增效率参数）
        results.append({
            **row,
            "delta_delta_ct": round(ddct, 3),
            "fold_change": round(fc, 3),
        })

    result_df = pd.DataFrame(results)

    # 按基因汇总统计
    gene_summary = []
    for gene in genes:
        gene_data = result_df[result_df["gene"] == gene]
        groups_in_data = gene_data["group"].unique()
        for g in groups_in_data:
            gd = gene_data[gene_data["group"] == g]
            gene_summary.append({
                "gene": gene,
                "group": g,
                "mean_fold_change": round(gd["fold_change"].mean(), 3),
                "sem": round(gd["fold_change"].sem(), 3) if len(gd) > 1 else 0,
                "n": len(gd),
            })

    # 统计检验 (vs Control)
    stats_results = {}
    control_data = result_df[control_mask]
    for gene in genes:
        ctrl_fc = control_data[control_data["gene"] == gene]["fold_change"].values
        gene_stats = []
        for g in result_df["group"].unique():
            if g == control_group or control_mask.iloc[0] is True and g == result_df.loc[control_mask, "group"].iloc[0]:
                continue
            exp_fc = result_df[(result_df["gene"] == gene) & (result_df["group"] == g)]["fold_change"].values
            if len(ctrl_fc) >= 2 and len(exp_fc) >= 2:
                t_stat, p_val = stats.ttest_ind(ctrl_fc, exp_fc)
                gene_stats.append({"comparison": f"{g} vs Control", "gene": gene,
                                   "p_value": round(float(p_val), 4),
                                   "significant": p_val < 0.05})
        if gene_stats:
            stats_results[gene] = gene_stats

    return _to_native({
        "ct_table": grouped.to_dict(orient="records"),
        "delta_ct": delta_ct_df.to_dict(orient="records"),
        "delta_delta_ct": result_df[["sample", "gene", "group", "delta_delta_ct", "fold_change"]].to_dict(orient="records"),
        "gene_summary": gene_summary,
        "statistics": stats_results,
        "control_group": control_group,
        "housekeeping_genes": housekeeping_genes,
        "method": method,
    })


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """自动识别和标准化列名"""
    col_map = {}
    for col in df.columns:
        col_lower = str(col).lower().strip()
        if col_lower in ("sample", "sample_name", "sample id", "sampleid"):
            col_map[col] = "sample"
        elif col_lower in ("gene", "target", "target_name", "gene_name", "target gene"):
            col_map[col] = "gene"
        elif col_lower in ("ct", "ct_value", "ct value", "cq", "cq_value", "ct mean"):
            col_map[col] = "ct_value"
        elif col_lower in ("group", "treatment", "condition"):
            col_map[col] = "group"
        elif col_lower in ("replicate", "rep", "well"):
            col_map[col] = "replicate"

    if col_map:
        df = df.rename(columns=col_map)

    # 处理未命名列（如 Excel 无表头数据）：基于内容启发式识别
    required = ["gene", "group", "ct_value"]
    if not all(c in df.columns for c in required):
        df = _heuristic_column_detection(df)

    # 最终确保必需列存在
    if "sample" not in df.columns:
        # 从 gene + group + replicate 生成 sample 名
        parts = []
        if "gene" in df.columns:
            parts.append(df["gene"].astype(str))
        if "group" in df.columns:
            parts.append(df["group"].astype(str))
        if "replicate" in df.columns:
            parts.append(df["replicate"].astype(str))
        if parts:
            df["sample"] = parts[0]
            for p in parts[1:]:
                df["sample"] = df["sample"] + "_" + p
        else:
            df["sample"] = df.iloc[:, 0].astype(str)

    if "gene" not in df.columns:
        # 尝试从文本列中找
        for col in df.select_dtypes(include=["object"]).columns:
            if df[col].nunique() < 20 and df[col].str.len().mean() < 15:
                df["gene"] = df[col]
                break
        if "gene" not in df.columns:
            df["gene"] = "Gene1"

    if "ct_value" not in df.columns:
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        # Ct 值通常在 15-40 范围
        for nc in numeric_cols:
            if 10 < df[nc].mean() < 45:
                df["ct_value"] = df[nc]
                break
        if "ct_value" not in df.columns and len(numeric_cols) > 0:
            df["ct_value"] = df[numeric_cols[0]]

    if "group" not in df.columns:
        for col in df.select_dtypes(include=["object"]).columns:
            if col != "gene":
                vals = df[col].unique()
                if len(vals) <= 10 and any("control" in str(v).lower() for v in vals):
                    df["group"] = df[col]
                    break
        if "group" not in df.columns:
            df["group"] = df.iloc[:, 0] if df.iloc[:, 0].dtype == object else "Exp"

    return df


def _heuristic_column_detection(df: pd.DataFrame) -> pd.DataFrame:
    """基于内容的启发式列识别（处理 Unnamed 列）"""
    col_map = {}
    for col in df.columns:
        col_str = str(col).lower().strip()
        # 检测 unnamed 列
        is_unnamed = "unnamed" in col_str or col_str == "" or col_str == "nan"

        if is_unnamed or col_str not in ("gene", "group", "sample", "ct_value", "replicate", "ct"):
            col_data = df[col]
            if col_data.dtype == object:
                unique_vals = col_data.dropna().unique()
                n_unique = len(unique_vals)
                # 基因名：通常 5-30 个唯一值，全大写或混合，长度 < 20
                if n_unique >= 2 and n_unique <= 30:
                    sample_vals = [str(v)[:20] for v in unique_vals[:5]]
                    # 检查是否像基因名（大写字母+数字+短横线）
                    import re
                    gene_pattern = sum(1 for v in sample_vals if re.match(r'^[A-Za-z][A-Za-z0-9\-\.]*$', str(v)))
                    if gene_pattern >= len(sample_vals) * 0.6 and "gene" not in col_map.values():
                        col_map[col] = "gene"
                        continue
                    # 检查组名（含 "control", 数字+单位 等）
                    control_like = any("control" in str(v).lower() or "ctrl" in str(v).lower() for v in sample_vals)
                    if control_like and "group" not in col_map.values():
                        col_map[col] = "group"
                        continue
                    # 如果 gene 还没被分配，这可能是 gene
                    if "gene" not in col_map.values():
                        col_map[col] = "gene"
                        continue
                    # 否则可能是 group
                    if "group" not in col_map.values():
                        col_map[col] = "group"
                        continue
                    col_map[col] = "sample"
            elif np.issubdtype(col_data.dtype, np.integer) and col_data.max() < 10:
                col_map[col] = "replicate"
            elif np.issubdtype(col_data.dtype, np.number):
                if 15 < col_data.mean() < 40 and "ct_value" not in col_map.values():
                    col_map[col] = "ct_value"
                elif "ct_value" not in col_map.values():
                    col_map[col] = "ct_value"

    if col_map:
        df = df.rename(columns=col_map)
    return df
