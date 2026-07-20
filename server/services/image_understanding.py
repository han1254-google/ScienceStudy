"""
图像理解服务 — GPT Vision API 封装
直接使用 OpenAI/DeepSeek API，支持视觉模型进行图像分析
支持：常规图像 (PNG/JPG) / TIF 科研图像 / 多图像批量分析
"""
import io
import base64
import logging
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

log = logging.getLogger("ImageUnderstanding")

# 视觉模型 — 直接使用 OpenAI 配置，不依赖 LLM_PROVIDER
VISION_API_KEY = OPENAI_API_KEY
VISION_BASE_URL = OPENAI_BASE_URL
VISION_MODEL = OPENAI_MODEL  # 如 gpt-4o, gpt-4.1, o4-mini 等支持 vision 的模型


def _image_to_base64(image_bytes: bytes, mime: str = "image/png") -> str:
    """将图像字节编码为 base64 data URI"""
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def _tif_to_png(tif_bytes: bytes) -> bytes:
    """
    TIF → PNG 转换，适配 Vision API
    - 多页 TIF：取第一页
    - 16-bit → 8-bit：百分位对比度拉伸
    - 多通道：保留 RGB / 灰度
    """
    import numpy as np
    from PIL import Image

    try:
        import tifffile
        img_array = tifffile.imread(io.BytesIO(tif_bytes))
    except ImportError:
        # 回退 Pillow
        img = Image.open(io.BytesIO(tif_bytes))
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        return buf.getvalue()

    # 多页 TIF → 取第一页
    if hasattr(img_array, "ndim") and img_array.ndim > 2:
        if img_array.ndim == 3 and img_array.shape[0] < 10:
            if img_array.shape[0] <= 4:
                # (C, H, W) → (H, W, C)
                img_array = np.transpose(img_array, (1, 2, 0))
            else:
                img_array = img_array[0]  # 取第一页
        elif img_array.ndim >= 3:
            img_array = img_array[0]

    # 16-bit → 8-bit 对比度拉伸
    if img_array.dtype == np.uint16:
        p2, p98 = np.percentile(img_array, (2, 98))
        if p98 > p2:
            img_array = np.clip((img_array.astype(float) - p2) / (p98 - p2) * 255, 0, 255)
        else:
            img_array = np.clip(img_array.astype(float) / 256, 0, 255)
        img_array = img_array.astype(np.uint8)

    # 灰度 → RGB
    img = Image.fromarray(img_array)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def get_image_info(image_bytes: bytes, filename: str = "") -> dict:
    """获取图像基本信息（尺寸、通道、格式等）"""
    from PIL import Image
    img = Image.open(io.BytesIO(image_bytes))
    return {
        "width": img.width,
        "height": img.height,
        "mode": img.mode,
        "format": img.format or filename.split(".")[-1].upper() if "." in filename else "Unknown",
    }


def analyze_images(
    images: list[bytes],
    prompt: str = "",
    filenames: list[str] = None,
    analysis_type: str = "general",
    stream: bool = False,
) -> dict:
    """
    调用 GPT Vision API 分析图像。

    Args:
        images: 图像字节列表（已预处理为 PNG）
        prompt: 用户自定义分析提示
        filenames: 原始文件名列表（用于日志）
        analysis_type: general / microscopy / ihc / wb / other
        stream: 是否流式输出

    Returns:
        {"success": bool, "analysis": str, "model_used": str, "images_info": [...]}
    """
    if not images:
        return {"success": False, "analysis": "", "model_used": VISION_MODEL,
                "error": "未提供图像"}

    if not VISION_API_KEY:
        return {"success": False, "analysis": "", "model_used": VISION_MODEL,
                "error": "未配置 OPENAI_API_KEY。请在 .env 文件中设置 OPENAI_API_KEY"}

    t0 = __import__("time").time()
    client = OpenAI(api_key=VISION_API_KEY, base_url=VISION_BASE_URL, timeout=120.0, max_retries=2)

    # 构建系统提示
    type_guidance = {
        "general": "请对该图像进行全面的描述和分析。",
        "microscopy": "这是一张显微镜图像。请识别染色类型（如HE、免疫荧光、IHC等），描述细胞/组织结构，评估图像质量，并提供定量分析建议（如细胞计数、阳性面积比等）。",
        "ihc": "这是一张免疫组化(IHC)染色图像。请识别阳性染色（通常为棕黄色DAB）的分布和强度，描述组织形态，评估染色质量，并建议定量指标（如H-Score、阳性面积比）。",
        "wb": "这是一张Western Blot图像。请识别条带位置、分析条带形态、评估背景水平，并提供定量建议（灰度值、归一化）。",
        "other": "请根据图像内容进行专业的科学图像分析。",
    }

    system_context = type_guidance.get(analysis_type, type_guidance["general"])

    if not prompt:
        prompt = f"""请详细分析上传的科研图像。

分析要求：
{system_context}

请按以下结构输出分析结果：

## 1. 图像类型识别
- 判断这是什么类型的科研图像
- 可能的实验方法

## 2. 内容描述
- 图像中的主要结构和特征
- 染色/标记情况

## 3. 定量分析建议
- 可以提取哪些定量指标
- 推荐的分析工具/方法

## 4. 论文发表建议
- 图像质量评估
- Figure 排版建议
- 图注撰写要点"""

    # 构建消息
    image_count = len(images)
    if filenames is None:
        filenames = [f"image_{i+1}.png" for i in range(image_count)]

    content_parts = [{"type": "text", "text": prompt}]
    for i, img_bytes in enumerate(images):
        mime = "image/png"
        if filenames and i < len(filenames):
            ext = filenames[i].split(".")[-1].lower() if "." in filenames[i] else "png"
            if ext in ("jpg", "jpeg"):
                mime = "image/jpeg"
            elif ext in ("tif", "tiff"):
                mime = "image/tiff"

        b64_data = base64.b64encode(img_bytes).decode("utf-8")
        content_parts.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime};base64,{b64_data}",
                "detail": "high",
            },
        })

    messages = [{"role": "user", "content": content_parts}]

    log.info(f"[Vision] analyzing {image_count} image(s), model={VISION_MODEL}, base_url={VISION_BASE_URL}")

    try:
        if stream:
            response = client.chat.completions.create(
                model=VISION_MODEL,
                messages=messages,
                max_tokens=2000,
                temperature=0.3,
                stream=True,
            )
            analysis_parts = []
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    analysis_parts.append(chunk.choices[0].delta.content)
            analysis = "".join(analysis_parts)
        else:
            response = client.chat.completions.create(
                model=VISION_MODEL,
                messages=messages,
                max_tokens=2000,
                temperature=0.3,
            )
            analysis = response.choices[0].message.content

        elapsed = __import__("time").time() - t0
        log.info(f"[Vision] done: {len(analysis)} chars ({elapsed:.1f}s)")

        # 收集图像信息
        images_info = []
        for i, img_bytes in enumerate(images):
            try:
                info = get_image_info(img_bytes, filenames[i] if i < len(filenames) else "")
                images_info.append(info)
            except Exception:
                images_info.append({"width": 0, "height": 0, "mode": "unknown", "format": "unknown"})

        return {
            "success": True,
            "analysis": analysis,
            "model_used": VISION_MODEL,
            "images_info": images_info,
            "image_count": image_count,
            "analysis_type": analysis_type,
        }

    except Exception as e:
        error_msg = str(e)
        log.error(f"[Vision] failed: {error_msg[:200]}")

        # 友好的错误提示
        if "vision" in error_msg.lower() or "image" in error_msg.lower() or "model" in error_msg.lower():
            friendly = (
                f"图像分析失败：模型 {VISION_MODEL} 可能不支持视觉功能。"
                "请在 .env 中设置 OPENAI_MODEL 为支持 vision 的模型（如 gpt-4o, gpt-4.1, o4-mini）。"
                f"\n\n原始错误: {error_msg[:300]}"
            )
        elif "api_key" in error_msg.lower() or "auth" in error_msg.lower():
            friendly = (
                "API Key 认证失败。请检查 .env 中的 OPENAI_API_KEY 是否正确设置。"
            )
        else:
            friendly = f"图像分析失败: {error_msg[:300]}"

        return {
            "success": False,
            "analysis": "",
            "model_used": VISION_MODEL,
            "error": friendly,
            "images_info": [],
        }
