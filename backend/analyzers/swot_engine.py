import json
import logging
from database import get_db_connection
from ai_insight_engine import call_gemini

logger = logging.getLogger(__name__)

def generate_swot_analysis(project_id: str, matrix_data: list, gemini_key: str = None) -> dict:
    """
    Generate SWOT analysis based on competitor matrix. Use Gemini if key is provided,
    otherwise build structured business analyst heuristics.
    """
    # Find our company
    own = next((c for c in matrix_data if c["is_own_company"]), None)
    if not own and matrix_data:
        own = matrix_data[0]
        
    competitors = [c for c in matrix_data if not c["is_own_company"]]
    
    # Format data for LLM
    comp_summary = []
    for c in competitors:
        comp_summary.append(
            f"競品 {c['name']} (Domain: {c['domain']}): 月訪問量 {c['monthly_visits']}, SEO關鍵字 {c['organic_keywords']}, 社群貼文量 {c['social_post_count']}, 好評率 {c['positive_ratio']*100}%"
        )
    
    prompt = f"""
    你是一位資深的策略管理顧問與商業數據分析師。
    請根據以下公司與競爭對手的真實數據，為我們公司「{own['name'] if own else '本公司'}」進行 SWOT 分析。
    
    【本公司數據】
    - 月訪問量：{own['monthly_visits'] if own else 0}
    - SEO關鍵字數：{own['organic_keywords'] if own else 0}
    - 社群輿情貼文量：{own['social_post_count'] if own else 0}
    - 好評率：{own['positive_ratio']*100 if own else 0}%
    - AI搜尋提及率：{own['geo']['mention_rate'] if own else 0}%
    
    【競品數據】
    {chr(10).join(comp_summary)}
    
    請產出 SWOT 分析（Strengths 優勢, Weaknesses 劣勢, Opportunities 機會, Threats 威脅），每個維度各提供 3-4 個具體、有憑有據、可執行的商業條目。
    
    請嚴格以下列 JSON 格式回傳，不要加任何 markdown 標記 (如 ```json) 以外的說明字串：
    {{
        "strengths": ["優勢條目1", "優勢條目2", "優勢條目3"],
        "weaknesses": ["劣勢條目1", "劣勢條目2", "劣勢條目3"],
        "opportunities": ["機會條目1", "機會條目2", "機會條目3"],
        "threats": ["威脅條目1", "威脅條目2", "威脅條目3"]
    }}
    """
    
    if gemini_key:
        try:
            raw_resp = call_gemini(prompt, gemini_key)
            clean_resp = raw_resp.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_resp)
            # Store in cache
            with get_db_connection() as conn:
                conn.execute("DELETE FROM ai_analyses WHERE project_id = ? AND analysis_type = 'swot'", (project_id,))
                conn.execute(
                    "INSERT INTO ai_analyses (id, project_id, analysis_type, content) VALUES (?, ?, 'swot', ?)",
                    (str(uuid.uuid4()), project_id, json.dumps(data))
                )
                conn.commit()
            return data
        except Exception as e:
            logger.error(f"Error generating SWOT via Gemini: {e}")
            
    # Try reading from cache first
    try:
        with get_db_connection() as conn:
            cache = conn.execute(
                "SELECT content FROM ai_analyses WHERE project_id = ? AND analysis_type = 'swot'",
                (project_id,)
            ).fetchone()
            if cache:
                return json.loads(cache["content"])
    except Exception as e:
        logger.error(f"Error reading SWOT cache: {e}")

    # Fallback/Heuristics SWOT based on metrics
    logger.info("Generating SWOT using local analytical heuristics")
    own_visits = own['monthly_visits'] if own else 0
    max_comp_visits = max([c['monthly_visits'] for c in competitors]) if competitors else 1
    
    strengths = [
        f"在流量管道分布中具有穩健的 Direct 直接流量，顯示品牌黏著度高。",
        f"社群輿情好評率達 {own['positive_ratio']*100 if own else 50}%，用戶滿意度高於行業平均值。"
    ]
    if own and own_visits > max_comp_visits:
        strengths.append("月流量規模居於市場領導地位，具備規模化的第一方數據資產。")
    else:
        strengths.append("利基定位清晰，單一工作階段平均停留時間領先特定對手。")
        
    weaknesses = [
        f"SEO 關鍵字覆蓋數 ({own['organic_keywords'] if own else 0} 個) 仍有擴充空間，需加強長尾字布局。",
        f"AI 搜尋提及率 (GEO) 僅為 {own['geo']['mention_rate'] if own else 0}%，容易在生成式推薦中被對手攔截。"
    ]
    if own and own_visits < max_comp_visits:
        weaknesses.append("相較於頭部競品，本站總體流量規模偏低，限制了自然轉化的基數。")
        
    opportunities = [
        "利用 Similarweb 競品流量來源分析，將預算集中投放於對手未占領的 Referral 推薦流量渠道。",
        "針對對手排名較低但 KD% 較低的長尾關鍵字，進行主題叢集 (Topic Cluster) SEO 優化。"
    ]
    
    threats = [
        "競品採取激進的搜尋廣告投放策略，熱門字詞的每次點擊成本 (CPC) 持續推高。",
        "AI 搜尋引擎 (ChatGPT, SGE) 對傳統自然搜尋流量的侵蝕，威脅本站核心自然流量管道。"
    ]
    
    heuristics_swot = {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "opportunities": opportunities,
        "threats": threats
    }
    
    return heuristics_swot

import uuid
