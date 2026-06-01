const BASE = '/api'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Document {
  id: string
  title: string
  doc_type: string
  jurisdiction: string
  effective_date: string
  created_at: string
}

export interface SearchResult {
  rank: number
  doc_title: string
  article_num: string
  clause_type: string
  doc_type: string
  rrf_score?: number
  bm25_score?: number
  vector_distance?: number
  clause_text: string
}

export interface CompareResult {
  query: string
  bm25: CompareItem[]
  vector: CompareItem[]
  hybrid: CompareItem[]
}

export interface CompareItem {
  article_num: string
  clause_type: string
  snippet: string
}

export interface AskResult {
  question: string
  answer: string
  sources: AskSource[]
}

export interface AskSource {
  doc_title: string
  article_num: string
  doc_type: string
  clause_type: string
  rrf_score: number
  snippet: string
}

export interface RiskResult {
  doc_id: string
  total_articles: number
  risk_summary: { HIGH: number; MEDIUM: number; LOW: number }
  risk_items: RiskItem[]
}

export interface RiskItem {
  article_num: string
  article_title: string
  risk_level: 'HIGH' | 'MEDIUM' | 'LOW'
  risk_type: string
  matched_text: string
  snippet: string
}

export interface ComplianceResult {
  doc_id: string
  doc_title: string
  doc_type: string
  total_rules: number
  passed: number
  failed: number
  results: ComplianceRule[]
}

export interface ComplianceRule {
  rule_id: string
  law: string
  description: string
  passed: boolean
  message: string
}

export interface RagDimension {
  id: string
  category: string
  question: string
  verdict: '符合' | '不符合' | '條款缺失' | '無法判斷'
  reasoning: string
  law_evidence: string[]
  contract_evidence: string[]
}

export interface RagComplianceResult {
  doc_id: string
  doc_title: string
  doc_type: string
  method: 'rag'
  total: number
  passed: number
  failed: number
  results: RagDimension[]
}

// ─── API calls ────────────────────────────────────────────────────────────────

export const getDocuments = () =>
  get<{ total: number; documents: Document[] }>('/documents')

export const searchClauses = (
  q: string,
  mode: string,
  docType?: string,
  topK = 5,
) => {
  const p = new URLSearchParams({ q, mode, top_k: String(topK) })
  if (docType) p.append('doc_type', docType)
  return get<{ query: string; mode: string; total: number; results: SearchResult[] }>(
    `/search?${p}`,
  )
}

export const compareSearch = (q: string, docType?: string, topK = 3) => {
  const p = new URLSearchParams({ q, top_k: String(topK) })
  if (docType) p.append('doc_type', docType)
  return get<CompareResult>(`/compare?${p}`)
}

export const askQuestion = (question: string, docType?: string, topK = 5) =>
  post<AskResult>('/ask', { question, doc_type: docType ?? null, top_k: topK })

export const getRisk = (docId: string) =>
  get<RiskResult>(`/risk/${docId}`)

export const getCompliance = (docId: string) =>
  get<ComplianceResult>(`/compliance/${docId}`)

export const getRagCompliance = (docId: string) =>
  get<RagComplianceResult>(`/compliance/rag/${docId}`)

export const checkHealth = () =>
  get<{ status: string }>('/health')
