import { useState } from 'react'
import {
  Card, Row, Col, Typography, Tabs, Button, Upload, Space, Table,
  InputNumber, Select, Divider, Empty, message, Slider, Spin, Image as AntImage, Steps,
} from 'antd'
import {
  PictureOutlined, LineChartOutlined, UploadOutlined,
  DownloadOutlined, PlayCircleOutlined, ExperimentOutlined,
  ScissorOutlined, CameraOutlined, BulbOutlined, InboxOutlined,
} from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import {
  analyzeCCK8, analyzeEdU, analyzeColony, analyzeWB, analyzeQPCR, analyzeIHC,
  type AnalysisResponse, type ChartItem,
} from '../../services/module2'

const { Title, Text, Paragraph } = Typography

// ==================== 共享组件 ====================

/** 图表展示 + 右键下载 */
function ChartDisplay({ chart }: { chart: ChartItem }) {
  const doDownload = () => {
    const a = document.createElement('a')
    a.href = chart.base64
    a.download = `${chart.chart_id}.png`
    a.click()
  }

  return (
    <div style={{ textAlign: 'center', marginBottom: 16 }}>
      <Text strong style={{ fontSize: 12 }}>{chart.title}</Text>
      <div style={{ marginTop: 8 }}>
        <AntImage
          src={chart.base64}
          alt={chart.title}
          style={{ maxWidth: '100%', borderRadius: 8 }}
          preview={{ mask: <span>点击预览 / 右键下载</span> }}
        />
      </div>
      <div>
        <Button type="link" size="small" icon={<DownloadOutlined />} onClick={doDownload}>
          下载 PNG
        </Button>
      </div>
      {chart.description && (
        <Text type="secondary" style={{ fontSize: 11, display: 'block' }}>{chart.description}</Text>
      )}
    </div>
  )
}

/** 下载模板 */
const API_BASE = 'http://localhost:8000/api/image-analysis'
function downloadTemplate(type: string) {
  const a = document.createElement('a')
  a.href = `${API_BASE}/templates/${type}/download`
  a.click()
}

/** 模板引导横幅 — 醒目提示"先下载模板" */
function TemplateBanner({ type }: { type: string }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      background: '#e6f4ff', border: '1px solid #91caff',
      borderRadius: 8, padding: '10px 16px', marginBottom: 16,
    }}>
      <Text strong style={{ fontSize: 13, whiteSpace: 'nowrap' }}>📋 操作流程：</Text>
      <Steps
        size="small"
        style={{ flex: 1, margin: 0 }}
        items={[
          {
            title: (
              <Button type="primary" size="small" icon={<DownloadOutlined />}
                onClick={() => downloadTemplate(type)}>
                下载数据模板
              </Button>
            ),
          },
          { title: '按模板填写数据' },
          { title: '上传文件开始分析' },
        ]}
      />
    </div>
  )
}

/** 图像上传区域 */
function ImageUploader({ accept = '.tif,.tiff,.jpg,.jpeg,.png,.bmp', hint }: { accept?: string; hint?: string }) {
  return (
    <Upload.Dragger
      accept={accept}
      multiple
      beforeUpload={() => false}
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

/** 分析结果面板 */
function ResultPanel({ result, loading }: { result: AnalysisResponse | null; loading: boolean }) {
  if (loading) {
    return (
      <Card size="small" title="📋 分析结果">
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin tip="正在分析中..." />
        </div>
      </Card>
    )
  }

  if (!result) {
    return (
      <Card size="small" title="📋 分析结果">
        <Empty description="请先上传数据并点击分析" />
      </Card>
    )
  }

  return (
    <>
      {result.charts && result.charts.length > 0 && (
        <Card size="small" title="📈 图表预览" style={{ marginTop: 16 }}>
          <Row gutter={[16, 16]}>
            {result.charts.map((chart) => (
              <Col key={chart.chart_id} xs={24} md={12}>
                <ChartDisplay chart={chart} />
              </Col>
            ))}
          </Row>
        </Card>
      )}

      {result.report && (
        <Card size="small" title="📝 分析报告" style={{ marginTop: 16 }}>
          <div style={{ fontSize: 13, lineHeight: 1.8 }}>
            <ReactMarkdown>{result.report}</ReactMarkdown>
          </div>
        </Card>
      )}
    </>
  )
}

// ==================== CCK8 面板 ====================

function CCK8Panel() {
  const [file, setFile] = useState<File | null>(null)
  const [fitModel, setFitModel] = useState('4pl')
  const [statMethod, setStatMethod] = useState('anova')
  const [errorBar, setErrorBar] = useState('sem')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalysisResponse | null>(null)

  const doAnalyze = async () => {
    if (!file) { message.warning('请先上传数据文件'); return }
    setLoading(true)
    try {
      const res = await analyzeCCK8(file, fitModel, statMethod, errorBar)
      setResult(res)
      message.success('CCK8 分析完成！')
    } catch (e: unknown) {
      message.error('分析失败: ' + (e as Error).message)
    }
    setLoading(false)
  }

  return (
    <div>
      <Title level={4}>CCK8 细胞增殖/毒性分析</Title>
      <Paragraph type="secondary">导入 OD 值数据，自动计算细胞活力、拟合剂量-效应曲线、计算 IC50</Paragraph>
      <TemplateBanner type="cck8" />
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card size="small" title="📊 数据导入">
            <Upload.Dragger
              accept=".xlsx,.csv" multiple={false}
              beforeUpload={(f) => { setFile(f); return false }}
              onRemove={() => setFile(null)}
              style={{ padding: '10px 0' }}
            >
              <p className="ant-upload-text"><InboxOutlined style={{ fontSize: 32, color: '#1677ff' }} /></p>
              <p className="ant-upload-text">点击或拖拽上传 Excel / CSV</p>
              <p className="ant-upload-hint">{file ? `已选择: ${file.name}` : '含 group, concentration, od_value 列'}</p>
            </Upload.Dragger>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card size="small" title="⚙️ 参数设置">
            <div style={{ marginBottom: 8 }}>
              <Text>拟合模型</Text>
              <Select value={fitModel} onChange={setFitModel} style={{ width: '100%' }} options={[
                { value: '4pl', label: '四参数 Logistic (4PL)' },
                { value: 'linear', label: '线性回归' },
                { value: 'log', label: '对数拟合' },
              ]} />
            </div>
            <div style={{ marginBottom: 8 }}>
              <Text>统计方法</Text>
              <Select value={statMethod} onChange={setStatMethod} style={{ width: '100%' }} options={[
                { value: 'anova', label: 'One-way ANOVA + Tukey' },
                { value: 'ttest', label: "Student's t-test" },
              ]} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <Text>误差棒</Text>
              <Select value={errorBar} onChange={setErrorBar} style={{ width: '100%' }} options={[
                { value: 'sem', label: 'Mean ± SEM' },
                { value: 'sd', label: 'Mean ± SD' },
              ]} />
            </div>
            <Button type="primary" icon={<PlayCircleOutlined />} block onClick={doAnalyze} loading={loading}>
              开始分析
            </Button>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <ResultPanel result={result} loading={loading} />
        </Col>
      </Row>
      {result && result.charts.length > 0 && (
        <Card size="small" title="📈 图表预览" style={{ marginTop: 16 }}>
          <Row gutter={[16, 16]}>
            {result.charts.map((c) => (
              <Col key={c.chart_id} xs={24} md={12}><ChartDisplay chart={c} /></Col>
            ))}
          </Row>
        </Card>
      )}
    </div>
  )
}

// ==================== EdU 面板 ====================

function EdUPanel() {
  const [files, setFiles] = useState<File[]>([])
  const [eduChannel, setEduChannel] = useState('green')
  const [threshold, setThreshold] = useState(30)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalysisResponse | null>(null)

  const doAnalyze = async () => {
    if (files.length === 0) { message.warning('请先上传图像'); return }
    setLoading(true)
    try {
      const res = await analyzeEdU(files, eduChannel, 'dapi', threshold)
      setResult(res)
      message.success('EdU 分析完成！')
    } catch (e: unknown) {
      message.error('分析失败: ' + (e as Error).message)
    }
    setLoading(false)
  }

  return (
    <div>
      <Title level={4}>EdU 细胞增殖图像分析</Title>
      <Paragraph type="secondary">上传 EdU 荧光图像，AI 自动识别 EdU+ 细胞和总细胞核，计算增殖率</Paragraph>
      <TemplateBanner type="edu" />
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card size="small" title="🖼️ 图像上传">
            <Upload.Dragger
              accept=".tif,.jpg,.png" multiple
              beforeUpload={(f) => { setFiles(prev => [...prev, f]); return false }}
              onRemove={(f) => setFiles(prev => prev.filter(x => x.name !== f.name))}
              style={{ padding: '10px 0' }}
            >
              <p className="ant-upload-text"><PictureOutlined style={{ fontSize: 36, color: '#1677ff' }} /></p>
              <p className="ant-upload-text">上传 EdU 荧光图像（可批量）</p>
              <p className="ant-upload-hint">{files.length > 0 ? `已选择 ${files.length} 张图像` : '支持 .tif / .jpg / .png'}</p>
            </Upload.Dragger>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card size="small" title="⚙️ 分析参数">
            <div style={{ marginBottom: 12 }}>
              <Text>EdU 通道颜色</Text>
              <Select value={eduChannel} onChange={setEduChannel} style={{ width: '100%' }} options={[
                { value: 'green', label: '绿色 (FITC / Alexa Fluor 488)' },
                { value: 'red', label: '红色 (Cy3 / Alexa Fluor 555)' },
                { value: 'far_red', label: '远红 (Cy5 / Alexa Fluor 647)' },
              ]} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <Text>核染料: DAPI / Hoechst (蓝色)</Text>
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text>EdU 阳性判定阈值: {threshold}</Text>
              <Slider value={threshold} onChange={setThreshold} min={1} max={100}
                marks={{ 10: '严格', 50: '中等', 90: '宽松' }} />
            </div>
            <Button type="primary" icon={<PlayCircleOutlined />} block onClick={doAnalyze} loading={loading}>
              开始分析
            </Button>
          </Card>
        </Col>
      </Row>
      <ResultPanel result={result} loading={loading} />
    </div>
  )
}

// ==================== 克隆形成 面板 ====================

function ColonyPanel() {
  const [files, setFiles] = useState<File[]>([])
  const [minArea, setMinArea] = useState(50)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalysisResponse | null>(null)

  const doAnalyze = async () => {
    if (files.length === 0) { message.warning('请先上传图像'); return }
    setLoading(true)
    try {
      const res = await analyzeColony(files, minArea, 'auto')
      setResult(res)
      message.success('克隆形成分析完成！')
    } catch (e: unknown) {
      message.error('分析失败: ' + (e as Error).message)
    }
    setLoading(false)
  }

  return (
    <div>
      <Title level={4}>细胞克隆形成分析</Title>
      <Paragraph type="secondary">上传结晶紫染色克隆图像，AI 自动识别和计数克隆集落</Paragraph>
      <TemplateBanner type="colony" />
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card size="small" title="🖼️ 图像上传">
            <Upload.Dragger
              accept=".tif,.jpg,.png,.bmp" multiple
              beforeUpload={(f) => { setFiles(prev => [...prev, f]); return false }}
              style={{ padding: '10px 0' }}
            >
              <p className="ant-upload-text"><PictureOutlined style={{ fontSize: 36, color: '#1677ff' }} /></p>
              <p className="ant-upload-text">上传结晶紫染色图像</p>
              <p className="ant-upload-hint">{files.length > 0 ? `已选择 ${files.length} 张图像` : '支持孔板/培养皿照片'}</p>
            </Upload.Dragger>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card size="small" title="⚙️ 分析参数">
            <div style={{ marginBottom: 12 }}>
              <Text>最小克隆面积 (像素)</Text>
              <InputNumber value={minArea} onChange={v => setMinArea(v || 50)} min={10} max={500} style={{ width: '100%' }} />
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text>分析区域: 自动检测孔/皿边界</Text>
            </div>
            <Button type="primary" icon={<PlayCircleOutlined />} block onClick={doAnalyze} loading={loading}>
              开始分析
            </Button>
          </Card>
        </Col>
      </Row>
      <ResultPanel result={result} loading={loading} />
    </div>
  )
}

// ==================== WB 面板 ====================

function WBPanel() {
  const [file, setFile] = useState<File | null>(null)
  const [lanes, setLanes] = useState(6)
  const [background, setBackground] = useState('rolling')
  const [housekeeping, setHousekeeping] = useState('gapdh')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalysisResponse | null>(null)

  const doAnalyze = async () => {
    if (!file) { message.warning('请先上传图像'); return }
    setLoading(true)
    try {
      const res = await analyzeWB(file, lanes, background, housekeeping)
      setResult(res)
      message.success('WB 定量分析完成！')
    } catch (e: unknown) {
      message.error('分析失败: ' + (e as Error).message)
    }
    setLoading(false)
  }

  return (
    <div>
      <Title level={4}>Western Blot 条带定量分析</Title>
      <Paragraph type="secondary">上传 WB 化学发光图像，自动识别泳道和条带，灰度定量</Paragraph>
      <TemplateBanner type="wb" />
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card size="small" title="🖼️ 图像上传">
            <Upload.Dragger
              accept=".tif,.jpg,.png,.bmp" multiple={false}
              beforeUpload={(f) => { setFile(f); return false }}
              onRemove={() => setFile(null)}
              style={{ padding: '10px 0' }}
            >
              <p className="ant-upload-text"><PictureOutlined style={{ fontSize: 36, color: '#1677ff' }} /></p>
              <p className="ant-upload-text">上传 WB 条带图像</p>
              <p className="ant-upload-hint">{file ? `已选择: ${file.name}` : '建议上传原始 16-bit TIFF'}</p>
            </Upload.Dragger>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card size="small" title="⚙️ 参数设置">
            <div style={{ marginBottom: 8 }}>
              <Text>泳道数</Text>
              <InputNumber value={lanes} onChange={v => setLanes(v || 6)} min={2} max={20} style={{ width: '100%' }} />
            </div>
            <div style={{ marginBottom: 8 }}>
              <Text>背景扣除</Text>
              <Select value={background} onChange={setBackground} style={{ width: '100%' }} options={[
                { value: 'rolling', label: 'Rolling Ball 算法' },
                { value: 'local', label: '局部背景扣除' },
                { value: 'none', label: '不扣除背景' },
              ]} />
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text>内参蛋白</Text>
              <Select value={housekeeping} onChange={setHousekeeping} style={{ width: '100%' }} options={[
                { value: 'gapdh', label: 'GAPDH' },
                { value: 'actin', label: 'β-actin' },
                { value: 'tubulin', label: 'β-tubulin' },
              ]} />
            </div>
            <Button type="primary" icon={<PlayCircleOutlined />} block onClick={doAnalyze} loading={loading}>
              开始定量分析
            </Button>
          </Card>
        </Col>
      </Row>
      <ResultPanel result={result} loading={loading} />
    </div>
  )
}

// ==================== qPCR 面板 ====================

function QPCRPanel() {
  const [file, setFile] = useState<File | null>(null)
  const [hkGenes, setHkGenes] = useState('GAPDH')
  const [controlGroup, setControlGroup] = useState('Control')
  const [method, setMethod] = useState('ddct')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalysisResponse | null>(null)

  const doAnalyze = async () => {
    if (!file) { message.warning('请先上传数据文件'); return }
    setLoading(true)
    try {
      const res = await analyzeQPCR(file, hkGenes, controlGroup, method)
      setResult(res)
      message.success('qPCR 分析完成！')
    } catch (e: unknown) {
      message.error('分析失败: ' + (e as Error).message)
    }
    setLoading(false)
  }

  return (
    <div>
      <Title level={4}>qPCR 结果分析</Title>
      <Paragraph type="secondary">导入 Ct 值数据，自动计算 ΔΔCt 和相对表达量</Paragraph>
      <TemplateBanner type="qpcr" />
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card size="small" title="📊 数据导入">
            <Upload.Dragger
              accept=".xlsx,.csv,.txt" multiple={false}
              beforeUpload={(f) => { setFile(f); return false }}
              style={{ padding: '10px 0' }}
            >
              <p className="ant-upload-text"><InboxOutlined style={{ fontSize: 32, color: '#1677ff' }} /></p>
              <p className="ant-upload-text">导入 Ct 值数据</p>
              <p className="ant-upload-hint">{file ? `已选择: ${file.name}` : '支持 Bio-Rad / ABI / Roche 导出格式'}</p>
            </Upload.Dragger>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card size="small" title="⚙️ 参数设置">
            <div style={{ marginBottom: 8 }}>
              <Text>内参基因</Text>
              <Select value={hkGenes} onChange={setHkGenes} style={{ width: '100%' }} options={[
                { value: 'GAPDH', label: 'GAPDH' },
                { value: 'ACTB', label: 'β-actin' },
                { value: '18S', label: '18S rRNA' },
              ]} />
            </div>
            <div style={{ marginBottom: 8 }}>
              <Text>对照组</Text>
              <Select value={controlGroup} onChange={setControlGroup} style={{ width: '100%' }} options={[
                { value: 'Control', label: 'Control 组' },
                { value: 'WT', label: 'WT 组' },
                { value: 'NC', label: 'NC 组' },
              ]} />
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text>计算方法</Text>
              <Select value={method} onChange={setMethod} style={{ width: '100%' }} options={[
                { value: 'ddct', label: 'ΔΔCt (2^(-ΔΔCt))' },
                { value: 'pfaffl', label: 'Pfaffl 法' },
              ]} />
            </div>
            <Button type="primary" icon={<PlayCircleOutlined />} block onClick={doAnalyze} loading={loading}>
              开始分析
            </Button>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <ResultPanel result={result} loading={loading} />
        </Col>
      </Row>
      {result && result.charts && result.charts.length > 0 && (
        <Card size="small" title="📈 图表预览" style={{ marginTop: 16 }}>
          <Row gutter={[16, 16]}>
            {result.charts.map((c) => (
              <Col key={c.chart_id} xs={24} md={12}><ChartDisplay chart={c} /></Col>
            ))}
          </Row>
        </Card>
      )}
    </div>
  )
}

// ==================== IHC 面板 ====================

function IHCPanel() {
  const [files, setFiles] = useState<File[]>([])
  const [stainType, setStainType] = useState('dab-he')
  const [dabThreshold, setDabThreshold] = useState(50)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalysisResponse | null>(null)

  const doAnalyze = async () => {
    if (files.length === 0) { message.warning('请先上传图像'); return }
    setLoading(true)
    try {
      const res = await analyzeIHC(files, stainType, dabThreshold)
      setResult(res)
      message.success('IHC 分析完成！')
    } catch (e: unknown) {
      message.error('分析失败: ' + (e as Error).message)
    }
    setLoading(false)
  }

  return (
    <div>
      <Title level={4}>IHC 免疫组化图像分析</Title>
      <Paragraph type="secondary">上传 IHC 染色图像，自动分离 DAB 阳性信号和苏木精复染，计算 H-Score</Paragraph>
      <TemplateBanner type="ihc" />
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card size="small" title="🖼️ 图像上传">
            <Upload.Dragger
              accept=".tif,.jpg,.png,.svs" multiple
              beforeUpload={(f) => { setFiles(prev => [...prev, f]); return false }}
              style={{ padding: '10px 0' }}
            >
              <p className="ant-upload-text"><PictureOutlined style={{ fontSize: 36, color: '#1677ff' }} /></p>
              <p className="ant-upload-text">上传 IHC 染色图像</p>
              <p className="ant-upload-hint">{files.length > 0 ? `已选择 ${files.length} 张图像` : '支持 DAB + Hematoxylin 染色图像'}</p>
            </Upload.Dragger>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card size="small" title="⚙️ 分析参数">
            <div style={{ marginBottom: 12 }}>
              <Text>染色方式</Text>
              <Select value={stainType} onChange={setStainType} style={{ width: '100%' }} options={[
                { value: 'dab-he', label: 'DAB (棕黄色) + 苏木精 (蓝色)' },
                { value: 'aec', label: 'AEC (红色) + 苏木精' },
                { value: 'if', label: '免疫荧光' },
              ]} />
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text>DAB 阳性阈值: {dabThreshold}</Text>
              <Slider value={dabThreshold} onChange={setDabThreshold} min={1} max={100} />
            </div>
            <Button type="primary" icon={<PlayCircleOutlined />} block onClick={doAnalyze} loading={loading}>
              开始分析
            </Button>
          </Card>
        </Col>
      </Row>
      <ResultPanel result={result} loading={loading} />
    </div>
  )
}

// ==================== 主组件 ====================

export default function ExperimentAnalysis() {
  const tabItems = [
    { key: 'cck8', label: <span><LineChartOutlined /> CCK8</span>, children: <CCK8Panel /> },
    { key: 'edu', label: <span><CameraOutlined /> EdU</span>, children: <EdUPanel /> },
    { key: 'colony', label: <span><ExperimentOutlined /> 克隆形成</span>, children: <ColonyPanel /> },
    { key: 'wb', label: <span><ScissorOutlined /> WB 定量</span>, children: <WBPanel /> },
    { key: 'qpcr', label: <span><LineChartOutlined /> qPCR</span>, children: <QPCRPanel /> },
    { key: 'ihc', label: <span><BulbOutlined /> IHC</span>, children: <IHCPanel /> },
  ]

  return <Tabs defaultActiveKey="cck8" items={tabItems} />
}
