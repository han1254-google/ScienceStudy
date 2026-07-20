"""
Western Blot 条带定量分析服务
- 泳道与条带自动检测
- 灰度值定量 (背景扣除)
- 内参归一化
"""
import numpy as np
import cv2


def detect_lanes(image, lane_count=None):
    """自动检测泳道位置"""
    # TODO: 实现泳道检测
    pass


def detect_bands(lane_image):
    """检测条带位置"""
    # TODO: 实现条带检测
    pass


def quantify_band(band_roi, background_roi=None):
    """条带灰度定量 (积分光密度)"""
    # TODO: 实现灰度定量
    pass


def normalize_expression(target_intensity, housekeeping_intensity):
    """内参归一化"""
    if housekeeping_intensity == 0:
        return 0.0
    return target_intensity / housekeeping_intensity
