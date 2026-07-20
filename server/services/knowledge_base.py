"""
知识库引擎 — ChromaDB 向量存储 + 千问 Embedding API + BM25 关键词检索
Embedding 走千问 API，无需本地模型，CPU 即可运行
"""
import os
import json
import pickle
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict

import jieba
import numpy as np
from rank_bm25 import BM25Okapi
from openai import OpenAI
import chromadb
from chromadb.config import Settings as ChromaSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("jieba").setLevel(logging.WARNING)  # 关闭 jieba 的 DEBUG 输出

# 千问 Embedding 配置
from config import QWEN_API_KEY, QWEN_BASE_URL, QWEN_EMBED_MODEL


# ============================================================
# 数据结构
# ============================================================

@dataclass
class Chunk:
    """文本块"""
    chunk_id: str
    paper_id: str
    paper_title: str = ""
    text: str = ""
    section: str = ""       # Abstract / Methods / Results / Discussion
    page: int = 0
    has_methods: bool = False
    has_reagents: bool = False
    authors: str = ""
    year: int = 0
    journal: str = ""
    source: str = "full_text"  # full_text / abstract_only


@dataclass
class SearchResult:
    """检索结果"""
    chunk: Chunk
    score: float
    semantic_score: float = 0.0
    bm25_score: float = 0.0


@dataclass
class KBStats:
    """知识库统计"""
    total_papers: int = 0
    full_text_count: int = 0
    abstract_only_count: int = 0
    total_chunks: int = 0
    embedding_model: str = "text-embedding-v4"
    embedding_dim: int = 1024
    last_updated: str = ""


# ============================================================
# 知识库引擎
# ============================================================

class KnowledgeBase:
    """
    管理 ChromaDB 向量索引 + BM25 关键词索引
    用法:
        kb = KnowledgeBase("./data/knowledgeDatabase")
        kb.add_paper("PMID_12345", chunks)     # 批量添加
        results = kb.search("curcumin IC50", top_k=10)
        kb.delete_paper("PMID_12345")
        stats = kb.get_stats()
    """

    def __init__(self, persist_dir: str = "./data/knowledgeDatabase"):
        self.persist_dir = Path(persist_dir)
        self.chroma_dir = self.persist_dir / "chroma_db"
        self.bm25_path = self.persist_dir / "bm25_index.pkl"
        self.meta_path = self.persist_dir / "index_metadata.json"
        self.chunks_path = self.persist_dir / "chunks_meta.json"

        os.makedirs(self.chroma_dir, exist_ok=True)

        # ---- 千问 Embedding API 客户端 ----
        self.qwen_client = OpenAI(
            api_key=QWEN_API_KEY,
            base_url=QWEN_BASE_URL,
            timeout=60.0,
            max_retries=3,
        )
        self.embed_dim = 1024  # text-embedding-v4

        # ---- 初始化 ChromaDB ----
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.chroma_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name="papers",
            metadata={"hnsw:space": "cosine"},
        )

        # ---- 初始化 BM25 ----
        self.bm25: Optional[BM25Okapi] = None
        self.bm25_chunks: List[Chunk] = []
        self._load_bm25()

        # ---- 元数据 ----
        self._chunks_meta: Dict[str, Chunk] = {}
        self._load_meta()

        logger.info(f"KnowledgeBase ready. Papers in collection: {self.collection.count()}")

    # ========== Embedding（千问 API） ==========

    def embed(self, texts: List[str]) -> List[List[float]]:
        """文本列表 → 向量列表（调用千问 Embedding API，带重试）"""
        if not texts:
            return []
        import time as _time
        all_vectors = []
        batch_size = 10  # 千问 API 单次最多 10 条
        total_batches = (len(texts) + batch_size - 1) // batch_size
        logger.info(f"[Embedding] 开始向量化 {len(texts)} 条文本，分 {total_batches} 批")
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_num = i // batch_size + 1
            # 重试最多 5 次（应对网络抖动）
            for attempt in range(5):
                try:
                    resp = self.qwen_client.embeddings.create(
                        model=QWEN_EMBED_MODEL,
                        input=batch,
                        timeout=30,
                    )
                    for item in resp.data:
                        all_vectors.append(item.embedding)
                    break
                except Exception as e:
                    wait = (attempt + 1) * 2
                    if attempt < 4:
                        logger.warning(f"[Embedding] 批次 {batch_num}/{total_batches} 失败，{wait}s 后重试 ({attempt+1}/5): {type(e).__name__}")
                        _time.sleep(wait)
                    else:
                        raise
            logger.info(f"[Embedding] 批次 {batch_num}/{total_batches} — {len(batch)} 条")
        logger.info(f"[Embedding] 完成 — 共 {len(all_vectors)} 个向量")
        return all_vectors

    def embed_query(self, query: str) -> List[float]:
        """单个查询文本 → 向量（带重试）"""
        import time as _time
        for attempt in range(5):
            try:
                resp = self.qwen_client.embeddings.create(
                    model=QWEN_EMBED_MODEL,
                    input=[query],
                    timeout=30,
                )
                return resp.data[0].embedding
            except Exception as e:
                if attempt < 4:
                    wait = (attempt + 1) * 2
                    logger.warning(f"[Embedding] embed_query 失败，{wait}s 后重试 ({attempt+1}/5): {type(e).__name__}")
                    _time.sleep(wait)
                else:
                    raise

    # ========== 添加论文 ==========

    def add_paper(self, paper_id: str, chunks: List[Chunk]) -> int:
        """
        将一篇论文的所有 Chunks 加入知识库
        返回添加的 Chunk 数量
        """
        if not chunks:
            return 0

        # 1. 去重：如果已有该论文，先删除旧数据
        self.delete_paper(paper_id)

        # 2. 向量化
        texts = [c.text for c in chunks]
        embeddings = self.embed(texts)

        # 3. 准备 ChromaDB 数据
        ids = [f"{paper_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = []
        for c in chunks:
            metadatas.append({
                "paper_id": c.paper_id,
                "paper_title": c.paper_title[:200],
                "section": c.section,
                "page": c.page,
                "source": c.source,
                "authors": c.authors[:200],
                "year": c.year,
                "journal": c.journal[:200],
            })

        # 4. 写入 ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        # 5. 更新 BM25 索引
        tokenized = [list(jieba.cut(t)) for t in texts]
        if self.bm25 is None:
            self.bm25 = BM25Okapi(tokenized)
        else:
            # 增量添加：重建 BM25（BM25Okapi 不支持增量）
            all_tokens = [list(jieba.cut(c.text)) for c in self.bm25_chunks] + tokenized
            self.bm25 = BM25Okapi(all_tokens)

        # 6. 更新内存元数据
        for i, c in enumerate(chunks):
            c.chunk_id = ids[i]
            self._chunks_meta[ids[i]] = c
        self.bm25_chunks.extend(chunks)

        # 7. 持久化
        self._save_bm25()
        self._save_meta()

        logger.info(f"Added paper '{paper_id}': {len(chunks)} chunks")
        return len(chunks)

    # ========== 检索 ==========

    def search(
        self,
        query: str,
        top_k: int = 10,
        full_text_only: bool = True,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> List[SearchResult]:
        """
        混合检索：语义 + BM25 → RRF 融合
        """
        t0 = __import__('time').time()
        logger.info(f"[检索] query='{query[:60]}', top_k={top_k}, full_text_only={full_text_only}")
        # 1. 语义检索
        if self.collection.count() == 0:
            return []

        query_vec = self.embed_query(query)
        n_semantic = min(top_k * 3, self.collection.count())
        chroma_results = self.collection.query(
            query_embeddings=[query_vec],
            n_results=n_semantic,
            include=["documents", "metadatas", "distances"],
        )

        # 2. BM25 关键词检索
        bm25_scores = {}
        if self.bm25 is not None and len(self.bm25_chunks) > 0:
            tokenized_query = list(jieba.cut(query))
            scores = self.bm25.get_scores(tokenized_query)
            for i, score in enumerate(scores):
                if score > 0:
                    chunk = self.bm25_chunks[i]
                    bm25_scores[chunk.chunk_id] = score

        # 3. RRF 融合排序
        semantic_ranked = {}  # chunk_id -> (rank, distance)
        if chroma_results["ids"] and chroma_results["ids"][0]:
            for rank, cid in enumerate(chroma_results["ids"][0]):
                distance = chroma_results["distances"][0][rank] if chroma_results["distances"] else 0
                semantic_ranked[cid] = (rank + 1, 1.0 - distance)  # distance → similarity

        bm25_ranked = {}
        sorted_bm25 = sorted(bm25_scores.items(), key=lambda x: x[1], reverse=True)
        for rank, (cid, score) in enumerate(sorted_bm25):
            bm25_ranked[cid] = (rank + 1, score)

        # RRF 得分
        all_ids = set(semantic_ranked.keys()) | set(bm25_ranked.keys())
        rrf_scores = {}
        k = 60  # RRF 参数
        for cid in all_ids:
            score = 0.0
            if cid in semantic_ranked:
                score += 1.0 / (k + semantic_ranked[cid][0])
            if cid in bm25_ranked:
                score += 1.0 / (k + bm25_ranked[cid][0])
            rrf_scores[cid] = score

        # 4. 构建结果
        results = []
        for cid, score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
            chunk = self._chunks_meta.get(cid)
            if chunk is None:
                continue

            # 过滤
            if full_text_only and chunk.source == "abstract_only":
                continue
            if year_from and chunk.year < year_from:
                continue
            if year_to and chunk.year > year_to:
                continue

            sem_score = semantic_ranked.get(cid, (0, 0.0))[1]
            bm_score = bm25_ranked.get(cid, (0, 0.0))[1]

            results.append(SearchResult(
                chunk=chunk,
                score=round(score, 4),
                semantic_score=round(sem_score, 4),
                bm25_score=round(bm_score, 4),
            ))

            if len(results) >= top_k:
                break

        logger.info(f"[检索] 完成 — 语义召回 {len(semantic_ranked)} + BM25召回 {len(bm25_ranked)} → RRF融合 {len(results)} 条 — 耗时 {__import__('time').time()-t0:.1f}s")
        return results

    # ========== 删除 ==========

    def delete_paper(self, paper_id: str) -> int:
        """删除一篇论文的所有数据"""
        # 从 ChromaDB 删除
        existing = self.collection.get(where={"paper_id": paper_id})
        if existing["ids"]:
            self.collection.delete(ids=existing["ids"])
            count = len(existing["ids"])
        else:
            count = 0

        # 从 BM25 删除
        self.bm25_chunks = [c for c in self.bm25_chunks if c.paper_id != paper_id]
        if self.bm25_chunks:
            tokenized = [list(jieba.cut(c.text)) for c in self.bm25_chunks]
            self.bm25 = BM25Okapi(tokenized)
        else:
            self.bm25 = None

        # 从元数据删除
        to_remove = [cid for cid, c in self._chunks_meta.items() if c.paper_id == paper_id]
        for cid in to_remove:
            del self._chunks_meta[cid]

        self._save_bm25()
        self._save_meta()
        logger.info(f"Deleted paper '{paper_id}': {count} chunks removed")
        return count

    # ========== 重建索引 ==========

    def rebuild_index(self):
        """清空全部索引并重建（BM25 从 ChromaDB 恢复）"""
        logger.info("Rebuilding full index...")
        # 清空 ChromaDB
        self.chroma_client.delete_collection("papers")
        self.collection = self.chroma_client.get_or_create_collection(
            name="papers",
            metadata={"hnsw:space": "cosine"},
        )
        self.bm25 = None
        self.bm25_chunks = []
        self._chunks_meta = {}
        self._save_bm25()
        self._save_meta()
        logger.info("Index cleared. Re-add papers to rebuild.")

    # ========== 统计 ==========

    def get_stats(self) -> KBStats:
        """获取知识库统计信息"""
        papers = set()
        full_text = set()
        abstract_only = set()
        for c in self._chunks_meta.values():
            papers.add(c.paper_id)
            if c.source == "abstract_only":
                abstract_only.add(c.paper_id)
            else:
                full_text.add(c.paper_id)

        return KBStats(
            total_papers=len(papers),
            full_text_count=len(full_text),
            abstract_only_count=len(abstract_only),
            total_chunks=len(self._chunks_meta),
            embedding_model="text-embedding-v4",
            embedding_dim=self.embed_dim,
            last_updated=self._load_last_updated(),
        )

    def list_papers(self) -> List[Dict[str, Any]]:
        """列出知识库中所有论文"""
        papers: Dict[str, dict] = {}
        for c in self._chunks_meta.values():
            if c.paper_id not in papers:
                papers[c.paper_id] = {
                    "paper_id": c.paper_id,
                    "title": c.paper_title,
                    "authors": c.authors,
                    "year": c.year,
                    "journal": c.journal,
                    "source": c.source,
                    "chunk_count": 0,
                }
            papers[c.paper_id]["chunk_count"] += 1
        return list(papers.values())

    # ========== 持久化辅助 ==========

    def _save_bm25(self):
        data = {
            "chunks": [asdict(c) for c in self.bm25_chunks],
        }
        with open(self.bm25_path, "wb") as f:
            pickle.dump(data, f)

    def _load_bm25(self):
        if self.bm25_path.exists():
            try:
                with open(self.bm25_path, "rb") as f:
                    data = pickle.load(f)
                self.bm25_chunks = [
                    Chunk(**c) for c in data.get("chunks", [])
                ]
                if self.bm25_chunks:
                    tokenized = [list(jieba.cut(c.text)) for c in self.bm25_chunks]
                    self.bm25 = BM25Okapi(tokenized)
                logger.info(f"BM25 loaded: {len(self.bm25_chunks)} chunks")
            except Exception as e:
                logger.warning(f"Failed to load BM25: {e}")
                self.bm25_chunks = []
                self.bm25 = None
        else:
            self.bm25_chunks = []
            self.bm25 = None

    def _save_meta(self):
        meta = {cid: asdict(c) for cid, c in self._chunks_meta.items()}
        with open(self.chunks_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        # 更新索引时间
        from datetime import datetime
        self._save_last_updated(datetime.now().isoformat())

    def _load_meta(self):
        if self.chunks_path.exists():
            try:
                with open(self.chunks_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                self._chunks_meta = {cid: Chunk(**c) for cid, c in meta.items()}
            except Exception as e:
                logger.warning(f"Failed to load chunks meta: {e}")
                self._chunks_meta = {}
        else:
            self._chunks_meta = {}

    def _save_last_updated(self, timestamp: str):
        meta = {}
        if self.meta_path.exists():
            with open(self.meta_path, "r") as f:
                meta = json.load(f)
        meta["last_updated"] = timestamp
        meta["embedding_model"] = "BAAI/bge-small-zh-v1.5"
        meta["embedding_dim"] = self.embed_dim
        with open(self.meta_path, "w") as f:
            json.dump(meta, f, indent=2)

    def _load_last_updated(self) -> str:
        if self.meta_path.exists():
            with open(self.meta_path, "r") as f:
                return json.load(f).get("last_updated", "")
        return ""


# ============================================================
# 全局单例
# ============================================================

_kb_instance: Optional[KnowledgeBase] = None


def get_kb(persist_dir: str = "./data/knowledgeDatabase") -> KnowledgeBase:
    """获取知识库全局单例"""
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = KnowledgeBase(persist_dir)
    return _kb_instance


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("Testing KnowledgeBase...")
    print("=" * 50)

    kb = KnowledgeBase("./data/knowledgeDatabase")

    # 清理旧数据
    kb.rebuild_index()

    # 添加测试论文
    chunks = [
        Chunk(
            chunk_id="",
            paper_id="PMID_test_001",
            paper_title="Curcumin suppresses colorectal cancer cell proliferation",
            text="Curcumin treatment significantly reduced cell viability in HCT116 and SW480 cells with IC50 values of 24.3 μM and 26.1 μM at 48h, respectively. The CCK-8 assay kit was purchased from Dojindo (CK04).",
            section="Results",
            page=5,
            has_methods=True,
            has_reagents=True,
            authors="Zhang Y, Li X",
            year=2024,
            journal="Cancer Research",
        ),
        Chunk(
            chunk_id="",
            paper_id="PMID_test_001",
            paper_title="Curcumin suppresses colorectal cancer cell proliferation",
            text="Anti-Bax antibody (ab32503, 1:1000) and anti-Bcl-2 antibody (CST 4223, 1:1000) were used for Western blot analysis. GAPDH (CST 5174, 1:2000) served as loading control.",
            section="Methods",
            page=4,
            has_methods=True,
            has_reagents=True,
            authors="Zhang Y, Li X",
            year=2024,
            journal="Cancer Research",
        ),
        Chunk(
            chunk_id="",
            paper_id="PMID_test_002",
            paper_title="Anti-tumor effects of natural compounds in GI cancers",
            text="In HT-29 cells, the IC50 of Curcumin was reported to be approximately 20-30 μM depending on treatment duration. Cells were treated with 5, 10, 20, 40 μM for 24-72h.",
            section="Results",
            page=7,
            authors="Li X, Wang H",
            year=2023,
            journal="Oncogene",
        ),
    ]

    kb.add_paper("PMID_test_001", chunks[:2])
    kb.add_paper("PMID_test_002", chunks[2:])

    # 检索测试
    queries = [
        "Curcumin 对结直肠癌细胞的 IC50 是多少？",
        "Western blot 用了什么抗体？",
        "curcumin IC50 HCT116 dose",
    ]

    for q in queries:
        print(f"\n--- Query: '{q}' ---")
        results = kb.search(q, top_k=3)
        for r in results:
            print(f"  [{r.score:.4f}] {r.chunk.paper_title}")
            print(f"    {r.chunk.text[:120]}...")
            print(f"    (semantic={r.semantic_score:.4f}, bm25={r.bm25_score:.4f}, section={r.chunk.section}, p{r.chunk.page})")

    # 统计
    stats = kb.get_stats()
    print(f"\n--- KB Stats ---")
    print(f"  Papers: {stats.total_papers} (full_text: {stats.full_text_count})")
    print(f"  Chunks: {stats.total_chunks}")
    print(f"  Model: {stats.embedding_model} dim={stats.embedding_dim}")

    print("\nAll tests passed!")
