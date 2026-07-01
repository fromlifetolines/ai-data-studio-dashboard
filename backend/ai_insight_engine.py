"""
AI Data Studio — backend/ai_insight_engine.py
將 GA4 數據丟給 OpenAI，生成人類可讀的行銷建議
"""

import json
import httpx
from openai import OpenAI


import time

def call_gemini(prompt: str, api_key: str, max_tokens: int = 800, enable_grounding: bool = False) -> str:
    """呼叫 Google Gemini Flash API，並包含自動重試機制以因應 503/429 等暫時性錯誤"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "maxOutputTokens": 8192,
            "temperature": 0.7
        }
    }
    
    if enable_grounding:
        payload["tools"] = [{"googleSearch": {}}]
    
    max_retries = 3
    backoff = 1.5
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=45.0) as client:
                resp = client.post(url, headers=headers, json=payload)
            
            # 如果是 503 或 429 這種暫時性或限流錯誤，進行重試
            if resp.status_code in (429, 503) and attempt < max_retries - 1:
                time.sleep(backoff * (attempt + 1))
                continue
                
            if resp.status_code != 200:
                raise Exception(f"Gemini API Error (HTTP {resp.status_code}): {resp.text}")
                
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError):
            raise Exception(f"Gemini API returned unexpected structure: {resp.text}")
        except httpx.RequestError as e:
            if attempt < max_retries - 1:
                time.sleep(backoff * (attempt + 1))
                continue
            raise e


def generate_insight(ga4_data: dict, openai_key: str = "", gemini_key: str = "") -> str:
    """
    輸入 GA4 數據，回傳 AI 生成的中文行銷建議摘要
    回傳格式：HTML 字串（可含 <strong> 標籤）
    """
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

    if gemini_key:
        return call_gemini(prompt, gemini_key, max_tokens=300)
    elif openai_key:
        client = OpenAI(api_key=openai_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    else:
        raise ValueError("需要提供 openai_key 或 gemini_key")


def generate_chat_reply(user_prompt: str, context_data: dict, openai_key: str = "", gemini_key: str = "") -> str:
    """
    輸入使用者發問與數據上下文，調用 OpenAI 或 Gemini 回傳繁體中文行銷分析建議
    """
    system_prompt = f"""
你是一位專業的數位行銷顧問與數據分析專家。你正在為客戶分析網站流量與廣告投放表現。
請根據以下提供的數據上下文（Context Data），回答使用者的問題。

【當前專案數據上下文】
{json.dumps(context_data, ensure_ascii=False, indent=2)}

【回答指南】
1. 請使用繁體中文回答，口吻專業、具體且有建設性。
2. 盡量從數據中找出問題點與機會，例如高跳出率頁面、低 ROAS 渠道或排名具潛力的關鍵字。
3. 建議要具體，可提供修改網頁內容、調整廣告受眾或修改 CTA 等方向。
4. 使用 Markdown 格式美化排版（如列點、粗體）。
"""

    if gemini_key:
        # 結合 System prompt 與 User prompt 為 Gemini 設計的單一 prompt
        full_prompt = f"{system_prompt}\n\n[使用者問題]\n{user_prompt}"
        return call_gemini(full_prompt, gemini_key, max_tokens=1000)
    elif openai_key:
        client = OpenAI(api_key=openai_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=600,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    else:
        raise ValueError("需要提供 openai_key 或 gemini_key")


def generate_action_roadmap(ga4_data: dict, openai_key: str = "", gemini_key: str = "") -> dict:
    """
    Generate short, medium, and long-term marketing action roadmap based on GA4 metrics.
    Returns: {"short_term": "...", "medium_term": "...", "long_term": "..."}
    """
    overview  = ga4_data.get("overview", {})
    pages     = ga4_data.get("top_pages", [])[:5]
    sources   = ga4_data.get("traffic_sources", [])

    prompt = f"""
    你是一位專業的行銷策略專家。請根據以下數據，制定三個階段的「行動決策指南」：
    1. 短期戰術 (1-30天)：立即可優化、修復或調配預算的事項。
    2. 中期規劃 (30-90天)：SEO結構調整、網頁轉換率優化 (CRO) 等。
    3. 長期戰略 (90天以上)：品牌布局、新客群開發、AI 搜尋能見度 (GEO) 等。
    
    【核心數據】
    - 工作階段：{overview.get('sessions', '—')}，較上期 {overview.get('sessions_delta', '—')}
    - 不重複用戶：{overview.get('users', '—')}，較上期 {overview.get('users_delta', '—')}
    - 平均停留時間：{overview.get('avg_duration', '—')}
    - 跳出率：{overview.get('bounce_rate', '—')}
    - 轉換率：{overview.get('conversions', '—')}
    
    請以繁體中文回答，並嚴格以下列 JSON 格式回傳，不可有任何 ```json 等 Markdown 包裹：
    {{
        "short_term": "短期建議內容（可用 <strong> 粗體標示關鍵字，約 50-80 字）",
        "medium_term": "中期建議內容（約 50-80 字）",
        "long_term": "長期建議內容（約 50-80 字）"
    }}
    """
    
    try:
        if gemini_key:
            res = call_gemini(prompt, gemini_key, max_tokens=1000)
            clean = res.replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
        elif openai_key:
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.7,
            )
            clean = response.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in generate_action_roadmap: {e}")
        
    # Return structured heuristics if failed or no key
    return {
        "short_term": "<strong>調整低 ROAS 廣告預算</strong>：將本週成效較低的付費廣告預算轉移至高點閱率 (CTR) 的渠道，並立即修復高跳出率頁面的 CTA 按鈕。",
        "medium_term": "<strong>進行關鍵字 Topic Cluster 優化</strong>：針對 GSC 曝光高但點擊低的潛力長尾字詞撰寫專題內容，並優化產品導購流程，降低購物車流失率。",
        "long_term": "<strong>布局 AI 搜尋能見度 (GEO)</strong>：強化網站的 JSON-LD 結構化資料，爭取在 Google AIO 與 ChatGPT 推薦清單中被引用，建立長期自然增長壁壘。"
    }

