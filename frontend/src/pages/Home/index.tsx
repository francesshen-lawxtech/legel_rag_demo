import { useNavigate } from 'react-router-dom'

const FEATURES = [
  {
    icon: '🔍',
    title: '智能搜尋',
    desc: '同一個查詢，BM25 關鍵字搜尋 vs 向量語意搜尋 vs Hybrid RRF 融合，三模式並排對比，直觀理解為什麼 Hybrid 贏。',
    tag: 'BM25 + Vector + RRF',
    path: '/search',
  },
  {
    icon: '💬',
    title: 'RAG 問答',
    desc: '輸入法律問題，系統召回最相關條款後交給 LLM 生成答案，每個回答都附帶條款出處，杜絕幻覺。',
    tag: 'Hybrid Retrieval → LLM → Citation',
    path: '/ask',
  },
  {
    icon: '📋',
    title: '合約分析',
    desc: '自動掃描合約的高風險條款（違約、競業禁止、免責），並逐條比對勞基法、採購法等強制規定。',
    tag: 'Risk Tagging + Compliance Check',
    path: '/analysis',
  },
]

const TECH = [
  { label: 'FastAPI', color: '#059669', bg: '#d1fae5' },
  { label: 'SQLite FTS5 (BM25)', color: '#b45309', bg: '#fef3c7' },
  { label: 'ChromaDB (Vector)', color: '#7c3aed', bg: '#ede9fe' },
  { label: 'RRF Fusion', color: '#1d4ed8', bg: '#dbeafe' },
  { label: 'Ollama / bge-m3', color: '#0f766e', bg: '#ccfbf1' },
  { label: 'LangChain RAG', color: '#be185d', bg: '#fce7f3' },
  { label: 'React + Vite', color: '#0369a1', bg: '#e0f2fe' },
  { label: 'Ant Design', color: '#1a365d', bg: '#e8eaf6' },
]

export default function Home() {
  const navigate = useNavigate()

  return (
    <div className="page">
      <div className="home-hero">
        <h1>⚖️ Legal RAG Demo</h1>
        <p>
          法律文件智能搜尋與合約審閱系統 Demo<br />
          展示 Hybrid BM25 + Vector Search、RAG Pipeline、合規自動化三大核心能力
        </p>
      </div>

      <div className="feature-cards">
        {FEATURES.map((f) => (
          <a
            key={f.path}
            className="feature-card"
            onClick={() => navigate(f.path)}
            style={{ cursor: 'pointer' }}
          >
            <div className="feature-icon">{f.icon}</div>
            <h3>{f.title}</h3>
            <p>{f.desc}</p>
            <span className="feature-tag">{f.tag}</span>
          </a>
        ))}
      </div>

      <div className="tech-section">
        <h2>技術架構</h2>
        <div className="tech-stack">
          {TECH.map((t) => (
            <span
              key={t.label}
              className="tech-badge"
              style={{ background: t.bg, color: t.color }}
            >
              {t.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
