"""
实验方案生成器 — DeepSeek LLM + 知识库检索
流程：DeepSeek 意图解析 → 多查询扩展 → 千问 Embedding 检索 → DeepSeek 方案生成
"""
import json, logging, time
from typing import List
from openai import OpenAI
from .knowledge_base import KnowledgeBase, SearchResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ExpDesigner")

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


def _llm_log(step: str, t0: float, resp, extra: str = ""):
    """记录 LLM 调用详情：耗时 + token 用量"""
    elapsed = time.time() - t0
    usage = resp.usage
    info = f"[LLM] {step}: {elapsed:.1f}s"
    if usage:
        info += f" | prompt={usage.prompt_tokens} completion={usage.completion_tokens} total={usage.total_tokens}"
    if extra:
        info += f" | {extra}"
    logger.info(info)


class ExperimentDesigner:

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=120.0, max_retries=3)

    def generate(self, user_idea: str, top_k: int = 30, max_embedding_calls: int = 5) -> dict:
        t0 = time.time()
        logger.info(f"[方案生成] 开始 — idea='{user_idea[:80]}'")

        # Step 1: DeepSeek 解析意图
        t1 = time.time()
        intent = self._parse_intent(user_idea)
        logger.info(f"[方案生成] Step1 意图解析 — {intent} — {time.time()-t1:.1f}s")

        # Step 2: 多查询检索（最多 max_embedding_calls 次千问调用）
        t2 = time.time()
        queries = self._build_search_queries(user_idea, intent)
        queries = queries[:max_embedding_calls]  # 限制轮次
        logger.info(f"[方案生成] Step2 {len(queries)} 个查询（限制 {max_embedding_calls} 轮）")

        all_results, seen_ids, embedding_errors = [], set(), 0
        for q in queries:
            try:
                for r in self.kb.search(q, top_k=10, full_text_only=True):
                    if r.chunk.chunk_id not in seen_ids:
                        seen_ids.add(r.chunk.chunk_id)
                        all_results.append(r)
            except Exception as e:
                embedding_errors += 1
                logger.warning(f"[方案生成] 检索失败({embedding_errors}): {type(e).__name__}")

        # 千问全部失败 → 回退：直接取 Chunks 给 DeepSeek
        if embedding_errors >= len(queries):
            logger.warning(f"[方案生成] 千问全部失败，回退直接取 Chunks")
            all_results = self._get_all_chunks(top_k)

        all_results.sort(key=lambda x: x.score if hasattr(x, 'score') else 0, reverse=True)
        evidence = all_results[:top_k]
        logger.info(f"[方案生成] Step2 完成 — {len(evidence)} chunks — {time.time()-t2:.1f}s")

        # Step 3: DeepSeek 生成方案
        t3 = time.time()
        plan = self._generate_plan(user_idea, evidence)
        logger.info(f"[方案生成] Step3 生成 — {len(plan)} chars — {time.time()-t3:.1f}s")

        citations = self._build_citations(evidence)
        source_map = self._build_source_map(evidence)  # [来源N] → 论文信息
        logger.info(f"[方案生成] 完成 — {len(citations)} refs — 总 {time.time()-t0:.1f}s")
        return {"title": "实验方案", "content": plan, "citations": citations,
                "source_map": source_map, "evidence_count": len(evidence)}

    def _parse_intent(self, user_idea: str) -> dict:
        t0 = time.time()
        resp = self.client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "system", "content": """从用户输入提取研究要素，只返回 JSON：
{"substance":"目标物质","disease":"疾病/表型","process":"生物学过程","pathway":"通路或null","research_type":"体外/体内/两者"}"""},
                {"role": "user", "content": user_idea}],
            temperature=0.1, max_tokens=300,
        )
        _llm_log("parse_intent", t0, resp)
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"): raw = raw.split("\n", 1)[1]
        if raw.endswith("```"): raw = raw[:-3]
        try: return json.loads(raw.strip())
        except json.JSONDecodeError: return {"substance":"","disease":"","process":"","pathway":None,"research_type":"体外"}

    def _build_search_queries(self, user_idea: str, intent: dict) -> List[str]:
        s, d, p = intent.get("substance",""), intent.get("disease",""), intent.get("process","")
        queries = [user_idea]
        if s and d: queries.append(f"{s} {d} {p}".strip())
        if s and d: queries.append(f"{s} in vitro {d} IC50 dose")
        if p: queries.append(f"{p} detection markers {d}")
        if intent.get("pathway"): queries.append(f"{intent['pathway']} {s} {d}")
        queries.append(f"{s} experimental methods {d}")
        return [q for q in queries if q.strip()]

    def _generate_plan(self, user_idea: str, evidence: List[SearchResult]) -> str:
        lines = []
        for i, r in enumerate(evidence):
            c = r.chunk
            lines.append(f"[来源{i+1}] {c.paper_title} ({c.authors}, {c.year}) - {c.section}, p{c.page}")
            lines.append(f"内容: {c.text[:500]}")
        evidence_text = "\n".join(lines)

        system = """你是资深生物医学研究科学家。基于用户研究想法和文献证据，生成实验方案。

要求:
- **引用格式必须使用 [来源1]、[来源2,3] 等标记，引用数字来自证据编号，不可使用其他格式**
- 试剂信息(品牌、货号)必须来自证据
- 证据不足明确指出
- 中文撰写，术语保留英文
- **总字数控制在 2000 字以内，简洁精炼，只写核心内容**

输出结构:
## 一、研究背景（2-3句话）
## 二、实验设计总览（列表）
## 三、核心实验方案（每步2-3句话）
## 四、预期结果（2-3条）
## 五、注意事项（关键风险）"""

        t0 = time.time()
        resp = self.client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "system", "content": system},
                       {"role": "user", "content": f"## 研究想法\n{user_idea}\n\n## 文献证据({len(evidence)}条)\n{evidence_text}\n\n请生成简洁的实验方案（2000字以内）。"}],
            temperature=0.3, max_tokens=3000,
        )
        _llm_log("generate_plan", t0, resp, f"evidence={len(evidence)}chunks")
        return resp.choices[0].message.content

    def _get_all_chunks(self, top_k: int) -> List[SearchResult]:
        """回退方案：千问不可用时，直接用 BM25 或随机取 Chunks 给 DeepSeek"""
        # 尝试 BM25（空查询会匹配所有文档）
        try:
            from .knowledge_base import Chunk
            results = []
            for c in self.kb.bm25_chunks[:top_k]:
                r = SearchResult(chunk=c, score=0.0)
                results.append(r)
            return results
        except Exception:
            return []

    def _build_source_map(self, evidence: List[SearchResult]) -> dict:
        """[来源N] → {title, authors, year, section, page}"""
        m = {}
        for i, r in enumerate(evidence):
            c = r.chunk
            m[str(i+1)] = {"title": c.paper_title, "authors": c.authors, "year": c.year,
                            "section": c.section, "page": c.page}
        return m

    def _build_citations(self, evidence: List[SearchResult]) -> List[dict]:
        seen = {}
        for r in evidence:
            c = r.chunk
            if c.paper_id not in seen:
                seen[c.paper_id] = {"index":len(seen)+1, "paper_id":c.paper_id, "title":c.paper_title, "authors":c.authors, "year":c.year, "journal":c.journal}
        return list(seen.values())
