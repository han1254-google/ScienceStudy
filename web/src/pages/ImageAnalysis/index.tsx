import { useState } from 'react'
import {
  Card, Row, Col, Typography, Tabs, Button, Upload, Space, Table,
  InputNumber, Select, Divider, Statistic, Empty, message, Slider,
} from 'antd'
import {
  PictureOutlined, LineChartOutlined, UploadOutlined,
  DownloadOutlined, PlayCircleOutlined, ExperimentOutlined,
  ScissorOutlined, CameraOutlined, BulbOutlined,
} from '@ant-design/icons'
import raccoonAvatar from '../../logo/浣熊.png'

const { Title, Text, Paragraph } = Typography

// ---------- 共享的图像上传区域 ----------
interface ImageUploaderProps {
  accept?: string
  hint?: string
  onUpload?: (file: File) => void
}

function ImageUploader({ accept = '.tif,.tiff,.jpg,.jpeg,.png,.bmp', hint, onUpload }: ImageUploaderProps) {
  return (
    <Upload.Dragger
      accept={accept}
      multiple
      beforeUpload={(file) => {
        onUpload?.(file)
        return false // 阻止自动上传
      }}
      style={{ padding: '20px 0' }}
    >
      <p className="ant-upload-drag-icon">
        <PictureOutlined style={{ fontSize: 48, color: '#1677ff' }} />
      </p>
      <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
      <p className="ant-upload-hint">{hint || `支持格式：${accept}`}</p>
    </Upload.Dragger>
  )
}

// ---------- CCK8 分析面板 ----------
function CCK8Analysis() {
  return (
    <div>
      <Title level={4}>CCK8 细胞增殖/毒性分析</Title>
      <Paragraph type="secondary">
        导入 OD 值数据，自动计算细胞活力、拟合剂量-效应曲线、计算 IC50
      </Paragraph>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card size="small" title="📊 数据导入">
            <Upload.Dragger accept=".xlsx,.csv" style={{ padding: '10px 0' }}>
              <p className="ant-upload-text">导入 Excel / CSV 数据</p>
              <p className="ant-upload-hint">支持手动输入 OD 值</p>
            </Upload.Dragger>
            <Divider />
            <Button type="dashed" block>或手动输入数据</Button>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card size="small" title="📈 参数设置">
            <div style={{ marginBottom: 8 }}>
              <Text>拟合模型</Text>
              <Select defaultValue="4pl" style={{ width: '100%' }} options={[
                { value: '4pl', label: '四参数 Logistic (4PL)' },
                { value: 'linear', label: '线性回归' },
                { value: 'log', label: '对数拟合' },
              ]} />
            </div>
            <div style={{ marginBottom: 8 }}>
              <Text>统计方法</Text>
              <Select defaultValue="anova" style={{ width: '100%' }} options={[
                { value: 'anova', label: 'One-way ANOVA + Tukey' },
                { value: 'ttest', label: "Student's t-test" },
                { value: 'dunnett', label: "Dunnett's test" },
              ]} />
            </div>
            <div>
              <Text>误差棒</Text>
              <Select defaultValue="sem" style={{ width: '100%' }} options={[
                { value: 'sem', label: 'Mean ± SEM' },
                { value: 'sd', label: 'Mean ± SD' },
              ]} />
            </div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card size="small" title="📋 分析结果">
            <Empty description="请先导入数据" />
          </Card>
        </Col>
      </Row>

      <Card size="small" title="图表预览" style={{ marginTop: 16 }}>
        <Empty description="导入数据后在此处显示剂量-效应曲线和柱状图预览" style={{ padding: 40 }} />
      </Card>
    </div>
  )
}

// ---------- EdU 分析面板 ----------
function EduAnalysis() {
  return (
    <div>
      <Title level={4}>EdU 细胞增殖图像分析</Title>
      <Paragraph type="secondary">
        上传 EdU 荧光图像，AI 自动识别 EdU 阳性细胞和总细胞核，计算阳性率
      </Paragraph>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card size="small" title="🖼️ 图像上传">
            <ImageUploader hint="支持 .tif / .jpg / .png，可批量上传多视野" />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card size="small" title="⚙️ 分析参数">
            <div style={{ marginBottom: 12 }}>
              <Text>EdU 通道颜色</Text>
              <Select defaultValue="green" style={{ width: '100%' }} options={[
                { value: 'green', label: '绿色 (FITC / Alexa Fluor 488)' },
                { value: 'red', label: '红色 (Cy3 / Alexa Fluor 555)' },
                { value: 'far-red', label: '远红 (Cy5 / Alexa Fluor 647)' },
              ]} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <Text>核染料</Text>
              <Select defaultValue="dapi" style={{ width: '100%' }} options={[
                { value: 'dapi', label: 'DAPI / Hoechst (蓝色)' },
              ]} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <Text>EdU 阳性判定阈值</Text>
              <Slider defaultValue={30} min={1} max={100} marks={{ 10: '严格', 50: '中等', 90: '宽松' }} />
            </div>
            <Button type="primary" icon={<PlayCircleOutlined />} block>
              开始分析
            </Button>
          </Card>
        </Col>
      </Row>

      <Card size="small" title="分析结果预览" style={{ marginTop: 16 }}>
        <Empty description="上传图像并点击分析后，在此处显示细胞识别标注图和统计结果" style={{ padding: 40 }} />
      </Card>
    </div>
  )
}

// ---------- 克隆形成分析面板 ----------
function ColonyAnalysis() {
  return (
    <div>
      <Title level={4}>细胞克隆形成分析</Title>
      <Paragraph type="secondary">
        上传结晶紫染色克隆图像，AI 自动识别和计数克隆
      </Paragraph>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card size="small" title="🖼️ 图像上传">
            <ImageUploader hint="支持孔板/培养皿照片，.jpg / .png / .tif" />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card size="small" title="⚙️ 分析参数">
            <div style={{ marginBottom: 12 }}>
              <Text>最小克隆面积 (像素)</Text>
              <InputNumber defaultValue={50} min={10} max={500} style={{ width: '100%' }} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <Text>最小克隆细胞数阈值</Text>
              <Select defaultValue={50} style={{ width: '100%' }} options={[
                { value: 30, label: '≥30 个细胞' },
                { value: 50, label: '≥50 个细胞（常用）' },
                { value: 100, label: '≥100 个细胞' },
              ]} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <Text>分析区域选择</Text>
              <Select defaultValue="auto" style={{ width: '100%' }} options={[
                { value: 'auto', label: '自动检测孔/皿边界' },
                { value: 'full', label: '整张图片' },
                { value: 'manual', label: '手动框选 ROI' },
              ]} />
            </div>
            <Button type="primary" icon={<PlayCircleOutlined />} block>
              开始分析
            </Button>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

// ---------- WB 分析面板 ----------
function WBAnalysis() {
  return (
    <div>
      <Title level={4}>Western Blot 条带定量分析</Title>
      <Paragraph type="secondary">
        上传 WB 化学发光图像，自动识别泳道和条带，灰度定量，内参归一化
      </Paragraph>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card size="small" title="🖼️ 图像上传">
            <ImageUploader accept=".tif,.tiff,.jpg,.png,.bmp" hint="建议上传原始 16-bit TIFF 图像" />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card size="small" title="⚙️ 参数设置">
            <div style={{ marginBottom: 12 }}>
              <Text>泳道数</Text>
              <InputNumber defaultValue={6} min={2} max={20} style={{ width: '100%' }} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <Text>背景扣除方法</Text>
              <Select defaultValue="rolling" style={{ width: '100%' }} options={[
                { value: 'rolling', label: 'Rolling Ball 算法' },
                { value: 'local', label: '局部背景扣除' },
                { value: 'none', label: '不扣除背景' },
              ]} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <Text>内参蛋白</Text>
              <Select defaultValue="gapdh" style={{ width: '100%' }} options={[
                { value: 'gapdh', label: 'GAPDH (37 kDa)' },
                { value: 'actin', label: 'β-actin (42 kDa)' },
                { value: 'tubulin', label: 'β-tubulin (55 kDa)' },
                { value: 'custom', label: '自定义内参' },
              ]} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <Text>目的蛋白分组</Text>
              <Select mode="multiple" defaultValue={['bax', 'bcl2']} style={{ width: '100%' }} options={[
                { value: 'bax', label: 'Bax' },
                { value: 'bcl2', label: 'Bcl-2' },
                { value: 'caspase3', label: 'Cleaved Caspase-3' },
              ]} />
            </div>
            <Button type="primary" icon={<PlayCircleOutlined />} block>
              开始定量分析
            </Button>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

// ---------- qPCR 分析面板 ----------
function QPCRAnalysis() {
  return (
    <div>
      <Title level={4}>qPCR 结果分析</Title>
      <Paragraph type="secondary">
        导入 qPCR 仪导出的 Ct 值数据，自动计算 ΔΔCt 和相对表达量
      </Paragraph>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card size="small" title="📊 数据导入">
            <Upload.Dragger accept=".xlsx,.csv,.txt" style={{ padding: '10px 0' }}>
              <p className="ant-upload-text">导入 Ct 值数据</p>
              <p className="ant-upload-hint">支持 Bio-Rad / ABI / Roche 导出格式</p>
            </Upload.Dragger>
            <Divider />
            <Button type="dashed" block>手动输入 Ct 值</Button>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card size="small" title="⚙️ 参数设置">
            <div style={{ marginBottom: 8 }}>
              <Text>内参基因</Text>
              <Select mode="multiple" defaultValue={['gapdh']} style={{ width: '100%' }} options={[
                { value: 'gapdh', label: 'GAPDH' },
                { value: 'actin', label: 'β-actin' },
                { value: '18s', label: '18S rRNA' },
              ]} />
            </div>
            <div style={{ marginBottom: 8 }}>
              <Text>对照组</Text>
              <Select defaultValue="control" style={{ width: '100%' }} options={[
                { value: 'control', label: 'Control 组' },
                { value: 'custom', label: '自定义对照组' },
              ]} />
            </div>
            <div>
              <Text>计算方法</Text>
              <Select defaultValue="ddct" style={{ width: '100%' }} options={[
                { value: 'ddct', label: 'ΔΔCt (2^(-ΔΔCt))' },
                { value: 'pfaffl', label: 'Pfaffl 法（需扩增效率）' },
              ]} />
            </div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card size="small" title="📋 结果">
            <Empty description="请先导入数据" />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

// ---------- IHC 分析面板 ----------
function IHCAnalysis() {
  return (
    <div>
      <Title level={4}>IHC 免疫组化图像分析</Title>
      <Paragraph type="secondary">
        上传 IHC 染色图像，自动分离 DAB 阳性信号和苏木精复染，计算 H-Score、阳性面积比等
      </Paragraph>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card size="small" title="🖼️ 图像上传">
            <ImageUploader accept=".tif,.jpg,.png,.svs" hint="支持不同放大倍数图像和全切片扫描 (.svs)" />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card size="small" title="⚙️ 分析参数">
            <div style={{ marginBottom: 12 }}>
              <Text>染色方式</Text>
              <Select defaultValue="dab-he" style={{ width: '100%' }} options={[
                { value: 'dab-he', label: 'DAB (棕黄色) + 苏木精 (蓝色)' },
                { value: 'aec', label: 'AEC (红色) + 苏木精' },
                { value: 'if', label: '免疫荧光' },
              ]} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <Text>定量指标</Text>
              <Select mode="multiple" defaultValue={['positive', 'hscore']} style={{ width: '100%' }} options={[
                { value: 'positive', label: '阳性面积比 (%)' },
                { value: 'aod', label: '平均光密度 (AOD)' },
                { value: 'iod', label: '积分光密度 (IOD)' },
                { value: 'hscore', label: 'H-Score' },
              ]} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <Text>DAB 阳性阈值</Text>
              <Slider defaultValue={50} min={1} max={100} />
            </div>
            <Button type="primary" icon={<PlayCircleOutlined />} block>
              开始分析
            </Button>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

// ---------- 主页面 ----------
export default function ImageAnalysis() {
  const tabItems = [
    { key: 'cck8', label: <span><LineChartOutlined /> CCK8</span>, children: <CCK8Analysis /> },
    { key: 'edu', label: <span><CameraOutlined /> EdU</span>, children: <EduAnalysis /> },
    { key: 'colony', label: <span><ExperimentOutlined /> 克隆形成</span>, children: <ColonyAnalysis /> },
    { key: 'wb', label: <span><ScissorOutlined /> WB 定量</span>, children: <WBAnalysis /> },
    { key: 'qpcr', label: <span><LineChartOutlined /> qPCR</span>, children: <QPCRAnalysis /> },
    { key: 'ihc', label: <span><BulbOutlined /> IHC</span>, children: <IHCAnalysis /> },
  ]

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <img src={raccoonAvatar} alt="" style={{ width: 56, height: 56, borderRadius: 12, flexShrink: 0 }} />
        <div>
          <Title level={3} style={{ marginBottom: 4 }}>图像分析</Title>
          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            覆盖 CCK8、EdU、克隆形成、Western Blot、qPCR、IHC 六大实验类型的 AI 图像识别与定量分析，一键生成 SCI 级别图表
          </Paragraph>
        </div>
      </div>

      <Card style={{ borderRadius: 12 }}>
        <Tabs defaultActiveKey="cck8" items={tabItems} />
      </Card>
    </div>
  )
}
