import { useEffect, useState } from 'react'
import { Select, Button, Tabs, Spin, Alert, Tag, Collapse } from 'antd'
import { CheckCircleFilled, CloseCircleFilled, QuestionCircleFilled } from '@ant-design/icons'
import {
  getDocuments, getRisk, getCompliance, getRagCompliance,
  type Document, type RiskResult, type ComplianceResult,
  type RagComplianceResult,
} from '../../api/client'

// ─── Risk Tab ────────────────────────────────────────────────────────────────

function RiskBadge({ level }: { level: 'HIGH' | 'MEDIUM' | 'LOW' }) {
  return <span className={`risk-level-badge ${level}`}>{level}</span>
}

function RiskTab({ data }: { data: RiskResult }) {
  return (
    <>
      <div style={{ fontSize: 13, color: '#64748b', marginBottom: 16 }}>
        共分析 {data.total_articles} 條條款，發現 {data.risk_items.length} 個風險項目
      </div>
      <div className="risk-summary">
        <div className="risk-stat high">
          <div className="risk-stat-num">{data.risk_summary.HIGH}</div>
          <div className="risk-stat-label">高風險</div>
        </div>
        <div className="risk-stat medium">
          <div className="risk-stat-num">{data.risk_summary.MEDIUM}</div>
          <div className="risk-stat-label">中風險</div>
        </div>
        <div className="risk-stat low">
          <div className="risk-stat-num">{data.risk_summary.LOW}</div>
          <div className="risk-stat-label">低風險</div>
        </div>
      </div>
      <div className="section-title">風險條款清單</div>
      {data.risk_items.length === 0 ? (
        <div className="empty-state"><div>未發現風險條款</div></div>
      ) : (
        data.risk_items.map((item, i) => (
          <div key={i} className="risk-item">
            <RiskBadge level={item.risk_level} />
            <div className="risk-item-body">
              <div className="risk-item-title">
                {item.article_num}　{item.risk_type}
                <span style={{ fontSize: 12, color: '#94a3b8', fontWeight: 400, marginLeft: 8 }}>
                  觸發：「{item.matched_text}」
                </span>
              </div>
              <div className="risk-item-snippet">{item.snippet}...</div>
            </div>
          </div>
        ))
      )}
    </>
  )
}

// ─── Rule-based Compliance Tab ────────────────────────────────────────────────

function ComplianceTab({ data }: { data: ComplianceResult }) {
  return (
    <>
      <div style={{ display: 'flex', gap: 24, marginBottom: 20 }}>
        <div>
          <span style={{ fontSize: 28, fontWeight: 800, color: '#16a34a' }}>{data.passed}</span>
          <span style={{ color: '#64748b', marginLeft: 6 }}>項通過</span>
        </div>
        <div>
          <span style={{ fontSize: 28, fontWeight: 800, color: '#dc2626' }}>{data.failed}</span>
          <span style={{ color: '#64748b', marginLeft: 6 }}>項未通過</span>
        </div>
        <div style={{ fontSize: 13, color: '#64748b', alignSelf: 'flex-end', marginBottom: 6 }}>
          共 {data.total_rules} 條規定
        </div>
      </div>
      <div className="section-title">逐條檢查</div>
      {data.results.map((rule, i) => (
        <div key={i} className="compliance-item">
          <div className="compliance-icon">
            {rule.passed
              ? <CheckCircleFilled style={{ color: '#16a34a' }} />
              : <CloseCircleFilled style={{ color: '#dc2626' }} />}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: 14, color: '#1e293b' }}>{rule.description}</div>
            <div className="compliance-law">{rule.law}</div>
            <div className={`compliance-msg ${rule.passed ? 'pass' : 'fail'}`}>{rule.message}</div>
          </div>
        </div>
      ))}
    </>
  )
}

// ─── RAG Compliance Tab ───────────────────────────────────────────────────────

const VERDICT_CONFIG: Record<string, { color: string; bg: string; icon: React.ReactNode }> = {
  '符合':    { color: '#16a34a', bg: '#f0fdf4', icon: <CheckCircleFilled /> },
  '不符合':  { color: '#dc2626', bg: '#fef2f2', icon: <CloseCircleFilled /> },
  '條款缺失':{ color: '#d97706', bg: '#fffbeb', icon: <CloseCircleFilled /> },
  '無法判斷':{ color: '#64748b', bg: '#f8fafc', icon: <QuestionCircleFilled /> },
}

function RagComplianceTab({ data }: { data: RagComplianceResult }) {
  return (
    <>
      {/* Summary */}
      <div style={{ display: 'flex', gap: 24, marginBottom: 20, alignItems: 'flex-end' }}>
        <div>
          <span style={{ fontSize: 28, fontWeight: 800, color: '#16a34a' }}>{data.passed}</span>
          <span style={{ color: '#64748b', marginLeft: 6 }}>項符合</span>
        </div>
        <div>
          <span style={{ fontSize: 28, fontWeight: 800, color: '#dc2626' }}>{data.failed}</span>
          <span style={{ color: '#64748b', marginLeft: 6 }}>項不符合</span>
        </div>
        <Tag color="purple" style={{ marginBottom: 4 }}>RAG + LLM 判斷</Tag>
        <span style={{ fontSize: 12, color: '#94a3b8' }}>
          法規條文由 ChromaDB 召回，由 {'{LLM}'} 對照合約內容自動裁定
        </span>
      </div>

      <div className="section-title">AI 合規逐項分析</div>

      {data.results.map((dim, i) => {
        const cfg = VERDICT_CONFIG[dim.verdict] ?? VERDICT_CONFIG['無法判斷']
        return (
          <div key={i} style={{
            background: cfg.bg, border: `1px solid ${cfg.color}33`,
            borderRadius: 8, padding: '14px 16px', marginBottom: 12,
          }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <span style={{ color: cfg.color, fontSize: 18 }}>{cfg.icon}</span>
              <Tag style={{ color: cfg.color, borderColor: cfg.color + '66', background: 'white', fontWeight: 700 }}>
                {dim.verdict}
              </Tag>
              <Tag color="blue">{dim.id}</Tag>
              <span style={{ fontWeight: 700, fontSize: 14, color: '#1e293b' }}>{dim.category}</span>
            </div>

            {/* Question */}
            <div style={{ fontSize: 13, color: '#475569', marginBottom: 10 }}>
              審查問題：{dim.question}
            </div>

            {/* Reasoning */}
            <div style={{
              background: 'white', borderRadius: 6, padding: '10px 12px',
              fontSize: 13, lineHeight: 1.8, color: '#1e293b',
              borderLeft: `3px solid ${cfg.color}`,
            }}>
              {dim.reasoning}
            </div>

            {/* Evidence */}
            {(dim.law_evidence.length > 0 || dim.contract_evidence.length > 0) && (
              <Collapse
                ghost
                style={{ marginTop: 10 }}
                items={[
                  {
                    key: 'evidence',
                    label: <span style={{ fontSize: 12, color: '#64748b' }}>查看引用來源</span>,
                    children: (
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                        <div>
                          <div style={{ fontSize: 12, fontWeight: 700, color: '#7c3aed', marginBottom: 6 }}>
                            📖 法規條文
                          </div>
                          {dim.law_evidence.map((e, j) => (
                            <div key={j} style={{
                              fontSize: 12, color: '#4c1d95', background: '#ede9fe',
                              borderRadius: 4, padding: '6px 8px', marginBottom: 6,
                            }}>{e}</div>
                          ))}
                          {dim.law_evidence.length === 0 && (
                            <div style={{ fontSize: 12, color: '#94a3b8' }}>
                              未找到相關法規（請先 ingest 勞動基準法 PDF）
                            </div>
                          )}
                        </div>
                        <div>
                          <div style={{ fontSize: 12, fontWeight: 700, color: '#1d4ed8', marginBottom: 6 }}>
                            📄 合約條款
                          </div>
                          {dim.contract_evidence.map((e, j) => (
                            <div key={j} style={{
                              fontSize: 12, color: '#1e3a5f', background: '#dbeafe',
                              borderRadius: 4, padding: '6px 8px', marginBottom: 6,
                            }}>{e}</div>
                          ))}
                          {dim.contract_evidence.length === 0 && (
                            <div style={{ fontSize: 12, color: '#94a3b8' }}>未找到相關條款</div>
                          )}
                        </div>
                      </div>
                    ),
                  },
                ]}
              />
            )}
          </div>
        )
      })}
    </>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function Analysis() {
  const [docs, setDocs] = useState<Document[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [riskData, setRiskData] = useState<RiskResult | null>(null)
  const [complianceData, setComplianceData] = useState<ComplianceResult | null>(null)
  const [ragData, setRagData] = useState<RagComplianceResult | null>(null)

  useEffect(() => {
    getDocuments()
      .then((res) => {
        setDocs(res.documents)
        if (res.documents.length > 0) setSelectedId(res.documents[0].id)
      })
      .catch(() => setError('無法載入文件清單，請先執行 ETL Pipeline'))
  }, [])

  const handleAnalyze = async () => {
    if (!selectedId) return
    setLoading(true)
    setError('')
    setRiskData(null)
    setComplianceData(null)
    setRagData(null)
    try {
      const [risk, compliance, rag] = await Promise.all([
        getRisk(selectedId),
        getCompliance(selectedId),
        getRagCompliance(selectedId),
      ])
      setRiskData(risk)
      setComplianceData(compliance)
      setRagData(rag)
    } catch (e) {
      setError('分析失敗，請確認已執行 ETL Pipeline 且 Ollama 正在運行')
    } finally {
      setLoading(false)
    }
  }

  const selectedDoc = docs.find((d) => d.id === selectedId)

  return (
    <div className="page">
      <div className="doc-selector-bar">
        <div style={{ fontSize: 16, fontWeight: 700, color: '#1a365d', marginBottom: 16 }}>
          📋 合約分析
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <div>
            <div className="filter-label" style={{ marginBottom: 4 }}>選擇合約</div>
            <Select
              size="large" style={{ width: 320 }}
              value={selectedId} onChange={setSelectedId}
              options={docs.map((d) => ({ label: `${d.title}（${d.id}）`, value: d.id }))}
              placeholder="請先執行 run_etl.py"
            />
          </div>
          <Button
            type="primary" size="large"
            onClick={handleAnalyze} loading={loading}
            disabled={!selectedId}
            style={{ marginTop: 20 }}
          >
            開始分析
          </Button>
          {selectedDoc && (
            <div style={{ marginTop: 20, fontSize: 13, color: '#64748b' }}>
              文件類型：{selectedDoc.doc_type}　生效日期：{selectedDoc.effective_date}
            </div>
          )}
        </div>
      </div>

      {error && (
        <Alert type="warning" showIcon message={error}
          description="請先執行：python run_etl.py，並確認 Ollama 運行中" style={{ marginBottom: 20 }} />
      )}

      {loading && (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#64748b' }}>
            分析中（RAG 合規需呼叫 LLM，約需 30-60 秒）...
          </div>
        </div>
      )}

      {!loading && riskData && complianceData && ragData && (
        <Tabs
          defaultActiveKey="rag"
          size="large"
          items={[
            {
              key: 'rag',
              label: (
                <span>
                  🤖 AI 合規分析
                  {ragData.failed > 0 && (
                    <span style={{
                      marginLeft: 8, background: '#dc2626', color: '#fff',
                      borderRadius: 10, padding: '1px 7px', fontSize: 12,
                    }}>
                      {ragData.failed} 不符合
                    </span>
                  )}
                </span>
              ),
              children: <RagComplianceTab data={ragData} />,
            },
            {
              key: 'risk',
              label: (
                <span>
                  ⚠️ 風險標記
                  {riskData.risk_summary.HIGH > 0 && (
                    <span style={{
                      marginLeft: 8, background: '#dc2626', color: '#fff',
                      borderRadius: 10, padding: '1px 7px', fontSize: 12,
                    }}>
                      {riskData.risk_summary.HIGH} HIGH
                    </span>
                  )}
                </span>
              ),
              children: <RiskTab data={riskData} />,
            },
            {
              key: 'compliance',
              label: (
                <span>
                  ✅ 規則合規
                  {complianceData.failed > 0 && (
                    <span style={{
                      marginLeft: 8, background: '#d97706', color: '#fff',
                      borderRadius: 10, padding: '1px 7px', fontSize: 12,
                    }}>
                      {complianceData.failed} 待確認
                    </span>
                  )}
                </span>
              ),
              children: <ComplianceTab data={complianceData} />,
            },
          ]}
        />
      )}

      {!loading && !riskData && !error && (
        <div className="empty-state">
          <div className="empty-icon">📋</div>
          <div>選擇合約後點擊「開始分析」</div>
          <div style={{ marginTop: 8, fontSize: 13 }}>
            🤖 AI 合規分析：LLM 對照勞基法自動裁定，需 Ollama 運行<br />
            ⚠️ 風險標記：rule-based 掃描，不需要 LLM<br />
            ✅ 規則合規：regex 比對，不需要 LLM
          </div>
        </div>
      )}
    </div>
  )
}
