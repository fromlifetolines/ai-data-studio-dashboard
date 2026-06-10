"""
AI Data Studio — backend/ai_insight_engine.py
將 GA4 數據丟給 OpenAI，生成人類可讀的行銷建議
"""

import json
from openai import OpenAI


def generate_insight(ga4_data: dict, openai_key: str) -> str:
    """
    輸入 GA4 數據，回傳 AI 生成的中文行銷建議摘要
    回傳格式：HTML 字串（可含 <strong> 標籤）
    """
    client = OpenAI(api_key=openai_key)

    overview  = ga4_data.get("overview", {})
    pages     = ga4_data.get("top_pages", [])[:5]
    sources   = ga4_data.get("traffic_sources", [])

    # 整理成易讀的提示詞
    prompt = f"""
你是一位專業的數位行銷顧問，請根據以下 GA4 數據，用繁體中文提供本週行銷建議摘要。

【本週核心數據】
- 工作階段：{overview.get('sessions', '—')}，較上期 {overview.get('sessions_delta', '—')}
- 不重複用戶：{overview.get('users', '—')}，較上期 {overview.get('users_delta', '—')}
- 平均停留時間：{overview.get('avg_duration', '—')}
- 整體跳出率：{overview.get('bounce_rate', '—')}
- 轉換次數：{overview.get('conversions', '—')}，較上期 {overview.get('conv_delta', '—')}

【流量來源前三】
{json.dumps(sources[:3], ensure_ascii=False)}

【跳出率最高的頁面 Top 3】
{json.dumps([p for p in pages if p.get('status') == 'bad'][:3], ensure_ascii=False)}

請提供：
1. 最重要的 2–3 個數據洞察（用 <strong> 標記關鍵詞）
2. 立即可執行的 1–2 個具體建議
3. 語氣專業但易懂，總字數 80–120 字

只回傳 HTML 摘要文字，不要加任何前言或標題。
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.7,
    )

    return response.choices[0].message.content.strip()
