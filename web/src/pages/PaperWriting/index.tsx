import { useState } from 'react'
import {
  Card, Row, Col, Typography, Tabs, Button, Input, Space, Select,
  Tag, Divider, Tree, Empty, message, Collapse, Table, Upload, Badge,
} from 'antd'
import {
  EditOutlined, FileTextOutlined, TranslationOutlined,
  DownloadOutlined, PlusOutlined, BulbOutlined,
  SaveOutlined, EyeOutlined, OrderedListOutlined,
  BookOutlined, MailOutlined, CheckCircleOutlined,
  PictureOutlined, FormatPainterOutlined,
} from '@ant-design/icons'
import squirrelAvatar from '../../logo/松鼠.png'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input
const { Panel } = Collapse

// ---------- 结构化写作编辑器 ----------
function StructuredEditor() {
  const [currentSection, setCurrentSection] = useState('abstract')

  const sections = [
    { key: 'title', title: 'Title（标题）', icon: '📌' },
    { key: 'abstract', title: 'Abstract（摘要）', icon: '📋' },
    { key: 'introduction', title: 'Introduction（引言）', icon: '📖' },
    { key: 'methods', title: 'Materials and Methods', icon: '🔬' },
    { key: 'results', title: 'Results（结果）', icon: '📊' },
    { key: 'discussion', title: 'Discussion（讨论）', icon: '💬' },
    { key: 'references', title: 'References（参考文献）', icon: '📚' },
    { key: 'legends', title: 'Figure Legends（图注）', icon: '🖼️' },
  ]

  const sectionPlaceholders: Record<string, string> = {
    abstract: 'Background / Methods / Results / Conclusions 结构...',
    introduction: '研究背景、文献综述、研究假说、研究目的...',
    methods: '细胞培养、CCK8、EdU、克隆形成、WB、qPCR、IHC、统计分析...',
    results: '物质A抑制结直肠癌细胞增殖... Western Blot结果表明...',
    discussion: '本研究发现...与Zhang et al.一致...创新点...局限性...展望...',
  }

  return (
    <div>
      <Title level={4}>结构化论文写作</Title>
      <Paragraph type="secondary">
        遵循 IMRaD 框架的论文写作工具，AI 辅助各章节撰写、润色、中英互译
      </Paragraph>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={5}>
          {/* 章节导航 */}
          <Card size="small" title="📑 论文章节">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {sections.map((s) => (
                <Button
                  key={s.key}
                  type={currentSection === s.key ? 'primary' : 'text'}
                  size="small"
                  block
                  style={{ textAlign: 'left', justifyContent: 'flex-start' }}
                  onClick={() => setCurrentSection(s.key)}
                >
                  {s.icon} {s.title}
                </Button>
              ))}
            </div>
          </Card>

          {/* 图表管理 */}
          <Card size="small" title="📊 图表管理" style={{ marginTop: 12 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {[1, 2, 3].map((n) => (
                <Tag key={n} color="blue" style={{ cursor: 'pointer' }}>
                  Figure {n} — 待生成
                </Tag>
              ))}
              <Button size="small" icon={<PlusOutlined />} block type="dashed">
                从图像分析导入图表
              </Button>
            </div>
          </Card>
        </Col>

        <Col xs={24} md={14}>
          {/* 编辑区 */}
          <Card
            size="small"
            title={
              <Space>
                <span>{sections.find((s) => s.key === currentSection)?.title}</span>
                <Tag color="blue">草稿</Tag>
              </Space>
            }
            extra={
              <Space>
                <Button size="small" icon={<BulbOutlined />}>AI 生成</Button>
                <Button size="small" icon={<TranslationOutlined />}>中译英</Button>
                <Button size="small" icon={<TranslationOutlined />}>英译中</Button>
                <Button size="small" icon={<FormatPainterOutlined />}>润色</Button>
              </Space>
            }
          >
            <TextArea
              rows={16}
              placeholder={sectionPlaceholders[currentSection] || '在此撰写内容...'}
            />

            <Divider />

            {/* AI 辅助快捷操作 */}
            <Collapse ghost size="small">
              <Panel header="AI 写作辅助" key="ai">
                <Space wrap>
                  <Button size="small">从实验设计导入背景文献</Button>
                  <Button size="small">从图像分析导入结果数据</Button>
                  <Button size="small">插入参考文献</Button>
                  <Button size="small">检查逻辑连贯性</Button>
                  <Button size="small">生成段落大纲</Button>
                </Space>
              </Panel>
            </Collapse>
          </Card>
        </Col>

        <Col xs={24} md={5}>
          {/* 写作统计 */}
          <Card size="small" title="📈 写作统计">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div><Text type="secondary">总字数</Text><br /><Text strong>0</Text></div>
              <div><Text type="secondary">引用数量</Text><br /><Text strong>0</Text></div>
              <div><Text type="secondary">图表数量</Text><br /><Text strong>0</Text></div>
              <div><Text type="secondary">完成度</Text><br /><Text strong>0%</Text></div>
            </Space>
          </Card>

          <Card size="small" title="⚙️ 投稿设置" style={{ marginTop: 12 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>目标期刊</Text>
                <Select placeholder="选择目标期刊" style={{ width: '100%' }} options={[
                  { value: 'cancer-res', label: 'Cancer Research' },
                  { value: 'oncogene', label: 'Oncogene' },
                  { value: 'cancer-lett', label: 'Cancer Letters' },
                  { value: 'ijbs', label: 'Int J Biol Sci' },
                ]} />
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>引用格式</Text>
                <Select defaultValue="vancouver" style={{ width: '100%' }} options={[
                  { value: 'vancouver', label: 'Vancouver' },
                  { value: 'apa', label: 'APA 7th' },
                  { value: 'gbt7714', label: 'GB/T 7714' },
                  { value: 'harvard', label: 'Harvard' },
                ]} />
              </div>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

// ---------- 参考文献管理 ----------
function ReferenceManager() {
  const columns = [
    { title: '#', dataIndex: 'index', key: 'index', width: 40 },
    { title: '作者', dataIndex: 'authors', key: 'authors', width: 160 },
    { title: '标题', dataIndex: 'title', key: 'title' },
    { title: '期刊', dataIndex: 'journal', key: 'journal', width: 160 },
    { title: '年份', dataIndex: 'year', key: 'year', width: 60 },
    { title: 'PMID/DOI', dataIndex: 'id', key: 'id', width: 140 },
  ]

  return (
    <div>
      <Title level={4}>参考文献管理</Title>
      <Paragraph type="secondary">
        支持 PMID / DOI 导入，自动格式化参考文献，支持多种引用格式
      </Paragraph>

      {/* 导入栏 */}
      <Space style={{ marginBottom: 16 }}>
        <Input.Search
          placeholder="输入 PMID (如 12345678) 或 DOI (如 10.1000/xxx)"
          enterButton="导入"
          style={{ width: 400 }}
          onSearch={() => message.info('参考文献导入功能将通过后端 API 接入')}
        />
        <Upload accept=".ris,.bib,.enw">
          <Button icon={<UploadOutlined />}>导入 RIS/BibTeX 文件</Button>
        </Upload>
      </Space>

      <Table
        dataSource={[
          { key: '1', index: 1, authors: 'Zhang Y, et al.', title: 'Curcumin suppresses colorectal cancer cell proliferation via Wnt/β-catenin pathway', journal: 'Cancer Res', year: 2024, id: 'PMID: 12345678' },
          { key: '2', index: 2, authors: 'Li X, et al.', title: 'Anti-tumor effects of natural compounds in gastrointestinal cancers', journal: 'Oncogene', year: 2023, id: 'DOI: 10.1000/xxx' },
        ]}
        columns={columns}
        size="small"
        scroll={{ x: 800 }}
      />
    </div>
  )
}

// ---------- 投稿辅助 ----------
function SubmissionHelper() {
  return (
    <div>
      <Title level={4}>投稿辅助</Title>
      <Paragraph type="secondary">
        Cover Letter 生成、Highlights、格式检查、摘要撰写等投稿一站式辅助
      </Paragraph>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card size="small" title="✉️ Cover Letter">
            <Space style={{ marginBottom: 12 }}>
              <Button size="small" icon={<BulbOutlined />}>AI 生成</Button>
            </Space>
            <TextArea rows={8} placeholder="Dear Editor, ..." />
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card size="small" title="⭐ Highlights">
            <Space style={{ marginBottom: 12 }}>
              <Button size="small" icon={<BulbOutlined />}>AI 生成</Button>
            </Space>
            <TextArea rows={8} placeholder="• 第一条亮点...&#10;• 第二条亮点...&#10;• 第三条亮点..." />
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card size="small" title="📋 结构化摘要">
            <Collapse ghost size="small">
              <Panel header="Background" key="bg">
                <TextArea rows={3} placeholder="Background..." />
              </Panel>
              <Panel header="Methods" key="methods">
                <TextArea rows={3} placeholder="Methods..." />
              </Panel>
              <Panel header="Results" key="results">
                <TextArea rows={3} placeholder="Results..." />
              </Panel>
              <Panel header="Conclusions" key="conclusions">
                <TextArea rows={3} placeholder="Conclusions..." />
              </Panel>
            </Collapse>
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card size="small" title="✅ 格式检查">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div><CheckCircleOutlined style={{ color: '#52c41a' }} /> <Text>字数检查 (摘要)</Text> — 待提交</div>
              <div><CheckCircleOutlined style={{ color: '#52c41a' }} /> <Text>图表数量限制</Text> — 待提交</div>
              <div><CheckCircleOutlined style={{ color: '#faad14' }} /> <Text>参考文献格式</Text> — 待检查</div>
            </Space>
            <Divider />
            <Button type="primary" icon={<CheckCircleOutlined />} block>运行格式检查</Button>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

// ---------- 主页面 ----------
export default function PaperWriting() {
  const tabItems = [
    {
      key: 'editor',
      label: <span><EditOutlined /> 结构化写作</span>,
      children: <StructuredEditor />,
    },
    {
      key: 'references',
      label: <span><BookOutlined /> 参考文献</span>,
      children: <ReferenceManager />,
    },
    {
      key: 'submission',
      label: <span><MailOutlined /> 投稿辅助</span>,
      children: <SubmissionHelper />,
    },
  ]

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <img src={squirrelAvatar} alt="" style={{ width: 56, height: 56, borderRadius: 12, flexShrink: 0 }} />
        <div>
          <Title level={3} style={{ marginBottom: 4 }}>论文撰写</Title>
          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            IMRaD 结构化写作框架 + 图表管理 + 参考文献管理 + AI 润色/翻译 — 从初稿到投稿一站式完成
          </Paragraph>
        </div>
      </div>

      <Card style={{ borderRadius: 12 }}>
        <Tabs defaultActiveKey="editor" items={tabItems} />
      </Card>
    </div>
  )
}
