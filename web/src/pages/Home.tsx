import { useNavigate } from 'react-router-dom'
import { Card, Row, Col, Typography, Tag, Space, Avatar } from 'antd'
import {
  ArrowRightOutlined,
  BulbOutlined,
} from '@ant-design/icons'
import owlAvatar from '../logo/猫头鹰.png'
import raccoonAvatar from '../logo/浣熊.png'
import hamsterAvatar from '../logo/仓鼠.png'
import squirrelAvatar from '../logo/松鼠.png'

const { Title, Text } = Typography

interface ModuleCard {
  key: string
  title: string
  description: string
  avatar: string
  agentName: string
  color: string
  features: string[]
  path: string
}

const modules: ModuleCard[] = [
  {
    key: 'experiment',
    title: '实验思路设计',
    description: '文献智能检索 · 实验方法提取 · 试剂信息汇总 · 方案自动生成',
    avatar: owlAvatar,
    agentName: '猫头鹰·智多星',
    color: '#7abf8c',
    features: [
      '文献多维对比（剂量/细胞系/试剂/货号）',
      '实验方法结构化提取',
      '横向扩展检索（同物质 × 不同癌种）',
      '实验方案推荐与分组设计',
    ],
    path: '/experiment-design',
  },
  {
    key: 'image',
    title: '图像分析',
    description: 'CCK8 · EdU · 克隆形成 · Western Blot · qPCR · IHC',
    avatar: raccoonAvatar,
    agentName: '浣熊·视觉专家',
    color: '#5790c4',
    features: [
      'EdU / 克隆 / WB / IHC AI 图像识别定量',
      'CCK8 IC50 计算与剂量曲线拟合',
      'qPCR ΔΔCt 自动计算',
      'SCI 级别图表导出（300dpi / 矢量图）',
    ],
    path: '/image-analysis',
  },
  {
    key: 'grant',
    title: '标书撰写',
    description: '技术路线图 · 机制图 · 立项依据 · 研究方案',
    avatar: hamsterAvatar,
    agentName: '仓鼠·架构师',
    color: '#e89560',
    features: [
      '国自然 / 省自然模板',
      '可视化技术路线图 & 机制图工具',
      '信号通路模板库（Wnt / PI3K / NF-κB …）',
      '立项依据 AI 辅助生成',
    ],
    path: '/grant-writing',
  },
  {
    key: 'paper',
    title: '论文撰写',
    description: '结构化写作 · 图表管理 · 参考文献 · 投稿辅助',
    avatar: squirrelAvatar,
    agentName: '松鼠·翻译官',
    color: '#9b7ec4',
    features: [
      'IMRaD 结构化写作框架',
      '中英双语 AI 润色与翻译',
      '图表自动编号与图注生成',
      '参考文献管理（PMID/DOI 导入）',
    ],
    path: '/paper-writing',
  },
]

export default function Home() {
  const navigate = useNavigate()

  return (
    <div className="page-container">
      {/* 顶部欢迎区域 */}
      <div style={{ marginBottom: 32, textAlign: 'center' }}>
        <Title level={2} style={{ marginBottom: 8 }}>
          🔬 科研智能助手
        </Title>
        <Text type="secondary" style={{ fontSize: 16 }}>
          从实验设计到论文发表，覆盖科研全流程的 AI 辅助平台
        </Text>
      </div>

      {/* 快速统计 — 使用头像 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
        {[
          { avatar: owlAvatar, label: '实验思路设计', agent: '猫头鹰·智多星', desc: '文献调研 → 方案生成' },
          { avatar: raccoonAvatar, label: '图像分析', agent: '浣熊·视觉专家', desc: '6 种实验结果自动分析' },
          { avatar: hamsterAvatar, label: '标书撰写', agent: '仓鼠·架构师', desc: '国自然/省自然模板' },
          { avatar: squirrelAvatar, label: '论文撰写', agent: '松鼠·翻译官', desc: '结构化写作 + AI 润色' },
        ].map((item) => (
          <Col xs={24} sm={12} lg={6} key={item.label}>
            <Card
              hoverable
              size="small"
              style={{ textAlign: 'center', borderRadius: 8 }}
              onClick={() => navigate(`/${['experiment-design','image-analysis','grant-writing','paper-writing'][['实验思路设计','图像分析','标书撰写','论文撰写'].indexOf(item.label)]}`)}
            >
              <Avatar src={item.avatar} size={56} style={{ marginBottom: 8 }} />
              <div style={{ fontWeight: 600, fontSize: 14 }}>{item.label}</div>
              <Text type="secondary" style={{ fontSize: 11 }}>
                {item.agent}
              </Text>
              <br />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {item.desc}
              </Text>
            </Card>
          </Col>
        ))}
      </Row>

      {/* 四大功能入口卡片 */}
      <Row gutter={[24, 24]}>
        {modules.map((mod) => (
          <Col xs={24} md={12} key={mod.key}>
            <Card
              hoverable
              style={{ borderRadius: 12, height: '100%' }}
              onClick={() => navigate(mod.path)}
              styles={{ body: { padding: 24 } }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 20 }}>
                {/* 左侧头像 */}
                <Avatar
                  src={mod.avatar}
                  size={80}
                  shape="square"
                  style={{ borderRadius: 12, flexShrink: 0, border: `3px solid ${mod.color}30` }}
                />

                {/* 右侧内容 */}
                <div style={{ flex: 1 }}>
                  <Title level={4} style={{ marginBottom: 2 }}>
                    {mod.title}
                  </Title>
                  <Text style={{ fontSize: 12, color: mod.color, fontWeight: 500 }}>
                    {mod.agentName}
                  </Text>
                  <br />
                  <Text type="secondary" style={{ fontSize: 13, marginBottom: 12, display: 'block' }}>
                    {mod.description}
                  </Text>

                  <Space wrap size={[4, 4]}>
                    {mod.features.map((f) => (
                      <Tag key={f} color={mod.color} style={{ fontSize: 12 }}>
                        {f}
                      </Tag>
                    ))}
                  </Space>

                  <div style={{ marginTop: 16, textAlign: 'right' }}>
                    <Text style={{ color: mod.color, fontSize: 13, cursor: 'pointer' }}>
                      进入模块 <ArrowRightOutlined />
                    </Text>
                  </div>
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* 底部提示 */}
      <Card
        style={{ marginTop: 24, borderRadius: 8, background: '#f6ffed', border: '1px solid #b7eb8f' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <BulbOutlined style={{ fontSize: 20, color: '#52c41a' }} />
          <div>
            <Text strong>推荐工作流</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 13 }}>
              模块 1（实验设计 → 文献调研）→ 模块 2（图像分析 → 数据处理）
              → 模块 3（标书撰写 → 预实验整合）→ 模块 4（论文撰写 → 成果输出）
            </Text>
          </div>
        </div>
      </Card>
    </div>
  )
}
