import { useState } from 'react'
import {
  Card, Row, Col, Typography, Upload, Button, Space, Empty,
  message, Spin, Input, Steps, Table, Alert,
} from 'antd'
import {
  CodeOutlined, PlayCircleOutlined, UploadOutlined,
  CopyOutlined, DownloadOutlined, ReloadOutlined, InboxOutlined,
} from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import {
  customGenerateCode, customExecuteCode,
  type GenerateCodeResponse, type ExecuteCodeResponse,
} from '../../services/module2'
import type { ChartItem } from '../../services/module2'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input

/** 图表预览 + 下载 */
function ChartCard({ chart }: { chart: ChartItem }) {
  return (
    <div style={{ textAlign: 'center', marginBottom: 12 }}>
      <Text strong style={{ fontSize: 12 }}>{chart.title}</Text>
      <img src={chart.base64} alt={chart.title} style={{ maxWidth: '100%', borderRadius: 8, marginTop: 8 }} />
      <br />
      <Button type="link" size="small" icon={<DownloadOutlined />}
        onClick={() => { const a = document.createElement('a'); a.href = chart.base64; a.download = `${chart.chart_id}.png`; a.click(); }}>
        下载
      </Button>
    </div>
  )
}

/** 数据预览表格 */
function DataPreview({ data, columns }: { data: Record<string, unknown>[]; columns: string[] }) {
  if (!data || data.length === 0) return null
  const cols = columns.map(c => ({ title: c, dataIndex: c, key: c, ellipsis: true }))
  return (
    <Table
      dataSource={data.map((row, i) => ({ ...row, _key: i }))}
      columns={cols}
      rowKey="_key"
      size="small"
      scroll={{ x: 'max-content' }}
      pagination={false}
      style={{ marginTop: 8 }}
    />
  )
}

export default function CustomAnalysis() {
  // Step 1: 上传
  const [file, setFile] = useState<File | null>(null)
  const [userPrompt, setUserPrompt] = useState('')
  const [loading, setLoading] = useState(false)

  // Step 2: 代码生成结果
  const [codeResult, setCodeResult] = useState<GenerateCodeResponse | null>(null)
  const [editedCode, setEditedCode] = useState('')

  // Step 3: 执行结果
  const [execResult, setExecResult] = useState<ExecuteCodeResponse | null>(null)
  const [execLoading, setExecLoading] = useState(false)

  const currentStep = execResult ? 2 : codeResult ? 1 : 0

  const doGenerate = async () => {
    if (!file) { message.warning('请先上传数据文件'); return }
    setLoading(true)
    setCodeResult(null)
    setExecResult(null)
    try {
      const res = await customGenerateCode(file, userPrompt)
      setCodeResult(res)
      setEditedCode(res.generated_code)
      message.success('代码生成完成！请查看并确认代码后点击执行。')
    } catch (e: unknown) {
      message.error('代码生成失败: ' + (e as Error).message)
    }
    setLoading(false)
  }

  const doExecute = async () => {
    setExecLoading(true)
    setExecResult(null)
    try {
      const res = await customExecuteCode(editedCode, codeResult?.data_file_id || '')
      setExecResult(res)
      if (res.success) {
        message.success(`执行成功！生成了 ${res.charts.length} 张图表`)
      } else {
        message.warning('执行完成，但有错误输出')
      }
    } catch (e: unknown) {
      message.error('执行失败: ' + (e as Error).message)
    }
    setExecLoading(false)
  }

  const copyCode = () => {
    navigator.clipboard.writeText(editedCode).then(() => message.success('已复制到剪贴板'))
  }

  return (
    <div>
      <Title level={4}>自定义数据分析</Title>
      <Paragraph type="secondary">
        上传数据文件 (.csv/.xlsx)，AI 自动读取数据结构，生成 Python 分析代码，执行后展示结果和图表
      </Paragraph>

      {/* 步骤指示器 */}
      <Steps
        current={currentStep}
        size="small"
        style={{ marginBottom: 24 }}
        items={[
          { title: '上传数据 + 描述需求' },
          { title: '查看/编辑代码' },
          { title: '执行 + 查看结果' },
        ]}
      />

      {/* Step 1: 上传 */}
      <Card size="small" title="📤 1. 上传数据文件" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} md={12}>
            <Upload.Dragger
              accept=".csv,.xlsx,.xls,.txt"
              multiple={false}
              beforeUpload={(f) => { setFile(f); return false }}
              onRemove={() => { setFile(null); setCodeResult(null); setExecResult(null) }}
              style={{ padding: '16px 0' }}
            >
              <p className="ant-upload-drag-icon"><InboxOutlined style={{ fontSize: 36, color: '#1677ff' }} /></p>
              <p className="ant-upload-text">点击或拖拽上传数据文件</p>
              <p className="ant-upload-hint">{file ? `✅ 已选择: ${file.name}` : '支持 .csv / .xlsx / .txt'}</p>
            </Upload.Dragger>
            {codeResult?.data_preview && (
              <DataPreview data={codeResult.data_preview} columns={codeResult.columns || []} />
            )}
          </Col>
          <Col xs={24} md={12}>
            <div style={{ marginBottom: 8 }}>
              <Text strong>分析需求描述（可选）</Text>
              <TextArea
                rows={4}
                value={userPrompt}
                onChange={e => setUserPrompt(e.target.value)}
                placeholder="例如: 请对数据进行分组统计分析，绘制柱状图，标注显著性差异..."
              />
            </div>
            <Button type="primary" icon={<CodeOutlined />} onClick={doGenerate}
              loading={loading} disabled={!file} block>
              生成分析代码
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Step 2: 代码展示 + 编辑 */}
      {codeResult && (
        <Card
          size="small"
          title="📝 2. Python 分析代码"
          style={{ marginBottom: 16 }}
          extra={
            <Space>
              <Button size="small" icon={<CopyOutlined />} onClick={copyCode}>复制</Button>
              <Button size="small" icon={<ReloadOutlined />}
                onClick={() => setEditedCode(codeResult.generated_code)}>重置</Button>
              <Button type="primary" size="small" icon={<PlayCircleOutlined />}
                onClick={doExecute} loading={execLoading}>执行代码</Button>
            </Space>
          }
        >
          {codeResult.explanation && (
            <Alert type="info" message={codeResult.explanation} style={{ marginBottom: 12 }} />
          )}
          <TextArea
            value={editedCode}
            onChange={e => setEditedCode(e.target.value)}
            rows={18}
            style={{
              fontFamily: '"Cascadia Code", "Fira Code", "JetBrains Mono", Consolas, monospace',
              fontSize: 13,
              lineHeight: 1.5,
              background: '#fafafa',
            }}
            placeholder="# Python 代码将在此显示..."
          />
        </Card>
      )}

      {/* Step 3: 执行结果 */}
      {execResult && (
        <Card size="small" title="📊 3. 执行结果">
          {execResult.error && (
            <Alert type="error" message="执行错误" description={execResult.error} style={{ marginBottom: 12 }} />
          )}

          {execResult.stdout && (
            <Card size="small" title="输出 (stdout)" style={{ marginBottom: 12 }}>
              <pre style={{
                maxHeight: 200, overflow: 'auto', fontSize: 12,
                background: '#f5f5f5', padding: 12, borderRadius: 4,
                whiteSpace: 'pre-wrap', wordBreak: 'break-all',
              }}>
                {execResult.stdout}
              </pre>
            </Card>
          )}

          {execResult.stderr && (
            <Card size="small" title="错误输出 (stderr)" style={{ marginBottom: 12 }}>
              <pre style={{
                maxHeight: 150, overflow: 'auto', fontSize: 12,
                background: '#fff2f0', padding: 12, borderRadius: 4,
                color: '#cf1322', whiteSpace: 'pre-wrap',
              }}>
                {execResult.stderr}
              </pre>
            </Card>
          )}

          {execResult.charts && execResult.charts.length > 0 && (
            <Card size="small" title={`📈 生成图表 (${execResult.charts.length} 张)`}>
              <Row gutter={[16, 16]}>
                {execResult.charts.map((chart, i) => (
                  <Col key={chart.chart_id || i} xs={24} md={12} lg={8}>
                    <ChartCard chart={chart} />
                  </Col>
                ))}
              </Row>
            </Card>
          )}

          {!execResult.stdout && !execResult.stderr && (!execResult.charts || execResult.charts.length === 0) && (
            <Empty description="代码执行完成，但没有输出内容" />
          )}
        </Card>
      )}
    </div>
  )
}
