"""
AI Data Studio — backend/main.py
FastAPI 後端 API 進入點

啟動方式：
  cd backend
  uvicorn main:app --reload --port 8000

API 文件：
  http://localhost:8000/docs
"""

import os
import json
import asyncio
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── 本地模組 ──────────────────────────────────────────
from ga4_client import GA4Client, GA4Config
from ai_insight_engine import generate_insight
from gsc_client import GSCClient
from gads_client import GoogleAdsClient
from meta_client import MetaAdsClient

# ── App 初始化 ────────────────────────────────────────
app = FastAPI(
    title="AI Data Studio API",
    description="全渠道數據分析後端，串接 GA4 / Search Console / Google Ads / Meta Ads",
    version="1.0.0"
)

# ── CORS（允許前端 GitHub Pages 呼叫）────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 設定檔路徑 ────────────────────────────────────────
SETTINGS_PATH = Path(__file__).parent.parent / "credentials" / "settings.json"
CREDENTIALS_DIR = Path(__file__).parent.parent / "credentials"
CREDENTIALS_DIR.mkdir(exist_ok=True)

# ══════════════════════════════════════════════════════
# Request / Response 資料模型
# ══════════════════════════════════════════════════════

class GA4Settings(BaseModel):
    property_id: str           # 例：properties/123456789
    credentials_json: str      # Service Account JSON 內容（字串）

class GSCSettings(BaseModel):
    site_url: str

class GAdsSettings(BaseModel):
    customer_id: str
    developer_token: str
    client_id: str
    client_secret: str
    refresh_token: str

class MetaSettings(BaseModel):
    account_id: str
    token: str

class SaveSettingsRequest(BaseModel):
    ga4: Optional[GA4Settings] = None
    gsc: Optional[GSCSettings] = None
    gads: Optional[GAdsSettings] = None
    meta: Optional[MetaSettings] = None
    openai_key: Optional[str] = None

class ValidateRequest(BaseModel):
    property_id: str
    credentials_json: str

class GSCValidateRequest(BaseModel):
    site_url: str

class GAdsValidateRequest(BaseModel):
    customer_id: str
    developer_token: str
    client_id: str
    client_secret: str
    refresh_token: str

class MetaValidateRequest(BaseModel):
    account_id: str
    token: str

# ══════════════════════════════════════════════════════
# 工具函式
# ══════════════════════════════════════════════════════

def load_settings() -> dict:
    """讀取本地設定檔"""
    if SETTINGS_PATH.exists():
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_settings(data: dict):
    """儲存設定到本地檔案"""
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_credentials_path() -> Optional[Path]:
    """取得 Service Account JSON 檔案路徑"""
    path = CREDENTIALS_DIR / "service-account.json"
    return path if path.exists() else None

# ══════════════════════════════════════════════════════
# API 路由
# ══════════════════════════════════════════════════════

# ── 健康檢查 ──────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    """健康檢查 + 設定狀態"""
    settings = load_settings()
    cred_path = get_credentials_path()

    return {
        "status": "ok",
        "version": "1.0.0",
        "config": {
            "ga4_configured":         bool(settings.get("ga4_property_id")) and cred_path is not None,
            "ga4_property_id":        settings.get("ga4_property_id", ""),
            "openai_configured":      bool(settings.get("openai_key") or os.getenv("OPENAI_API_KEY")),
            "credentials_file_exists": cred_path is not None,
            "gsc_configured":          bool(settings.get("gsc_site_url")) and cred_path is not None,
            "gads_configured":         bool(settings.get("gads_customer_id")),
            "meta_configured":         bool(settings.get("meta_account_id")),
            "demo_mode":              not (bool(settings.get("ga4_property_id")) and cred_path is not None),
        }
    }

# ── 儲存設定 ──────────────────────────────────────────
@app.post("/api/settings/save")
async def save_api_settings(req: SaveSettingsRequest):
    """
    儲存 GA4 Property ID、Service Account JSON、OpenAI Key、GSC、Google Ads、Meta Ads 設定
    這是用戶在「設定頁面」填完表單後呼叫的端點
    """
    settings = load_settings()

    if req.ga4:
        # 標準化 Property ID 格式
        prop_id = req.ga4.property_id.strip()
        if not prop_id.startswith("properties/"):
            prop_id = f"properties/{prop_id}"
        settings["ga4_property_id"] = prop_id

        # 儲存 Service Account JSON 到 credentials/ 目錄
        cred_path = CREDENTIALS_DIR / "service-account.json"
        try:
            parsed = json.loads(req.ga4.credentials_json)
            with open(cred_path, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Service Account JSON 格式錯誤，請確認內容是完整的 JSON 格式。")

    if req.gsc:
        settings["gsc_site_url"] = req.gsc.site_url.strip()

    if req.gads:
        settings["gads_customer_id"] = req.gads.customer_id.strip()
        settings["gads_developer_token"] = req.gads.developer_token.strip()
        settings["gads_client_id"] = req.gads.client_id.strip()
        settings["gads_client_secret"] = req.gads.client_secret.strip()
        settings["gads_refresh_token"] = req.gads.refresh_token.strip()

    if req.meta:
        settings["meta_account_id"] = req.meta.account_id.strip()
        settings["meta_token"] = req.meta.token.strip()

    if req.openai_key:
        settings["openai_key"] = req.openai_key.strip()

    save_settings(settings)
    return {"success": True, "message": "設定已儲存"}

# ── 驗證 GA4 連線 ─────────────────────────────────────
@app.post("/api/settings/validate-ga4")
async def validate_ga4(req: ValidateRequest):
    """
    驗證 GA4 Property ID + Service Account 是否能成功連線
    """
    try:
        # 暫時寫入 credentials 測試
        temp_path = CREDENTIALS_DIR / "service-account.json"
        parsed = json.loads(req.credentials_json)
        with open(temp_path, "w") as f:
            json.dump(parsed, f)

        prop_id = req.property_id
        if not prop_id.startswith("properties/"):
            prop_id = f"properties/{prop_id}"

        config = GA4Config(
            property_id=prop_id,
            credentials_path=str(temp_path)
        )
        client = GA4Client(config)
        result = client.test_connection()

        return {"success": True, "message": "GA4 連線成功！", "property_name": result.get("name", "")}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Service Account JSON 格式錯誤")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"連線失敗：{str(e)}")

# ── 驗證 Search Console 連線 ───────────────────────────
@app.post("/api/settings/validate-gsc")
async def validate_gsc(req: GSCValidateRequest):
    """
    驗證 Search Console 連線
    """
    cred_path = get_credentials_path()
    if not cred_path:
        raise HTTPException(status_code=400, detail="請先上傳或貼上 GA4 的 Service Account JSON，兩者使用相同金鑰。")
    try:
        client = GSCClient(str(cred_path), req.site_url)
        result = client.test_connection()
        return {"success": True, "message": f"Search Console 連線成功！已連接到 {result['site']}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"連線失敗：{str(e)}")

# ── 驗證 Google Ads 連線 ─────────────────────────────
@app.post("/api/settings/validate-gads")
async def validate_gads(req: GAdsValidateRequest):
    """
    驗證 Google Ads 連線
    """
    try:
        client = GoogleAdsClient(
            customer_id=req.customer_id,
            developer_token=req.developer_token,
            client_id=req.client_id,
            client_secret=req.client_secret,
            refresh_token=req.refresh_token
        )
        result = client.test_connection()
        return {"success": True, "message": f"Google Ads 連線成功！客戶 ID: {result['customer_id']}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"連線失敗：{str(e)}")

# ── 驗證 Meta Ads 連線 ───────────────────────────────
@app.post("/api/settings/validate-meta")
async def validate_meta(req: MetaValidateRequest):
    """
    驗證 Meta Ads 連線
    """
    try:
        client = MetaAdsClient(
            ad_account_id=req.account_id,
            access_token=req.token
        )
        result = client.test_connection()
        return {"success": True, "message": f"Meta Ads 連線成功！帳戶名稱: {result['name']}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"連線失敗：{str(e)}")

# ── 讀取目前設定 ──────────────────────────────────────
@app.get("/api/settings")
async def get_settings():
    """讀取目前的設定狀態（不回傳敏感資訊）"""
    settings = load_settings()
    cred_path = get_credentials_path()

    return {
        "ga4_property_id":         settings.get("ga4_property_id", ""),
        "ga4_configured":          bool(settings.get("ga4_property_id")) and cred_path is not None,
        "openai_configured":       bool(settings.get("openai_key") or os.getenv("OPENAI_API_KEY")),
        "credentials_file_exists": cred_path is not None,
        "gsc_site_url":            settings.get("gsc_site_url", ""),
        "gsc_configured":          bool(settings.get("gsc_site_url")) and cred_path is not None,
        "gads_customer_id":        settings.get("gads_customer_id", ""),
        "gads_developer_token":    settings.get("gads_developer_token", ""),
        "gads_client_id":          settings.get("gads_client_id", ""),
        "gads_client_secret":      settings.get("gads_client_secret", ""),
        "gads_refresh_token":      settings.get("gads_refresh_token", ""),
        "gads_configured":         bool(settings.get("gads_customer_id")),
        "meta_account_id":         settings.get("meta_account_id", ""),
        "meta_token":              settings.get("meta_token", ""),
        "meta_configured":         bool(settings.get("meta_account_id"))
    }

# ── 完整 Dashboard 數據 ───────────────────────────────
@app.get("/api/dashboard")
async def get_dashboard(
    start_date: str = "30daysAgo",
    end_date:   str = "today"
):
    """
    主要 API：回傳完整 Dashboard 所需的所有數據
    前端 dashboard.js 呼叫這個端點

    Query params:
      start_date: 例 "7daysAgo", "30daysAgo", "2025-01-01"
      end_date:   例 "today", "2025-06-08"
    """
    settings = load_settings()
    cred_path = get_credentials_path()

    # ── Demo Mode：沒有設定 credentials 時返回假數據 ──
    if not settings.get("ga4_property_id") or not cred_path:
        return JSONResponse(content={
            "mode": "demo",
            "message": "目前為 Demo 模式。請至「設定」頁面輸入 GA4 Property ID 與 Service Account 金鑰以顯示真實數據。",
            "data": _get_demo_data()
        })

    # ── 真實模式：呼叫 GA4 / GSC / Ads API ────────────────
    try:
        # 1. 準備各種 Clients
        ga4_client = None
        if settings.get("ga4_property_id") and cred_path:
            config = GA4Config(
                property_id=settings["ga4_property_id"],
                credentials_path=str(cred_path)
            )
            ga4_client = GA4Client(config)

        gsc_client = None
        if settings.get("gsc_site_url") and cred_path:
            gsc_client = GSCClient(str(cred_path), settings["gsc_site_url"])

        gads_client = None
        if settings.get("gads_customer_id") and settings.get("gads_developer_token"):
            gads_client = GoogleAdsClient(
                customer_id=settings["gads_customer_id"],
                developer_token=settings["gads_developer_token"],
                client_id=settings.get("gads_client_id", ""),
                client_secret=settings.get("gads_client_secret", ""),
                refresh_token=settings.get("gads_refresh_token", "")
            )

        meta_client = None
        if settings.get("meta_account_id") and settings.get("meta_token"):
            meta_client = MetaAdsClient(
                ad_account_id=settings["meta_account_id"],
                access_token=settings["meta_token"]
            )

        # 2. 並行拉取數據
        tasks = []
        
        # GA4 Tasks
        if ga4_client:
            tasks.append(asyncio.to_thread(ga4_client.get_overview, start_date, end_date))
            tasks.append(asyncio.to_thread(ga4_client.get_sessions_trend, start_date, end_date))
            tasks.append(asyncio.to_thread(ga4_client.get_traffic_sources, start_date, end_date))
            tasks.append(asyncio.to_thread(ga4_client.get_top_pages, start_date, end_date))
            tasks.append(asyncio.to_thread(ga4_client.get_device_breakdown, start_date, end_date))
        else:
            tasks.extend([None, None, None, None, None])

        # GSC Tasks
        if gsc_client:
            tasks.append(asyncio.to_thread(gsc_client.get_keywords_report, start_date, end_date))
            tasks.append(asyncio.to_thread(gsc_client.get_daily_trends, "13daysAgo", "today"))
            tasks.append(asyncio.to_thread(gsc_client.get_search_type_breakdown, start_date, end_date))
        else:
            tasks.extend([None, None, None])

        # GAds Tasks
        if gads_client:
            tasks.append(asyncio.to_thread(gads_client.get_campaigns_report, start_date, end_date))
            tasks.append(asyncio.to_thread(gads_client.get_daily_trends, "13daysAgo", "today"))
        else:
            tasks.extend([None, None])

        # Meta Tasks
        if meta_client:
            tasks.append(asyncio.to_thread(meta_client.get_campaigns_report, start_date, end_date))
            tasks.append(asyncio.to_thread(meta_client.get_daily_trends, "13daysAgo", "today"))
        else:
            tasks.extend([None, None])

        # 執行 Tasks
        # 過濾非 None 任務來並行執行，以防 exceptions
        exec_tasks = [t for t in tasks if t is not None]
        raw_results = await asyncio.gather(*exec_tasks, return_exceptions=True)
        
        # 還原到對應位置
        results = []
        result_idx = 0
        for t in tasks:
            if t is None:
                results.append(None)
            else:
                r = raw_results[result_idx]
                if isinstance(r, Exception):
                    print(f"[WARN] 數據拉取失敗：{r}")
                    results.append(None)
                else:
                    results.append(r)
                result_idx += 1

        # 展開結果
        ga4_overview, ga4_sessions_trend, ga4_traffic_sources, ga4_top_pages, ga4_device = results[0:5]
        gsc_kws, gsc_trend, gsc_search_type = results[5:8]
        gads_campaigns, gads_trend = results[8:10]
        meta_campaigns, meta_trend = results[10:12]

        demo = _get_demo_data()

        # 3. 處理 GA4 數據
        if not ga4_overview:
            ga4_overview = {}
        sessions_val = f"{ga4_overview.get('sessions', 0):,}" if "sessions" in ga4_overview else demo["kpis"]["sessions"]["value"]
        sessions_delta = ga4_overview.get("sessions_delta", "—")
        sessions_trend = "up" if "+" in sessions_delta else "down" if "-" in sessions_delta else "flat"

        users_val = f"{ga4_overview.get('users', 0):,}" if "users" in ga4_overview else demo["kpis"]["users"]["value"]
        users_delta = ga4_overview.get("users_delta", "—")
        users_trend = "up" if "+" in users_delta else "down" if "-" in users_delta else "flat"

        s_trend = ga4_sessions_trend.get("sessions_trend", []) if ga4_sessions_trend else demo["sessions_trend"]
        u_trend = ga4_sessions_trend.get("users_trend", []) if ga4_sessions_trend else demo["users_trend"]
        nu_trend = ga4_sessions_trend.get("new_users_trend", []) if ga4_sessions_trend else demo["new_users_trend"]

        t_sources = ga4_traffic_sources if ga4_traffic_sources else demo["traffic_source"]
        dev_data = ga4_device if ga4_device else demo["device"]
        pages_data = ga4_top_pages if ga4_top_pages else demo["pages"]

        # 4. 處理 GSC 數據
        kws = gsc_kws if gsc_kws is not None else demo["keywords"]
        
        # 曝光 KPI
        gsc_total_imp = 0
        if gsc_trend and gsc_trend.get("ssc_imp"):
            gsc_total_imp = sum(gsc_trend["ssc_imp"])
            
        imp_val = f"{gsc_total_imp:,}" if gsc_total_imp > 0 else demo["kpis"]["impressions"]["value"]
        imp_delta = "—"
        imp_trend = "flat"

        ssc_imp = gsc_trend.get("ssc_imp", []) if gsc_trend else demo["ssc_imp"]
        ssc_click = gsc_trend.get("ssc_click", []) if gsc_trend else demo["ssc_click"]
        search_type = gsc_search_type if gsc_search_type else demo["search_type"]

        # 5. 處理廣告數據 (Google Ads & Meta Ads)
        channels = []
        total_spend = 0.0
        total_rev = 0.0
        
        # Google Ads
        gads_spend = 0.0
        gads_imp = 0
        gads_clicks = 0
        gads_conv = 0.0
        gads_rev = 0.0
        
        if gads_campaigns:
            for c in gads_campaigns:
                gads_spend += c["spend"]
                gads_imp += c["imp"]
                gads_clicks += c["click"]
                gads_conv += c["conv"]
                gads_rev += c["spend"] * c["roas"]
            
            total_spend += gads_spend
            total_rev += gads_rev
            
            gads_roas = gads_rev / gads_spend if gads_spend > 0 else 0.0
            gads_cpa = gads_spend / gads_conv if gads_conv > 0 else 0.0
            channels.append({
                "name": "Google Ads",
                "icon": "ti-brand-google",
                "icon_bg": "#EFF6FF",
                "icon_color": "#1d4ed8",
                "spend": f"${gads_spend:,.0f}",
                "imp": f"{gads_imp/1000:.1f}K" if gads_imp >= 1000 else str(gads_imp),
                "click": f"{gads_clicks:,}",
                "conv": f"{gads_conv:,.0f}",
                "cpa": f"${gads_cpa:.1f}",
                "roas": f"{gads_roas:.2f}×",
                "status": "good" if gads_roas >= 3.0 else "warn" if gads_roas >= 1.5 else "bad"
            })
        else:
            channels.append(demo["channels"][0])
            total_spend += 68200.0
            total_rev += 68200.0 * 4.2

        # Meta Ads
        meta_spend = 0.0
        meta_imp = 0
        meta_clicks = 0
        meta_conv = 0.0
        meta_rev = 0.0
        
        if meta_campaigns:
            for c in meta_campaigns:
                meta_spend += c["spend"]
                meta_imp += c["imp"]
                meta_clicks += c["click"]
                meta_conv += c["conv"]
                meta_rev += c["spend"] * c["roas"]
                
            total_spend += meta_spend
            total_rev += meta_rev
            
            meta_roas = meta_rev / meta_spend if meta_spend > 0 else 0.0
            meta_cpa = meta_spend / meta_conv if meta_conv > 0 else 0.0
            channels.append({
                "name": "Meta Ads",
                "icon": "ti-brand-facebook",
                "icon_bg": "#F5F3FF",
                "icon_color": "#6d28d9",
                "spend": f"${meta_spend:,.0f}",
                "imp": f"{meta_imp/1000:.1f}K" if meta_imp >= 1000 else str(meta_imp),
                "click": f"{meta_clicks:,}",
                "conv": f"{meta_conv:,.0f}",
                "cpa": f"${meta_cpa:.1f}",
                "roas": f"{meta_roas:.2f}×",
                "status": "good" if meta_roas >= 3.0 else "warn" if meta_roas >= 1.5 else "bad"
            })
        else:
            channels.append(demo["channels"][1])
            total_spend += 42300.0
            total_rev += 42300.0 * 2.8

        # YouTube Ads (Keep demo)
        channels.append(demo["channels"][2])
        total_spend += 14000.0
        total_rev += 14000.0 * 1.9

        # ROAS KPI
        roas_val = f"{total_rev / total_spend:.2f}×" if total_spend > 0 else demo["kpis"]["roas"]["value"]
        
        # Budget breakdown
        gads_pct = round(gads_spend / total_spend * 100) if total_spend > 0 and gads_campaigns else 55
        meta_pct = round(meta_spend / total_spend * 100) if total_spend > 0 and meta_campaigns else 34
        yt_pct = 100 - gads_pct - meta_pct if gads_campaigns or meta_campaigns else 11
        
        budget = [
            {"label": "Google", "value": gads_pct, "color": "#2563EB"},
            {"label": "Meta", "value": meta_pct, "color": "#6b7280"},
            {"label": "YouTube", "value": yt_pct, "color": "#d1d5db"}
        ]

        # Daily advertising trends
        ad_spend_trend = []
        ad_rev_trend = []
        
        if gads_trend or meta_trend:
            merged_daily = {}
            if gads_trend and gads_trend.get("labels"):
                for idx, lbl in enumerate(gads_trend["labels"]):
                    merged_daily[lbl] = {
                        "spend": gads_trend["spend_trend"][idx],
                        "revenue": gads_trend["revenue_trend"][idx]
                    }
            if meta_trend and meta_trend.get("labels"):
                for idx, lbl in enumerate(meta_trend["labels"]):
                    if lbl not in merged_daily:
                        merged_daily[lbl] = {"spend": 0.0, "revenue": 0.0}
                    merged_daily[lbl]["spend"] += meta_trend["spend_trend"][idx]
                    merged_daily[lbl]["revenue"] += meta_trend["revenue_trend"][idx]
            
            if not merged_daily:
                ad_spend_trend = demo["ad_spend"]
                ad_rev_trend = demo["ad_revenue"]
            else:
                sorted_lbls = sorted(merged_daily.keys())
                for lbl in sorted_lbls[-14:]:
                    ad_spend_trend.append(round(merged_daily[lbl]["spend"] / 1000.0, 1))
                    ad_rev_trend.append(round(merged_daily[lbl]["revenue"] / 1000.0, 1))
        else:
            ad_spend_trend = demo["ad_spend"]
            ad_rev_trend = demo["ad_revenue"]

        # KPIs
        kpis = {
            "sessions":    {"value": sessions_val, "delta": sessions_delta, "trend": sessions_trend},
            "users":       {"value": users_val,    "delta": users_delta,    "trend": users_trend},
            "impressions": {"value": imp_val,      "delta": imp_delta,      "trend": imp_trend},
            "roas":        {"value": roas_val,     "delta": "—",            "trend": "flat"}
        }

        # 6. AI 洞察
        openai_key = settings.get("openai_key") or os.getenv("OPENAI_API_KEY", "")
        ai_summary = ""
        if openai_key:
            try:
                temp_analytics_data = {
                    "overview": ga4_overview,
                    "sessions_trend": ga4_sessions_trend,
                    "traffic_sources": t_sources,
                    "top_pages": pages_data,
                    "device": dev_data,
                    "keywords": kws,
                    "channels": channels
                }
                ai_summary = await asyncio.to_thread(
                    generate_insight, temp_analytics_data, openai_key
                )
            except Exception as e:
                print(f"[WARN] AI 洞察生成失敗：{e}")
                ai_summary = "AI 分析暫時無法使用，請稍後再試。"

        data_payload = {
            "ai_summary": ai_summary or f"已成功串接真實數據！工作階段共 {ga4_overview.get('sessions', 0):,} 次，自然點擊 {sum(ssc_click):,} 次，廣告總花費 ${total_spend:,.0f}，全渠道 ROAS {roas_val}。",
            "kpis": kpis,
            "sessions_trend": s_trend,
            "users_trend": u_trend,
            "new_users_trend": nu_trend,
            "traffic_source": t_sources,
            "device": dev_data,
            "pages": pages_data,
            "keywords": kws,
            "ssc_imp": ssc_imp,
            "ssc_click": ssc_click,
            "search_type": search_type,
            "channels": channels,
            "ad_revenue": ad_rev_trend,
            "ad_spend": ad_spend_trend,
            "budget": budget,
        }

        return JSONResponse(content={
            "mode": "live",
            "data": data_payload
        })

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"數據撈取失敗：{str(e)}。請確認設定資訊與 API 金鑰是否正確。"
        )

# ── 單獨 GA4 端點 ─────────────────────────────────────
@app.get("/api/ga4")
async def get_ga4_data(
    metric:     str = "sessions",
    start_date: str = "30daysAgo",
    end_date:   str = "today"
):
    """取得特定 GA4 指標數據"""
    settings = load_settings()
    cred_path = get_credentials_path()

    if not settings.get("ga4_property_id") or not cred_path:
        raise HTTPException(status_code=400, detail="尚未設定 GA4，請先完成串接設定。")

    config = GA4Config(
        property_id=settings["ga4_property_id"],
        credentials_path=str(cred_path)
    )
    client = GA4Client(config)

    try:
        data = client.get_metric(metric, start_date, end_date)
        return {"metric": metric, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── AI 洞察端點 ───────────────────────────────────────
@app.get("/api/ai-insight")
async def get_ai_insight():
    """取得最新 AI 洞察文字"""
    settings = load_settings()
    openai_key = settings.get("openai_key") or os.getenv("OPENAI_API_KEY", "")

    if not openai_key:
        return {"insight": "請設定 OpenAI API Key 以啟用 AI 洞察功能。", "mode": "no_key"}

    # 這裡可以從快取讀取，避免每次都重新呼叫 AI
    return {"insight": "AI 洞察功能已啟用。請呼叫 /api/dashboard 取得完整分析。", "mode": "ready"}

# ══════════════════════════════════════════════════════
# Demo 數據（沒有 credentials 時使用）
# ══════════════════════════════════════════════════════

def _get_demo_data() -> dict:
    """回傳 Demo 模式假數據，與前端 MOCK 對應"""
    return {
        "ai_summary": "這是 <strong>Demo 模式</strong>，目前顯示的是示範數據。請前往「設定」頁面串接你的 GA4 帳號，即可看到真實數據與 AI 分析。",
        "kpis": {
            "sessions":    {"value": "38,241", "delta": "+9.4%", "trend": "up"},
            "users":       {"value": "28,109", "delta": "+5.2%", "trend": "up"},
            "impressions": {"value": "182K",   "delta": "+12%",  "trend": "up"},
            "roas":        {"value": "3.61×",  "delta": "—",     "trend": "flat"},
        },
        "sessions_trend":  [2400,2800,2600,3100,3300,3800,3600,3200,3700,4000,4300,4100,4500,4700],
        "users_trend":     [1800,2100,1950,2300,2450,2800,2650,2400,2800,3000,3200,3100,3400,3500],
        "new_users_trend": [1100,1300,1200,1500,1600,1900,1750,1500,1750,1900,2000,1950,2100,2200],
        "traffic_source": [
            {"label": "自然搜尋", "value": 61, "color": "#2563EB"},
            {"label": "直接流量", "value": 18, "color": "#6b7280"},
            {"label": "社群媒體", "value": 12, "color": "#93c5fd"},
            {"label": "其他",     "value":  9, "color": "#e5e7eb"},
        ],
        "device": [
            {"label": "手機", "value": 58, "color": "#2563EB"},
            {"label": "桌機", "value": 34, "color": "#6b7280"},
            {"label": "平板", "value":  8, "color": "#d1d5db"},
        ],
        "pages": [
            {"path": "/",               "views": 12401, "unique": 9820,  "time": "3:12", "bounce": "38%", "conv": "4.2%", "status": "good"},
            {"path": "/pricing",        "views": 7832,  "unique": 6140,  "time": "1:05", "bounce": "78%", "conv": "1.8%", "status": "bad"},
            {"path": "/blog/ga4-guide", "views": 5210,  "unique": 4890,  "time": "4:28", "bounce": "41%", "conv": "2.9%", "status": "good"},
            {"path": "/features",       "views": 3980,  "unique": 3200,  "time": "2:50", "bounce": "45%", "conv": "3.1%", "status": "warn"},
            {"path": "/docs",           "views": 2140,  "unique": 1980,  "time": "5:10", "bounce": "33%", "conv": "6.4%", "status": "good"},
        ],
        "keywords": [
            {"kw": "數據分析工具",          "imp": 28400, "click": 1477, "ctr": "5.2%", "rank": "#4.0", "trend": "+2", "opp": "進入首頁", "opp_type": "good"},
            {"kw": "GA4 教學",              "imp": 19200, "click": 1306, "ctr": "6.8%", "rank": "#3.2", "trend": "+3", "opp": "搶 Top3",  "opp_type": "good"},
            {"kw": "網站流量分析",          "imp": 15800, "click":  616, "ctr": "3.9%", "rank": "#6.1", "trend": "−1", "opp": "加強內容", "opp_type": "warn"},
            {"kw": "google analytics 設定", "imp": 11400, "click":  240, "ctr": "2.1%", "rank": "#12",  "trend": "+5", "opp": "有潛力",   "opp_type": "warn"},
            {"kw": "SEO 工具推薦",          "imp":  9600, "click":  173, "ctr": "1.8%", "rank": "#18",  "trend": "—",  "opp": "待衝刺",   "opp_type": "bad"},
        ],
        "ssc_imp":    [11000,12500,12000,13800,14200,15000,14500,13200,14800,16000,17000,16500,18000,18200],
        "ssc_click":  [420,490,460,530,550,590,570,510,570,620,660,640,690,692],
        "search_type": [
            {"label": "網頁", "value": 83, "color": "#2563EB"},
            {"label": "圖片", "value": 10, "color": "#6b7280"},
            {"label": "影片", "value":  7, "color": "#d1d5db"},
        ],
        "channels": [
            {"name": "Google Ads",  "icon": "ti-brand-google",   "icon_bg": "#EFF6FF", "icon_color": "#1d4ed8", "spend": "$68,200", "imp": "520K",  "click": "18,400", "conv": "1,140", "cpa": "$59.8",  "roas": "4.2×", "status": "good"},
            {"name": "Meta Ads",    "icon": "ti-brand-facebook", "icon_bg": "#F5F3FF", "icon_color": "#6d28d9", "spend": "$42,300", "imp": "890K",  "click": "11,200", "conv": "580",   "cpa": "$72.9",  "roas": "2.8×", "status": "warn"},
            {"name": "YouTube Ads", "icon": "ti-brand-youtube",  "icon_bg": "#FFF7ED", "icon_color": "#c2410c", "spend": "$14,000", "imp": "1.2M",  "click": "4,800",  "conv": "122",   "cpa": "$114.8", "roas": "1.9×", "status": "bad"},
        ],
        "ad_revenue": [29,33,31,36,39,44,42,38,43,47,50,49,53,56],
        "ad_spend":   [7.5,8,8,9,10,11,9.5,8.8,10,12,13,12,13,14],
        "budget": [
            {"label": "Google",  "value": 55, "color": "#2563EB"},
            {"label": "Meta",    "value": 34, "color": "#6b7280"},
            {"label": "YouTube", "value": 11, "color": "#d1d5db"},
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
