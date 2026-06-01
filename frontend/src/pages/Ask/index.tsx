import { useState } from 'react'
import { Button, Select, Spin, Tag, Alert } from 'antd'
import { askQuestion, type AskResult } from '../../api/client'

const DOC_TYPES = [
  { label: '全部文件', value: '' },
  { label: 'NDA 保密協議', value: 'NDA' },
  { label: '勞動契約', value: '勞動契約' },
  { label: '採購合約', value: '採購合約' },
]

const SAMPLE_QUESTIONS = [
  '競業禁止補償金如何計算？',
  '採購合約逾期罰款的上限是多少？',
  '保密義務在合約終止後還繼續多久？',
  '勞工特別休假未休完怎麼辦？',
  '不可抗力事件如何認定？',
]

export default function Ask() {
  const [question, setQuestion] = useState('')
  const [docType, setDocType] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AskResult | null>(null)
  const [error, setError] = useState('')

  const handleAsk = async () => {
    if (!question.trim()) return
    setLoading(true)
    setResult(null)
    setError('')
    try {
      const res = await askQuestion(question, docType || undefined, 5)
      setResult(res)
    } catch (e) {
      setError('API 呼叫失敗，請確認後端已啟動（python app.py）')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      {/* Input Section */}
      <div className="ask-section">
        <h2>💬 RAG 法律問答</h2>
        <div className="filter-bar" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
          <div>
            <div className="filter-label" style={{ marginBottom: 8 }}>問題</div>
            <textarea
              style={{
                width: '100%', minHeight: 80, padding: '10px 12px',
                border: '1px solid #e2e8f0', borderRadius: 8,
                fontSize: 15, resize: 'vertical', fontFamily: 'inherit',
                outline: 'none', lineHeight: 1.7,
              }}
              placeholder="輸入法律問題，例如：競業禁止補償金如何計算？"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && e.ctrlKey) handleAsk() }}
            />
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <div className="filter-group">
              <div className="filter-label">限定文件</div>
              <Select
                value={docType} onChange={setDocType}
                style={{ width: 160 }} options={DOC_TYPES}
              />
            </div>
            <Button
              type="primary" size="large"
              onClick={handleAsk} loading={loading}
              style={{ marginTop: 20 }}
            >
              送出問題
            </Button>
            <span style={{ fontSize: 12, color: '#94a3b8', marginTop: 20 }}>Ctrl+Enter</span>
          </div>
        </div>

        {/* Sample questions */}
        <div style={{ marginTop: 12 }}>
          <span style={{ fontSize: 13, color: '#64748b', marginRight: 10 }}>範例問題：</span>
          <div className="sample-queries">
            {SAMPLE_QUESTIONS.map((q) => (
              <span key={q} className="sample-chip" onClick={() => setQuestion(q)}>
                {q}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#64748b' }}>
            召回相關條款並生成答案中...
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <Alert type="error" message={error} showIcon style={{ marginBottom: 20 }} />
      )}

      {/* Result */}
      {result && !loading && (
        <>
          {/* LLM Answer */}
          <div className="ask-section">
            <div className="section-title">AI 回答</div>
            <div className="answer-box">
              <div className="answer-text">{result.answer}</div>
            </div>
          </div>

          {/* Sources */}
          {result.sources.length > 0 && (
            <div className="ask-section">
              <div className="section-title">引用來源（{result.sources.length} 個條款）</div>
              {result.sources.map((s, i) => (
                <div key={i} className="source-card">
                  <div className="source-meta">
                    <Tag color="navy" style={{ background: '#1a365d', color: '#fff', border: 'none' }}>
                      #{i + 1}
                    </Tag>
                    <Tag color="blue">{s.doc_title}</Tag>
                    <Tag style={{ fontWeight: 700 }}>{s.article_num}</Tag>
                    <Tag color="purple">{s.clause_type}</Tag>
                    <span style={{ fontSize: 12, color: '#94a3b8', marginLeft: 'auto' }}>
                      RRF {s.rrf_score.toFixed(4)}
                    </span>
                  </div>
                  <div className="source-snippet">{s.snippet}</div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Empty state */}
      {!result && !loading && !error && (
        <div className="empty-state">
          <div className="empty-icon">💬</div>
          <div>輸入法律問題，系統會從合約庫中召回最相關的條款</div>
          <div style={{ marginTop: 8, fontSize: 13 }}>
            需要 Ollama 運行中才能產生 LLM 答案；召回條款不需要 Ollama
          </div>
        </div>
      )}
    </div>
  )
}
