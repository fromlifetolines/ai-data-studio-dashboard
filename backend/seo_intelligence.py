"""
AI Data Studio — backend/seo_intelligence.py
SEO 智慧分析模組 — 全免費數據來源

數據來源策略：
1. Google PageSpeed Insights API → Core Web Vitals / 效能評分（免費，無需 Key）
2. Open PageRank API → 域名評分（免費，基於 Common Crawl）
3. Google Search Console（已串接）→ 真實關鍵字排名
4. seo_evaluator.py → 技術 SEO 評測（直接爬網頁 HTML）
5. Gemini Grounding → 關鍵字研究 + 競品分析（AI 推估）
"""

import json
import re
import httpx
import asyncio
from typing import Optional, Dict, List, Any


# ══════════════════════════════════════════════════════
# 1. Google PageSpeed Insights API（完全免費，無需 API Key）
# ══════════════════════════════════════════════════════

def get_pagespeed_data(url: str) -> Dict[str, Any]:
    """
    呼叫 Google PageSpeed Insights API 取得 Core Web Vitals 與效能評分。
    完全免費，無需 API Key。
    """
    # 確保有 scheme
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    results = {"mobile": {}, "desktop": {}}

    for strategy in ["mobile", "desktop"]:
        try:
            api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
            # httpx 需要用 list of tuples 來重複 query param
            params = [
                ("url",      url),
                ("strategy", strategy),
                ("category", "performance"),
                ("category", "seo"),
                ("category", "accessibility"),
                ("category", "best-practices"),
            ]
            with httpx.Client(timeout=45.0) as client:
                resp = client.get(api_url, params=params)

            if resp.status_code != 200:
                print(f"[PageSpeed Error] HTTP {resp.status_code}: {resp.text[:200]}")
                results[strategy] = _empty_pagespeed()
                continue

            data = resp.json()
            categories = data.get("lighthouseResult", {}).get("categories", {})
            audits = data.get("lighthouseResult", {}).get("audits", {})

            # 分類評分（0~100）
            perf_score = round((categories.get("performance", {}).get("score", 0) or 0) * 100)
            seo_score = round((categories.get("seo", {}).get("score", 0) or 0) * 100)
            a11y_score = round((categories.get("accessibility", {}).get("score", 0) or 0) * 100)
            bp_score = round((categories.get("best-practices", {}).get("score", 0) or 0) * 100)

            # Core Web Vitals
            lcp_raw = audits.get("largest-contentful-paint", {}).get("displayValue", "—")
            fid_raw = audits.get("total-blocking-time", {}).get("displayValue", "—")
            cls_raw = audits.get("cumulative-layout-shift", {}).get("displayValue", "—")
            fcp_raw = audits.get("first-contentful-paint", {}).get("displayValue", "—")
            ttfb_raw = audits.get("server-response-time", {}).get("displayValue", "—")
            speed_index_raw = audits.get("speed-index", {}).get("displayValue", "—")

            # LCP 等級判斷
            def _lcp_grade(val_str: str) -> str:
                try:
                    sec = float(re.sub(r"[^\d.]", "", val_str))
                    if sec <= 2.5: return "good"
                    elif sec <= 4.0: return "needs-improvement"
                    else: return "poor"
                except:
                    return "unknown"

            def _cls_grade(val_str: str) -> str:
                try:
                    num = float(re.sub(r"[^\d.]", "", val_str))
                    if num <= 0.1: return "good"
                    elif num <= 0.25: return "needs-improvement"
                    else: return "poor"
                except:
                    return "unknown"

            results[strategy] = {
                "scores": {
                    "performance": perf_score,
                    "seo": seo_score,
                    "accessibility": a11y_score,
                    "best_practices": bp_score
                },
                "cwv": {
                    "lcp": {"value": lcp_raw, "grade": _lcp_grade(lcp_raw)},
                    "tbt": {"value": fid_raw, "grade": "good" if "ms" in fid_raw and float(re.sub(r"[^\d.]", "", fid_raw) or "999") < 200 else "needs-improvement"},
                    "cls": {"value": cls_raw, "grade": _cls_grade(cls_raw)},
                    "fcp": {"value": fcp_raw},
                    "ttfb": {"value": ttfb_raw},
                    "speed_index": {"value": speed_index_raw}
                }
            }

        except Exception as e:
            print(f"[PageSpeed Exception] {e}")
            results[strategy] = _empty_pagespeed()

    return results


def _empty_pagespeed() -> Dict:
    return {
        "scores": {"performance": 0, "seo": 0, "accessibility": 0, "best_practices": 0},
        "cwv": {
            "lcp": {"value": "—", "grade": "unknown"},
            "tbt": {"value": "—", "grade": "unknown"},
            "cls": {"value": "—", "grade": "unknown"},
            "fcp": {"value": "—"},
            "ttfb": {"value": "—"},
            "speed_index": {"value": "—"}
        }
    }


# ══════════════════════════════════════════════════════
# 2. Open PageRank API（免費，基於 Common Crawl 資料）
# ══════════════════════════════════════════════════════

def get_open_pagerank(domains: List[str]) -> Dict[str, Any]:
    """
    呼叫 Open PageRank API 取得域名評分（DR/PageRank）。
    完全免費，無需 API Key。
    https://www.domcop.com/openpagerank/
    """
    results = {}
    if not domains:
        return results

    try:
        # 清理 domain（移除 scheme 和路徑）
        clean_domains = []
        for d in domains:
            d = d.strip().lower()
            if "://" in d:
                d = d.split("://")[1]
            d = d.split("/")[0]
            if d:
                clean_domains.append(d)

        if not clean_domains:
            return results

        # 一次最多查 100 個 domain
        params = "&".join([f"domains[]={d}" for d in clean_domains[:10]])
        url = f"https://openpagerank.com/api/v1.0/getPageRank?{params}"

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers={"API-OPR": "not-required"})

        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("response", []):
                domain = item.get("domain", "")
                pr = item.get("page_rank_decimal", 0) or 0
                rank = item.get("rank", 0) or 0
                results[domain] = {
                    "open_pagerank": round(float(pr), 2),
                    "global_rank": rank,
                    "grade": _pr_grade(float(pr))
                }
        else:
            # Fallback：回傳 0
            for d in clean_domains:
                results[d] = {"open_pagerank": 0, "global_rank": 0, "grade": "N/A"}

    except Exception as e:
        print(f"[OpenPageRank Exception] {e}")
        for d in domains:
            results[d] = {"open_pagerank": 0, "global_rank": 0, "grade": "N/A"}

    return results


def _pr_grade(pr: float) -> str:
    if pr >= 7.0: return "excellent"
    elif pr >= 5.0: return "good"
    elif pr >= 3.0: return "fair"
    elif pr > 0: return "low"
    else: return "unknown"


# ══════════════════════════════════════════════════════
# 3. Gemini Grounding — 關鍵字研究
# ══════════════════════════════════════════════════════

def keyword_research_gemini(keyword: str, site_url: str, gemini_key: str) -> Dict[str, Any]:
    """
    使用 Gemini Grounding 進行關鍵字研究。
    基於 Google 搜尋即時資料，給出搜尋量估算、競爭度、相關關鍵字。
    """
    from ai_insight_engine import call_gemini

    domain = site_url.strip().replace("https://", "").replace("http://", "").split("/")[0]

    prompt = f"""
你是 SEO 專家。請使用 Google 搜尋分析以下關鍵字：「{keyword}」

請提供：
1. 預估月搜尋量（台灣/全球）
2. 競爭難度（1-100）
3. 預估 CPC（競價成本，USD）
4. 你的網站 {domain} 目前排名（如果有）
5. 10 個相關長尾關鍵字，含各自的搜尋量和競爭度
6. SERP 上的熱門競爭對手（前3名網域）
7. 關鍵字意圖分析（資訊型/交易型/導航型/商業型）

嚴格以 JSON 格式回傳，不要包含 markdown 標記：
{{
  "keyword": "{keyword}",
  "monthly_searches_tw": 1200,
  "monthly_searches_global": 8500,
  "difficulty": 45,
  "cpc_usd": 0.8,
  "your_rank": null,
  "intent": "informational",
  "intent_zh": "資訊型",
  "related_keywords": [
    {{"keyword": "相關詞1", "monthly_searches": 500, "difficulty": 30}},
    {{"keyword": "相關詞2", "monthly_searches": 300, "difficulty": 25}},
    {{"keyword": "相關詞3", "monthly_searches": 200, "difficulty": 40}},
    {{"keyword": "相關詞4", "monthly_searches": 150, "difficulty": 35}},
    {{"keyword": "相關詞5", "monthly_searches": 120, "difficulty": 50}},
    {{"keyword": "相關詞6", "monthly_searches": 100, "difficulty": 20}},
    {{"keyword": "相關詞7", "monthly_searches": 80, "difficulty": 15}},
    {{"keyword": "相關詞8", "monthly_searches": 60, "difficulty": 45}},
    {{"keyword": "相關詞9", "monthly_searches": 50, "difficulty": 55}},
    {{"keyword": "相關詞10", "monthly_searches": 40, "difficulty": 30}}
  ],
  "top_competitors": [
    {{"domain": "example.com", "title": "競爭頁面標題"}},
    {{"domain": "example2.com", "title": "競爭頁面標題"}},
    {{"domain": "example3.com", "title": "競爭頁面標題"}}
  ]
}}
"""
    try:
        raw = call_gemini(prompt, gemini_key, enable_grounding=True)
        clean = raw.replace("```json", "").replace("```", "").strip()
        # 找 JSON 部分
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start >= 0 and end > start:
            clean = clean[start:end]
        return json.loads(clean)
    except Exception as e:
        print(f"[Keyword Research Gemini Error] {e}")
        raise e


# ══════════════════════════════════════════════════════
# 4. Gemini Grounding — 競爭對手 SEO 分析
# ══════════════════════════════════════════════════════

def competitor_seo_analysis_gemini(my_domain: str, competitor_domain: str, gemini_key: str) -> Dict[str, Any]:
    """
    使用 Gemini Grounding 分析競爭對手的 SEO 表現。
    """
    from ai_insight_engine import call_gemini

    prompt = f"""
你是 SEO 競爭情報分析師。請使用 Google 搜尋分析以下兩個網站的 SEO 比較：

我方網站：{my_domain}
競爭對手：{competitor_domain}

請分析：
1. 各自的預估自然搜尋流量（月流量）
2. 各自的預估關鍵字排名數量（前100名）
3. 競爭對手的 Top 5 排名關鍵字
4. 競爭對手的 Top 5 流量頁面
5. 競爭差距分析：對手比我們強在哪裡，我們能超越的機會點
6. 建議優先搶攻的關鍵字缺口（我方沒有但對手有排名的高機會詞）

嚴格以 JSON 格式回傳，不要包含 markdown 標記：
{{
  "my_domain": {{
    "domain": "{my_domain}",
    "monthly_organic_traffic": 5000,
    "keyword_count": 320,
    "domain_strength": 45
  }},
  "competitor": {{
    "domain": "{competitor_domain}",
    "monthly_organic_traffic": 12000,
    "keyword_count": 680,
    "domain_strength": 58,
    "top_keywords": [
      {{"keyword": "關鍵字1", "position": 2, "monthly_searches": 2000}},
      {{"keyword": "關鍵字2", "position": 4, "monthly_searches": 1500}},
      {{"keyword": "關鍵字3", "position": 1, "monthly_searches": 1200}},
      {{"keyword": "關鍵字4", "position": 7, "monthly_searches": 800}},
      {{"keyword": "關鍵字5", "position": 3, "monthly_searches": 600}}
    ],
    "top_pages": [
      {{"url": "/page1", "title": "頁面標題1", "monthly_traffic": 3000}},
      {{"url": "/page2", "title": "頁面標題2", "monthly_traffic": 2000}},
      {{"url": "/page3", "title": "頁面標題3", "monthly_traffic": 1500}},
      {{"url": "/page4", "title": "頁面標題4", "monthly_traffic": 1000}},
      {{"url": "/page5", "title": "頁面標題5", "monthly_traffic": 800}}
    ]
  }},
  "gap_analysis": {{
    "competitor_advantages": ["對手優勢1", "對手優勢2", "對手優勢3"],
    "my_opportunities": ["機會點1", "機會點2", "機會點3"],
    "keyword_gaps": [
      {{"keyword": "缺口關鍵字1", "monthly_searches": 500, "difficulty": 35, "opportunity_score": 85}},
      {{"keyword": "缺口關鍵字2", "monthly_searches": 300, "difficulty": 25, "opportunity_score": 90}},
      {{"keyword": "缺口關鍵字3", "monthly_searches": 200, "difficulty": 20, "opportunity_score": 75}}
    ]
  }}
}}
"""
    try:
        raw = call_gemini(prompt, gemini_key, enable_grounding=True)
        clean = raw.replace("```json", "").replace("```", "").strip()
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start >= 0 and end > start:
            clean = clean[start:end]
        return json.loads(clean)
    except Exception as e:
        print(f"[Competitor SEO Gemini Error] {e}")
        raise e


# ══════════════════════════════════════════════════════
# 5. GSC 關鍵字排名重新格式化（用於 Rank Tracker）
# ══════════════════════════════════════════════════════

def format_gsc_rank_tracker(gsc_rows: list) -> Dict[str, Any]:
    """
    將 GSC query_search_analytics 原始回傳格式化為排名追蹤器格式。
    GSC 原始格式：
      { "keys": ["關鍵字"], "clicks": 10, "impressions": 200, "ctr": 0.05, "position": 4.2 }
    """
    if not gsc_rows:
        return {"keywords": [], "summary": {}}

    # 解析原始 GSC 格式
    parsed = []
    for row in gsc_rows:
        keys = row.get("keys", [])
        kw = keys[0] if keys else ""
        if not kw:
            continue
        parsed.append({
            "keyword":     kw,
            "clicks":      int(row.get("clicks", 0)),
            "impressions": int(row.get("impressions", 0)),
            "ctr":         float(row.get("ctr", 0)),
            "position":    float(row.get("position", 0)),
        })

    # 按點擊數排序
    sorted_kws = sorted(parsed, key=lambda x: x["clicks"], reverse=True)

    total_clicks      = sum(k["clicks"]      for k in sorted_kws)
    total_impressions = sum(k["impressions"] for k in sorted_kws)
    avg_position = sum(k["position"] for k in sorted_kws) / max(len(sorted_kws), 1)

    top3  = [k for k in sorted_kws if k["position"] <= 3]
    top10 = [k for k in sorted_kws if 3 < k["position"] <= 10]
    top30 = [k for k in sorted_kws if 10 < k["position"] <= 30]

    formatted = []
    for kw in sorted_kws[:200]:
        pos = kw["position"]
        if pos <= 3:
            pos_badge = "🥇 Top 3"
            pos_class = "top3"
        elif pos <= 10:
            pos_badge = "🥈 Top 10"
            pos_class = "top10"
        elif pos <= 30:
            pos_badge = "🥉 Top 30"
            pos_class = "top30"
        else:
            pos_badge = f"#{round(pos)}"
            pos_class = "others"

        formatted.append({
            "keyword":        kw["keyword"],
            "position":       round(pos, 1),
            "position_badge": pos_badge,
            "position_class": pos_class,
            "clicks":         kw["clicks"],
            "impressions":    kw["impressions"],
            "ctr":            kw["ctr"],
        })

    return {
        "keywords": formatted,
        "summary": {
            "total_keywords":   len(sorted_kws),
            "total_clicks":     total_clicks,
            "total_impressions": total_impressions,
            "avg_position":     round(avg_position, 1),
            "top3_count":       len(top3),
            "top10_count":      len(top10),
            "top30_count":      len(top30),
        }
    }

