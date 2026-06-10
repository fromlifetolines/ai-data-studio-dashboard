"""
AI 洞察引擎
將 GA4 / 廣告數據送入 OpenAI，生成可執行的行銷建議。
若無 API Key，回傳規則式 mock 洞察。
"""

import os
from typing import Any

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def _mock_insight(ga4_data: dict, ads_data: dict) -> dict[str, Any]:
    """規則式 mock 洞察，確保無 API Key 時仍有專業輸出。"""
    traffic = ga4_data.get("traffic_sources", {})
    labels = traffic.get("labels", [])
    values = traffic.get("values", [])

    top_source = labels[0] if labels else "Organic Search"
    top_pct = values[0] if values else 45

    roas = ads_data.get("roas", 3.61)
    spend_change = ads_data.get("spend_change_pct", 12)
    revenue_change = ads_data.get("revenue_change_pct", 8)

    insights = [
        {
            "type": "opportunity",
            "title": "流量結構健康",
            "text": f"{top_source} 佔比 {top_pct}%，為主要流量來源。建議持續優化 SEO 內容以降低付費流量依賴。",
        },
        {
            "type": "warning" if spend_change > 10 else "info",
            "title": "廣告花費監控",
            "text": f"本週廣告花費較上週 ↑{spend_change}%，整體 ROAS 為 {roas}。"
            + (" 花費增幅高於收益增幅，建議檢視受眾設定與出價策略。" if spend_change > revenue_change else " 花費與收益同步成長，投放策略穩健。"),
        },
        {
            "type": "action",
            "title": "本週行動建議",
            "text": "週末轉換率通常較高，建議週五加碼 Meta 與 Google Ads 預算 15–20%，並 A/B 測試 Landing Page CTA 文案。",
        },
    ]

    headline = (
        f"整體 ROAS {roas}，收益 ↑{revenue_change}%。"
        f"{' 注意廣告成本上升，優先檢視低 ROAS 渠道。' if spend_change > revenue_change else ' 投放效率良好，可適度擴量。'}"
    )

    return {
        "headline": headline,
        "insights": insights,
        "generated_by": "rule_engine",
    }


def generate_insights(
    ga4_data: dict[str, Any],
    ads_data: dict[str, Any],
) -> dict[str, Any]:
    """
    生成 AI 行銷洞察。
    有 OPENAI_API_KEY 時使用 GPT；否則使用規則式 mock。
    """
    if not OPENAI_API_KEY:
        return _mock_insight(ga4_data, ads_data)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)

        prompt = f"""你是一位資深數位行銷顧問。根據以下數據，用繁體中文提供 3 條精準、可執行的行銷建議。

GA4 數據摘要：
- 流量來源：{ga4_data.get('traffic_sources', {})}
- 總 Sessions：{ga4_data.get('summary', {}).get('total_sessions', 'N/A')}
- 轉換率：{ga4_data.get('summary', {}).get('conversion_rate', 'N/A')}%

廣告數據：
- 總花費：${ads_data.get('total_spend', 0):,.0f}
- 總收益：${ads_data.get('total_revenue', 0):,.0f}
- ROAS：{ads_data.get('roas', 0)}
- 花費變化：{ads_data.get('spend_change_pct', 0)}%
- 收益變化：{ads_data.get('revenue_change_pct', 0)}%

請以 JSON 格式回覆：
{{
  "headline": "一句話本週決策摘要",
  "insights": [
    {{"type": "opportunity|warning|action|info", "title": "標題", "text": "具體建議"}}
  ]
}}
只回傳 JSON，不要其他文字。"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        import json
        result = json.loads(response.choices[0].message.content)
        result["generated_by"] = "openai"
        return result

    except Exception as e:
        result = _mock_insight(ga4_data, ads_data)
        result["error"] = str(e)
        return result
