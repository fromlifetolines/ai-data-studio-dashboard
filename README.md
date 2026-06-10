# AI Data Studio Dashboard

全渠道數據分析 + AI 洞察 Dashboard。整合 GA4、Google Search Console、Google Ads、Meta Ads，以無印風 × Fintech 介面呈現，透過 AI 提供可執行的行銷建議。

目前 GitHub Pages 會發布 `frontend/` 靜態 dashboard；若後端沒有啟動，前端會自動顯示 Demo Mode。啟動 FastAPI 後，前端會嘗試讀取 `http://localhost:8000/api/dashboard`，之後可以替換成正式 API domain。

## 快速開始

### 1. 安裝後端依賴

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 啟動 API 伺服器

```bash
cd backend
uvicorn main:app --reload --port 8000
```

API 文件：http://localhost:8000/docs

### 3. 開啟 Dashboard

用瀏覽器直接開啟 `frontend/index.html`，或使用本地伺服器：

```bash
cd frontend
python3 -m http.server 3000
```

然後前往 http://localhost:3000

### 4. 串接真實數據（選填）

1. 複製 `.env.example` 為 `.env`，填入 GA4 Property ID
2. 將 GCP Service Account JSON 放入 `credentials/service-account.json`
3. 詳細步驟請看 [Onboarding 教學](onboarding/index.html)

## GitHub Pages

專案內已包含 `.github/workflows/pages.yml`。推送到 GitHub `main` branch 後，到 repository 的 `Settings → Pages`，將 Source 設為 `GitHub Actions`，即可透過 GitHub Pages 查看 `frontend/` dashboard。

## 專案結構

```
ai-data-studio-dashboard/
├── backend/           # FastAPI 後端
│   ├── main.py        # API 進入點
│   ├── ga4_client.py  # GA4 數據撈取
│   └── ai_insight_engine.py  # AI 洞察
├── frontend/          # 前端 Dashboard
│   ├── index.html
│   ├── styles.css
│   └── dashboard.js
├── onboarding/        # 新手串接教學（4 步驟）
└── credentials/       # API 金鑰（.gitignore）
```

## API 端點

| 端點 | 說明 |
|------|------|
| `GET /api/health` | 健康檢查 + 設定狀態 |
| `GET /api/dashboard` | 完整 Dashboard 數據 |
| `GET /api/ga4` | GA4 原始數據 |
| `GET /api/ai-insight` | AI 洞察 |

## 開發模式

未設定 credentials 時，系統自動使用 **Demo Mode**（mock 數據），可直接預覽完整 UI 與 AI 洞察流程。

## 授權

Private — 商業用途
