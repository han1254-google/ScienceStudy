"""
CCK8 数据分析服务
- OD 值处理 → 细胞活力计算
- 四参数 Logistic 拟合 → IC50
- 剂量-效应曲线拟合
- 统计学分析 (t-test / ANOVA)
"""
import numpy as np
from scipy.optimize import curve_fit
from scipy import stats


def calc_cell_viability(od_experiment, od_control, od_blank=0):
    """计算细胞活力 (% of Control)"""
    return (od_experiment - od_blank) / (od_control - od_blank) * 100


def four_pl(x, a, b, c, d):
    """四参数 Logistic 模型"""
    return d + (a - d) / (1 + (x / c) ** b)


def calc_ic50(doses, viabilities):
    """拟合 4PL 曲线并计算 IC50"""
    # TODO: 实现完整的 4PL 拟合逻辑
    pass


def compare_groups(groups: list, method: str = "anova"):
    """多组统计比较"""
    # TODO: 实现 t-test / ANOVA 统计检验
    pass
