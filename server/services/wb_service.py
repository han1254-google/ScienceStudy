"""
Western Blot 条带定量分析服务
- 泳道自动检测 (垂直投影)
- 条带检测 (水平投影局部极小值)
- 灰度定量 (积分光密度)
- 内参归一化
"""
import numpy as np
import cv2
import base64
import logging
from scipy import ndimage
from scipy.signal import find_peaks

log = logging.getLogger("WB")


def analyze_wb_image(
    img_bytes: bytes,
    lanes: int = None,
    background: str = "rolling",
    housekeeping: str = "gapdh",
) -> dict:
    """
    分析 WB 图像。

    Returns:
        {
            "lanes": [{index, bands: [{position, intensity, area, ...}]}],
            "normalized_expression": {protein: {group: fold_change}},
            "annotated_b64": "",
            "lane_profile_b64": "",
        }
    """
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)
    if img is None:
        img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_UNCHANGED)
        if img is not None and img.ndim == 3:
            img = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
        elif img is not None and img.ndim == 2:
            pass
        else:
            return {"error": "无法解码图像", "lanes": [], "normalized_expression": {}}

    h, w = img.shape

    # ---- 泳道检测 ----
    if lanes is None:
        detected_lanes = _detect_lanes(img)
        lanes = max(detected_lanes, 2)
        log.info(f"[WB] auto-detected {lanes} lanes")
    else:
        lanes = int(lanes)

    lane_boundaries = _find_lane_boundaries(img, lanes)

    # ---- 逐泳道分析 ----
    lane_data = []
    all_bands_intensity = {}

    for i in range(lanes):
        x1, x2 = lane_boundaries[i], lane_boundaries[i + 1]
        lane_img = img[:, x1:x2]

        # 背景扣除
        if background == "rolling":
            lane_img = _rolling_ball_bg_subtract(lane_img)
        elif background == "local":
            lane_img = _local_bg_subtract(lane_img)

        # 条带检测
        bands = _detect_bands(lane_img)

        for band in bands:
            band["lane"] = i + 1
            band["intensity"] = round(float(band["intensity"]), 2)
            band["area"] = round(float(band["area"]), 2)

        lane_data.append({
            "index": i + 1,
            "x_range": [int(x1), int(x2)],
            "bands": bands,
        })

        for b in bands:
            key = f"lane_{i+1}_band_{b['position']}"
            all_bands_intensity[key] = b["intensity"]

    # ---- 生成标注图像 ----
    annotated_b64 = _generate_wb_annotated(img, lane_boundaries, lane_data)

    # ---- 泳道强度剖面图 ----
    lane_profiles = [_get_lane_profile(img, lane_boundaries[i], lane_boundaries[i + 1])
                     for i in range(lanes)]

    return {
        "lanes": lane_data,
        "lane_count": lanes,
        "total_bands": sum(len(ld["bands"]) for ld in lane_data),
        "band_intensities": all_bands_intensity,
        "annotated_b64": annotated_b64,
        "lane_profiles": lane_profiles,
        "normalized_expression": {},  # 需要用户指定内参泳道和目的蛋白泳道
        "image_size": (w, h),
    }


def _detect_lanes(img: np.ndarray) -> int:
    """通过垂直投影自动检测泳道数"""
    profile = np.mean(img, axis=0)
    # 平滑
    from scipy.ndimage import gaussian_filter1d
    profile_smooth = gaussian_filter1d(profile.astype(float), sigma=5)

    # 找极小值（泳道间空隙）
    min_peaks, _ = find_peaks(-profile_smooth, distance=20, prominence=np.std(profile_smooth) * 0.5)

    if len(min_peaks) >= 1:
        return max(len(min_peaks) + 1, 2)

    # 回退：按宽度估算
    estimated = max(img.shape[1] // 80, 2)
    return max(min(estimated, 15), 2)


def _find_lane_boundaries(img: np.ndarray, lanes: int) -> list:
    """找到泳道边界 x 坐标"""
    w = img.shape[1]
    profile = np.mean(img, axis=0)
    from scipy.ndimage import gaussian_filter1d
    profile_smooth = gaussian_filter1d(profile.astype(float), sigma=5)

    if lanes <= 1:
        return [0, w]

    # 等分法（默认）
    boundaries = [int(w * i / lanes) for i in range(lanes + 1)]

    # 尝试微调至局部极小值
    min_peaks, properties = find_peaks(-profile_smooth, distance=max(w // (lanes * 2), 15),
                                        prominence=np.std(profile_smooth) * 0.3)
    if len(min_peaks) >= lanes - 1:
        # 取 lanes-1 个最显著的极小值
        prominences = properties.get("prominences", [0] * len(min_peaks))
        top_indices = np.argsort(prominences)[-(lanes - 1):]
        adjusted = sorted(min_peaks[top_indices])
        boundaries = [0] + adjusted + [w]

    return boundaries


def _detect_bands(lane_img: np.ndarray) -> list:
    """检测单个泳道内的条带"""
    h = lane_img.shape[0]
    # 水平投影
    profile = np.mean(lane_img, axis=1)
    from scipy.ndimage import gaussian_filter1d
    profile_smooth = gaussian_filter1d(profile.astype(float), sigma=3)

    # 找峰值（条带）
    peaks, properties = find_peaks(profile_smooth, distance=max(h // 20, 10),
                                    prominence=np.std(profile_smooth) * 1.5,
                                    height=np.percentile(profile_smooth, 50))

    bands = []
    for idx, peak_pos in enumerate(peaks):
        # 条带区域 (peak ± 15 pixels)
        y1 = max(0, peak_pos - 15)
        y2 = min(h, peak_pos + 15)
        band_roi = lane_img[y1:y2, :]

        intensity = float(np.sum(band_roi))  # 积分光密度
        area = float(np.sum(band_roi > 0))
        peak_height = float(profile_smooth[peak_pos])

        bands.append({
            "position": int(peak_pos),
            "y_range": [int(y1), int(y2)],
            "intensity": intensity,
            "area": area,
            "peak_height": peak_height,
        })

    return bands


def _rolling_ball_bg_subtract(img: np.ndarray, radius: int = 50) -> np.ndarray:
    """Rolling Ball 背景扣除"""
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (radius * 2 + 1, radius * 2 + 1))
    background = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)
    subtracted = cv2.subtract(img.astype(np.int16), background.astype(np.int16))
    return np.clip(subtracted, 0, 255).astype(np.uint8)


def _local_bg_subtract(img: np.ndarray) -> np.ndarray:
    """局部背景扣除（使用大核中值滤波）"""
    background = cv2.medianBlur(img, 51)
    subtracted = cv2.subtract(img.astype(np.int16), background.astype(np.int16))
    return np.clip(subtracted, 0, 255).astype(np.uint8)


def _generate_wb_annotated(img: np.ndarray, boundaries: list, lane_data: list) -> str:
    """生成标注的 WB 图像"""
    h, w = img.shape
    annotated = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    # 画泳道线
    for bx in boundaries:
        cv2.line(annotated, (int(bx), 0), (int(bx), h), (0, 255, 255), 1)

    # 画条带框
    for ld in lane_data:
        x1, x2 = ld["x_range"]
        for band in ld["bands"]:
            y1, y2 = band["y_range"]
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(annotated, f"L{ld['index']}", (x1 + 2, y1 + 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

    _, buf = cv2.imencode(".png", annotated)
    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def _get_lane_profile(img: np.ndarray, x1: int, x2: int) -> list:
    """获取泳道强度剖面"""
    lane = img[:, int(x1):int(x2)]
    profile = np.mean(lane, axis=1)
    return [round(float(v), 2) for v in profile]


def normalize_expression(target_intensity: float, housekeeping_intensity: float) -> float:
    """内参归一化"""
    if housekeeping_intensity == 0:
        return 0.0
    return target_intensity / housekeeping_intensity
