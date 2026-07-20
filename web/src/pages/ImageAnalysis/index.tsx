import { useState } from 'react'
import { Card, Tabs, Typography } from 'antd'
import { LineChartOutlined, CodeOutlined, CameraOutlined } from '@ant-design/icons'
import raccoonAvatar from '../../logo/浣熊.png'
import ExperimentAnalysis from './ExperimentAnalysis'
import CustomAnalysis from './CustomAnalysis'
import ImageUnderstanding from './ImageUnderstanding'

const { Title, Paragraph } = Typography

export default function ImageAnalysis() {
  const [activeTab, setActiveTab] = useState('template')

  const tabItems = [
    {
      key: 'template',
      label: <span><LineChartOutlined /> 实验数据分析</span>,
      children: <ExperimentAnalysis />,
    },
    {
      key: 'custom',
      label: <span><CodeOutlined /> 自定义分析</span>,
      children: <CustomAnalysis />,
    },
    {
      key: 'vision',
      label: <span><CameraOutlined /> 图像理解</span>,
      children: <ImageUnderstanding />,
    },
  ]

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <img src={raccoonAvatar} alt="" style={{ width: 56, height: 56, borderRadius: 12, flexShrink: 0 }} />
        <div>
          <Title level={3} style={{ marginBottom: 4 }}>图像分析</Title>
          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            实验数据模板分析 · AI 自定义代码分析 · AI 图像视觉理解
          </Paragraph>
        </div>
      </div>

      <Card style={{ borderRadius: 12 }}>
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Card>
    </div>
  )
}
