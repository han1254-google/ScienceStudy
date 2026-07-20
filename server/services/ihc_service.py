"""
IHC 免疫组化图像分析服务
- DAB/Hematoxylin 颜色反卷积
- 阳性区域识别与面积计算
- H-Score / AOD / IOD 定量
"""
import numpy as np
import cv2
import base64
import logging
from scipy import ndimage

log = logging.getLogger("IHC")

# 标准 DAB + Hematoxylin 染色向量 (R, G, B)
# Ruifrok & Johnston (2001) 方法
STAIN_VECTORS = {
    "dab-he": {
        "H": np.array([0.650, 0.704, 0.286]),   # 苏木精 (蓝色)
        "DAB": np.array([0.268, 0.570, 0.776]),  # DAB (棕色)
    },
    "aec": {
        "H": np.array([0.650, 0.704, 0.286]),
        "AEC": np.array([0.119, 0.754, 0.646]),  # AEC (红色)
    },
}


def analyze_ihc_images(
    images: list[bytes],
    stain_type: str = "dab-he",
    dab_threshold: float = 50.0,
    metrics: list[str] = None,
) -> dict:
    """
    分析 IHC 染色图像。

    Returns:
        {
            "per_image": [{positive_area_ratio, aod, iod, hscore, annotated_b64, ...}],
            "summary": {mean_positive_area_ratio, mean_hscore, ...},
        }
    """
    if metrics is None:
        metrics = ["positive", "aod", "iod", "hscore"]

    per_image = []
    for i, img_bytes in enumerate(images):
        result = _analyze_single_ihc(img_bytes, stain_type, dab_threshold, metrics)
        result["image_index"] = i
        per_image.append(result)

    # 汇总
    pa_ratios = [r.get("positive_area_ratio", 0) for r in per_image]
    hscores = [r.get("hscore", 0) for r in per_image]
    aods = [r.get("aod", 0) for r in per_image]

    return {
        "per_image": per_image,
        "summary": {
            "image_count": len(images),
            "mean_positive_area_ratio": round(np.mean(pa_ratios), 2),
            "mean_hscore": round(np.mean(hscores), 2),
            "mean_aod": round(np.mean(aods), 4),
            "stain_type": stain_type,
            "dab_threshold": dab_threshold,
            "metrics": metrics,
        },
    }


def _analyze_single_ihc(
    img_bytes: bytes,
    stain_type: str,
    dab_threshold: float,
    metrics: list[str],
) -> dict:
    """单张 IHC 图像分析"""
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return {"error": "无法解码图像", "positive_area_ratio": 0}

    h, w = img.shape[:2]
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float64) / 255.0

    # ---- 颜色反卷积 ----
    if stain_type in STAIN_VECTORS:
        vectors = STAIN_VECTORS[stain_type]
        dab_channel, he_channel = _color_deconvolution(img_rgb, vectors)
    else:
        # IF: 简单通道分离
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float64) / 255.0
        dab_channel = gray
        he_channel = 1.0 - gray

    # ---- 组织掩码 ----
    tissue_mask = _create_tissue_mask(he_channel)

    # ---- DAB 阳性分割 ----
    dab_norm = (dab_channel - dab_channel.min()) / (dab_channel.max() - dab_channel.min() + 1e-8) * 255
    _, positive_mask = cv2.threshold(dab_norm.astype(np.uint8), dab_threshold, 255, cv2.THRESH_BINARY)
    positive_mask = positive_mask.astype(bool) & (tissue_mask > 0)

    # ---- 定量指标 ----
    tissue_area = np.sum(tissue_mask > 0)
    positive_area = np.sum(positive_mask)

    result = {}

    # 阳性面积比
    result["positive_area_ratio"] = round(positive_area / tissue_area * 100, 2) if tissue_area > 0 else 0

    # AOD: Average Optical Density
    if tissue_area > 0:
        positive_intensities = dab_channel[positive_mask]
        result["aod"] = round(float(np.mean(positive_intensities)) if len(positive_intensities) > 0 else 0, 4)
    else:
        result["aod"] = 0

    # IOD: Integrated Optical Density
    result["iod"] = round(float(np.sum(dab_channel[positive_mask])), 2)

    # H-Score
    result["hscore"] = _calculate_hscore(dab_channel, positive_mask, tissue_mask)

    # 强度分级
    result["intensity_levels"] = _classify_intensity(dab_channel, positive_mask)

    # ---- 生成标注图像 ----
    annotated_b64 = _generate_ihc_overlay(img, tissue_mask, positive_mask, dab_channel)
    result["annotated_b64"] = annotated_b64
    result["image_size"] = (w, h)

    return result


def _color_deconvolution(img_rgb: np.ndarray, vectors: dict) -> tuple:
    """
    颜色反卷积 — 分离 DAB 和 Hematoxylin。
    基于 Ruifrok & Johnston (2001) 方法。
    """
    # 光学密度转换
    OD = -np.log(np.maximum(img_rgb, 1e-6))

    # 构建染色矩阵 M: (3, n_stains) — RGB → stain concentrations
    stain_names = list(vectors.keys())
    M = np.column_stack([vectors[name] for name in stain_names])  # (3, n_stains)

    # 伪逆求解: C = pinv(M) @ OD  ⇒ C_flat: (N, n_stains)
    OD_flat = OD.reshape(-1, 3)
    M_pinv = np.linalg.pinv(M)  # (n_stains, 3)
    C_flat = np.dot(OD_flat, M_pinv.T)  # (N, n_stains)

    # 重构各通道
    h_idx = [i for i, name in enumerate(stain_names) if name.upper() in ("H", "HEMATOXYLIN")]
    d_idx = [i for i, name in enumerate(stain_names) if name.upper() in ("DAB", "AEC")]

    he_channel = C_flat[:, h_idx].sum(axis=1).reshape(img_rgb.shape[:2]) if h_idx else np.zeros(img_rgb.shape[:2])
    dab_channel = C_flat[:, d_idx].sum(axis=1).reshape(img_rgb.shape[:2]) if d_idx else np.zeros(img_rgb.shape[:2])

    # 归一化到 [0, 1]
    for ch in [he_channel, dab_channel]:
        ch_min, ch_max = ch.min(), ch.max()
        if ch_max > ch_min:
            ch[...] = (ch - ch_min) / (ch_max - ch_min)
        else:
            ch[...] = 0

    return dab_channel, he_channel


def _create_tissue_mask(he_channel: np.ndarray) -> np.ndarray:
    """从苏木精通道创建组织掩码"""
    # Otsu 阈值
    he_uint8 = (np.clip(he_channel, 0, 1) * 255).astype(np.uint8)
    _, mask = cv2.threshold(he_uint8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # 形态学清理
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    return mask


def _calculate_hscore(
    dab_channel: np.ndarray,
    positive_mask: np.ndarray,
    tissue_mask: np.ndarray,
) -> float:
    """
    计算 H-Score = Σ(强度等级 × 该等级阳性细胞百分比)
    等级: 0(阴性), 1(弱阳), 2(中阳), 3(强阳)
    """
    if not np.any(positive_mask):
        return 0.0

    pos_intensities = dab_channel[positive_mask]
    if len(pos_intensities) == 0:
        return 0.0

    # 按强度分布分级
    max_val = pos_intensities.max() if pos_intensities.max() > 0 else 1
    thresholds = [0, 0.25 * max_val, 0.5 * max_val, 0.75 * max_val, max_val + 1e-6]

    total_positive = len(pos_intensities)
    hscore = 0.0
    for level in range(4):
        count = np.sum((pos_intensities >= thresholds[level]) & (pos_intensities < thresholds[level + 1]))
        percentage = count / max(total_positive, 1) * 100
        hscore += (level + 1) * percentage

    return round(float(hscore), 2)


def _classify_intensity(dab_channel: np.ndarray, positive_mask: np.ndarray) -> dict:
    """阳性强度分为弱/中/强三个等级"""
    if not np.any(positive_mask):
        return {"weak": 0, "moderate": 0, "strong": 0, "total_positive": 0}

    intensities = dab_channel[positive_mask]
    max_val = intensities.max() if intensities.max() > 0 else 1
    p33, p66 = np.percentile(intensities, [33, 66]) if len(intensities) > 1 else [max_val / 3, max_val * 2 / 3]

    weak = int(np.sum(intensities < p33))
    moderate = int(np.sum((intensities >= p33) & (intensities < p66)))
    strong = int(np.sum(intensities >= p66))

    return {
        "weak": weak,
        "moderate": moderate,
        "strong": strong,
        "total_positive": int(len(intensities)),
    }


def _generate_ihc_overlay(
    img: np.ndarray,
    tissue_mask: np.ndarray,
    positive_mask: np.ndarray,
    dab_channel: np.ndarray,
) -> str:
    """生成 IHC 分析叠加图：红色=DAB阳性区域，蓝色=苏木精区域"""
    overlay = img.copy()

    # 红色 = DAB 阳性
    pos_vis = np.zeros_like(img)
    pos_vis[positive_mask] = (0, 0, 255)  # BGR 红色
    overlay = cv2.addWeighted(overlay, 0.7, pos_vis, 0.3, 0)

    # 组织边界
    contours, _ = cv2.findContours(tissue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, contours, -1, (255, 255, 0), 1)

    _, buf = cv2.imencode(".png", overlay)
    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
    return f"data:image/png;base64,{b64}"
