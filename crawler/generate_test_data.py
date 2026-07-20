"""
生成 Module 2 六大实验类型的测试数据
输出目录: testData/{cck8,edu,colony,wb,qpcr,ihc}
"""
import os
import numpy as np
import pandas as pd
import cv2
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

OUT = Path(__file__).parent.parent / "testData"
SEED = 42
np.random.seed(SEED)

# ============================================================
# 1. CCK8 — OD值数据 (Excel)
# ============================================================
def gen_cck8():
    """生成 CCK8 OD 值数据，含剂量-效应关系"""
    records = []
    groups = {
        "Control":     [0,   0.85, 0.03],
        "DrugA 1μM":  [1,   0.80, 0.03],
        "DrugA 5μM":  [5,   0.68, 0.04],
        "DrugA 10μM": [10,  0.52, 0.03],
        "DrugA 20μM": [20,  0.35, 0.03],
        "DrugA 50μM": [50,  0.18, 0.02],
    }
    for group, (conc, base_od, std) in groups.items():
        for rep in range(3):
            od = base_od + np.random.normal(0, std)
            records.append({
                "group": group, "concentration(μM)": conc,
                "OD450": round(max(0, od), 4), "replicate": rep + 1,
            })
    df = pd.DataFrame(records)
    df.to_excel(OUT / "cck8" / "cck8_dose_response.xlsx", index=False)
    print(f"  [CCK8] cck8_dose_response.xlsx — {len(df)} rows")

    # 另一个文件：多时间点
    records2 = []
    for group, ods in {
        "Control":  [0.42, 0.78, 1.25, 1.82],
        "DrugA 10μM": [0.41, 0.55, 0.62, 0.58],
        "DrugB 10μM": [0.43, 0.65, 0.85, 0.95],
    }.items():
        for t, (h, base_od) in enumerate(zip([0, 24, 48, 72], ods)):
            for rep in range(3):
                od = base_od + np.random.normal(0, 0.04)
                records2.append({
                    "group": group, "time_point(h)": h,
                    "OD450": round(max(0, od), 4), "replicate": rep + 1,
                })
    df2 = pd.DataFrame(records2)
    df2.to_excel(OUT / "cck8" / "cck8_time_course.xlsx", index=False)
    print(f"  [CCK8] cck8_time_course.xlsx — {len(df2)} rows")


# ============================================================
# 2. EdU — 荧光图像
# ============================================================
def gen_edu():
    """生成模拟 EdU 荧光图像（DAPI蓝 + EdU绿 双通道）"""
    configs = [
        ("Control",     200, 90,  45),
        ("Control",     200, 88,  44),
        ("Drug 5μM",   200, 75,  37),
        ("Drug 5μM",   200, 78,  39),
        ("Drug 20μM",  200, 40,  20),
        ("Drug 20μM",  200, 35,  17),
    ]
    for i, (group, total, dapi_bright, edu_bright) in enumerate(configs):
        h, w = 400, 400
        dapi = np.random.randint(5, 15, (h, w)).astype(np.uint8)
        edu  = np.random.randint(2, 8,  (h, w)).astype(np.uint8)
        # 画细胞核
        nuclei_positions = []
        for _ in range(total):
            cy, cx = np.random.randint(30, h - 30), np.random.randint(30, w - 30)
            r = np.random.randint(8, 14)
            nuclei_positions.append((cy, cx, r))
            # DAPI 信号
            yy, xx = np.ogrid[:h, :w]
            mask = (yy - cy) ** 2 + (xx - cx) ** 2 <= r ** 2
            dapi[mask] = np.clip(dapi_bright + np.random.randint(-20, 10), 0, 255)
        # EdU 阳性：随机选一部分核
        edu_positive = int(total * (edu_bright / 200))
        positive_indices = np.random.choice(total, edu_positive, replace=False)
        for idx in positive_indices:
            cy, cx, r = nuclei_positions[idx]
            yy, xx = np.ogrid[:h, :w]
            mask = (yy - cy) ** 2 + (xx - cx) ** 2 <= r ** 2
            edu[mask] = np.clip(edu_bright + np.random.randint(-15, 15), 0, 255)
        # 合成 RGB: B=DAPI, G=EdU, R=0
        img = np.stack([dapi, edu, np.zeros_like(dapi)], axis=-1)
        path = OUT / "edu" / f"edu_{group.replace(' ','_')}_FOV{i+1}.png"
        cv2.imwrite(str(path), img)
        print(f"  [EdU] {path.name} — {total} nuclei, ~{edu_positive} EdU+")


# ============================================================
# 3. 克隆形成 — 结晶紫染色图像
# ============================================================
def gen_colony():
    """生成模拟克隆形成图像（紫色背景 + 深色克隆点）"""
    configs = [
        ("Control",       65),
        ("Control",       58),
        ("Drug 2μM",     42),
        ("Drug 2μM",     38),
        ("Drug 10μM",    12),
        ("Drug 10μM",     8),
    ]
    for i, (group, n_colonies) in enumerate(configs):
        h, w = 500, 500
        # 浅紫灰色背景（模拟结晶紫染色后的孔板）
        bg = np.ones((h, w, 3), dtype=np.uint8)
        bg[:, :, 0] = np.random.randint(200, 230, (h, w))
        bg[:, :, 1] = np.random.randint(190, 220, (h, w))
        bg[:, :, 2] = np.random.randint(200, 235, (h, w))
        img = bg.copy()
        for _ in range(n_colonies):
            cy, cx = np.random.randint(30, h - 30), np.random.randint(30, w - 30)
            r = np.random.randint(8, 22)
            yy, xx = np.ogrid[:h, :w]
            mask = (yy - cy) ** 2 + (xx - cx) ** 2 <= r ** 2
            # 深紫色克隆
            for ch in range(3):
                img[mask, ch] = np.random.randint(30, 100)
        path = OUT / "colony" / f"colony_{group.replace(' ','_')}_n{n_colonies}.png"
        cv2.imwrite(str(path), img)
        print(f"  [Colony] {path.name} — ~{n_colonies} colonies")


# ============================================================
# 4. WB — 化学发光条带图像
# ============================================================
def _add_gaussian_band(img, cy, cx_start, cx_end, height, intensity):
    """在图像上画一个高斯条带"""
    h, w = img.shape
    for x in range(cx_start, cx_end):
        for dy in range(-height * 2, height * 2 + 1):
            y = cy + dy
            if 0 <= y < h:
                dist = (dy / height) ** 2
                val = intensity * np.exp(-dist / 2)
                img[y, x] = max(img[y, x], val)

def gen_wb():
    """生成模拟 WB 化学发光图像"""
    configs = [
        # (文件名, 泳道配置: [(蛋白名, 条带强度), ...])
        ("Control", [
            ("GAPDH",   0.7), ("Bax",     0.3), ("Bcl-2",   0.8), ("Caspase-3", 0.15),
        ]),
        ("Drug_Low", [
            ("GAPDH",   0.7), ("Bax",     0.5), ("Bcl-2",   0.55), ("Caspase-3", 0.35),
        ]),
        ("Drug_High", [
            ("GAPDH",   0.7), ("Bax",     0.85), ("Bcl-2",  0.2), ("Caspase-3", 0.75),
        ]),
    ]
    for group, bands_config in configs:
        h, w = 600, 160
        img = np.ones((h, w), dtype=np.float64) * 0.85  # 浅灰背景
        # 添加随机噪声
        img += np.random.normal(0, 0.02, (h, w))
        # 4 个泳道
        lane_centers = [25, 65, 105, 140]
        lane_width = 16
        for li, (protein, intensity) in enumerate(bands_config):
            cx = lane_centers[li]
            cy_positions = [120, 260, 380, 480]  # 4 条带垂直位置
            cy = cy_positions[li]
            _add_gaussian_band(img, cy, cx - lane_width, cx + lane_width, 14, intensity)
        img_uint8 = np.clip(img * 255, 0, 255).astype(np.uint8)
        path = OUT / "wb" / f"wb_{group}.png"
        cv2.imwrite(str(path), img_uint8)
        print(f"  [WB] {path.name} — 4 lanes × 4 bands")


# ============================================================
# 5. qPCR — Ct 值数据 (Excel)
# ============================================================
def gen_qpcr():
    """生成 qPCR Ct 值数据"""
    genes = ["Bax", "Bcl-2", "Caspase-3", "p53", "Cyclin D1", "GAPDH"]
    groups = ["Control", "Drug 5μM", "Drug 10μM", "Drug 20μM"]
    # 预设 fold change (相对 Control)
    fc_map = {
        "Bax":       [1.0, 1.5, 2.3, 3.1],
        "Bcl-2":     [1.0, 0.75, 0.35, 0.18],
        "Caspase-3": [1.0, 1.8, 2.5, 3.8],
        "p53":       [1.0, 1.3, 1.9, 2.6],
        "Cyclin D1": [1.0, 0.85, 0.55, 0.28],
        "GAPDH":     [1.0, 1.0, 1.0, 1.0],
    }
    gapdh_ct = 22.3  # GAPDH base Ct
    records = []
    for gi, gene in enumerate(genes):
        for grpi, group in enumerate(groups):
            fc = fc_map[gene][grpi]
            # target_ct = gapdh_ct - log2(fc)
            target_ct = gapdh_ct - np.log2(max(fc, 0.01))
            for rep in range(3):
                ct = target_ct + np.random.normal(0, 0.15)
                records.append({
                    "gene": gene, "group": group,
                    "Ct": round(ct, 3), "replicate": rep + 1,
                })
    df = pd.DataFrame(records)
    df.to_excel(OUT / "qpcr" / "qpcr_ct_values.xlsx", index=False)
    print(f"  [qPCR] qpcr_ct_values.xlsx — {len(df)} rows, {len(genes)} genes × {len(groups)} groups")


# ============================================================
# 6. IHC — DAB 染色图像
# ============================================================
def gen_ihc():
    """生成模拟 IHC 染色图像（苏木精蓝紫 + DAB 棕色阳性区域）"""
    configs = [
        ("Normal",       15, 40),
        ("Normal",       20, 50),
        ("Tumor_Grade1", 40, 140),
        ("Tumor_Grade1", 45, 165),
        ("Tumor_Grade2", 60, 220),
        ("Tumor_Grade2", 70, 270),
    ]
    for i, (label, pos_pct, hscore) in enumerate(configs):
        h, w = 400, 400
        # 苏木精背景（蓝紫色）
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:, :, 0] = np.random.randint(160, 200, (h, w))  # B
        img[:, :, 1] = np.random.randint(140, 175, (h, w))  # G
        img[:, :, 2] = np.random.randint(160, 200, (h, w))  # R
        # DAB 阳性区域（棕黄色斑块）
        n_spots = int(pos_pct * 3)
        for _ in range(n_spots):
            cy, cx = np.random.randint(30, h - 30), np.random.randint(30, w - 30)
            r = np.random.randint(15, 40)
            yy, xx = np.ogrid[:h, :w]
            mask = (yy - cy) ** 2 + (xx - cx) ** 2 <= r ** 2
            intensity = np.random.randint(0.3, 1.0)
            img[mask, 0] = np.clip(img[mask, 0] * (1 - intensity * 0.6), 0, 255).astype(np.uint8)
            img[mask, 1] = np.clip(img[mask, 1] * (1 - intensity * 0.5), 0, 255).astype(np.uint8)
            img[mask, 2] = np.clip(img[mask, 2] * (1 - intensity * 0.3), 0, 255).astype(np.uint8)
        # 转换为 BGR (OpenCV)
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        path = OUT / "ihc" / f"ihc_{label}_Hscore{hscore}_FOV{i+1}.png"
        cv2.imwrite(str(path), img_bgr)
        print(f"  [IHC] {path.name} — ~{pos_pct}% positive, H-Score ~{hscore}")


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    print("Generating test data for Module 2...\n")
    gen_cck8()
    print()
    gen_edu()
    print()
    gen_colony()
    print()
    gen_wb()
    print()
    gen_qpcr()
    print()
    gen_ihc()
    print(f"\nDone! All data saved to {OUT.resolve()}")
    print(f"  cck8/    — 2 Excel files")
    print(f"  edu/     — 6 fluorescence images")
    print(f"  colony/  — 6 crystal violet images")
    print(f"  wb/      — 3 blot images")
    print(f"  qpcr/    — 1 Excel file")
    print(f"  ihc/     — 6 IHC images")
