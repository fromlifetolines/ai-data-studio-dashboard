import httpx
import logging
import hashlib
import json

logger = logging.getLogger(__name__)

async def fetch_semrush_data(domain: str, api_key: str = None, gemini_key: str = None) -> dict:
    """
    Fetch SEO snapshot and organic/paid keywords for a given domain using SEMrush API if API key is provided,
    otherwise falling back to Google Search Grounding to retrieve live web data.
    """
    domain = domain.strip().lower()
    if "://" in domain:
        domain = domain.split("://")[-1]
    domain = domain.split("/")[0]

    if api_key:
        url = f"https://api.semrush.com/?type=domain_rank&key={api_key}&domain={domain}&export_columns=Or,Ot,Oc"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200 and "Error" not in response.text:
                    lines = response.text.strip().split("\n")
                    if len(lines) > 1:
                        headers = lines[0].split(";")
                        values = lines[1].split(";")
                        data = dict(zip(headers, values))
                        return {
                            "organic_keywords": int(data.get("Or", 0)),
                            "organic_traffic_value": int(data.get("Oc", 0)),
                            "top_keywords": [],  # Extra request would fetch lists
                            "paid_keywords": []
                        }
        except Exception as e:
            logger.error(f"Error fetching from SEMrush API: {e}")

    # Fallback: Google Search Grounding (100% Free & grounded on actual web search index)
    if gemini_key:
        logger.info(f"Using Google Search Grounding for free SEMrush estimates on domain: {domain}")
        prompt = f"""
        請使用 Google 搜尋引擎尋找網站「{domain}」的 SEO 指標。
        分析該網站近期的搜尋表現，並給出以下預估值：
        1. 自然搜尋關鍵字總數 (organic_keywords) - 該網域在 Google 排名前 100 名的關鍵字數量。
        2. 自然流量價值 (organic_traffic_value) - 美金估計值。
        3. 五個主要排名熱門關鍵字清單，包含關鍵字名稱(keyword)、排名(position)、搜尋量(volume)。
        4. 兩個正在投放的搜尋廣告關鍵字與廣告文案。

        請嚴格以 JSON 格式回傳，不要包含 markdown (如 ```json) 或任何其他多餘字元：
        {{
            "organic_keywords": 1200,
            "organic_traffic_value": 350,
            "top_keywords": [
                {{"keyword": "關鍵字1", "position": 3, "volume": 1200}},
                {{"keyword": "關鍵字2", "position": 5, "volume": 800}},
                {{"keyword": "關鍵字3", "position": 1, "volume": 350}},
                {{"keyword": "關鍵字4", "position": 8, "volume": 200}},
                {{"keyword": "關鍵字5", "position": 12, "volume": 150}}
            ],
            "paid_keywords": [
                {{"keyword": "廣告字1", "ad_copy": "廣告文案描述1"}},
                {{"keyword": "廣告字2", "ad_copy": "廣告文案描述2"}}
            ]
        }}
        """
        try:
            from ai_insight_engine import call_gemini
            raw_resp = call_gemini(prompt, gemini_key, enable_grounding=True)
            clean_resp = raw_resp.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_resp)
            return {
                "organic_keywords": int(data.get("organic_keywords", 0)),
                "organic_traffic_value": int(data.get("organic_traffic_value", 0)),
                "top_keywords": data.get("top_keywords", []),
                "paid_keywords": data.get("paid_keywords", [])
            }
        except Exception as e:
            logger.error(f"Error fetching SEMrush estimates via Gemini Grounding: {e}")

    # If no API key and no Gemini key, return empty metrics
    logger.warning(f"SEMrush API key and Gemini key not configured. Returning empty metrics for domain: {domain}")
    return {
        "organic_keywords": 0,
        "organic_traffic_value": 0,
        "top_keywords": [],
        "paid_keywords": []
    }
