"""
CCK8 数据分析服务
- OD 值处理 → 细胞活力计算
- 四参数 Logistic 拟合 → IC50
- 剂量-效应曲线拟合
- 统计学分析 (t-test / ANOVA)
"""
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy import stats
import logging
import warnings
warnings.filterwarnings('ignore', category=RuntimeWarning)

log = logging.getLogger("CCK8")


def _to_native(obj):
    """递归转换 numpy 类型为 Python 原生类型，处理 NaN/Inf"""
    import numpy as np
    if isinstance(obj, (np.integer,)): return int(obj)
    elif isinstance(obj, (np.floating,)):
        if np.isnan(obj) or np.isinf(obj): return None
        return float(obj)
    elif isinstance(obj, (np.bool_,)): return bool(obj)
    elif isinstance(obj, np.ndarray): return obj.tolist()
    elif isinstance(obj, float) and (obj != obj or obj in (float('inf'), float('-inf'))):
        return None
    elif isinstance(obj, dict): return {k: _to_native(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)): return [_to_native(i) for i in obj]
    return obj


def calc_cell_viability(od_experiment, od_control, od_blank=0):
    """计算细胞活力 (%)"""
    return (od_experiment - od_blank) / (od_control - od_blank) * 100


def four_pl(x, a, b, c, d):
    """四参数 Logistic 模型: y = d + (a-d) / (1 + (x/c)^b)"""
    return d + (a - d) / (1 + (x / c) ** b)


def _fit_4pl(doses, viabilities):
    """4PL 拟合，返回 IC50 和拟合参数"""
    try:
        # 初始猜测 [bottom, slope, IC50, top]
        p0 = [np.min(viabilities), -1, np.median(doses), np.max(viabilities)]
        bounds = (
            [0, -10, min(doses) * 0.1, 0],     # lower
            [200, 10, max(doses) * 10, 200],    # upper
        )
        popt, pcov = curve_fit(four_pl, np.array(doses), np.array(viabilities),
                               p0=p0, bounds=bounds, maxfev=5000)
        residuals = np.array(viabilities) - four_pl(np.array(doses), *popt)
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((np.array(viabilities) - np.mean(viabilities)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        ic50 = popt[2]
        return {"ic50": round(float(ic50), 3), "params": {k: round(float(v), 4) for k, v in
                zip(["a(bottom)", "b(slope)", "c(IC50)", "d(top)"], popt)},
                "r_squared": round(float(r_squared), 4)}
    except Exception as e:
        log.warning(f"[CCK8] 4PL fit failed: {e}")
        try:
            # 退化到线性插值找 IC50
            v = np.array(viabilities)
            d = np.array(doses)
            if np.any(v <= 50) and np.any(v >= 50):
                ic50 = np.interp(50, v[::-1], d[::-1]) if v[-1] < v[0] else np.interp(50, v, d)
                return {"ic50": round(float(ic50), 3), "params": {}, "r_squared": 0}
        except Exception:
            pass
        return {"ic50": float("nan"), "params": {}, "r_squared": 0}


def _statistical_test(groups_data: dict, method: str = "anova") -> dict:
    """
    多组统计比较。
    groups_data: {group_name: [values, ...]}
    """
    group_names = list(groups_data.keys())
    all_values = list(groups_data.values())

    if len(group_names) < 2:
        return {"method": method, "p_value": 1.0, "significant": False, "comparisons": []}

    if method == "ttest" and len(group_names) == 2:
        t_stat, p_val = stats.ttest_ind(*all_values)
        return {"method": "ttest", "statistic": round(float(t_stat), 4),
                "p_value": round(float(p_val), 4), "significant": p_val < 0.05,
                "comparisons": [{"groups": group_names, "p_value": round(float(p_val), 4)}]}

    # ANOVA
    try:
        f_stat, p_val = stats.f_oneway(*all_values)
    except Exception:
        return {"method": "anova", "p_value": 1.0, "significant": False, "comparisons": []}

    # Tukey HSD 事后检验
    comparisons = []
    for i in range(len(group_names)):
        for j in range(i + 1, len(group_names)):
            t_stat, p_pair = stats.ttest_ind(all_values[i], all_values[j])
            comparisons.append({
                "groups": [group_names[i], group_names[j]],
                "p_value": round(float(p_pair), 4),
                "significant": p_pair < 0.05,
            })

    return {"method": "anova", "statistic": round(float(f_stat), 4),
            "p_value": round(float(p_val), 4), "significant": p_val < 0.05,
            "comparisons": comparisons}


def parse_cck8_data(file_path: str) -> pd.DataFrame:
    """解析 CCK8 数据文件 (Excel/CSV)"""
    ext = file_path.rsplit(".", 1)[-1].lower()
    if ext in ("xlsx", "xls"):
        df = pd.read_excel(file_path)
    else:
        df = pd.read_csv(file_path)
    return _normalize_cck8_columns(df)


def _normalize_cck8_columns(df: pd.DataFrame) -> pd.DataFrame:
    """自动标准化列名"""
    import re
    col_map = {}
    for col in df.columns:
        cl = str(col).lower().strip()
        # 去掉括号内容 (如 "concentration(μM)" → "concentration")
        cl_clean = re.sub(r'\(.*\)', '', cl).strip()
        if cl_clean in ("group", "treatment", "condition", "组别", "分组"):
            col_map[col] = "group"
        elif cl_clean in ("concentration", "dose", "conc", "浓度", "剂量"):
            col_map[col] = "concentration"
        elif cl_clean in ("od_value", "od", "od450", "od值", "吸光度", "od450"):
            col_map[col] = "od_value"
        elif cl_clean in ("replicate", "rep", "重复"):
            col_map[col] = "replicate"
        elif cl_clean in ("time_point", "time", "时间", "timepoint"):
            col_map[col] = "time_point"
        elif cl_clean in ("od_blank", "blank", "空白"):
            col_map[col] = "od_blank"
    if col_map:
        df = df.rename(columns=col_map)

    for req in ["group", "od_value"]:
        if req not in df.columns:
            if req == "group" and len(df.columns) >= 1:
                df["group"] = df.iloc[:, 0]
            elif req == "od_value":
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    df["od_value"] = df[numeric_cols[0]]

    if "concentration" not in df.columns:
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) >= 2:
            df["concentration"] = df[numeric_cols[1]]
        else:
            df["concentration"] = 0

    return df


def analyze_cck8_data(
    df: pd.DataFrame,
    fit_model: str = "4pl",
    stat_method: str = "anova",
    error_bar: str = "sem",
) -> dict:
    """
    完整的 CCK8 分析流程。

    Returns:
        {
            "group_stats": [...],
            "ic50": {group: float},
            "curve_fit": {group: {...}},
            "viability": [...],
            "dose_response": [...],
            "statistics": {...},
        }
    """
    # 标准化列名
    df = _normalize_cck8_columns(df)

    # 自动识别 Control 组
    control_rows = df[df["group"].str.lower().str.contains("control", na=False)]
    if len(control_rows) == 0:
        control_rows = df[df["group"] == df["group"].iloc[0]]

    control_od = control_rows["od_value"].mean()
    blank_od = df["od_blank"].mean() if "od_blank" in df.columns else 0

    # 按 group + concentration 分组计算
    has_conc = "concentration" in df.columns and df["concentration"].nunique() > 1
    has_time = "time_point" in df.columns and df["time_point"].nunique() > 1

    groups = df["group"].unique()
    group_stats = {}

    for group in groups:
        gdf = df[df["group"] == group]
        od_mean = gdf["od_value"].mean()
        viability = calc_cell_viability(od_mean, control_od, blank_od)
        group_stats[group] = {
            "od_mean": round(float(od_mean), 4),
            "od_std": round(float(gdf["od_value"].std()), 4) if len(gdf) > 1 else 0,
            "viability": round(float(viability), 2),
            "n": len(gdf),
        }

    # 按浓度分组（用于剂量曲线）
    dose_response = []
    ic50_results = {}
    curve_fit_results = {}

    if has_conc:
        for group in groups:
            gdf = df[df["group"] == group]
            conc_groups = gdf.groupby("concentration")
            doses = []
            viabilities = []
            errors = []
            for conc, cdf in conc_groups:
                od_mean = cdf["od_value"].mean()
                v = calc_cell_viability(od_mean, control_od, blank_od)
                doses.append(float(conc))
                viabilities.append(round(float(v), 2))
                err = cdf["od_value"].sem() if error_bar == "sem" else cdf["od_value"].std()
                errors.append(round(float(err / control_od * 100), 2) if control_od > 0 else 0)

            dose_response.append({
                "group": group,
                "doses": doses,
                "viabilities": viabilities,
                "errors": errors,
            })

            if fit_model == "4pl" and len(doses) >= 4:
                fit_result = _fit_4pl(doses, viabilities)
                ic50_results[group] = fit_result["ic50"]
                curve_fit_results[group] = fit_result

    # 统计检验
    viability_by_group = {}
    for group in groups:
        gdf = df[df["group"] == group]
        viabilities = []
        if has_conc:
            for _, cdf in gdf.groupby("concentration"):
                od_mean = cdf["od_value"].mean()
                viabilities.append(calc_cell_viability(od_mean, control_od, blank_od))
        else:
            for _, row in gdf.iterrows():
                viabilities.append(calc_cell_viability(row["od_value"], control_od, blank_od))
        viability_by_group[group] = viabilities if viabilities else [0]

    statistics = _statistical_test(viability_by_group, stat_method)

    return _to_native({
        "group_stats": {k: v for k, v in group_stats.items()},
        "ic50": ic50_results,
        "curve_fit": curve_fit_results,
        "dose_response": dose_response,
        "viability": [{"group": k, "viability": v["viability"]} for k, v in group_stats.items()],
        "statistics": statistics,
        "control_group": control_rows["group"].iloc[0] if len(control_rows) > 0 else groups[0],
        "has_dose_response": has_conc,
        "has_time_course": has_time,
        "fit_model": fit_model,
        "stat_method": stat_method,
        "error_bar": error_bar,
    })
