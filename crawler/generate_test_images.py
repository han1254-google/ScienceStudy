"""
 — 
 CCK8 / EdU /  / WB / qPCR / IHC 
"""
import os
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import openpyxl
from openpyxl.utils import get_column_letter
from scipy.ndimage import gaussian_filter
from scipy.interpolate import interp1d

BASE_DIR = Path(__file__).parent
IMAGE_DIR = BASE_DIR / "test_images"

# 
for cat in ["cck8", "edu", "colony", "wb", "qpcr", "ihc"]:
    os.makedirs(IMAGE_DIR / cat, exist_ok=True)

# ============================================================
# 1. CCK8 —  Excel  + 
# ============================================================

def generate_cck8_data():
    """
     CCK8 OD  (Excel )
     OD450 
    """
    print("\n  CCK8 ...")

    # 
    concentrations = [0, 2.5, 5, 10, 20, 40, 80]  # μM
    time_points = [24, 48, 72]  # 
    replicates = 3

    wb = openpyxl.Workbook()

    # ---- Sheet 1:  OD  ----
    ws1 = wb.active
    ws1.title = "OD"
    ws1.append([" (μM)", " (h)", "1", "2", "3"])

    np.random.seed(42)
    for conc in concentrations:
        for t in time_points:
            #  OD 
            base_od = 2.0 / (1 + (conc / 15)**1.2)  # -
            time_factor = 1 - (t - 24) / 200  # 
            base_od *= time_factor
            # 
            ods = base_od + np.random.normal(0, 0.03, replicates)
            ods = np.clip(ods, 0.05, 2.5)
            ws1.append([conc, t] + [round(v, 4) for v in ods])

    # ---- Sheet 2:  ----
    ws2 = wb.create_sheet("")
    ws2.append([" (μM)", " (h)", "(%)", "SD(%)", "SEM(%)", "P"])

    for conc in concentrations:
        for t in time_points:
            base_viability = 100 / (1 + (conc / 18)**1.5)  # IC50 ~18μM
            noise = np.random.normal(0, 3)
            viability = np.clip(base_viability + noise, 0, 105)
            sem = 2 + np.random.normal(0, 0.5)
            p_value = abs(np.random.normal(0, 0.1)) if conc > 0 else 1.0
            p_str = f"{p_value:.4f}" if conc > 0 else "-"
            ws2.append([
                conc, t,
                round(viability, 1),
                round(sem * 1.5, 1),
                round(sem, 1),
                p_str,
            ])

    # ---- Sheet 3: IC50  ----
    ws3 = wb.create_sheet("IC50")
    ws3.append([" (h)", "IC50 (μM)", "R²", "95%CI ", "95%CI "])
    for t in time_points:
        ws3.append([
            t,
            round(18 + np.random.normal(0, 1.5), 2),
            round(0.98 + np.random.normal(0, 0.01), 4),
            round(15 + np.random.normal(0, 2), 2),
            round(21 + np.random.normal(0, 2), 2),
        ])

    filepath = IMAGE_DIR / "cck8" / "cck8_test_data.xlsx"
    wb.save(filepath)
    print(f"   {filepath}")


# ============================================================
# 2. EdU —  (DAPI  + EdU /)
# ============================================================

def add_cell_nucleus(draw, cx, cy, radius, color, intensity=200):
    """"""
    for r in range(radius, 0, -1):
        alpha = int(intensity * (1 - r / radius) * 0.8 + intensity * 0.2)
        # 
        for angle in np.linspace(0, 2*np.pi, max(8, radius*4)):
            dx = int(r * 0.85 * np.cos(angle) + np.random.randint(-1, 2))
            dy = int(r * 0.85 * np.sin(angle) + np.random.randint(-1, 2))
            x, y = cx + dx, cy + dy
            try:
                draw.point((x, y), fill=(*color, alpha))
            except (IndexError, TypeError):
                pass


def generate_edu_images(n_images: int = 6):
    """
     EdU 
    DAPI+ EdU
     EdU 
    """
    print("\n  EdU ...")

    np.random.seed(123)
    for idx in range(n_images):
        w, h = 1024, 1024

        # DAPI 
        dapi_img = Image.new("RGBA", (w, h), (0, 0, 0, 255))
        dapi_draw = ImageDraw.Draw(dapi_img)

        # EdU 
        edu_img = Image.new("RGBA", (w, h), (0, 0, 0, 255))
        edu_draw = ImageDraw.Draw(edu_img)

        #  vs 
        group_ratios = [0.55, 0.45, 0.30, 0.20, 0.12, 0.05]  #  EdU 
        edu_ratio = group_ratios[idx % len(group_ratios)]

        # 
        n_cells = 150 + np.random.randint(-20, 20)
        placed = []
        max_attempts = n_cells * 3
        attempts = 0

        while len(placed) < n_cells and attempts < max_attempts:
            cx = np.random.randint(50, w - 50)
            cy = np.random.randint(50, h - 50)
            radius = np.random.randint(8, 22)

            # 
            overlap = False
            for px, py, pr in placed:
                if np.sqrt((cx - px)**2 + (cy - py)**2) < (radius + pr + 3):
                    overlap = True
                    break

            if not overlap:
                placed.append((cx, cy, radius))
                # DAPI 
                add_cell_nucleus(dapi_draw, cx, cy, radius, (30, 60, 220), intensity=220)

                # EdU 
                is_positive = np.random.random() < edu_ratio
                if is_positive:
                    add_cell_nucleus(edu_draw, cx, cy, radius, (30, 220, 60), intensity=200)
            attempts += 1

        # 
        for _ in range(500):
            nx, ny = np.random.randint(0, w), np.random.randint(0, h)
            noise_val = np.random.randint(0, 20)
            dapi_draw.point((nx, ny), fill=(noise_val, noise_val, noise_val + 10, 30))
            edu_draw.point((nx, ny), fill=(noise_val, noise_val, noise_val, 30))

        # 
        merged = Image.new("RGBA", (w, h), (0, 0, 0, 255))
        merged = Image.alpha_composite(merged, dapi_img)
        merged = Image.alpha_composite(merged, edu_img)

        #  RGB 
        group_name = f"{'Control' if idx < 2 else f'Treatment_{(idx-1)*10}uM'}"
        filename = f"edu_{group_name}_ratio{edu_ratio:.0%}.png"

        merged_rgb = Image.new("RGB", (w, h), (0, 0, 0))
        merged_rgb.paste(merged, (0, 0), merged)

        merged_rgb.save(IMAGE_DIR / "edu" / filename)
        print(f"   edu/{filename}  ({len(placed)} , EdU+ = {edu_ratio:.0%})")

    print(f"  ->  {n_images}  EdU ")


# ============================================================
# 3.  — 
# ============================================================

def generate_colony_images(n_images: int = 6):
    """
    
     6 
    """
    print("\n ...")

    np.random.seed(456)
    colony_counts = [85, 62, 40, 25, 15, 8]  # 

    for idx in range(n_images):
        w, h = 800, 800
        # 
        bg_color = (235, 230, 225)
        img = Image.new("RGB", (w, h), bg_color)
        draw = ImageDraw.Draw(img)

        # /
        center_x, center_y = w // 2, h // 2
        radius = 340
        for angle in range(0, 360, 2):
            for r_offset in [-1, 0, 1]:
                x = int(center_x + (radius + r_offset) * np.cos(np.radians(angle)))
                y = int(center_y + (radius + r_offset) * np.sin(np.radians(angle)))
                try:
                    draw.point((x, y), fill=(180, 175, 170))
                except (IndexError, TypeError):
                    pass

        # 
        n_colonies = colony_counts[idx % len(colony_counts)]
        placed = []

        for _ in range(n_colonies):
            # 
            r = np.random.exponential(radius * 0.25)
            theta = np.random.uniform(0, 2 * np.pi)
            cx = int(center_x + r * np.cos(theta))
            cy = int(center_y + r * np.sin(theta))
            # 
            if np.sqrt((cx - center_x)**2 + (cy - center_y)**2) > radius - 50:
                continue

            # 
            colony_radius = int(np.random.gamma(2, 3) + 3)  # 3-15 

            # 
            for pr in range(colony_radius, 0, -1):
                # 
                purple = int(80 + (colony_radius - pr) * 30)
                color = (
                    min(255, purple + 30),
                    min(255, purple - 20),
                    min(255, purple + 40),
                )
                for angle in np.linspace(0, 2*np.pi, max(4, pr*3)):
                    px = int(cx + pr * np.cos(angle) + np.random.randint(-1, 2))
                    py = int(cy + pr * np.sin(angle) + np.random.randint(-1, 2))
                    if 0 <= px < w and 0 <= py < h:
                        try:
                            draw.point((px, py), fill=color)
                        except (IndexError, TypeError):
                            pass

            placed.append((cx, cy, colony_radius))

        # 
        for _ in range(2000):
            bx = np.random.randint(0, w)
            by = np.random.randint(0, h)
            noise = np.random.randint(-8, 8)
            base_pixel = img.getpixel((bx, by))
            try:
                draw.point((bx, by), fill=tuple(
                    min(255, max(0, v + noise)) for v in base_pixel
                ))
            except (IndexError, TypeError):
                pass

        group_name = f"{'Control' if idx < 2 else f'Drug_{(idx-1)*5}uM'}"
        filename = f"colony_{group_name}_n{n_colonies}.png"
        img.save(IMAGE_DIR / "colony" / filename)
        print(f"   colony/{filename}  ({n_colonies} )")

    print(f"  ->  {n_images} ")


# ============================================================
# 4. WB — 
# ============================================================

def generate_wb_images(n_images: int = 4):
    """
     Western Blot 
    
    """
    print("\n  WB ...")

    np.random.seed(789)
    proteins = ["Bax (21kDa)", "Bcl-2 (26kDa)", "Cleaved Caspase-3 (17kDa)", "GAPDH (37kDa)"]

    for idx, protein in enumerate(proteins):
        w, h = 900, 400
        # 
        img = Image.new("RGB", (w, h), (5, 5, 10))
        draw = ImageDraw.Draw(img)

        # 
        n_lanes = 6
        lane_width = w // (n_lanes + 1)

        # 
        if "Bax" in protein:
            trends = [0.3, 0.6, 0.9, 1.2, 1.5, 1.8]  # 
        elif "Bcl-2" in protein:
            trends = [1.8, 1.5, 1.2, 0.9, 0.6, 0.3]  # 
        elif "Caspase" in protein:
            trends = [0.2, 0.4, 0.7, 1.0, 1.4, 1.8]  # 
        else:
            trends = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]  # 

        band_positions = [h // 2]  # 

        # 
        lane_labels = ["Control", "2.5μM", "5μM", "10μM", "20μM", "40μM"]

        for lane in range(n_lanes):
            x_center = int((lane + 1) * lane_width)

            # 
            for y in range(50, h - 50):
                texture = np.random.randint(-3, 3)
                for dx in range(-lane_width//4, lane_width//4):
                    px = x_center + dx
                    if 0 <= px < w:
                        try:
                            current = img.getpixel((px, y))
                            new_val = min(25, max(0, current[0] + texture))
                            draw.point((px, y), fill=(new_val, new_val, new_val + 3))
                        except (IndexError, TypeError):
                            pass

            # 
            for band_pos in band_positions:
                intensity = trends[lane]
                band_h = int(8 + intensity * 5)  # 
                band_w = int(lane_width * 0.45)

                for by in range(band_pos - band_h, band_pos + band_h):
                    for bx in range(x_center - band_w, x_center + band_w):
                        # 
                        dx = (bx - x_center) / band_w
                        dy = (by - band_pos) / band_h
                        profile = np.exp(-(dx**2 * 2 + dy**2 * 3))
                        brightness = int(profile * intensity * 220 + np.random.randint(-10, 10))
                        brightness = min(255, max(0, brightness))
                        if 0 <= bx < w and 0 <= by < h:
                            try:
                                draw.point((bx, by), fill=(brightness, brightness, brightness))
                            except (IndexError, TypeError):
                                pass

        #  draw 
        protein_short = protein.split(" ")[0]
        draw.text((10, band_positions[0] - 20), protein_short, fill=(150, 150, 150))

        filename = f"wb_{protein.replace(' ', '_').replace('(', '').replace(')', '')}.png"
        img.save(IMAGE_DIR / "wb" / filename)
        print(f"   wb/{filename}")

    print(f"  ->  {n_images}  WB ")


# ============================================================
# 5. qPCR —  Ct 
# ============================================================

def generate_qpcr_data():
    """
     qPCR Ct  (Excel)
     Ct ΔΔCt 
    """
    print("\n  qPCR ...")

    np.random.seed(321)
    genes = ["Bax", "Bcl-2", "Caspase-3", "Cyclin D1", "c-Myc", "p53"]
    housekeeping = "GAPDH"
    groups = ["Control", "5μM", "10μM", "20μM"]
    replicates = 3

    # 
    fold_changes = {
        "Bax": [1.0, 1.4, 2.1, 3.2],
        "Bcl-2": [1.0, 0.75, 0.5, 0.3],
        "Caspase-3": [1.0, 1.3, 2.0, 2.8],
        "Cyclin D1": [1.0, 0.8, 0.55, 0.35],
        "c-Myc": [1.0, 0.7, 0.45, 0.25],
        "p53": [1.0, 1.2, 1.6, 2.2],
    }

    wb = openpyxl.Workbook()

    # ---- Sheet 1:  Ct  ----
    ws1 = wb.active
    ws1.title = "Ct"
    ws1.append(["", "", "", "Ct"])

    for gene in genes + [housekeeping]:
        for gi, group in enumerate(groups):
            fc = fold_changes.get(gene, [1.0]*len(groups))[gi]
            #  Ct  Ct ~22-28ΔCt  fold change
            base_ct = 24 + np.random.normal(0, 0.3)
            delta_ct = -np.log2(fc)  # fold change -> ΔΔCt
            for rep in range(replicates):
                ct = base_ct + delta_ct + np.random.normal(0, 0.15)
                ws1.append([gene, group, rep + 1, round(ct, 3)])

    # GAPDH  Ct
    for group in groups:
        for rep in range(replicates):
            ct = 20.5 + np.random.normal(0, 0.1)
            ws1.append([housekeeping, group, rep + 1, round(ct, 3)])

    # ---- Sheet 2:  ----
    ws2 = wb.create_sheet("")
    ws2.append(["", "", "2^(-ΔΔCt)", "SD", "SEM", "P"])

    for gene in genes:
        fc_list = fold_changes.get(gene, [1.0]*len(groups))
        for gi, group in enumerate(groups):
            fc = fc_list[gi]
            sem = 0.1 + abs(np.random.normal(0, 0.05))
            p_value = abs(np.random.normal(0, 0.05)) if gi > 0 else 1.0
            p_str = f"{p_value:.4f}" if gi > 0 else "-"
            ws2.append([
                gene, group,
                round(fc + np.random.normal(0, 0.05), 3),
                round(sem * 3, 3),
                round(sem, 3),
                p_str,
            ])

    filepath = IMAGE_DIR / "qpcr" / "qpcr_test_data.xlsx"
    wb.save(filepath)
    print(f"   {filepath}")


# ============================================================
# 6. IHC —  DAB 
# ============================================================

def generate_ihc_images(n_images: int = 6):
    """
     IHC 
    DAB ()  +  () 
    """
    print("\n  IHC ...")

    np.random.seed(654)
    hscore_values = [40, 85, 135, 190, 240, 290]  #  H-Score

    for idx in range(n_images):
        w, h = 1024, 768
        img = Image.new("RGB", (w, h), (248, 244, 240))
        draw = ImageDraw.Draw(img)

        hscore = hscore_values[idx % len(hscore_values)]
        positive_ratio = hscore / 300 * 0.8  # 

        # 
        n_tissue_regions = 50 + np.random.randint(-10, 10)

        for _ in range(n_tissue_regions):
            # 
            cx = np.random.randint(50, w - 50)
            cy = np.random.randint(50, h - 50)
            region_radius = np.random.randint(20, 80)

            #  DAB 
            is_positive = np.random.random() < positive_ratio

            for rr in range(region_radius):
                n_points = int(rr * 2.5) + 3
                for _ in range(n_points):
                    angle = np.random.uniform(0, 2 * np.pi)
                    r_var = rr * np.sqrt(np.random.random())  # 
                    px = int(cx + r_var * np.cos(angle))
                    py = int(cy + r_var * np.sin(angle))

                    if 0 <= px < w and 0 <= py < h:
                        if is_positive:
                            # DAB 
                            # 
                            intensity_strength = np.random.random()
                            r = int(140 + intensity_strength * 80)
                            g = int(80 + intensity_strength * 50)
                            b = int(30 + intensity_strength * 40)
                            color = (r, g, b)
                        else:
                            # 
                            r = int(140 + np.random.randint(-15, 15))
                            g = int(120 + np.random.randint(-15, 15))
                            b = int(170 + np.random.randint(-15, 15))
                            color = (r, g, b)

                        try:
                            draw.point((px, py), fill=color)
                        except (IndexError, TypeError):
                            pass

        # 
        for _ in range(5000):
            ix = np.random.randint(0, w)
            iy = np.random.randint(0, h)
            current = img.getpixel((ix, iy))
            # 
            if sum(current) > 500:  # /
                stroma = (220 + np.random.randint(-10, 10),
                          200 + np.random.randint(-10, 10),
                          195 + np.random.randint(-10, 10))
                try:
                    draw.point((ix, iy), fill=stroma)
                except (IndexError, TypeError):
                    pass

        # 
        scale_y = h - 30
        draw.line([(50, scale_y), (150, scale_y)], fill=(0, 0, 0), width=2)
        draw.text((55, scale_y - 18), "100 μm", fill=(0, 0, 0))

        group_name = f"{'Normal' if idx < 2 else f'Tumor_Grade_{idx//2}'}"
        filename = f"ihc_{group_name}_Hscore{hscore}.png"
        img.save(IMAGE_DIR / "ihc" / filename)
        print(f"   ihc/{filename}  ( H-Score ≈ {hscore})")

    print(f"  ->  {n_images}  IHC ")


# ============================================================
# 7. 
# ============================================================

def generate_manifest():
    """"""
    manifest = {
        "description": "ScienceStudy ",
        "categories": {},
    }

    for cat in ["cck8", "edu", "colony", "wb", "qpcr", "ihc"]:
        cat_dir = IMAGE_DIR / cat
        files = list(cat_dir.glob("*")) if cat_dir.exists() else []
        manifest["categories"][cat] = {
            "count": len(files),
            "files": [str(f.name) for f in files],
        }

    manifest_path = IMAGE_DIR / "manifest.json"
    import json
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"\n : {manifest_path}")


# ============================================================
# 
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  ")
    print("   CCK8 | EdU |  | WB | qPCR | IHC ")
    print("=" * 60)

    generate_cck8_data()
    generate_edu_images(6)
    generate_colony_images(6)
    generate_wb_images(4)
    generate_qpcr_data()
    generate_ihc_images(6)
    generate_manifest()

    print("\n" + "=" * 60)
    print("   !")
    print(f"   {IMAGE_DIR}")
    print("=" * 60)
