"""
PMC Open Access 真实实验图像爬虫
通过 PubMed Central OA API 下载开放获取论文的全部图片
"""
import os, sys, time, io, re, tarfile, tempfile
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional as Opt, List

BASE_DIR = Path(__file__).parent
IMAGE_DIR = BASE_DIR / "test_images"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "ScienceStudy-Crawler/1.0 (research@example.com)",
})

# 搜索关键词 -> 保存目录
QUERIES = {
    "cck8": ['"cell viability" CCK-8 assay', '"dose response" cell proliferation', '"CCK8" cancer'],
    "edu": ['"EdU" proliferation immunofluorescence', '"EdU assay" DAPI cells', '"EdU positive" cancer cells'],
    "colony": ['"colony formation" crystal violet', '"clonogenic assay" cancer', '"colony formation assay" plate'],
    "wb": ['"western blot" GAPDH chemiluminescence', '"western blot" protein expression cancer', '"western blot" apoptosis'],
    "ihc": ['"immunohistochemistry" DAB staining tumor', '"IHC" H-score quantification', '"immunohistochemical staining" cancer'],
}


def search_pmc(query: str, max_results: int = 10) -> List[str]:
    """搜索 PMC 开放获取文章，返回 PMC ID 列表"""
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pmc",
        "term": f'{query} AND open+access[filter]',
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance",
    }
    try:
        r = SESSION.get(url, params=params, timeout=20)
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        return ids
    except Exception as e:
        print(f"    search error: {e}")
        return []


def get_oa_package_url(pmcid: str) -> Opt[str]:
    """获取 OA TGZ 包下载链接"""
    url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=PMC{pmcid}"
    try:
        r = SESSION.get(url, timeout=20)
        root = ET.fromstring(r.text)
        for record in root.iter("record"):
            for link in record.iter("link"):
                if link.get("format") == "tgz":
                    href = link.get("href", "")
                    # 替换 FTP 为 HTTPS
                    href = href.replace("ftp://ftp.ncbi.nlm.nih.gov", "https://ftp.ncbi.nlm.nih.gov")
                    return href
    except Exception as e:
        print(f"    OA API error for PMC{pmcid}: {e}")
    return None


def download_and_extract_images(pmcid: str, tgz_url: str, save_dir: Path) -> int:
    """下载 TGZ 包并提取图片"""
    count = 0
    try:
        # 1. 下载 TGZ
        print(f"      downloading {pmcid}...")
        r = SESSION.get(tgz_url, timeout=120, stream=True)
        if r.status_code != 200:
            print(f"      download failed: {r.status_code}")
            return 0

        tgz_data = io.BytesIO(r.content)
        size_mb = len(r.content) // (1024 * 1024)
        print(f"      package {size_mb} MB, extracting...")

        # 2. 解压并提取图片
        with tarfile.open(fileobj=tgz_data, mode="r:gz") as tar:
            for member in tar.getmembers():
                name = member.name.lower()
                # 只提取图片文件
                if any(name.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.tif', '.tiff']):
                    try:
                        f = tar.extractfile(member)
                        if f:
                            data = f.read()
                            # 跳过太小的图（图标/logo）和太大的（可能是原始数据）
                            if 5000 < len(data) < 10 * 1024 * 1024:
                                # 用原始文件名保存
                                fname = Path(member.name).name
                                out_path = save_dir / f"PMC{pmcid}_{fname}"
                                with open(out_path, "wb") as fw:
                                    fw.write(data)
                                count += 1
                    except Exception:
                        pass

        print(f"      extracted {count} images")
    except Exception as e:
        print(f"      error: {e}")

    return count


def run(categories: Opt[List[str]] = None, articles_per_query: int = 5):
    """主爬虫流程"""
    if categories is None:
        categories = list(QUERIES.keys())

    print("=" * 60)
    print("  PMC Open Access Image Crawler")
    print("  Downloading real published experiment figures")
    print("=" * 60)

    total = 0

    for cat in categories:
        queries = QUERIES.get(cat, [])
        save_dir = IMAGE_DIR / cat
        os.makedirs(save_dir, exist_ok=True)

        print(f"\n---[{cat.upper()}]---")
        cat_count = 0
        seen_pmcids = set()

        for query in queries[:2]:
            print(f"  query: '{query}'")
            pmcids = search_pmc(query, max_results=articles_per_query)
            print(f"    found {len(pmcids)} articles")

            for pmcid in pmcids:
                if pmcid in seen_pmcids:
                    continue
                seen_pmcids.add(pmcid)

                tgz_url = get_oa_package_url(pmcid)
                if not tgz_url:
                    continue

                n = download_and_extract_images(pmcid, tgz_url, save_dir)
                cat_count += n
                total += n
                time.sleep(2)  # 礼貌间隔，避免被限制

                if cat_count >= 30:
                    break

            if cat_count >= 30:
                break

        print(f"  [{cat}] total: {cat_count} images")

    print(f"\n{'=' * 60}")
    print(f"  Done! Total: {total} images")
    print(f"  Saved to: {IMAGE_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    cats = sys.argv[1:] if len(sys.argv) > 1 else None
    run(categories=cats)
