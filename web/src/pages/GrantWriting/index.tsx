import { useState } from 'react'
import {
  Card, Row, Col, Typography, Tabs, Button, Input, Space, Select,
  Tag, Divider, Tree, Empty, message, Collapse, Upload,
} from 'antd'
import {
  FileTextOutlined, ApartmentOutlined, BranchesOutlined,
  BulbOutlined, AimOutlined, CheckCircleOutlined,
  ClockCircleOutlined, DownloadOutlined, PlusOutlined,
  EditOutlined, EyeOutlined, SaveOutlined,
} from '@ant-design/icons'
import hamsterAvatar from '../../logo/仓鼠.png'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input
const { Panel } = Collapse

// ---------- 标书章节编辑器 ----------
function SectionsEditor() {
  const [template, setTemplate] = useState('nsfc-general')

  const sectionTree = [
    {
      title: '一、立项依据与研究意义',
      key: 'background',
      children: [
        { title: '1.1 研究背景', key: 'bg-1' },
        { title: '1.2 国内外研究现状', key: 'bg-2' },
        { title: '1.3 研究假说与科学问题', key: 'bg-3' },
        { title: '1.4 前期研究基础', key: 'bg-4' },
      ],
    },
    {
      title: '二、研究目标与内容',
      key: 'objectives',
      children: [
        { title: '2.1 研究目标', key: 'obj-1' },
        { title: '2.2 研究内容', key: 'obj-2' },
      ],
    },
    {
      title: '三、研究方案与技术路线',
      key: 'methods',
      children: [
        { title: '3.1 实验方案', key: 'method-1' },
        { title: '3.2 技术路线图', key: 'method-2' },
        { title: '3.3 可行性分析', key: 'method-3' },
      ],
    },
    {
      title: '四、创新点',
      key: 'innovation',
    },
    {
      title: '五、预期成果与研究计划',
      key: 'outcome',
      children: [
        { title: '5.1 预期成果', key: 'out-1' },
        { title: '5.2 年度研究计划', key: 'out-2' },
      ],
    },
  ]

  return (
    <div>
      <Title level={4}>标书结构化撰写</Title>
      <Paragraph type="secondary">
        基于国自然/省自然模板的结构化标书编辑器，AI 辅助撰写各章节
      </Paragraph>

      {/* 模板选择 */}
      <Space style={{ marginBottom: 16 }}>
        <Text strong>模板：</Text>
        <Select value={template} onChange={setTemplate} style={{ width: 200 }} options={[
          { value: 'nsfc-general', label: '国自然·面上项目' },
          { value: 'nsfc-youth', label: '国自然·青年基金' },
          { value: 'nsfc-key', label: '国自然·重点项目' },
          { value: 'provincial', label: '省自然基金' },
          { value: 'custom', label: '自定义模板' },
        ]} />
        <Button icon={<SaveOutlined />}>保存草稿</Button>
        <Button icon={<EyeOutlined />}>预览</Button>
        <Button type="primary" icon={<DownloadOutlined />}>导出 Word</Button>
      </Space>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={6}>
          {/* 章节导航树 */}
          <Card size="small" title="📑 章节导航">
            <Tree
              treeData={sectionTree}
              defaultExpandAll
              blockNode
              style={{ background: 'transparent' }}
            />
          </Card>
        </Col>

        <Col xs={24} md={18}>
          {/* 编辑区 */}
          <Card size="small" title="✏️ 立项依据">
            <Space style={{ marginBottom: 12 }}>
              <Button size="small" icon={<BulbOutlined />}>AI 生成初稿</Button>
              <Button size="small" icon={<EditOutlined />}>AI 润色</Button>
              <Button size="small">引用文献</Button>
              <Button size="small">插入预实验数据</Button>
            </Space>

            <TextArea
              rows={12}
              placeholder="在此撰写立项依据，或点击「AI 生成初稿」从文献调研结果自动生成..."
            />

            <Divider />

            {/* 参考文献快捷插入 */}
            <div>
              <Text strong style={{ fontSize: 13 }}>📚 引用的文献</Text>
              <Empty description="暂无引用文献，点击上方「引用文献」添加" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            </div>
          </Card>

          <Card size="small" title="✏️ 研究目标与内容" style={{ marginTop: 16 }}>
            <TextArea rows={8} placeholder="撰写研究目标和研究内容..." />
          </Card>

          <Card size="small" title="✏️ 研究方案" style={{ marginTop: 16 }}>
            <TextArea rows={10} placeholder="撰写详细实验方案..." />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

// ---------- 技术路线图工具 ----------
function TechRoadmap() {
  return (
    <div>
      <Title level={4}>技术路线图</Title>
      <Paragraph type="secondary">
        可视化实验流程设计 — 拖拽节点、连线、分组，生成 SCI 级技术路线图
      </Paragraph>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={4}>
          <Card size="small" title="图元工具箱">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Tag color="blue">实验步骤</Tag>
              <Tag color="green">检测方法</Tag>
              <Tag color="orange">分组</Tag>
              <Tag color="purple">结果输出</Tag>
              <Tag color="red">结论</Tag>
              <Button icon={<PlusOutlined />} size="small" block>自定义节点</Button>
            </Space>

            <Divider />

            <div>
              <Text strong style={{ fontSize: 12 }}>模板</Text>
              <br />
              <Button size="small" block style={{ marginTop: 8 }}>体外实验路线</Button>
              <Button size="small" block style={{ marginTop: 4 }}>体内实验路线</Button>
              <Button size="small" block style={{ marginTop: 4 }}>临床样本路线</Button>
              <Button size="small" block style={{ marginTop: 4 }}>综合路线</Button>
            </div>
          </Card>
        </Col>
        <Col xs={24} md={16}>
          <Card size="small" title="画布" style={{ minHeight: 400 }}>
            <Empty description="从左侧工具箱拖拽节点到画布，连线构建技术路线图" style={{ padding: 60 }} />
          </Card>
        </Col>
        <Col xs={24} md={4}>
          <Card size="small" title="属性">
            <Empty description="选中节点查看属性" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          </Card>
          <Card size="small" title="导出" style={{ marginTop: 12 }}>
            <Button icon={<DownloadOutlined />} block style={{ marginBottom: 8 }}>导出 SVG</Button>
            <Button icon={<DownloadOutlined />} block>导出 PNG (300dpi)</Button>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

// ---------- 机制图工具 ----------
function MechanismDiagram() {
  const pathwayTemplates = [
    'Wnt/β-catenin', 'PI3K/AKT/mTOR', 'NF-κB', 'JAK/STAT',
    'MAPK/ERK', 'TGF-β/Smad', 'p53 凋亡', '自噬通路',
    '铁死亡', '细胞周期调控',
  ]

  return (
    <div>
      <Title level={4}>机制图绘制</Title>
      <Paragraph type="secondary">
        信号通路/分子机制示意图 — 内置通路模板库，拖拽式分子图元，支持自定义修饰
      </Paragraph>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={4}>
          <Card size="small" title="🧬 通路模板">
            {pathwayTemplates.map((p) => (
              <Tag key={p} style={{ display: 'block', marginBottom: 6, cursor: 'pointer' }}>
                {p}
              </Tag>
            ))}
          </Card>

          <Card size="small" title="图元库" style={{ marginTop: 12 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Tag color="blue">细胞膜受体</Tag>
              <Tag color="green">激酶</Tag>
              <Tag color="orange">转录因子</Tag>
              <Tag color="purple">线粒体</Tag>
              <Tag color="cyan">细胞核</Tag>
              <Divider style={{ margin: '4px 0' }} />
              <Tag>→ 激活</Tag>
              <Tag>⊣ 抑制</Tag>
              <Tag>Ⓟ 磷酸化</Tag>
              <Tag>Ⓤ 泛素化</Tag>
              <Tag>⇢ 易位</Tag>
            </Space>
          </Card>
        </Col>

        <Col xs={24} md={16}>
          <Card size="small" title="画布" style={{ minHeight: 400 }}>
            <Empty description="选择通路模板快速开始，或从零绘制分子机制图" style={{ padding: 60 }} />
          </Card>
        </Col>

        <Col xs={24} md={4}>
          <Card size="small" title="属性">
            <Empty description="选中图元查看属性" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          </Card>
          <Card size="small" title="导出" style={{ marginTop: 12 }}>
            <Button icon={<DownloadOutlined />} block style={{ marginBottom: 8 }}>导出 SVG</Button>
            <Button icon={<DownloadOutlined />} block>导出 PNG (300dpi)</Button>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

// ---------- 主页面 ----------
export default function GrantWriting() {
  const tabItems = [
    {
      key: 'editor',
      label: <span><EditOutlined /> 标书撰写</span>,
      children: <SectionsEditor />,
    },
    {
      key: 'roadmap',
      label: <span><ApartmentOutlined /> 技术路线图</span>,
      children: <TechRoadmap />,
    },
    {
      key: 'mechanism',
      label: <span><BranchesOutlined /> 机制图</span>,
      children: <MechanismDiagram />,
    },
  ]

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <img src={hamsterAvatar} alt="" style={{ width: 56, height: 56, borderRadius: 12, flexShrink: 0 }} />
        <div>
          <Title level={3} style={{ marginBottom: 4 }}>标书撰写</Title>
          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            结构化标书编辑器 + 可视化技术路线图 + 机制图工具 — 覆盖国自然/省自然模板，AI 辅助各章节撰写
          </Paragraph>
        </div>
      </div>

      <Card style={{ borderRadius: 12 }}>
        <Tabs defaultActiveKey="editor" items={tabItems} />
      </Card>
    </div>
  )
}
