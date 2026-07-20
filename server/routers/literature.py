"""
Module 1（实验思路设计）API 路由 — 多数据源论文检索 + 上传 + 知识库 + 方案生成
日志记录到 server/logs/app.log
"""
import os, uuid, logging, json, time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from services.knowledge_base import get_kb
from services.pdf_processor import PDFProcessor
from services.experiment_designer import ExperimentDesigner

# ---- 文件日志 ----
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
_fh = RotatingFileHandler(LOG_DIR / "app.log", maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
_root = logging.getLogger()
_root.handlers.clear()
_root.addHandler(_fh)
_root.setLevel(logging.INFO)
for lib in ["jieba", "httpx", "chromadb", "uvicorn.access"]:
    logging.getLogger(lib).setLevel(logging.WARNING)

log = logging.getLogger("API")
router = APIRouter()
DOWNLOAD_DIR = Path("./data/downloadPapers")

# ---- 模型 ----

class CrawlRequest(BaseModel):
    query: str
    max_results: int = 20
    date_range: str = "all"
    sources: List[str] = ["pubmed"]

class SearchRequest(BaseModel):
    query: str = ""
    top_k: int = 10
    full_text_only: bool = True
    year_from: Optional[int] = None
    year_to: Optional[int] = None

class DesignRequest(BaseModel):
    description: str


# ============================================================
# 多数据源检索
# ============================================================

def _search_pubmed(query: str, max_results: int, date_range: str) -> dict:
    import requests as rq
    t0 = time.time()
    # 精准匹配：短语加引号 + 各词 AND
    words = query.split()
    pubmed_query = f'"{query}" AND ' + " AND ".join(words) if len(words) > 1 else query
    log.info(f"[PubMed] search: '{pubmed_query[:60]}' max={max_results}")
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {"db": "pubmed", "term": pubmed_query, "retmax": max_results, "retmode": "json", "sort": "relevance"}
    if date_range == "5y": params["mindate"], params["datetype"] = "2021/01/01", "pdat"
    elif date_range == "3y": params["mindate"], params["datetype"] = "2023/01/01", "pdat"
    elif date_range == "1y": params["mindate"], params["datetype"] = "2025/01/01", "pdat"

    r = rq.get(url, params=params, timeout=20)
    data = r.json()
    ids = data.get("esearchresult", {}).get("idlist", [])
    total = int(data.get("esearchresult", {}).get("count", 0))
    log.info(f"[PubMed] found {total}, got {len(ids)} IDs ({time.time()-t0:.1f}s)")
    papers = []
    if ids:
        t1 = time.time()
        for attempt in range(3):
            try:
                fr = rq.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                             params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"}, timeout=20)
                fd = fr.json()
                for pmid in ids:
                    info = fd.get("result", {}).get(pmid, {})
                    papers.append({"source": "PubMed", "id": pmid, "title": info.get("title", ""),
                        "authors": ", ".join([a.get("name", "") for a in info.get("authors", [])[:5]]),
                        "year": int(info.get("pubdate", "2020").split(" ")[0]) if info.get("pubdate") else 0,
                        "journal": info.get("source", ""),
                        "doi": info.get("elocationid", "").replace("doi: ", "") if info.get("elocationid") else "",
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"})
                break
            except Exception as e:
                if attempt < 2: log.warning(f"[PubMed] retry {attempt+1}/3: {type(e).__name__}"); time.sleep(1)
                else: raise
        log.info(f"[PubMed] metadata fetched {len(papers)} papers ({time.time()-t1:.1f}s)")
    return {"total": total, "papers": papers}


def _search_arxiv(query: str, max_results: int) -> dict:
    import requests as rq
    import xml.etree.ElementTree as ET
    t0 = time.time()
    log.info(f"[arXiv] search: '{query[:60]}'")
    try:
        # arXiv API: 搜标题（与官网结果最接近），按提交日期降序
        arxiv_query = " AND ".join([f"ti:{w}" for w in query.split()])
        r = rq.get("http://export.arxiv.org/api/query",
                   params={"search_query": arxiv_query, "max_results": max_results, "sortBy": "submittedDate", "sortOrder": "descending"}, timeout=20)
        root = ET.fromstring(r.text)
        ns = "{http://www.w3.org/2005/Atom}"
        papers = []
        for entry in root.findall(f"{ns}entry"):
            title_el = entry.find(f"{ns}title")
            id_el = entry.find(f"{ns}id")
            pub_el = entry.find(f"{ns}published")
            papers.append({"source": "arXiv", "id": id_el.text.split("/")[-1].replace("v", "") if id_el is not None else "",
                "title": title_el.text.strip().replace("\n", " ") if title_el is not None else "",
                "authors": ", ".join([a.find(f"{ns}name").text for a in entry.findall(f"{ns}author") if a.find(f"{ns}name") is not None]),
                "year": int(pub_el.text[:4]) if pub_el is not None else 0,
                "journal": "arXiv", "doi": "", "url": id_el.text if id_el is not None else ""})
        log.info(f"[arXiv] done {len(papers)} papers ({time.time()-t0:.1f}s)")
        return {"total": len(papers), "papers": papers[:max_results]}
    except Exception as e:
        log.warning(f"[arXiv] failed: {type(e).__name__}")
        return {"total": 0, "papers": []}


def _search_biorxiv(query: str, max_results: int) -> dict:
    import requests as rq
    t0 = time.time()
    log.info(f"[bioRxiv] search: '{query[:60]}'")
    try:
        r = rq.get(f"https://api.biorxiv.org/search/{query}/0", timeout=20)
        data = r.json()
        papers = []
        for item in data.get("collection", [])[:max_results]:
            papers.append({"source": "bioRxiv", "id": item.get("doi", ""),
                "title": item.get("title", ""), "authors": item.get("authors", ""),
                "year": int(item.get("date", "2020")[:4]) if item.get("date") else 0,
                "journal": "bioRxiv (Preprint)", "doi": item.get("doi", ""),
                "url": f"https://www.biorxiv.org/content/{item.get('doi', '')}" if item.get("doi") else ""})
        log.info(f"[bioRxiv] done {len(papers)} papers ({time.time()-t0:.1f}s)")
        return {"total": len(papers), "papers": papers}
    except Exception as e:
        log.warning(f"[bioRxiv] failed: {type(e).__name__}")
        return {"total": 0, "papers": []}


@router.post("/search-papers")
async def search_papers(req: CrawlRequest):
    t0 = time.time()
    log.info(f"[检索] query='{req.query[:60]}' sources={req.sources} max={req.max_results}")
    all_papers, total = [], 0
    for source in req.sources:
        t_src = time.time()
        if source == "pubmed": r = _search_pubmed(req.query, req.max_results, req.date_range)
        elif source == "arxiv": r = _search_arxiv(req.query, req.max_results)
        elif source == "biorxiv": r = _search_biorxiv(req.query, req.max_results)
        else: continue
        all_papers.extend(r["papers"]); total += r["total"]
        log.info(f"[检索] {source}: {len(r['papers'])} papers ({time.time()-t_src:.1f}s)")

    seen, unique = set(), []
    for p in all_papers:
        key = p["title"][:80].lower().strip()
        if key not in seen: seen.add(key); unique.append(p)
    log.info(f"[检索] done: {total} hits -> {len(unique)} unique ({time.time()-t0:.1f}s)")
    return {"query": req.query, "sources": req.sources, "total_found": total, "papers": unique[:req.max_results]}


@router.post("/pubmed-search")
async def pubmed_search(req: CrawlRequest):
    req.sources = ["pubmed"]
    return await search_papers(req)


# ============================================================
# 知识库
# ============================================================

@router.get("/kb/stats")
async def get_kb_stats():
    kb = get_kb()
    s = kb.get_stats()
    return {**s.__dict__, "papers": kb.list_papers()}

@router.get("/kb/papers")
async def list_papers():
    return {"papers": get_kb().list_papers()}

@router.delete("/kb/papers/{paper_id}")
async def delete_paper(paper_id: str):
    get_kb().delete_paper(paper_id)
    return {"success": True}

@router.post("/kb/rebuild")
async def rebuild_kb():
    get_kb().rebuild_index()
    return {"status": "done"}


# ============================================================
# PDF 上传 + 入库
# ============================================================

@router.post("/upload")
async def upload_papers(files: List[UploadFile] = File(...), topic: str = Form("")):
    t0 = time.time()
    kb, proc = get_kb(), PDFProcessor()
    log.info(f"[上传] {len(files)} files, topic='{topic or '(none)'}'")
    save_dir = DOWNLOAD_DIR / (topic or "manual_upload")
    uploaded, duplicates, paper_ids = 0, 0, []

    for file in files:
        safe_name = file.filename.replace(" ", "_")
        file_path = save_dir / safe_name
        content = await file.read()
        file_hash = __import__('hashlib').md5(content).hexdigest()[:12]

        is_dup = False
        for ep in kb.list_papers():
            if ep.get('paper_id', '').endswith(file_hash):
                duplicates += 1; log.info(f"[上传] dup: {file.filename}"); is_dup = True; break
        if is_dup: continue

        t_file = time.time()
        os.makedirs(save_dir, exist_ok=True)
        with open(file_path, "wb") as f: f.write(content)
        log.info(f"[上传] saved: {file.filename} ({len(content)/1024:.0f}KB)")

        try:
            meta = proc.extract_metadata(str(file_path))
            full_text, pages = proc.extract_full_text(str(file_path))
            pid = f"UP_{uuid.uuid4().hex[:8]}_{file_hash}"
            chunks = proc.chunk_paper(full_text, paper_id=pid,
                title=meta.title if meta else file.filename,
                authors=meta.authors if meta else "", year=0, journal="", source="full_text")
            log.info(f"[上传] text: {file.filename} {pages}p {len(full_text)}chars -> {len(chunks)} chunks")
        except Exception as e:
            log.warning(f"[上传] extract failed: {file.filename}: {e}")
            chunks = []

        if chunks:
            kb.add_paper(chunks[0].paper_id, chunks)
            uploaded += 1; paper_ids.append(chunks[0].paper_id)
            log.info(f"[上传] indexed: {chunks[0].paper_id} ({time.time()-t_file:.1f}s)")

    log.info(f"[上传] done: {uploaded} ok, {duplicates} dup ({time.time()-t0:.1f}s)")
    return {"uploaded": uploaded, "duplicates": duplicates, "paper_ids": paper_ids}


# ============================================================
# 检索 + 方案生成
# ============================================================

@router.post("/search")
async def search_kb(req: SearchRequest):
    t0 = time.time()
    log.info(f"[搜索] query='{req.query[:60]}' top_k={req.top_k}")
    results = get_kb().search(req.query, top_k=req.top_k, full_text_only=req.full_text_only,
                               year_from=req.year_from, year_to=req.year_to)
    items = []
    for r in results:
        c = r.chunk
        items.append({"score": r.score, "semantic_score": r.semantic_score, "bm25_score": r.bm25_score,
            "paper_id": c.paper_id, "paper_title": c.paper_title, "authors": c.authors,
            "year": c.year, "journal": c.journal, "section": c.section, "page": c.page,
            "text_snippet": c.text[:300], "source": c.source, "chunk_id": c.chunk_id})
    log.info(f"[搜索] done: {len(items)} results ({time.time()-t0:.1f}s)")
    return {"query": req.query, "results": items, "total": len(items)}


@router.post("/design")
async def design_experiment(req: DesignRequest):
    t0 = time.time()
    log.info(f"[方案] start: '{req.description[:80]}'")
    kb = get_kb()
    if kb.collection.count() == 0:
        log.warning("[方案] KB empty")
        return {"error": "知识库为空，请先上传论文", "suggestion": "去「上传论文」Tab 上传 PDF"}
    try:
        plan = ExperimentDesigner(kb).generate(req.description)
        log.info(f"[方案] done: {len(plan.get('citations',[]))} refs ({time.time()-t0:.1f}s)")
        return plan
    except Exception as e:
        log.error(f"[方案] fail ({time.time()-t0:.1f}s): {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
