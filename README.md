# Legal RAG Demo

法律文件智慧檢索與問答系統，結合 Hybrid BM25 + Vector Search 與本地 LLM（Ollama），提供條款搜尋、合約風險分析、法規合規檢查等功能。

## 系統架構

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (React + Vite)            │
│   首頁 / 條款搜尋 / RAG 問答 / 合約分析              │
└───────────────────────┬─────────────────────────────┘
                        │ HTTP
┌───────────────────────▼─────────────────────────────┐
│              Backend (FastAPI, port 8088)            │
│  /search  /ask  /risk/:id  /compliance/:id  /compare │
└──────┬──────────────────────────┬────────────────────┘
       │                          │
┌──────▼──────┐          ┌────────▼────────┐
│  SQLite     │          │   ChromaDB      │
│  (BM25 FTS5)│          │  (Vector Index) │
│  條款關鍵字 │          │  條款語意向量   │
└─────────────┘          └────────┬────────┘
                                  │ Embedding
                         ┌────────▼────────┐
                         │  Ollama (本地)  │
                         │  bge-m3 / LLM   │
                         └─────────────────┘
```

### 搜尋核心：Hybrid BM25 + Vector + RRF

| 模式 | 原理 | 適用場景 |
|------|------|---------|
| BM25 | SQLite FTS5 關鍵字比對 | 法律術語、條號精確匹配（如「民法第184條」） |
| Vector | ChromaDB cosine 相似度 | 語意查詢（如「提早結束合約要賠多少」） |
| Hybrid | RRF 名次融合（k=60） | 預設模式，兩者互補，不需調整分數量綱 |

RRF（Reciprocal Rank Fusion）以名次取代原始分數合併，天然解決 BM25 負值與向量距離無法直接相加的問題。

---

## 功能一覽

- **條款搜尋**：三種模式（BM25 / Vector / Hybrid）可切換對比
- **RAG 問答**：召回相關條款後送本地 LLM 生成繁中答案，附條款出處引用
- **合約風險分析**：Rule-based 掃描 HIGH / MEDIUM / LOW 風險條款（違約賠償、競業禁止、免責條款等）
- **法規合規檢查**：對照勞動基準法、勞動基準法施行細則等規定，標記潛在違規條款
- **RAG 合規檢查**：將法規全文也 ingest 進向量庫，由 LLM 自動對照判斷，取代 hardcoded 規則
- **模式比較端點**：同一查詢同時回傳三種模式結果，方便並排展示

---

## 專案結構

```
legal-rag-demo/
├── app.py                  # FastAPI 主程式（API 路由）
├── run_etl.py              # ETL Pipeline 執行器
├── requirements.txt
│
├── etl/                    # 四步驟資料管線（每步可獨立重跑）
│   ├── 01_ingest_raw_docs.py      # 原始文件進入 SQLite
│   ├── 02_extract_clauses.py      # 條款擷取與分塊
│   ├── 03_normalize_metadata.py   # Metadata 正規化（clause_type / risk_level）
│   └── 04_build_vector_index.py   # 向量索引寫入 ChromaDB
│
├── rag/
│   ├── retriever.py        # BM25、Vector、RRF Fusion 核心邏輯
│   └── pipeline.py         # RAG 流程（召回 → 組 prompt → 呼叫 LLM）
│
├── search/
│   ├── clause_search.py    # 搜尋入口，分派三種模式
│   ├── risk_tagger.py      # 合約風險條款標記
│   ├── compliance_check.py # Rule-based 合規檢查
│   └── rag_compliance.py   # RAG-based 合規檢查
│
├── utils/
│   ├── db.py               # SQLite 連線設定
│   ├── embedding.py        # Embedding（優先 Ollama，fallback sentence-transformers）
│   └── io.py               # 檔案讀取工具
│
├── data/
│   ├── raw/                # 原始文件（PDF / TXT）
│   │   ├── nda_template.txt
│   │   ├── labor_contract.txt
│   │   ├── procurement_contract.txt
│   │   ├── labor_law.pdf
│   │   └── labor_law_enforcement_rules.pdf
│   ├── legal_docs.db       # SQLite 資料庫
│   └── chroma_db/          # ChromaDB 向量索引（.gitignore 排除）
│
└── frontend/               # React + TypeScript + Vite
    └── src/
        ├── pages/
        │   ├── Home/       # 首頁
        │   ├── Search/     # 條款搜尋
        │   ├── Ask/        # RAG 問答
        │   └── Analysis/   # 合約分析
        └── api/client.ts   # API 呼叫層
```

---

## 快速開始

### 前置需求

- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com/)（本地 LLM，可選）

### 1. 安裝後端相依套件

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
# 複製範本並填入設定（Ollama 預設不需修改）
cp .env.example .env
```

`.env` 可用變數：

```env
OLLAMA_URL=http://localhost:11434
LLM_MODEL=qwen2.5:3b
EMBEDDING_MODEL=bge-m3:latest
HF_TOKEN=hf_your_token_here   # 選填，HuggingFace token
```

> 若不啟動 Ollama，API 仍可運作，`/ask` 端點會直接回傳召回條款並說明 LLM 不可用。

### 3. 執行 ETL Pipeline（建立索引）

```bash
python run_etl.py
```

Pipeline 依序執行四個步驟，每步驟均為冪等設計，可單獨重跑：

```
Step 1：原始文件進入系統
Step 2：條款擷取與分塊（法律 Chunking）
Step 3：Metadata 正規化（clause_type / risk_level）
Step 4：向量索引建立（ChromaDB）
```

### 4. 啟動後端 API

```bash
python app.py
# API 運行於 http://localhost:8088
# 互動文件：http://localhost:8088/docs
```

### 5. 啟動前端

```bash
cd frontend
npm install
npm run dev
# 前端運行於 http://localhost:5200
```

---

## API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/health` | 健康檢查 |
| GET | `/documents` | 列出所有文件 |
| GET | `/search?q=...&mode=hybrid` | 條款搜尋（bm25 / vector / hybrid） |
| POST | `/ask` | RAG 問答，回傳答案 + 出處 |
| GET | `/risk/{doc_id}` | 合約風險分析報告 |
| GET | `/compliance/{doc_id}` | Rule-based 合規檢查 |
| GET | `/compliance/rag/{doc_id}` | RAG-based 合規檢查 |
| GET | `/compare?q=...` | 三種搜尋模式並排比較 |

### 搜尋範例

```bash
# Hybrid 搜尋（預設）
curl "http://localhost:8088/search?q=保密義務終止後還存在嗎&mode=hybrid"

# 三種模式並排比較
curl "http://localhost:8088/compare?q=違約賠償&top_k=3"

# RAG 問答
curl -X POST http://localhost:8088/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "競業禁止條款的期限是多久？", "doc_type": "勞動契約"}'
```

---

## 技術選型說明

| 元件 | 選擇 | 理由 |
|------|------|------|
| 向量資料庫 | ChromaDB | 輕量、本地部署、無需額外服務 |
| 關鍵字搜尋 | SQLite FTS5 | 內建 BM25，零依賴，與主資料庫合一 |
| LLM | Ollama (qwen2.5:3b) | 完全本地、免費、資料不外傳，3B 輕量適合本機執行 |
| Embedding | bge-m3 (Ollama) | 多語言向量模型，中文效果佳；fallback 至 sentence-transformers |
| Web Framework | FastAPI | 自動生成 OpenAPI 文件，async 支援 |
| 前端 | React + Vite + TypeScript | 快速開發，型別安全 |

---

## 注意事項

- `data/chroma_db/` 為向量索引目錄，已加入 `.gitignore`，需執行 ETL 後本地生成
- `data/legal_docs.db` 已隨 repo 附上（預建索引），可直接啟動 API 測試搜尋
- Ollama 為可選元件，不啟動時搜尋功能完整可用，僅 `/ask` 的 LLM 生成會降級
