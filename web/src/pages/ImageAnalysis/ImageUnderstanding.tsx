import { useState } from 'react'
import {
  Card, Row, Col, Typography, Upload, Button, Space, Select,
  Empty, message, Spin, Tag, Descriptions, Image as AntImage, Input,
} from 'antd'
import {
  CameraOutlined, UploadOutlined, BulbOutlined,
  SendOutlined, FileImageOutlined,
} from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import { understandImage, type ImageUnderstandingResponse } from '../../services/module2'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input

const ANALYSIS_TYPE_OPTIONS = [
  { value: 'general', label: '通用分析' },
  { value: 'microscopy', label: '显微镜图像' },
  { value: 'ihc', label: 'IHC 免疫组化' },
  { value: 'wb', label: 'Western Blot' },
  { value: 'other', label: '其他' },
]

export default function ImageUnderstanding() {
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string>('')
  const [prompt, setPrompt] = useState('请详细分析此图像的科学内容，包括图像类型、主要结构/元素、染色信息（如适用）、以及定量分析建议。')
  const [description, setDescription] = useState('')
  const [analysisType, setAnalysisType] = useState('general')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ImageUnderstandingResponse | null>(null)

  const handleFile = (f: File) => {
    setFile(f)
    setResult(null)
    // 生成预览 URL
    const url = URL.createObjectURL(f)
    setPreviewUrl(url)
    return false
  }

  const doAnalyze = async () => {
    if (!file) { message.warning('请先上传图像'); return }
    setLoading(true)
    setResult(null)
    try {
      const desc = description ? description : ''
      const res = await understandImage(file, prompt, desc, analysisType)
      setResult(res)
      if (res.success) {
        message.success('图像分析完成！')
      } else {
        message.warning(res.error || '分析失败，请检查 LLM 配置')
      }
    } catch (e: unknown) {
      message.error('分析失败: ' + (e as Error).message)
    }
    setLoading(false)
  }

  return (
    <div>
      <Title level={4}>AI 图像理解</Title>
      <Paragraph type="secondary">
        上传科研图像（支持 TIF/JPG/PNG），附加说明，AI 视觉模型自动分析图像内容、识别实验类型、给出定量建议和论文描述
      </Paragraph>

      {/* 提示信息 */}
      <Card size="small" style={{ marginBottom: 16, background: '#f6f8fa' }}>
        <Text type="secondary">
          💡 <strong>TIF 图像自动处理</strong>: 16-bit → 8-bit 对比度拉伸、多页取首页、转换为 PNG 后发送至 Vision 模型。
          图像分析直接使用 <Tag color="blue">OPENAI_API_KEY</Tag> 配置的 GPT 模型（如 gpt-4o），与 LLM_PROVIDER 无关。
        </Text>
      </Card>

      <Row gutter={[16, 16]}>
        {/* 左侧: 上传 + 设置 */}
        <Col xs={24} lg={10}>
          <Card size="small" title="🖼️ 图像上传">
            <Upload.Dragger
              accept=".tif,.tiff,.jpg,.jpeg,.png,.bmp"
              multiple={false}
              beforeUpload={handleFile}
              onRemove={() => { setFile(null); setPreviewUrl(''); setResult(null) }}
              style={{ padding: '16px 0' }}
            >
              <p className="ant-upload-drag-icon">
                <CameraOutlined style={{ fontSize: 40, color: '#1677ff' }} />
              </p>
              <p className="ant-upload-text">点击或拖拽上传图像</p>
              <p className="ant-upload-hint">
                {file ? `✅ ${file.name} (${(file.size / 1024).toFixed(1)} KB)` : '支持 .tif / .jpg / .png'}
              </p>
            </Upload.Dragger>

            {/* 图像预览 */}
            {previewUrl && (
              <div style={{ textAlign: 'center', marginTop: 16 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>图像预览</Text>
                <AntImage
                  src={previewUrl}
                  alt="preview"
                  style={{ maxWidth: '100%', maxHeight: 250, borderRadius: 8, marginTop: 8 }}
                  fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
                />
              </div>
            )}
          </Card>

          <Card size="small" title="⚙️ 分析设置" style={{ marginTop: 16 }}>
            <div style={{ marginBottom: 12 }}>
              <Text strong>图像类型</Text>
              <Select value={analysisType} onChange={setAnalysisType}
                style={{ width: '100%', marginTop: 4 }}
                options={ANALYSIS_TYPE_OPTIONS} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <Text strong>补充说明（可选）</Text>
              <TextArea
                rows={2}
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="例如: 这是结直肠癌组织的 IHC 染色，抗体为 Ki-67，放大倍数 200x..."
                style={{ marginTop: 4 }}
              />
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>分析提示</Text>
              <TextArea
                rows={4}
                value={prompt}
                onChange={e => setPrompt(e.target.value)}
                style={{ marginTop: 4 }}
              />
            </div>
            <Button type="primary" icon={<SendOutlined />} block
              onClick={doAnalyze} loading={loading} disabled={!file}>
              开始图像分析
            </Button>
          </Card>
        </Col>

        {/* 右侧: 分析结果 */}
        <Col xs={24} lg={14}>
          {loading ? (
            <Card size="small" title="🤖 AI 分析中...">
              <div style={{ textAlign: 'center', padding: 60 }}>
                <Spin size="large" tip="AI 正在分析图像，请稍候..." />
              </div>
            </Card>
          ) : result ? (
            <>
              {/* 图像信息 */}
              {result.image_info && (
                <Card size="small" title="📷 图像信息" style={{ marginBottom: 16 }}>
                  <Descriptions size="small" column={3}>
                    <Descriptions.Item label="尺寸">{result.image_info.width} × {result.image_info.height}</Descriptions.Item>
                    <Descriptions.Item label="模式">{result.image_info.mode}</Descriptions.Item>
                    <Descriptions.Item label="格式">{result.image_info.original_format}</Descriptions.Item>
                  </Descriptions>
                  {result.model_used && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      分析模型: <Tag>{result.model_used}</Tag>
                    </Text>
                  )}
                </Card>
              )}

              {/* 分析结果 */}
              <Card
                size="small"
                title="🤖 AI 分析结果"
                extra={result.success ? <Tag color="green">分析完成</Tag> : <Tag color="red">分析失败</Tag>}
              >
                {result.error && (
                  <div style={{
                    background: '#fff2f0', border: '1px solid #ffccc7',
                    padding: 16, borderRadius: 8, marginBottom: 16,
                  }}>
                    <Text type="danger">{result.error}</Text>
                  </div>
                )}
                {result.analysis ? (
                  <div style={{ fontSize: 14, lineHeight: 1.8, maxHeight: 600, overflow: 'auto' }}>
                    <ReactMarkdown>{result.analysis}</ReactMarkdown>
                  </div>
                ) : (
                  <Empty description="未获得分析结果" />
                )}
              </Card>
            </>
          ) : (
            <Card size="small" title="🤖 AI 分析结果">
              <Empty description="上传图像并点击分析后，AI 分析结果将显示在此" style={{ padding: 40 }} />
            </Card>
          )}
        </Col>
      </Row>
    </div>
  )
}
