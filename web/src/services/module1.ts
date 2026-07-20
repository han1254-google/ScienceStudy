/**
 * Module 1（实验思路设计）API 调用层
 */
const BASE = 'http://localhost:8000/api/literature';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// ---- 类型 ----

export interface KBStats {
  total_papers: number;
  full_text_count: number;
  abstract_only_count: number;
  total_chunks: number;
  embedding_model: string;
  embedding_dim: number;
  last_updated: string;
  papers: PaperInfo[];
}

export interface PaperInfo {
  paper_id: string;
  title: string;
  authors: string;
  year: number;
  journal: string;
  source: string;
  chunk_count: number;
}

export interface SearchResult {
  score: number;
  semantic_score: number;
  bm25_score: number;
  paper_id: string;
  paper_title: string;
  authors: string;
  year: number;
  journal: string;
  section: string;
  page: number;
  text_snippet: string;
  source: string;
  chunk_id: string;
}

export interface PubMedPaper {
  pmid: string;
  title: string;
  authors: string;
  year: number;
  journal: string;
  doi: string;
  has_full_text: boolean;
}

export interface ExperimentPlan {
  title: string;
  content: string;
  citations: Array<{
    index: number;
    paper_id: string;
    title: string;
    authors: string;
    year: number;
    journal: string;
  }>;
  source_map: Record<string, { title: string; authors: string; year: number; section: string; page: number }>;
  evidence_count: number;
  error?: string;
  suggestion?: string;
}

// ---- API 函数 ----

/** 获取知识库统计 */
export async function getKBStats(): Promise<KBStats> {
  return get('/kb/stats');
}

/** 上传 PDF 论文 */
export async function uploadPapers(files: File[], topic?: string): Promise<{ uploaded: number; duplicates: number; paper_ids: string[] }> {
  const form = new FormData();
  files.forEach(f => form.append('files', f));
  if (topic) form.append('topic', topic);
  const res = await fetch(`${BASE}/upload`, { method: 'POST', body: form });
  return res.json();
}

/** 搜索知识库 */
export async function searchKB(query: string, topK = 10, fullTextOnly = true): Promise<{ query: string; results: SearchResult[]; total: number }> {
  return post('/search', { query, top_k: topK, full_text_only: fullTextOnly });
}

/** 生成实验方案 */
export async function generatePlan(description: string): Promise<ExperimentPlan> {
  return post('/design', { description });
}

/** 多数据源检索 */
export async function searchPapers(query: string, maxResults = 20, dateRange = 'all', sources: string[] = ['pubmed']): Promise<{ query: string; sources: string[]; total_found: number; papers: PubMedPaper[] }> {
  return post('/search-papers', { query, max_results: maxResults, date_range: dateRange, sources });
}

/** PubMed 检索（向后兼容） */
export async function searchPubMed(query: string, maxResults = 20, dateRange = 'all'): Promise<{ query: string; total_found: number; papers: PubMedPaper[] }> {
  return post('/pubmed-search', { query, max_results: maxResults, date_range: dateRange });
}

/** 删除论文 */
export async function deletePaper(paperId: string): Promise<void> {
  await fetch(`${BASE}/kb/papers/${paperId}`, { method: 'DELETE' });
}

/** 重建知识库 */
export async function rebuildKB(): Promise<void> {
  await post('/kb/rebuild');
}
