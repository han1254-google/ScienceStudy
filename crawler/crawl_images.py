"""
 — 
PubMed Central (PMC)Open-iFigshare 
"""
import os
import time
import json
import hashlib
import requests
from pathlib import Path
from urllib.parse import quote, urljoin
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = Path(__file__).parent
IMAGE_DIR = BASE_DIR / "test_images"
os.makedirs(IMAGE_DIR / "cck8", exist_ok=True)
os.makedirs(IMAGE_DIR / "edu", exist_ok=True)
os.makedirs(IMAGE_DIR / "colony", exist_ok=True)
os.makedirs(IMAGE_DIR / "wb", exist_ok=True)
os.makedirs(IMAGE_DIR / "qpcr", exist_ok=True)
os.makedirs(IMAGE_DIR / "ihc", exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "ScienceStudy-ImageCrawler/1.0 (research tool; mailto:research@example.com)",
    "Accept": "application/json, text/plain, */*",
})

# ============================================================
# 1. PubMed Central (PMC) Open Access 
# ============================================================

def search_pmc_ids(query: str, max_results: int = 20) -> list[dict]:
    """ PMC """
    base_url = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
    #  E-utilities  PMC
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pmc",
        "term": f'"{query}" AND open+access[filter]',
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance",
    }
    try:
        resp = SESSION.get(search_url, params=params, timeout=30)
        data = resp.json()
        ids = data.get("esearchresult", {}).get("idlist", [])
        articles = []
        for pmcid in ids:
            articles.append({"pmcid": pmcid, "source": "PMC"})
        print(f"  [PMC]  '{query}' ->  {len(articles)} ")
        return articles
    except Exception as e:
        print(f"  [PMC] : {e}")
        return []


def download_pmc_figures(pmcid: str, save_dir: Path) -> int:
    """ PMC """
    #  PMC API 
    # PMC  URL : https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{id}/bin/{filename}
    #  oa API  JATS XML graphic 
    oa_url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=PMC{pmcid}"
    count = 0
    try:
        resp = SESSION.get(oa_url, timeout=30)
        #  XML 
        text = resp.text
        # 
        import re
        # PMC : nlm-xxx, f1, fig1, etc.
        # 
        for i in range(1, 11):  #  10 
            for ext in [".jpg", ".png", ".gif"]:
                #  URL 
                base = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}"
                urls = [
                    f"{base}/bin/nlm{i:04d}{ext}",
                    f"{base}/bin/f{i}{ext}",
                    f"{base}/bin/fig{i}{ext}",
                    f"{base}/bin/Figure{i}{ext}",
                ]
                for url in urls:
                    try:
                        img_resp = SESSION.get(url, timeout=15, stream=True)
                        if img_resp.status_code == 200 and len(img_resp.content) > 1000:
                            filename = f"PMC{pmcid}_{i}{ext}"
                            filepath = save_dir / filename
                            with open(filepath, "wb") as f:
                                f.write(img_resp.content)
                            count += 1
                            print(f"     {filename} ({len(img_resp.content)//1024} KB)")
                            break  # 
                    except Exception:
                        continue
    except Exception as e:
        print(f"     PMC{pmcid} : {e}")
    return count


# ============================================================
# 2. Open-i (NIH ) 
# ============================================================

def search_openi_images(query: str, max_results: int = 10) -> list[dict]:
    """
     Open-i (NIH) 
    Open-i  CCK8/EdU/WB/IHC 
    """
    search_url = "https://openi.nlm.nih.gov/api/search"
    params = {
        "q": query,
        "m": 1,  # 
        "n": max_results,
    }
    results = []
    try:
        # Open-i API 
        url = f"{search_url}?query={quote(query)}&m=1&n={max_results}"
        resp = SESSION.get(url, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("list", []):
                img_url = f"https://openi.nlm.nih.gov/{item.get('imgLarge', '')}"
                if img_url:
                    results.append({
                        "url": img_url,
                        "title": item.get("title", ""),
                        "pmid": item.get("pmid", ""),
                        "source": "Open-i",
                    })
        print(f"  [Open-i]  '{query}' ->  {len(results)} ")
    except Exception as e:
        print(f"  [Open-i] : {e}")
    return results


def download_openi_image(item: dict, save_dir: Path) -> bool:
    """ Open-i """
    url = item["url"]
    if not url:
        return False
    try:
        resp = SESSION.get(url, timeout=30, stream=True)
        if resp.status_code == 200 and len(resp.content) > 5000:
            #  URL 
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            ext = ".jpg" if b"jpg" in resp.content[:100] else ".png"
            filepath = save_dir / f"openi_{url_hash}{ext}"
            with open(filepath, "wb") as f:
                f.write(resp.content)
            print(f"     openi_{url_hash}{ext} ({len(resp.content)//1024} KB)")
            return True
    except Exception as e:
        print(f"     : {e}")
    return False


# ============================================================
# 3.  (Google  —  API)
# ============================================================

# ============================================================
# 4.  ()
# ============================================================

# ============================================================
# 5. 
# ============================================================

# 
SEARCH_QUERIES = {
    "cck8": [
        "CCK8 cell viability assay",
        "CCK-8 proliferation curve",
        "dose response curve cell viability",
    ],
    "edu": [
        "EdU assay fluorescence microscopy",
        "EdU proliferation immunofluorescence",
        "EdU positive cells DAPI",
    ],
    "colony": [
        "colony formation assay crystal violet",
        "clonogenic assay 6-well plate",
        "colony formation cancer cells",
    ],
    "wb": [
        "western blot chemiluminescence",
        "western blot bands GAPDH",
        "western blot protein expression",
    ],
    "qpcr": [],  # qPCR 
    "ihc": [
        "immunohistochemistry DAB staining",
        "IHC immunohistochemistry tumor",
        "H-score IHC quantification",
    ],
}


def crawl_all(categories: Optional[list] = None, max_per_category: int = 10):
    """
    
    """
    if categories is None:
        categories = list(SEARCH_QUERIES.keys())

    print("=" * 60)
    print("  ")
    print("  : PubMed Central + Open-i (NIH)")
    print("=" * 60)

    total_downloaded = 0

    for category in categories:
        queries = SEARCH_QUERIES.get(category, [])
        if not queries:
            continue

        print(f"\n{'='*40}")
        print(f"   {category.upper()} — {IMAGE_DIR / category}")
        print(f"{'='*40}")

        cat_downloaded = 0

        for query in queries[:2]:  #  2 
            print(f"\n   : '{query}'")

            #  1: PMC 
            articles = search_pmc_ids(query, max_results=5)
            for article in articles[:3]:
                count = download_pmc_figures(article["pmcid"], IMAGE_DIR / category)
                cat_downloaded += count
                time.sleep(0.5)  # 

            #  2: Open-i 
            images = search_openi_images(query, max_results=5)
            for img in images[:3]:
                ok = download_openi_image(img, IMAGE_DIR / category)
                if ok:
                    cat_downloaded += 1
                time.sleep(0.5)

        print(f"\n   {category}  {cat_downloaded} ")
        total_downloaded += cat_downloaded

    print(f"\n{'='*60}")
    print(f"    {total_downloaded} ")
    print(f"   : {IMAGE_DIR}")
    print(f"{'='*60}")

    return total_downloaded


def crawl_category(category: str, max_results: int = 15):
    """"""
    queries = SEARCH_QUERIES.get(category, [category])
    save_dir = IMAGE_DIR / category
    downloaded = 0

    print(f"\n{'='*50}")
    print(f"   [{category}] ")
    print(f"{'='*50}")

    for query in queries[:3]:
        print(f"\n   '{query}'")

        # PMC
        articles = search_pmc_ids(query, max_results=5)
        for article in articles[:3]:
            n = download_pmc_figures(article["pmcid"], save_dir)
            downloaded += n
            time.sleep(0.3)

        # Open-i
        images = search_openi_images(query, max_results=5)
        for img in images[:3]:
            if download_openi_image(img, save_dir):
                downloaded += 1
            time.sleep(0.3)

        if downloaded >= max_results:
            break

    print(f"\n   [{category}]  —  {downloaded}  -> {save_dir}")
    return downloaded


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # 
        category = sys.argv[1]
        crawl_category(category)
    else:
        # 
        crawl_all(max_per_category=10)
