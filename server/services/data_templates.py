"""
实验数据模板 — 6 类实验的输入格式定义
用于前端展示期望格式、后端校验数据结构
"""
from typing import Optional

TEMPLATES = {
    "cck8": {
        "experiment_type": "cck8",
        "label": "CCK8 细胞增殖/毒性分析",
        "description": "导入 OD 值数据（Excel/CSV），自动计算细胞活力、拟合剂量-效应曲线、计算 IC50",
        "accepted_formats": [".xlsx", ".csv", ".xls"],
        "explanation": {
            "columns": {
                "group": "处理组名称（如 Control, DrugA, DrugB）",
                "concentration": "药物浓度 (μM)，Control 组填 0",
                "od_value": "OD450 吸光度值",
                "replicate": "（可选）生物学重复编号 1/2/3",
                "time_point": "（可选）检测时间点 (h)",
                "od_blank": "（可选）空白孔 OD 值",
            },
            "sample_data": [
                {"group": "Control", "concentration": 0, "od_value": 0.85, "replicate": 1},
                {"group": "DrugA", "concentration": 1, "od_value": 0.82, "replicate": 1},
                {"group": "DrugA", "concentration": 10, "od_value": 0.65, "replicate": 1},
                {"group": "DrugA", "concentration": 50, "od_value": 0.35, "replicate": 1},
            ],
        },
        "chart_types": ["dose_curve", "bar_chart"],
        "params": [
            {"name": "fit_model", "label": "拟合模型", "type": "select",
             "options": [{"value": "4pl", "label": "四参数 Logistic"},
                         {"value": "linear", "label": "线性回归"},
                         {"value": "log", "label": "对数拟合"}],
             "default": "4pl"},
            {"name": "stat_method", "label": "统计方法", "type": "select",
             "options": [{"value": "anova", "label": "One-way ANOVA + Tukey"},
                         {"value": "ttest", "label": "Student's t-test"}],
             "default": "anova"},
            {"name": "error_bar", "label": "误差棒", "type": "select",
             "options": [{"value": "sem", "label": "Mean ± SEM"},
                         {"value": "sd", "label": "Mean ± SD"}],
             "default": "sem"},
        ],
    },

    "edu": {
        "experiment_type": "edu",
        "label": "EdU 细胞增殖图像分析",
        "description": "上传 EdU 荧光图像，AI 自动识别 EdU+ 细胞和总细胞核，计算增殖率",
        "accepted_formats": [".tif", ".tiff", ".jpg", ".jpeg", ".png", ".czi"],
        "explanation": {
            "image_requirements": "需要双通道荧光图像：蓝色=DAPI/Hoechst(细胞核), 绿色/红色=EdU(增殖)",
            "supported_channels": "green (FITC/Alexa488), red (Cy3/Alexa555), far-red (Cy5/Alexa647)",
            "batch_support": "可批量上传多个视野，自动汇总统计",
        },
        "chart_types": ["bar_chart", "annotated_image"],
        "params": [
            {"name": "edu_channel", "label": "EdU 通道颜色", "type": "select",
             "options": [{"value": "green", "label": "绿色 (FITC/Alexa488)"},
                         {"value": "red", "label": "红色 (Cy3/Alexa555)"},
                         {"value": "far_red", "label": "远红 (Cy5/Alexa647)"}],
             "default": "green"},
            {"name": "nuclear_dye", "label": "核染料", "type": "select",
             "options": [{"value": "dapi", "label": "DAPI/Hoechst (蓝色)"}],
             "default": "dapi"},
            {"name": "threshold", "label": "EdU 阳性判定阈值", "type": "slider",
             "min": 1, "max": 100, "default": 30,
             "marks": {"10": "严格", "50": "中等", "90": "宽松"}},
        ],
    },

    "colony": {
        "experiment_type": "colony",
        "label": "细胞克隆形成分析",
        "description": "上传结晶紫染色克隆图像，AI 自动识别和计数克隆集落",
        "accepted_formats": [".tif", ".jpg", ".jpeg", ".png", ".bmp"],
        "explanation": {
            "image_requirements": "结晶紫染色的细胞克隆形成图像（6孔板/培养皿照片）",
            "min_clone_size": "默认识别 ≥50 个细胞的集落，可调整阈值",
        },
        "chart_types": ["bar_chart", "annotated_image"],
        "params": [
            {"name": "min_area", "label": "最小克隆面积 (像素)", "type": "number",
             "min": 10, "max": 500, "default": 50},
            {"name": "min_cells", "label": "最少细胞数阈值", "type": "select",
             "options": [{"value": "30", "label": "≥30 个细胞"},
                         {"value": "50", "label": "≥50 个细胞（常用）"},
                         {"value": "100", "label": "≥100 个细胞"}],
             "default": "50"},
            {"name": "roi_mode", "label": "分析区域", "type": "select",
             "options": [{"value": "auto", "label": "自动检测孔/皿边界"},
                         {"value": "full", "label": "整张图片"},
                         {"value": "manual", "label": "手动框选 ROI"}],
             "default": "auto"},
        ],
    },

    "wb": {
        "experiment_type": "wb",
        "label": "Western Blot 条带定量",
        "description": "上传 WB 化学发光图像，自动识别泳道和条带，灰度定量，内参归一化",
        "accepted_formats": [".tif", ".tiff", ".jpg", ".png", ".bmp"],
        "explanation": {
            "image_requirements": "WB 化学发光成像图像，建议上传原始 16-bit TIFF",
            "lane_note": "自动检测泳道数，也可手动指定",
        },
        "chart_types": ["bar_chart", "lane_plot", "annotated_image"],
        "params": [
            {"name": "lanes", "label": "泳道数", "type": "number",
             "min": 2, "max": 20, "default": 6},
            {"name": "background", "label": "背景扣除方法", "type": "select",
             "options": [{"value": "rolling", "label": "Rolling Ball"},
                         {"value": "local", "label": "局部背景扣除"},
                         {"value": "none", "label": "不扣除背景"}],
             "default": "rolling"},
            {"name": "housekeeping", "label": "内参蛋白", "type": "select",
             "options": [{"value": "gapdh", "label": "GAPDH"},
                         {"value": "actin", "label": "β-actin"},
                         {"value": "tubulin", "label": "β-tubulin"},
                         {"value": "custom", "label": "自定义"}],
             "default": "gapdh"},
        ],
    },

    "qpcr": {
        "experiment_type": "qpcr",
        "label": "qPCR 结果分析",
        "description": "导入 qPCR 仪导出的 Ct 值数据，自动计算 ΔΔCt 和相对表达量",
        "accepted_formats": [".xlsx", ".csv", ".txt"],
        "explanation": {
            "columns": {
                "sample": "样本名称",
                "gene": "基因名称（含内参）",
                "ct_value": "Ct 值",
                "group": "（可选）分组标签",
                "replicate": "（可选）技术重复编号",
            },
            "sample_data": [
                {"sample": "Control_1", "gene": "GAPDH", "ct_value": 18.2, "group": "Control"},
                {"sample": "Control_1", "gene": "Bax", "ct_value": 24.5, "group": "Control"},
                {"sample": "Drug_1", "gene": "GAPDH", "ct_value": 18.3, "group": "Drug"},
                {"sample": "Drug_1", "gene": "Bax", "ct_value": 22.1, "group": "Drug"},
            ],
            "supported_instruments": ["Bio-Rad CFX", "ABI StepOne/QuantStudio", "Roche LightCycler"],
        },
        "chart_types": ["bar_chart"],
        "params": [
            {"name": "housekeeping_genes", "label": "内参基因", "type": "select",
             "options": [{"value": "GAPDH", "label": "GAPDH"},
                         {"value": "ACTB", "label": "β-actin"},
                         {"value": "18S", "label": "18S rRNA"}],
             "default": "GAPDH",
             "multiple": True},
            {"name": "control_group", "label": "对照组", "type": "text", "default": "Control"},
            {"name": "method", "label": "计算方法", "type": "select",
             "options": [{"value": "ddct", "label": "ΔΔCt (2^(-ΔΔCt))"},
                         {"value": "pfaffl", "label": "Pfaffl 法（需扩增效率）"}],
             "default": "ddct"},
        ],
    },

    "ihc": {
        "experiment_type": "ihc",
        "label": "IHC 免疫组化图像分析",
        "description": "上传 IHC 染色图像，自动分离 DAB 阳性信号和苏木精复染，计算 H-Score 等定量指标",
        "accepted_formats": [".tif", ".jpg", ".png", ".svs"],
        "explanation": {
            "image_requirements": "DAB（棕黄色）+ 苏木精（蓝色复染）的 IHC 染色图像",
            "batch_support": "可批量上传不同放大倍数/不同区域的图像",
        },
        "chart_types": ["bar_chart", "deconv_overlay"],
        "params": [
            {"name": "stain_type", "label": "染色方式", "type": "select",
             "options": [{"value": "dab-he", "label": "DAB (棕黄色) + 苏木精 (蓝色)"},
                         {"value": "aec", "label": "AEC (红色) + 苏木精"},
                         {"value": "if", "label": "免疫荧光"}],
             "default": "dab-he"},
            {"name": "dab_threshold", "label": "DAB 阳性阈值", "type": "slider",
             "min": 1, "max": 100, "default": 50},
        ],
    },
}


def get_template(experiment_type: str) -> dict:
    """获取指定实验类型的数据模板"""
    if experiment_type not in TEMPLATES:
        raise ValueError(f"未知实验类型: {experiment_type}。支持: {', '.join(TEMPLATES.keys())}")
    return TEMPLATES[experiment_type]


def list_templates() -> list:
    """列出所有实验模板摘要"""
    return [
        {"key": key, "label": t["label"], "description": t["description"]}
        for key, t in TEMPLATES.items()
    ]
