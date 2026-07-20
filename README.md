# 🔬 ScienceStudy — 科研智能助手

AI 辅助生物医学研究一体化平台，覆盖 **实验设计 → 图像分析 → 标书撰写 → 论文撰写** 全流程。

## 四大模块

| 模块 | Agent | 功能 |
|------|-------|------|
| 🦉 **实验思路设计** | 猫头鹰·智多星 | 多数据源文献检索 → 知识库索引 → 智能检索 → 实验方案生成 |
| 🦝 **图像分析** | 浣熊·视觉专家 | CCK8 / EdU / 克隆形成 / WB / qPCR / IHC 六类实验图像定量分析 |
| 🐹 **标书撰写** | 仓鼠·架构师 | 国自然/省自然模板 + 技术路线图 + 机制图工具 |
| 🐿️ **论文撰写** | 松鼠·翻译官 | IMRaD 结构化写作 + AI 润色 + 参考文献管理 |

## 技术栈

| 组件 | 技术 |
|------|------|
| **前端** | React 18 + TypeScript + Ant Design 5 + React Router + ECharts |
| **后端** | Python FastAPI |
| **Embedding** | 千问 `text-embedding-v4` API（1024 维） |
| **LLM** | DeepSeek `deepseek-v4-pro` API |
| **向量数据库** | ChromaDB（本地，CPU） |
| **关键词检索** | BM25 + jieba 分词（本地，CPU） |
| **PDF 解析** | PyMuPDF |
| **文献检索** | PubMed E-utilities + arXiv API + bioRxiv API |

## 快速开始

### 环境要求

- Python 3.9+
- Node.js 18+
- Windows / macOS / Linux

### 1. 安装依赖

```bash
# 后端
cd server
pip install -r requirements.txt

# 前端
cd web
npm install
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key
```

### 3. 启动

```bash
# 后端（终端 1）
cd server
python -c "import uvicorn; uvicorn.run('main:app', host='127.0.0.1', port=8000)"

# 前端（终端 2）
cd web
npm run dev
```

打开 http://localhost:5173

## 项目结构

```
scienceStudy/
├── server/                          # Python FastAPI 后端
│   ├── main.py                      # 应用入口
│   ├── config.py                    # 配置（从 .env 加载）
│   ├── routers/
│   │   ├── literature.py            # 文献检索/上传/知识库/方案生成 API
│   │   ├── image_analysis.py        # 图像分析 API
│   │   ├── writing.py               # AI 写作 API
│   │   └── export.py                # 图表导出 API
│   └── services/
│       ├── knowledge_base.py        # ChromaDB + Embedding + BM25 引擎
│       ├── pdf_processor.py         # PDF 文本提取 + Chunking
│       ├── experiment_designer.py   # DeepSeek 实验方案生成
│       └── ...                      # CCK8/EdU/Colony/WB/qPCR/IHC 服务
├── web/                             # React + TypeScript 前端
│   └── src/
│       ├── pages/
│       │   ├── ExperimentDesign/    # 实验思路设计（5 个 Tab）
│       │   ├── ImageAnalysis/       # 图像分析（6 个分析面板）
│       │   ├── GrantWriting/        # 标书撰写
│       │   └── PaperWriting/        # 论文撰写
│       └── services/module1.ts      # Module 1 API 调用层
├── crawler/                         # 测试图像爬虫 + 合成生成器
├── requirements.md                  # 完整需求规格说明书
└── .env.example                     # API Key 配置模板
```

## Module 1 核心 Pipeline

```
用户输入 → DeepSeek 意图解析 → 多查询扩展（最多 5 个）
        → 千问 Embedding ×1 → ChromaDB 语义检索 + BM25 关键词检索
        → RRF 融合排序 → DeepSeek 方案生成
        → 每条建议标注 [来源N]，点击可查看出自哪篇论文
```

## 已实现

- [x] 多数据源论文检索（PubMed / arXiv / bioRxiv）
- [x] PDF 上传 + 全量文本提取 + Chunking
- [x] 知识库（ChromaDB + BM25 + 语义标签）
- [x] 混合检索（语义 + 关键词 + RRF 融合）
- [x] AI 实验方案生成（DeepSeek，带论文引用溯源）
- [x] 方案 Markdown 下载

## 待实现

- [ ] PubMed 论文自动下载 PDF
- [ ] 图像分析 6 类实验全 AI 处理
- [ ] 标书撰写 + 技术路线图/机制图
- [ ] 论文结构化写作 + AI 润色

## License

MIT
