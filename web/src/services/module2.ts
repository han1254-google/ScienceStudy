/**
 * Module 2（图像分析）API 调用层
 * 覆盖三大子模块:
 *   2.1 模板数据分析 (6 类实验)
 *   2.2 自定义数据分析 (AI 代码生成 + 执行)
 *   2.3 AI 图像理解 (Vision 模型)
 */
const BASE = 'http://localhost:8000/api/image-analysis';

// ---- 泛型请求辅助 ----

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function postJSON<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// ---- 类型定义 ----

export interface ChartItem {
  chart_id: string;
  title: string;
  base64: string;   // "data:image/png;base64,..."
  description: string;
}

export interface AnalysisResponse {
  success: boolean;
  experiment_type: string;
  data: Record<string, unknown>;
  stats: Record<string, unknown>;
  charts: ChartItem[];
  report: string;
  download_filename: string;
}

export interface TemplateInfo {
  key: string;
  label: string;
  description: string;
}

export interface TemplateDetail {
  experiment_type: string;
  label: string;
  description: string;
  accepted_formats: string[];
  explanation: Record<string, unknown>;
  chart_types: string[];
  params: Array<Record<string, unknown>>;
}

// ---- 2.1 模板数据分析 ----

export async function getTemplates(): Promise<{ templates: TemplateInfo[] }> {
  return get('/templates');
}

export async function getTemplateDetail(type: string): Promise<TemplateDetail> {
  return get(`/templates/${type}`);
}

/** CCK8 细胞增殖/毒性分析 */
export async function analyzeCCK8(
  file: File,
  fitModel = '4pl',
  statMethod = 'anova',
  errorBar = 'sem',
): Promise<AnalysisResponse> {
  const form = new FormData();
  form.append('file', file);
  form.append('fit_model', fitModel);
  form.append('stat_method', statMethod);
  form.append('error_bar', errorBar);
  const res = await fetch(`${BASE}/experiments/cck8/analyze`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`CCK8 分析失败: ${res.status} ${res.statusText}`);
  return res.json();
}

/** EdU 细胞增殖图像分析 */
export async function analyzeEdU(
  files: File[],
  eduChannel = 'green',
  nuclearDye = 'dapi',
  threshold = 30,
): Promise<AnalysisResponse> {
  const form = new FormData();
  files.forEach(f => form.append('files', f));
  form.append('edu_channel', eduChannel);
  form.append('nuclear_dye', nuclearDye);
  form.append('threshold', String(threshold));
  const res = await fetch(`${BASE}/experiments/edu/analyze`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`EdU 分析失败: ${res.status} ${res.statusText}`);
  return res.json();
}

/** 细胞克隆形成分析 */
export async function analyzeColony(
  files: File[],
  minArea = 50,
  roiMode = 'auto',
): Promise<AnalysisResponse> {
  const form = new FormData();
  files.forEach(f => form.append('files', f));
  form.append('min_area', String(minArea));
  form.append('roi_mode', roiMode);
  const res = await fetch(`${BASE}/experiments/colony/analyze`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`克隆形成分析失败: ${res.status} ${res.statusText}`);
  return res.json();
}

/** Western Blot 条带定量分析 */
export async function analyzeWB(
  file: File,
  lanes = 6,
  background = 'rolling',
  housekeeping = 'gapdh',
): Promise<AnalysisResponse> {
  const form = new FormData();
  form.append('file', file);
  form.append('lanes', String(lanes));
  form.append('background', background);
  form.append('housekeeping', housekeeping);
  const res = await fetch(`${BASE}/experiments/wb/analyze`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`WB 分析失败: ${res.status} ${res.statusText}`);
  return res.json();
}

/** qPCR 结果分析 */
export async function analyzeQPCR(
  file: File,
  housekeepingGenes = 'GAPDH',
  controlGroup = 'Control',
  method = 'ddct',
): Promise<AnalysisResponse> {
  const form = new FormData();
  form.append('file', file);
  form.append('housekeeping_genes', housekeepingGenes);
  form.append('control_group', controlGroup);
  form.append('method', method);
  const res = await fetch(`${BASE}/experiments/qpcr/analyze`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`qPCR 分析失败: ${res.status} ${res.statusText}`);
  return res.json();
}

/** IHC 免疫组化图像分析 */
export async function analyzeIHC(
  files: File[],
  stainType = 'dab-he',
  dabThreshold = 50,
): Promise<AnalysisResponse> {
  const form = new FormData();
  files.forEach(f => form.append('files', f));
  form.append('stain_type', stainType);
  form.append('dab_threshold', String(dabThreshold));
  const res = await fetch(`${BASE}/experiments/ihc/analyze`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`IHC 分析失败: ${res.status} ${res.statusText}`);
  return res.json();
}

// ---- 2.2 自定义数据分析 ----

export interface GenerateCodeResponse {
  success: boolean;
  generated_code: string;
  language: string;
  explanation: string;
  data_file_id: string;
  data_preview: Record<string, unknown>[];
  columns: string[];
  shape: number[];
}

export interface ExecuteCodeResponse {
  success: boolean;
  stdout: string;
  stderr: string;
  charts: ChartItem[];
  error: string;
  exit_code: number;
}

/** AI 生成 Python 分析代码 */
export async function customGenerateCode(
  file: File,
  userPrompt = '',
): Promise<GenerateCodeResponse> {
  const form = new FormData();
  form.append('file', file);
  if (userPrompt) form.append('user_prompt', userPrompt);
  const res = await fetch(`${BASE}/custom/generate-code`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`代码生成失败: ${res.status} ${res.statusText}`);
  return res.json();
}

/** 执行 Python 代码（沙盒子进程） */
export async function customExecuteCode(
  code: string,
  dataFileId = '',
): Promise<ExecuteCodeResponse> {
  return postJSON('/custom/execute-code', { code, data_file_id: dataFileId });
}

// ---- 2.3 AI 图像理解 ----

export interface ImageUnderstandingResponse {
  success: boolean;
  analysis: string;
  model_used: string;
  image_info: {
    width: number;
    height: number;
    mode: string;
    original_format: string;
  };
  filename: string;
  error?: string;
}

/** AI 视觉图像分析 */
export async function understandImage(
  file: File,
  prompt = '请详细分析这张科研图像',
  description = '',
  analysisType = 'general',
): Promise<ImageUnderstandingResponse> {
  const form = new FormData();
  form.append('file', file);
  form.append('prompt', prompt);
  if (description) form.append('description', description);
  form.append('analysis_type', analysisType);
  const res = await fetch(`${BASE}/understand/image`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`图像理解失败: ${res.status} ${res.statusText}`);
  return res.json();
}
