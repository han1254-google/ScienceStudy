"""
EdU 细胞增殖图像分析服务
- 多通道荧光图像分离
- 细胞核分割 (Otsu + Watershed)
- EdU 阳性细胞识别
- EdU 阳性率 = EdU+ 核数 / 总核数 × 100%
"""
import numpy as np
import cv2
import base64
from skimage import segmentation, measure, morphology
from scipy import ndimage as ndi
import logging

log = logging.getLogger("EdU")


def analyze_edu_images(
    images: list[bytes],
    edu_channel: str = "green",
    nuclear_dye: str = "dapi",
    threshold: float = 30.0,
) -> dict:
    """
    分析 EdU 荧光图像。

    返回:
        {
            "per_image": [{total_nuclei, edu_positive, positive_rate, annotated_b64, ...}],
            "summary": {total_nuclei, total_positive, mean_positive_rate, group_stats},
        }
    """
    per_image = []
    for i, img_bytes in enumerate(images):
        result = _analyze_single_edu(img_bytes, edu_channel, nuclear_dye, threshold)
        result["image_index"] = i
        per_image.append(result)

    # 汇总统计
    total_nuclei = sum(r.get("total_nuclei", 0) for r in per_image)
    total_positive = sum(r.get("edu_positive", 0) for r in per_image)
    rates = [r.get("positive_rate", 0) for r in per_image if r.get("total_nuclei", 0) > 0]

    return {
        "per_image": per_image,
        "summary": {
            "image_count": len(images),
            "total_nuclei_sum": total_nuclei,
            "total_positive_sum": total_positive,
            "overall_positive_rate": round(total_positive / total_nuclei * 100, 2) if total_nuclei > 0 else 0,
            "mean_positive_rate": round(np.mean(rates), 2) if rates else 0,
            "std_positive_rate": round(np.std(rates), 2) if len(rates) > 1 else 0,
            "edu_channel": edu_channel,
            "threshold": threshold,
        },
    }


def _analyze_single_edu(
    img_bytes: bytes,
    edu_channel: str = "green",
    nuclear_dye: str = "dapi",
    threshold: float = 30.0,
) -> dict:
    """单张 EdU 图像分析"""
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        # 尝试灰度/多通道
        img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_UNCHANGED)
        if img is None:
            return {"error": "无法解码图像", "total_nuclei": 0, "edu_positive": 0, "positive_rate": 0}

    h, w = img.shape[:2]

    # 通道分离
    if img.ndim == 2:
        # 灰度图，假设为核染色
        dapi_channel = img
        edu_ch = img  # fallback
    elif img.ndim == 3 and img.shape[2] >= 3:
        b, g, r = cv2.split(img[:, :, :3])
        # 按颜色映射通道
        dapi_channel = b  # 蓝色 = DAPI
        if edu_channel == "green":
            edu_ch = g
        elif edu_channel == "red":
            edu_ch = r
        elif edu_channel == "far_red":
            edu_ch = r  # fallback: 通常远红在R通道
        else:
            edu_ch = g
    else:
        dapi_channel = img[:, :, 0] if img.ndim == 3 else img
        edu_ch = img[:, :, 1] if img.ndim == 3 and img.shape[2] > 1 else img

    # ---- 细胞核分割 ----
    nuclei_mask = _segment_nuclei_otsu_watershed(dapi_channel)

    # 标记连通区域
    labels = measure.label(nuclei_mask)
    regions = measure.regionprops(labels)

    # ---- EdU 阳性判定 ----
    edu_positive_count = 0
    for region in regions:
        # 提取该核区域内的 EdU 信号均值
        coords = region.coords
        edu_values = edu_ch[coords[:, 0], coords[:, 1]]
        mean_edu_intensity = float(np.mean(edu_values))

        # 判定 (可基于绝对阈值或相对阈值)
        if mean_edu_intensity > threshold:
            edu_positive_count += 1

    total_nuclei = len(regions)
    positive_rate = (edu_positive_count / total_nuclei * 100) if total_nuclei > 0 else 0

    # ---- 生成标注图像 ----
    annotated_img = _generate_edu_annotated(img, nuclei_mask, regions, edu_ch, threshold)

    return {
        "total_nuclei": total_nuclei,
        "edu_positive": edu_positive_count,
        "edu_negative": total_nuclei - edu_positive_count,
        "positive_rate": round(positive_rate, 2),
        "annotated_b64": annotated_img,
        "image_size": (w, h),
    }


def _segment_nuclei_otsu_watershed(channel: np.ndarray) -> np.ndarray:
    """Otsu + 距离变换 + Watershed 分割细胞核"""
    # 高斯平滑
    blurred = cv2.GaussianBlur(channel, (5, 5), 0)

    # Otsu 二值化
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 距离变换
    dist = ndi.distance_transform_edt(binary > 0)
    dist_smooth = cv2.GaussianBlur(dist.astype(np.float32), (7, 7), 0)

    # 局部极大值作为种子
    from skimage.feature import peak_local_max
    coords = peak_local_max(dist_smooth, min_distance=10, threshold_abs=np.percentile(dist_smooth[dist_smooth > 0], 30) if np.any(dist_smooth > 0) else 1)
    markers = np.zeros(dist.shape, dtype=np.int32)
    for i, coord in enumerate(coords):
        markers[tuple(coord)] = i + 1

    # Watershed
    labels = segmentation.watershed(-dist_smooth, markers, mask=binary > 0)

    # 小对象过滤
    min_size = 30  # 最小核面积
    for r in measure.regionprops(labels):
        if r.area < min_size:
            labels[labels == r.label] = 0

    return labels > 0


def _generate_edu_annotated(
    img: np.ndarray,
    nuclei_mask: np.ndarray,
    regions: list,
    edu_channel: np.ndarray,
    threshold: float,
) -> str:
    """生成标注图像 (EdU+ = 绿色, EdU- = 蓝色)"""
    h, w = nuclei_mask.shape
    # RGB overlay
    if img.ndim == 2:
        display = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] >= 3:
        display = img[:, :, :3].copy()
    else:
        display = cv2.cvtColor(img[:, :, 0], cv2.COLOR_GRAY2BGR)

    for region in regions:
        coords = region.coords
        edu_values = edu_channel[coords[:, 0], coords[:, 1]]
        mean_edu = float(np.mean(edu_values))

        color = (0, 255, 0) if mean_edu > threshold else (255, 0, 0)  # 绿=EdU+, 蓝=EdU-
        for y, x in coords[::3]:  # 每3个像素画一个点以加速
            if 0 <= y < h and 0 <= x < w:
                display[y, x] = color

    # 绘制轮廓
    contours, _ = cv2.findContours(nuclei_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(display, contours, -1, (255, 255, 255), 1)

    # 编码
    _, buf = cv2.imencode(".png", display)
    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def calc_edu_ratio(positive_count: int, total_count: int) -> float:
    """计算 EdU 阳性率 (%)"""
    if total_count == 0:
        return 0.0
    return positive_count / total_count * 100
