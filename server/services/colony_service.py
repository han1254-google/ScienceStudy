"""
细胞克隆形成分析服务
- 克隆识别与分割
- 克隆计数 (按面积筛选)
- 克隆形成率计算
"""
import cv2
import numpy as np
from skimage import measure
import io
import base64
import logging

log = logging.getLogger("Colony")


def analyze_colony_images(
    images: list[bytes],
    min_area: int = 50,
    roi_mode: str = "auto",
) -> dict:
    """
    分析克隆形成图像。

    Args:
        images: 图像字节列表
        min_area: 最小克隆面积 (像素)
        roi_mode: 分析区域模式 (auto/full)

    Returns:
        {
            "per_image": [{count, areas, annotated_b64, colony_formation_rate, ...}],
            "summary": {total_colonies, mean_count, mean_area, ...},
        }
    """
    per_image = []
    for i, img_bytes in enumerate(images):
        result = _analyze_single_colony(img_bytes, min_area, roi_mode)
        result["image_index"] = i
        per_image.append(result)

    counts = [r["count"] for r in per_image]
    all_areas = []
    for r in per_image:
        all_areas.extend(r.get("areas", []))

    return {
        "per_image": per_image,
        "summary": {
            "total_images": len(images),
            "total_colonies": sum(counts),
            "mean_count": round(np.mean(counts), 1) if counts else 0,
            "std_count": round(np.std(counts), 1) if len(counts) > 1 else 0,
            "mean_area": round(np.mean(all_areas), 1) if all_areas else 0,
            "median_area": round(np.median(all_areas), 1) if all_areas else 0,
            "area_range": [int(np.min(all_areas)), int(np.max(all_areas))] if all_areas else [0, 0],
        },
    }


def _analyze_single_colony(img_bytes: bytes, min_area: int, roi_mode: str) -> dict:
    """单张图像克隆分析"""
    # 解码
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return {"error": "无法解码图像", "count": 0, "areas": [], "annotated_b64": ""}

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # ROI 提取
    if roi_mode == "auto":
        mask = _detect_well_boundary(gray)
        if mask is not None and np.sum(mask) > 0.1 * mask.size:
            gray = cv2.bitwise_and(gray, gray, mask=mask)
        else:
            mask = np.ones_like(gray) * 255

    # 预处理
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # 形态学处理
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)

    # 查找轮廓
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 过滤 + 标注
    colonies = []
    annotated = img.copy()
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area >= min_area:
            M = cv2.moments(cnt)
            if M["m00"] > 0:
                cx, cy = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
                colonies.append({"area": round(float(area), 1), "centroid": (cx, cy)})
                cv2.drawContours(annotated, [cnt], -1, (0, 0, 255), 2)
                cv2.putText(annotated, str(len(colonies)), (cx, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

    # 编码标注图像
    _, buf = cv2.imencode(".png", annotated)
    annotated_b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

    return {
        "count": len(colonies),
        "areas": [c["area"] for c in colonies],
        "annotated_b64": f"data:image/png;base64,{annotated_b64}",
        "image_size": (w, h),
        "min_area_threshold": min_area,
    }


def _detect_well_boundary(gray: np.ndarray) -> np.ndarray:
    """尝试检测孔/皿的圆形边界"""
    blurred = cv2.GaussianBlur(gray, (9, 9), 2)
    circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, dp=1.2, minDist=100,
                                param1=50, param2=30, minRadius=50, maxRadius=int(min(gray.shape) * 0.8))
    if circles is not None and len(circles) > 0:
        circles = np.uint16(np.around(circles))
        mask = np.zeros_like(gray)
        x, y, r = circles[0][0]
        cv2.circle(mask, (x, y), int(r * 0.9), 255, -1)
        return mask
    return None


def count_colonies(image: np.ndarray, min_area: int = 50) -> int:
    """快速计数克隆数（无标注）"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return sum(1 for c in contours if cv2.contourArea(c) >= min_area)


def calc_colony_formation_rate(colony_count: int, seeded_cells: int) -> float:
    """计算克隆形成率 (%)"""
    if seeded_cells == 0:
        return 0.0
    return colony_count / seeded_cells * 100
