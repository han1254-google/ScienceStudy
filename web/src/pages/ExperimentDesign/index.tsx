import { useState, useEffect, useMemo } from 'react'
import {
  Card, Row, Col, Typography, Input, Button, Tabs, Space, Tag, Upload,
  Empty, Divider, message, Select, Table, Statistic, List, Spin, Collapse,
  Modal, Checkbox, Tooltip, Popover
} from 'antd'
import {
  SearchOutlined, UploadOutlined, ExperimentOutlined,
  PlayCircleOutlined, ReloadOutlined, BookOutlined,
  BulbOutlined, DeleteOutlined, FileTextOutlined,
  DownloadOutlined, InboxOutlined,
} from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import owlAvatar from '../../logo/猫头鹰.png'
import {
  getKBStats, uploadPapers, searchKB, generatePlan, searchPapers, deletePaper, rebuildKB,
  type KBStats, type SearchResult, type PubMedPaper, type ExperimentPlan,
} from '../../services/module1'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input
const { Dragger } = Upload

// ============================================================
// Tab 1: 多数据源论文检索
// ============================================================
function PaperSearch() {
  const [keyword, setKeyword] = useState('')
  const [loading, setLoading] = useState(false)
  const [papers, setPapers] = useState<PubMedPaper[]>([])
  const [total, setTotal] = useState(0)
  const [sources, setSources] = useState<string[]>(['pubmed'])

  const doSearch = async () => {
    if (!keyword.trim()) { message.warning('请输入检索关键词'); return }
    if (sources.length === 0) { message.warning('至少选择一个数据源'); return }
    setLoading(true)
    try {
      const res = await searchPapers(keyword, 20, 'all', sources)
      setPapers(res.papers)
      setTotal(res.total_found)
    } catch (e: any) {
      message.error('检索失败: ' + e.message)
    }
    setLoading(false)
  }

  const cols = [
    { title: '来源', dataIndex: 'source', key: 'source', width: 80,
      render: (s: string) => <Tag color={s === 'PubMed' ? 'blue' : s === 'arXiv' ? 'green' : 'orange'}>{s}</Tag> },
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true, width: 300,
      render: (t: string) => <Text strong>{t}</Text> },
    { title: '作者', dataIndex: 'authors', key: 'authors', width: 150, ellipsis: true },
    { title: '年份', dataIndex: 'year', key: 'year', width: 60 },
    { title: '期刊', dataIndex: 'journal', key: 'journal', width: 150, ellipsis: true },
    { title: 'ID', dataIndex: 'id', key: 'id', width: 100, ellipsis: true },
  ]

  return (
    <div>
      <Title level={4}>文献检索</Title>
      <Paragraph type="secondary">支持 PubMed、arXiv、bioRxiv 多数据源检索</Paragraph>

      <Row gutter={12} style={{ marginBottom: 8 }}>
        <Col flex="auto">
          <Input
            size="large"
            placeholder="如: Curcumin colorectal cancer autophagy"
            value={keyword}
            onChange={e => setKeyword(e.target.value)}
            onPressEnter={doSearch}
          />
        </Col>
        <Col>
          <Button type="primary" size="large" icon={<SearchOutlined />} loading={loading} onClick={doSearch}>
            检索
          </Button>
        </Col>
      </Row>

      <Space style={{ marginBottom: 16 }}>
        <Text type="secondary">数据源：</Text>
        <Checkbox checked={sources.includes('pubmed')} onChange={e => e.target.checked ? setSources([...sources, 'pubmed']) : setSources(sources.filter(s => s !== 'pubmed'))}>PubMed</Checkbox>
        <Checkbox checked={sources.includes('arxiv')} onChange={e => e.target.checked ? setSources([...sources, 'arxiv']) : setSources(sources.filter(s => s !== 'arxiv'))}>arXiv</Checkbox>
        <Checkbox checked={sources.includes('biorxiv')} onChange={e => e.target.checked ? setSources([...sources, 'biorxiv']) : setSources(sources.filter(s => s !== 'biorxiv'))}>bioRxiv</Checkbox>
      </Space>

      {total > 0 && <Text type="secondary">共找到 {total} 篇论文（显示前 {papers.length} 篇）</Text>}

      {papers.length > 0 && (
        <Table dataSource={papers} columns={cols} rowKey="id" size="small" scroll={{ x: 900 }}
          style={{ marginTop: 12 }} />
      )}

      {!loading && papers.length === 0 && (
        <Empty description="输入关键词并选择数据源，检索论文" style={{ padding: 40 }} />
      )}
    </div>
  )
}

// ============================================================
// Tab 2: 上传论文
// ============================================================
function PaperUpload({ onDone }: { onDone: () => void }) {
  const [uploading, setUploading] = useState(false)
  const [topic, setTopic] = useState('')

  const doUpload = async (fileList: any) => {
    const files = fileList.map((f: any) => f.originFileObj || f)
    if (files.length === 0) return
    setUploading(true)
    try {
      const res = await uploadPapers(files, topic || undefined)
      message.success(`上传完成：${res.uploaded} 篇成功，${res.duplicates} 篇重复`)
      onDone()
    } catch (e: any) {
      message.error('上传失败: ' + e.message)
    }
    setUploading(false)
  }

  return (
    <div>
      <Title level={4}>上传论文 PDF</Title>
      <Paragraph type="secondary">拖拽 PDF 文件到此区域，自动提取全文并索引到知识库</Paragraph>

      <Space style={{ marginBottom: 12 }}>
        <Text>主题标签（可选）：</Text>
        <Input placeholder="如 Curcumin_CRC" value={topic} onChange={e => setTopic(e.target.value)}
          style={{ width: 250 }} />
      </Space>

      <Dragger
        accept=".pdf"
        multiple
        showUploadList={{ showRemoveIcon: true }}
        beforeUpload={() => false}
        onChange={(info) => {
          if (info.file.status !== 'uploading') {
            doUpload(info.fileList.filter((f: any) => f.status !== 'done'))
          }
        }}
      >
        <p className="ant-upload-drag-icon"><InboxOutlined /></p>
        <p className="ant-upload-text">点击或拖拽 PDF 文件到此区域</p>
        <p className="ant-upload-hint">支持批量上传，系统将自动提取全文并索引</p>
      </Dragger>

      {uploading && <Spin tip="正在处理..." style={{ display: 'block', marginTop: 16 }} />}
    </div>
  )
}

// ============================================================
// Tab 3: 知识库
// ============================================================
function KnowledgeBasePanel() {
  const [stats, setStats] = useState<KBStats | null>(null)
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const s = await getKBStats()
      setStats(s)
    } catch (e: any) { message.error('加载失败: ' + e.message) }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const papers = stats?.papers || []

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>知识库</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>刷新</Button>
          <Button icon={<ReloadOutlined />} onClick={async () => { await rebuildKB(); load(); }}
            danger type="dashed">重建索引</Button>
        </Space>
      </div>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}><Statistic title="论文总数" value={stats?.total_papers || 0} /></Col>
        <Col span={6}><Statistic title="全文论文" value={stats?.full_text_count || 0} suffix={stats ? `/ ${stats.total_papers}` : ''} /></Col>
        <Col span={6}><Statistic title="Chunk 数" value={stats?.total_chunks || 0} /></Col>
        <Col span={6}><Statistic title="Embedding 维度" value={stats?.embedding_dim || 0} /></Col>
      </Row>

      <Table
        dataSource={papers}
        rowKey="paper_id"
        size="small"
        columns={[
          { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true, width: 300 },
          { title: '作者', dataIndex: 'authors', key: 'authors', width: 140, ellipsis: true },
          { title: '年份', dataIndex: 'year', key: 'year', width: 60 },
          { title: '期刊', dataIndex: 'journal', key: 'journal', width: 150, ellipsis: true },
          { title: '来源', dataIndex: 'source', key: 'source', width: 80,
            render: (s: string) => s === 'full_text' ? <Tag color="green">全文</Tag> : <Tag color="orange">仅摘要</Tag> },
          { title: 'Chunks', dataIndex: 'chunk_count', key: 'chunk_count', width: 70 },
          {
            title: '操作', key: 'action', width: 80,
            render: (_: any, r: any) => (
              <Button size="small" danger icon={<DeleteOutlined />}
                onClick={async () => { await deletePaper(r.paper_id); load() }} />
            ),
          },
        ]}
        pagination={{ pageSize: 10 }}
        loading={loading}
        locale={{ emptyText: '知识库为空。请上传 PDF 或等待论文爬取完成' }}
      />
    </div>
  )
}

// ============================================================
// Tab 4: 智能检索
// ============================================================
function SmartSearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [fullTextOnly, setFullTextOnly] = useState(true)

  const doSearch = async () => {
    if (!query.trim()) { message.warning('请输入检索词'); return }
    setLoading(true)
    try {
      const res = await searchKB(query, 15, fullTextOnly)
      setResults(res.results)
    } catch (e: any) { message.error('检索失败: ' + e.message) }
    setLoading(false)
  }

  return (
    <div>
      <Title level={4}>知识库智能检索</Title>
      <Paragraph type="secondary">自然语言搜索已索引的论文全文，支持中英文混合查询</Paragraph>

      <Row gutter={12} style={{ marginBottom: 12 }}>
        <Col flex="auto">
          <Input.Search
            size="large"
            placeholder="如: Curcumin 对 HCT116 的 IC50 是多少？"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onSearch={doSearch}
            enterButton="搜索"
            loading={loading}
          />
        </Col>
      </Row>
      <Space style={{ marginBottom: 16 }}>
        <Tag color={fullTextOnly ? 'green' : 'default'} style={{ cursor: 'pointer' }}
          onClick={() => setFullTextOnly(!fullTextOnly)}>
          {fullTextOnly ? '✓ 仅全文' : '全部（含摘要）'}
        </Tag>
      </Space>

      {results.length > 0 && (
        <List
          dataSource={results}
          renderItem={(r: SearchResult) => (
            <Card size="small" style={{ marginBottom: 8 }} key={r.chunk_id}
              title={<Text strong>{r.paper_title}</Text>}
              extra={<Tag color="blue">{r.score.toFixed(3)}</Tag>}>
              <Space wrap size={[4, 4]} style={{ marginBottom: 6 }}>
                <Tag>{r.authors}</Tag>
                <Tag>{r.year}</Tag>
                <Tag color="purple">{r.journal}</Tag>
                <Tag color="cyan">{r.section} · p{r.page}</Tag>
                {r.source === 'abstract_only' && <Tag color="orange">⚠ 仅摘要</Tag>}
              </Space>
              <Paragraph ellipsis={{ rows: 3 }} style={{ marginBottom: 0, fontSize: 13, color: '#555' }}>
                {r.text_snippet}
              </Paragraph>
            </Card>
          )}
        />
      )}

      {!loading && results.length === 0 && (
        <Empty description="输入自然语言问题进行搜索" style={{ padding: 40 }} />
      )}
    </div>
  )
}

// ============================================================
// 方案内容渲染 — 引文 [1] [2,3] [来源4] 可点击查看出处
// ============================================================
function PlanContent({ content, sourceMap }: { content: string; sourceMap: Record<string, { title: string; authors: string; year: number; section: string; page: number }> }) {
  type CitationInfo = { title: string; authors: string; year: number; section: string; page: number } | null

  const renderCitations = (text: string) => {
    // 匹配 [来源N] [N] [N,M] 等引用格式
    const parts: Array<{ type: 'text' | 'citation'; content: string; nums?: number[]; info?: CitationInfo }> = []
    const regex = /\[(?:来源)?(\d+(?:,\d+)*)\]/g
    let lastIdx = 0
    let match
    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIdx) {
        parts.push({ type: 'text', content: text.slice(lastIdx, match.index) })
      }
      const nums = match[1].split(',').map(Number)
      const info = sourceMap[nums[0].toString()] || null
      parts.push({ type: 'citation', content: match[0], nums, info })
      lastIdx = match.index + match[0].length
    }
    if (lastIdx < text.length) {
      parts.push({ type: 'text', content: text.slice(lastIdx) })
    }

    return parts.map((p, i) => {
      if (p.type === 'citation' && p.info) {
        return (
          <Tooltip key={i} title={`${p.info.title} — ${p.info.section}, p${p.info.page}`}>
            <span style={{ color: '#1677ff', fontWeight: 'bold', cursor: 'pointer', textDecoration: 'underline dotted' }}>
              {p.content}
            </span>
          </Tooltip>
        )
      }
      return <span key={i}>{p.content}</span>
    })
  }

  return (
    <div style={{ lineHeight: 1.9 }}>
      <ReactMarkdown
        components={{
          p: ({ children }) => {
            const text = Array.isArray(children) ? children.map(c => typeof c === 'string' ? c : '').join('') : String(children || '')
            return <p style={{ marginBottom: 12 }}>{renderCitations(text)}</p>
          },
          li: ({ children }) => {
            const text = Array.isArray(children) ? children.map(c => typeof c === 'string' ? c : '').join('') : String(children || '')
            return <li>{renderCitations(text)}</li>
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}


// ============================================================
// Tab 5: 实验方案生成
// ============================================================
function ExperimentDesigner() {
  const [idea, setIdea] = useState('')
  const [plan, setPlan] = useState<ExperimentPlan | null>(null)
  const [loading, setLoading] = useState(false)

  const doGenerate = async () => {
    if (!idea.trim()) { message.warning('请输入实验思路'); return }
    setLoading(true)
    setPlan(null)
    try {
      const p = await generatePlan(idea)
      if (p.error) {
        message.warning(p.error + (p.suggestion ? ` — ${p.suggestion}` : ''))
      } else {
        setPlan(p)
        message.success('方案生成完成！')
      }
    } catch (e: any) { message.error('生成失败: ' + e.message) }
    setLoading(false)
  }

  return (
    <div>
      <Title level={4}>实验方案生成</Title>
      <Paragraph type="secondary">输入实验 idea，系统从知识库检索相关文献，生成带引用的详细实验方案</Paragraph>
      <Paragraph type="secondary" style={{ color: '#fa8c16' }}>
        ⚠️ 确保知识库已有论文（先去「上传论文」Tab 上传至少1篇），否则方案无法生成
      </Paragraph>

      <TextArea
        rows={4}
        placeholder="如: 我想研究姜黄素对结直肠癌细胞自噬的影响，请设计体外实验方案"
        value={idea}
        onChange={e => setIdea(e.target.value)}
        style={{ marginBottom: 12 }}
      />
      <Button type="primary" size="large" icon={<BulbOutlined />} loading={loading}
        onClick={doGenerate} block>
        生成实验方案
      </Button>

      {loading && <Spin tip="正在检索知识库 + DeepSeek 生成方案..." style={{ display: 'block', marginTop: 16 }} />}

      {plan && (
        <Card title={plan.title} style={{ marginTop: 16 }}
          extra={
            <Space>
              <Tag color="green">引用 {plan.evidence_count} 个文献片段</Tag>
              <Button size="small" icon={<DownloadOutlined />} onClick={() => {
                const md = `# ${plan.title}\n\n${plan.content}\n\n---\n\n## 引用文献\n\n${plan.citations?.map(c => `[${c.index}] ${c.authors} (${c.year}). **${c.title}**. *${c.journal}*.`).join('\n\n')}`
                const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url; a.download = `${plan.title || '实验方案'}.md`; a.click()
                URL.revokeObjectURL(url)
              }}>下载 Markdown</Button>
            </Space>
          }>
          <PlanContent content={plan.content} sourceMap={plan.source_map} />
          <Divider />
          <Title level={5}>引用文献</Title>
          {plan.citations?.map(c => (
            <div key={c.index} style={{ marginBottom: 4, fontSize: 13 }}>
              [{c.index}] {c.authors} ({c.year}). <Text strong>{c.title}</Text>. <Text italic>{c.journal}</Text>.
            </div>
          ))}
        </Card>
      )}
    </div>
  )
}

// ============================================================
// 主页面
// ============================================================
export default function ExperimentDesign() {
  const [activeTab, setActiveTab] = useState('pubmed')
  const [refreshKey, setRefreshKey] = useState(0)

  const tabItems = [
    { key: 'pubmed', label: <span><SearchOutlined /> 文献检索</span>,
      children: <PaperSearch /> },
    { key: 'upload', label: <span><UploadOutlined /> 上传论文</span>,
      children: <PaperUpload onDone={() => setRefreshKey(k => k + 1)} /> },
    { key: 'kb', label: <span><BookOutlined /> 知识库</span>,
      children: <KnowledgeBasePanel key={refreshKey} /> },
    { key: 'search', label: <span><SearchOutlined /> 智能检索</span>,
      children: <SmartSearch /> },
    { key: 'design', label: <span><ExperimentOutlined /> 实验设计</span>,
      children: <ExperimentDesigner /> },
  ]

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <img src={owlAvatar} alt="" style={{ width: 56, height: 56, borderRadius: 12, flexShrink: 0 }} />
        <div>
          <Title level={3} style={{ marginBottom: 4 }}>实验思路设计</Title>
          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            PubMed 检索 → 上传/爬取论文 → 知识库索引 → 智能检索 → 实验方案生成
          </Paragraph>
        </div>
      </div>

      <Card style={{ borderRadius: 12 }}>
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Card>
    </div>
  )
}
