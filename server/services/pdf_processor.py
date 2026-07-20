"""
PDF 处理器 — 文本提取 + 智能 Chunking
"""
import re
import logging
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass, field

import fitz  # PyMuPDF

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# 数据结构
# ============================================================

@dataclass
class PaperMeta:
    """论文元数据"""
    title: str = ""
    authors: str = ""
    year: int = 0
    journal: str = ""
    doi: str = ""
    pmid: str = ""
    abstract: str = ""
    full_text: str = ""
    pages: int = 0
    has_full_text: bool = False
    local_path: str = ""


@dataclass
class Section:
    """文本章节"""
    title: str
    content: str
    start_page: int = 0


# ============================================================
# Chunk 数据类（与 knowledge_base.py 保持一致）
# ============================================================

@dataclass
class Chunk:
    """文本块"""
    chunk_id: str = ""
    paper_id: str = ""
    paper_title: str = ""
    text: str = ""
    section: str = ""
    page: int = 0
    has_methods: bool = False
    has_reagents: bool = False
    authors: str = ""
    year: int = 0
    journal: str = ""
    source: str = "full_text"


# ============================================================
# 章节标题匹配模式（英文论文 IMRaD 结构）
# ============================================================

SECTION_PATTERNS = [
    # (正则, 标准名称)
    (r'(?i)^(?:I\.?\s*)?(?:INTRODUCTION|BACKGROUND)$', 'Introduction'),
    (r'(?i)^(?:II\.?\s*)?(?:MATERIAL[S]?\s*(?:AND|&)\s*METHOD[S]?|METHOD[S]?|EXPERIMENTAL\s*(?:PROCEDURE[S]?|SECTION))$', 'Methods'),
    (r'(?i)^(?:III\.?\s*)?(?:RESULT[S]?(?:\s*AND\s*DISCUSSION)?|FINDING[S]?)$', 'Results'),
    (r'(?i)^(?:IV\.?\s*)?(?:DISCUSSION|CONCLUSION[S]?)$', 'Discussion'),
    (r'(?i)^(?:ACKNOWLEDGMENT[S]?|ACKNOWLEDGEMENT[S]?)$', 'Acknowledgments'),
    (r'(?i)^(?:REFERENCE[S]?|BIBLIOGRAPHY|LITERATURE\s*CITED)$', 'References'),
    (r'(?i)^(?:ABSTRACT|SUMMARY)$', 'Abstract'),
]

# 中文论文章节模式
CN_SECTION_PATTERNS = [
    (r'^(?:摘要|摘要：|【摘要】)', 'Abstract'),
    (r'^(?:引言|前言|研究背景|背景)', 'Introduction'),
    (r'^(?:材料[和与]方法|实验方法|方法学|研究方法|实验部分)', 'Methods'),
    (r'^(?:结果|实验结果|研究结果)', 'Results'),
    (r'^(?:讨论|分析讨论|结果与讨论|讨论与结论)', 'Discussion'),
    (r'^(?:结论|总结|小结|结论与展望)', 'Discussion'),
    (r'^(?:参考文献|参考书目)', 'References'),
    (r'^(?:致谢|鸣谢)', 'Acknowledgments'),
]


# ============================================================
# PDF 处理器
# ============================================================

class PDFProcessor:
    """
    PDF 文本提取 + Chunking
    用法:
        proc = PDFProcessor()
        meta = proc.extract_metadata(pdf_path)
        text = proc.extract_full_text(pdf_path)
        chunks = proc.chunk_paper(text, paper_id="PMID_xxx", title="...")
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 80):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    # ========== 文本提取 ==========

    def extract_full_text(self, pdf_path: str) -> Tuple[str, int]:
        """
        使用 PyMuPDF 逐页提取 PDF 的完整文本
        返回 (完整文本, 页数)
        """
        doc = fitz.open(pdf_path)
        pages_text = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            if text.strip():
                pages_text.append((page_num + 1, text.strip()))
        doc.close()

        full_text = "\n\n".join(f"[PAGE {p}]\n{t}" for p, t in pages_text)
        return full_text, len(pages_text)

    def extract_metadata(self, pdf_path: str) -> PaperMeta:
        """提取 PDF 元数据"""
        doc = fitz.open(pdf_path)
        meta = doc.metadata
        pages = len(doc)

        # 尝试从第一页提取标题
        title = meta.get("title", "")
        if not title:
            try:
                first_page_text = doc[0].get_text("text")
                # 取前 200 字符作为候选标题
                lines = [l.strip() for l in first_page_text.split("\n") if l.strip()]
                if lines:
                    title = lines[0][:300]
            except Exception:
                pass

        doc.close()

        return PaperMeta(
            title=title or Path(pdf_path).stem,
            authors=meta.get("author", ""),
            doi=meta.get("doi", ""),
            pages=pages,
            has_full_text=True,
            local_path=pdf_path,
        )

    # ========== 章节识别 ==========

    def identify_sections(self, text: str) -> List[Section]:
        """
        从全文中识别 IMRaD 章节
        返回按顺序排列的章节列表
        """
        lines = text.split("\n")
        sections = []
        current_section = Section(title="Unknown", content="")
        found_first_section = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # 检查是否是章节标题
            section_name = self._match_section_title(stripped)
            if section_name:
                if found_first_section or section_name in ("Abstract", "Introduction"):
                    # 保存当前章节
                    if current_section.content.strip():
                        sections.append(current_section)
                    current_section = Section(title=section_name, content="")
                    found_first_section = True
                    continue

            if found_first_section:
                current_section.content += stripped + " "

        # 保存最后一个章节
        if current_section.content.strip():
            sections.append(current_section)

        # 如果没有识别出章节，整个文本作为一个章节
        if not sections:
            sections.append(Section(title="Full Text", content=text))

        return sections

    def _match_section_title(self, line: str) -> Optional[str]:
        """尝试匹配章节标题"""
        line = line.strip().rstrip(".")
        # 英文模式
        for pattern, name in SECTION_PATTERNS:
            if re.match(pattern, line):
                return name
        # 中文模式
        for pattern, name in CN_SECTION_PATTERNS:
            if re.match(pattern, line):
                return name
        return None

    # ========== Chunking ==========

    def chunk_paper(
        self,
        text: str,
        paper_id: str,
        title: str = "",
        authors: str = "",
        year: int = 0,
        journal: str = "",
        source: str = "full_text",
    ) -> List[Chunk]:
        """
        将论文全量文本切分为 Chunks
        策略：先识别章节 → 每个章节内按段落 + 滑动窗口切分
        """
        sections = self.identify_sections(text)
        chunks = []

        for section in sections:
            section_chunks = self._chunk_section(
                section,
                paper_id=paper_id,
                title=title,
                authors=authors,
                year=year,
                journal=journal,
                source=source,
            )
            chunks.extend(section_chunks)

        # 去重：相邻相同内容的 chunk 合并
        chunks = self._deduplicate_chunks(chunks)

        logger.info(f"Paper '{paper_id}': {len(sections)} sections → {len(chunks)} chunks")
        return chunks

    def _chunk_section(
        self,
        section: Section,
        paper_id: str,
        title: str,
        authors: str,
        year: int,
        journal: str,
        source: str,
    ) -> List[Chunk]:
        """在单个章节内按段落 + 滑动窗口切分"""
        # 按句号/换行分段
        paragraphs = re.split(r'(?<=[.!?。！？])\s+', section.content)
        paragraphs = [p.strip() for p in paragraphs if len(p.strip()) > 20]

        if not paragraphs:
            return []

        chunks = []
        # 简单滑动窗口
        i = 0
        chunk_idx = 0
        while i < len(paragraphs):
            chunk_text = paragraphs[i]
            j = i + 1
            while j < len(paragraphs) and len(chunk_text) + len(paragraphs[j]) < self.chunk_size:
                chunk_text += " " + paragraphs[j]
                j += 1

            if len(chunk_text) >= 30:  # 最小 Chunk 长度
                chunks.append(Chunk(
                    paper_id=paper_id,
                    paper_title=title,
                    text=chunk_text,
                    section=section.title,
                    page=0,  # 精确页码需从 PDF 提取时保留
                    has_methods=section.title == "Methods" or "method" in chunk_text.lower(),
                    has_reagents="ab" in chunk_text.lower() or "antibod" in chunk_text.lower(),
                    authors=authors,
                    year=year,
                    journal=journal,
                    source=source,
                ))
                chunk_idx += 1

            # 滑动（保留一个段落重叠）
            i = j - 1 if j - 1 > i else i + 1
            if i + 1 > len(paragraphs):
                break

        return chunks

    def _deduplicate_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """合并内容高度相似的相邻 Chunks"""
        if len(chunks) <= 1:
            return chunks
        result = [chunks[0]]
        for i in range(1, len(chunks)):
            prev = result[-1]
            curr = chunks[i]
            # 简单去重：如果重叠超过 50%，合并
            overlap = self._text_overlap(prev.text, curr.text)
            if overlap > 0.5:
                # 合并
                result[-1].text = prev.text + " " + curr.text[len(curr.text)//2:]
            else:
                result.append(curr)
        return result

    def _text_overlap(self, text1: str, text2: str) -> float:
        """计算两段文本的字符级重叠率"""
        if not text1 or not text2:
            return 0.0
        # 取 text1 的后半段和 text2 的前半段比较
        half1 = text1[len(text1)//2:]
        half2 = text2[:len(text2)//2]
        # 简单的 n-gram 重叠
        n = 20
        grams1 = set(half1[i:i+n] for i in range(0, len(half1)-n, n))
        grams2 = set(half2[i:i+n] for i in range(0, len(half2)-n, n))
        if not grams1 or not grams2:
            return 0.0
        intersection = grams1 & grams2
        return len(intersection) / min(len(grams1), len(grams2))


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("Testing PDFProcessor...")
    print("=" * 50)

    proc = PDFProcessor()

    # 用纯文本测试（不需要真实 PDF）
    sample_text = """
Abstract
Curcumin is a natural polyphenol with anti-cancer properties.

Introduction
Colorectal cancer is the third most common cancer worldwide. Natural compounds
have gained attention for their chemopreventive potential. Curcumin, derived from
Curcuma longa, exhibits anti-proliferative and pro-apoptotic effects in various
cancer cell lines.

Materials and Methods
Cell Culture. HCT116 and SW480 cells were cultured in RPMI-1640 medium
supplemented with 10% FBS at 37C with 5% CO2.

CCK-8 Assay. Cell viability was measured using CCK-8 kit (Dojindo, CK04).
Cells were seeded at 5x10^3 cells/well in 96-well plates and treated with
Curcumin (Sigma-Aldrich, C7727) at 0, 5, 10, 20, 40, 80 uM for 24, 48, 72h.

Western Blot. Primary antibodies: anti-Bax (Abcam, ab32503, 1:1000),
anti-Bcl-2 (CST, 4223, 1:1000), anti-GAPDH (CST, 5174, 1:2000).

Results
Curcumin inhibited HCT116 and SW480 proliferation in a dose-dependent manner.
The IC50 values were 24.3 uM and 26.1 uM at 48h, respectively. Western blot
analysis showed increased Bax and decreased Bcl-2 expression after treatment.

Discussion
Our results demonstrate that Curcumin effectively suppresses colorectal cancer
cell proliferation and induces apoptosis via the mitochondrial pathway.
"""

    chunks = proc.chunk_paper(
        sample_text,
        paper_id="PMID_test",
        title="Curcumin suppresses colorectal cancer cell proliferation",
        authors="Zhang et al.",
        year=2024,
        journal="Cancer Research",
    )

    for c in chunks:
        print(f"\n  [{c.section}] {c.text[:100]}...")
        print(f"    methods={c.has_methods}, reagents={c.has_reagents}")

    print(f"\nTotal chunks: {len(chunks)}")
    print(f"Sections found: {set(c.section for c in chunks)}")
