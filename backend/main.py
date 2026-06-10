"""
AI Data Studio Dashboard — FastAPI 後端
提供 Dashboard 數據、AI 洞察、健康檢查等 API。
"""

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai_insight_engine import generate_insights
from ga4_client import fetch_ga4_data

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(
    title="AI Data Studio API",
    description="全渠道數據分析 + AI 洞察後端",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Mock 廣告數據（Phase 3 將替換為 Google Ads / Meta API） ──

def _mock_ads_data() -> dict:
    return {
        "total_spend": 124_500,
        "total_revenue": 450_200,
        "roas": 3.61,
        "spend_change_pct": 12,
        "revenue_change_pct": 8,
        "channels": {
            "google_ads": {"spend": 68_000, "conversions": 892, "roas": 3.8},
            "meta_ads": {"spend": 56_500, "conversions": 654, "roas": 3.4},
        },
        "daily_spend": [15200, 17800, 16500, 19200, 21000, 18500, 14300],
        "daily_revenue": [52000, 61000, 58000, 72000, 85000, 78000, 44200],
    }


# ── Response Models ──

class KPIs(BaseModel):
    total_spend: float
    total_revenue: float
    roas: float
    spend_change_pct: float
    revenue_change_pct: float
    roas_change_label: str


class DashboardResponse(BaseModel):
    kpis: KPIs
    ga4: dict
    ads: dict
    ai_insight: dict
    data_source: str


def _percent_items(labels: list[str], values: list[int | float], colors: list[str]) -> list[dict[str, Any]]:
    total = sum(values) or 1
    return [
        {
            "label": label,
            "value": round(value / total * 100),
            "color": colors[index % len(colors)],
        }
        for index, (label, value) in enumerate(zip(labels, values, strict=False))
    ]


def _frontend_dashboard_payload(ga4: dict[str, Any], ads: dict[str, Any], ai: dict[str, Any]) -> dict[str, Any]:
    summary = ga4.get("summary", {})
    daily = ga4.get("daily_metrics", {})
    traffic = ga4.get("traffic_sources", {})
    sessions = daily.get("sessions") or [2400, 2800, 2600, 3100, 3300, 3800, 3600, 3200, 3700, 4000, 4300, 4100, 4500, 4700]
    conversions = daily.get("conversions") or [34, 39, 36, 43, 46, 52, 50, 45, 50, 55, 60, 57, 64, 67]
    users = [round(value * 0.74) for value in sessions]
    new_users = [round(value * 0.47) for value in sessions]
    total_sessions = summary.get("total_sessions") or sum(sessions)
    total_users = summary.get("total_users") or sum(users)
    total_conversions = summary.get("conversions") or sum(conversions)
    roas = ads.get("roas", 3.61)
    ai_summary = ai.get("headline") or "AI 已完成本週摘要。自然搜尋與付費廣告是主要觀察重點，建議優先檢查高流量低轉換頁面與低 ROAS 渠道。"

    return {
        "ai_summary": ai_summary,
        "kpis": {
            "sessions": {"value": f"{total_sessions:,}", "delta": "+9.4%", "trend": "up"},
            "users": {"value": f"{total_users:,}", "delta": "+5.2%", "trend": "up"},
            "impressions": {"value": "182K", "delta": "+12%", "trend": "up"},
            "roas": {"value": f"{roas:.2f}x", "delta": ads.get("roas_change_label", "持平"), "trend": "flat"},
        },
        "sessions_trend": sessions,
        "users_trend": users,
        "new_users_trend": new_users,
        "traffic_source": _percent_items(
            traffic.get("labels") or ["自然搜尋", "直接流量", "社群媒體", "其他"],
            traffic.get("values") or [61, 18, 12, 9],
            ["#2563EB", "#6b7280", "#93c5fd", "#e5e7eb"],
        ),
        "device": [
            {"label": "手機", "value": 58, "color": "#2563EB"},
            {"label": "桌機", "value": 34, "color": "#6b7280"},
            {"label": "平板", "value": 8, "color": "#d1d5db"},
        ],
        "pages": [
            {"path": "/", "views": 12401, "unique": 9820, "time": "3:12", "bounce": "38%", "conv": "4.2%", "status": "good"},
            {"path": "/pricing", "views": 7832, "unique": 6140, "time": "1:05", "bounce": "78%", "conv": "1.8%", "status": "bad"},
            {"path": "/blog/ga4-guide", "views": 5210, "unique": 4890, "time": "4:28", "bounce": "41%", "conv": "2.9%", "status": "good"},
            {"path": "/features", "views": 3980, "unique": 3200, "time": "2:50", "bounce": "45%", "conv": "3.1%", "status": "warn"},
            {"path": "/docs", "views": 2140, "unique": 1980, "time": "5:10", "bounce": "33%", "conv": "6.4%", "status": "good"},
        ],
        "keywords": [
            {"kw": "數據分析工具", "imp": 28400, "click": 1477, "ctr": "5.2%", "rank": "#4.0", "trend": "+2", "opp": "進入首頁", "opp_type": "good"},
            {"kw": "GA4 教學", "imp": 19200, "click": 1306, "ctr": "6.8%", "rank": "#3.2", "trend": "+3", "opp": "搶 Top3", "opp_type": "good"},
            {"kw": "網站流量分析", "imp": 15800, "click": 616, "ctr": "3.9%", "rank": "#6.1", "trend": "-1", "opp": "加強內容", "opp_type": "warn"},
            {"kw": "google analytics 設定", "imp": 11400, "click": 240, "ctr": "2.1%", "rank": "#12", "trend": "+5", "opp": "有潛力", "opp_type": "warn"},
            {"kw": "SEO 工具推薦", "imp": 9600, "click": 173, "ctr": "1.8%", "rank": "#18", "trend": "-", "opp": "待衝刺", "opp_type": "bad"},
        ],
        "ssc_imp": [11000, 12500, 12000, 13800, 14200, 15000, 14500, 13200, 14800, 16000, 17000, 16500, 18000, 18200],
        "ssc_click": [420, 490, 460, 530, 550, 590, 570, 510, 570, 620, 660, 640, 690, 692],
        "search_type": [
            {"label": "網頁", "value": 83, "color": "#2563EB"},
            {"label": "圖片", "value": 10, "color": "#6b7280"},
            {"label": "影片", "value": 7, "color": "#d1d5db"},
        ],
        "channels": [
            {"name": "Google Ads", "icon": "ti-brand-google", "icon_bg": "#EFF6FF", "icon_color": "#1d4ed8", "spend": "$68,200", "imp": "520K", "click": "18,400", "conv": "1,140", "cpa": "$59.8", "roas": "4.2x", "status": "good"},
            {"name": "Meta Ads", "icon": "ti-brand-facebook", "icon_bg": "#F5F3FF", "icon_color": "#6d28d9", "spend": "$42,300", "imp": "890K", "click": "11,200", "conv": "580", "cpa": "$72.9", "roas": "2.8x", "status": "warn"},
            {"name": "YouTube Ads", "icon": "ti-brand-youtube", "icon_bg": "#FFF7ED", "icon_color": "#c2410c", "spend": "$14,000", "imp": "1.2M", "click": "4,800", "conv": "122", "cpa": "$114.8", "roas": "1.9x", "status": "bad"},
        ],
        "ad_revenue": ads.get("daily_revenue") or [29, 33, 31, 36, 39, 44, 42, 38, 43, 47, 50, 49, 53, 56],
        "ad_spend": ads.get("daily_spend") or [7.5, 8, 8, 9, 10, 11, 9.5, 8.8, 10, 12, 13, 12, 13, 14],
        "budget": [
            {"label": "Google", "value": 55, "color": "#2563EB"},
            {"label": "Meta", "value": 34, "color": "#6b7280"},
            {"label": "YouTube", "value": 11, "color": "#d1d5db"},
        ],
        "data_source": ga4.get("source", "mock"),
        "ai_insight": ai,
    }


# ── Endpoints ──

@app.get("/")
def root():
    return {
        "service": "AI Data Studio API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    has_ga4_creds = (Path(__file__).parent.parent / "credentials" / "service-account.json").exists()
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    return {
        "status": "ok",
        "ga4_configured": has_ga4_creds,
        "openai_configured": has_openai,
        "mode": "live" if has_ga4_creds else "demo",
    }


@app.get("/api/dashboard")
def get_dashboard():
    """主 Dashboard 數據：KPI + GA4 + 廣告 + AI 洞察"""
    ga4 = fetch_ga4_data()
    ads = _mock_ads_data()
    ai = generate_insights(ga4, ads)

    roas_change = "持平"
    if ads["revenue_change_pct"] > ads["spend_change_pct"]:
        roas_change = "↑ 改善"
    elif ads["revenue_change_pct"] < ads["spend_change_pct"]:
        roas_change = "↓ 下滑"

    ads["roas_change_label"] = roas_change
    return _frontend_dashboard_payload(ga4, ads, ai)


@app.get("/api/ga4")
def get_ga4():
    return fetch_ga4_data()


@app.get("/api/ai-insight")
def get_ai_insight():
    ga4 = fetch_ga4_data()
    ads = _mock_ads_data()
    return generate_insights(ga4, ads)
