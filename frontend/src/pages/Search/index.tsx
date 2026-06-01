import { useState } from 'react'
import { Input, Button, Select, Tag, Spin, Segmented } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { searchClauses, compareSearch, type SearchResult, type CompareItem } from '../../api/client'

const DOC_TYPES = [
  { label: '全部文件', value: '' },
  { label: 'NDA 保密協議', value: 'NDA' },
  { label: '勞動契約', value: '勞動契約' },
  { label: '採購合約', value: '採購合約' },
]

const CLAUSE_COLORS: Record<string, string> = {
  違約責任: '#dc2626', 終止條款: '#dc2626', 逾期罰款: '#dc2626', 競業禁止: '#dc2626',
  保密義務: '#d97706', 智財歸屬: '#d97706', 不可抗力: '#d97706', 付款條款: '#d97706',
  定義條款: '#16a34a', 爭議解決: '#16a34a', 工時工資: '#16a34a',
  一般條款: '#64748b',
}

const SAMPLES_SINGLE = [
  '保密義務終止後還持續多久',
  '競業禁止補償金',
  '逾期罰款上限',
]

const SAMPLES_COMPARE = [
  '提早解除合約賠償',
  '勞工特別休假',
  '不可抗力免責',
]

function ClauseTypTag({ type }: { type: string }) {
  const color = CLAUSE_COLORS[type] ?? '#64748b'
  return (
    <Tag style={{ color, borderColor: color + '44', background: color + '11', fontSize: 12 }}>
      {type}
    </Tag>
  )
}

function ResultCard({ r }: { r: SearchResult }) {
  return (
    <div className="result-card">
      <div className="result-header">
        <span className="result-article">{r.article_num}</span>
        <ClauseTypTag type={r.clause_type} />
        <Tag color="geekblue" style={{ fontSize: 12 }}>{r.doc_title || r.doc_type}</Tag>
      </div>
      <div className="result-snippet">{r.clause_text}</div>
      <div className="result-footer">
        {r.rrf_score != null && (
          <span className="score-chip">RRF {r.rrf_score.toFixed(4)}</span>
        )}
        {r.bm25_score != null && (
          <span className="score-chip">BM25 {r.bm25_score.toFixed(2)}</span>
        )}
        {r.vector_distance != null && (
          <span className="score-chip">dist {r.vector_distance.toFixed(3)}</span>
        )}
      </div>
    </div>
  )
}

function CompareColumn({
  mode, items, color,
}: {
  mode: string
  items: CompareItem[]
  color: string
}) {
  const labels: Record<string, string> = {
    bm25: '🔤 BM25 關鍵字',
    vector: '🧠 向量語意',
    hybrid: '⚡ Hybrid RRF',
  }
  return (
    <div className="compare-col">
      <div className={`compare-header ${mode}`}>
        <span>{labels[mode]}</span>
        <span style={{ marginLeft: 'auto', fontWeight: 400, opacity: 0.7, fontSize: 11 }}>
          {items.length} 筆
        </span>
      </div>
      <div className="compare-body">
        {items.length === 0 ? (
          <div className="compare-empty">未找到相關條款</div>
        ) : (
          items.map((item, i) => (
            <div key={i} className="compare-item">
              <div className="compare-art">
                {item.article_num}
                <ClauseTypTag type={item.clause_type} />
              </div>
              <div className="compare-snippet">{item.snippet}</div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default function Search() {
  const [query, setQuery] = useState('')
  const [docType, setDocType] = useState('')
  const [mode, setMode] = useState<'single' | 'compare'>('compare')
  const [searchMode, setSearchMode] = useState('hybrid')
  const [loading, setLoading] = useState(false)
  const [singleResults, setSingleResults] = useState<SearchResult[]>([])
  const [compareData, setCompareData] = useState<{
    bm25: CompareItem[]; vector: CompareItem[]; hybrid: CompareItem[]
  } | null>(null)

  const handleSearch = async () => {
    if (!query.trim()) return
    setLoading(true)
    setSingleResults([])
    setCompareData(null)
    try {
      if (mode === 'compare') {
        const res = await compareSearch(query, docType || undefined, 4)
        setCompareData(res)
      } else {
        const res = await searchClauses(query, searchMode, docType || undefined, 5)
        setSingleResults(res.results)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const samples = mode === 'compare' ? SAMPLES_COMPARE : SAMPLES_SINGLE

  return (
    <div className="page-wide">
      <div className="filter-bar">
        <div className="search-input-wrap">
          <div className="filter-label">搜尋條款</div>
          <Input
            size="large"
            placeholder="輸入關鍵字或語意查詢，例如：保密義務終止後還持續多久"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onPressEnter={handleSearch}
            prefix={<SearchOutlined />}
            allowClear
          />
        </div>

        <div className="filter-group">
          <div className="filter-label">文件類型</div>
          <Select
            size="large"
            value={docType}
            onChange={setDocType}
            style={{ width: 160 }}
            options={DOC_TYPES}
          />
        </div>

        <div className="filter-group">
          <div className="filter-label">查詢模式</div>
          <Segmented
            size="large"
            value={mode}
            onChange={(v) => setMode(v as 'single' | 'compare')}
            options={[
              { label: '單一模式', value: 'single' },
              { label: '三模式對比', value: 'compare' },
            ]}
          />
        </div>

        {mode === 'single' && (
          <div className="filter-group">
            <div className="filter-label">搜尋演算法</div>
            <Select
              size="large"
              value={searchMode}
              onChange={setSearchMode}
              style={{ width: 140 }}
              options={[
                { label: '⚡ Hybrid', value: 'hybrid' },
                { label: '🔤 BM25', value: 'bm25' },
                { label: '🧠 Vector', value: 'vector' },
              ]}
            />
          </div>
        )}

        <Button type="primary" size="large" onClick={handleSearch} loading={loading}>
          搜尋
        </Button>
      </div>

      {/* Sample queries */}
      <div style={{ marginBottom: 20 }}>
        <span style={{ fontSize: 13, color: '#64748b', marginRight: 10 }}>範例查詢：</span>
        <div className="sample-queries" style={{ display: 'inline-flex', flexWrap: 'wrap', gap: 8 }}>
          {samples.map((s) => (
            <span key={s} className="sample-chip" onClick={() => { setQuery(s); }}>
              {s}
            </span>
          ))}
        </div>
      </div>

      {/* Results */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#64748b' }}>搜尋中...</div>
        </div>
      )}

      {!loading && mode === 'compare' && compareData && (
        <>
          <div className="section-title">三模式對比結果</div>
          <div style={{ fontSize: 13, color: '#64748b', marginBottom: 16 }}>
            💡 同一個查詢「{query}」，三種演算法的召回差異
          </div>
          <div className="compare-grid">
            <CompareColumn mode="bm25" items={compareData.bm25} color="#92400e" />
            <CompareColumn mode="vector" items={compareData.vector} color="#5b21b6" />
            <CompareColumn mode="hybrid" items={compareData.hybrid} color="#14532d" />
          </div>
        </>
      )}

      {!loading && mode === 'single' && singleResults.length > 0 && (
        <>
          <div className="section-title">{singleResults.length} 筆結果</div>
          {singleResults.map((r) => (
            <ResultCard key={r.rank} r={r} />
          ))}
        </>
      )}

      {!loading && !compareData && singleResults.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">🔍</div>
          <div>輸入查詢後按搜尋，支援中文語意查詢</div>
          <div style={{ marginTop: 8, fontSize: 13 }}>
            切換「三模式對比」可並排看 BM25 vs 向量 vs Hybrid 的差異
          </div>
        </div>
      )}
    </div>
  )
}
