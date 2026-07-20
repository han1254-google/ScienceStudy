"""
qPCR 数据分析服务
- ΔCt / ΔΔCt 计算
- 2^(-ΔΔCt) 相对定量
- 多内参基因支持
"""
import numpy as np


def calc_delta_ct(ct_target, ct_housekeeping):
    """计算 ΔCt = Ct_目的 - Ct_内参"""
    return ct_target - ct_housekeeping


def calc_delta_delta_ct(delta_ct_experiment, delta_ct_control):
    """计算 ΔΔCt = ΔCt_实验 - ΔCt_对照"""
    return delta_ct_experiment - delta_ct_control


def calc_relative_expression(delta_delta_ct):
    """计算相对表达量 = 2^(-ΔΔCt)"""
    return np.power(2, -delta_delta_ct)


def analyze_qpcr_data(ct_data, housekeeping_genes, control_group):
    """
    完整的 qPCR 数据分析流程
    TODO: 实现完整的数据导入、分组计算、统计检验
    """
    pass
