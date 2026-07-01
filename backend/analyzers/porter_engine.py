import json
import logging
from database import get_db_connection

logger = logging.getLogger(__name__)

def evaluate_porter_forces(project_id: str, matrix_data: list) -> dict:
    """
    Perform Porter's Five Forces analysis dynamically based on competitor counts, traffic concentration,
    and search ad density.
    Returns: Dict containing scores (1-10) and notes for each force.
    """
    own = next((c for c in matrix_data if c["is_own_company"]), None)
    competitors = [c for c in matrix_data if not c["is_own_company"]]
    comp_count = len(competitors)
    
    # 1. 現有競爭者強度 (Rivalry)
    traffic_rivalry = 0
    if own and competitors and comp_count > 0:
        avg_comp_traffic = sum(c["monthly_visits"] for c in competitors) / comp_count
        own_traffic = own["monthly_visits"] or 1
        ratio = avg_comp_traffic / own_traffic
        if ratio > 1.5:
            traffic_rivalry = 3.0  # Competitors are much stronger
        elif ratio > 0.8:
            traffic_rivalry = 2.0  # Close competition
        else:
            traffic_rivalry = 1.0  # We dominate
    
    rivalry_score = round(min(1.5 + comp_count * 0.8 + traffic_rivalry, 9.5), 1)
    rivalry_notes = f"市場上有 {comp_count} 家主要競品。我方流量與競品相近，在關鍵字廣告版位上存在溫和對抗，競爭對抗強度中等。"
    
    # 2. 新進入者威脅 (New Entrants)
    avg_keywords = sum(c["organic_keywords"] for c in matrix_data) / len(matrix_data) if matrix_data else 0
    if avg_keywords < 1000:
        entrants_score = 8.5
        entrants_notes = "行業整體線上關鍵字佈局門檻極低，SEO 壁壘尚未建立，新品牌極易透過數位廣告切入市場，威脅性高。"
    elif avg_keywords < 5000:
        entrants_score = 5.5
        entrants_notes = "行業具備一定的專業關鍵字技術與利基門檻，新進入者需要投入中等資源建置內容，威脅性中等。"
    else:
        entrants_score = 2.5
        entrants_notes = "行業領先者已建立強大關鍵字壁壘，新品牌獲客成本極高，進入門檻極高。"
    
    # 3. 替代品威脅 (Substitutes)
    avg_geo = sum(c["geo"]["mention_rate"] for c in matrix_data) / len(matrix_data) if matrix_data else 0
    if avg_geo > 40:
        substitutes_score = 8.0
        substitutes_notes = "生成式 AI（如 ChatGPT、Google AI Overviews）在該行業的品牌引用與解答率高，替代品威脅顯著。"
    else:
        substitutes_score = 3.0
        substitutes_notes = "當前 AI 搜尋直接解答比例偏低，傳統網頁瀏覽仍是客戶獲取資訊之主要管道，替代品威脅小。"
    
    # 4. 買方議價力 (Buyers)
    own_sentiment = own["positive_ratio"] if own else 0.5
    buyers_score = round(min(2.5 + (1.0 - own_sentiment) * 11.0, 9.5), 1)
    buyers_notes = f"我方正面好評率僅 {int(own_sentiment * 100)}%，顯著低於競品。買方轉換至對手品牌的切換成本低，買方議價力極強。"
    
    # 5. 供應商議價力 (Suppliers)
    with get_db_connection() as conn:
        proj = conn.execute("SELECT industry FROM projects WHERE id = ?", (project_id,)).fetchone()
    industry = proj["industry"] if proj else "生技醫療儀器"
    
    if "生技" in industry or "醫療" in industry:
        suppliers_score = 8.0
        suppliers_notes = "核心代理儀器與耗材多由國外原廠獨家授權，且受限於全球供應鏈與定價權限制，供應商議價力高。"
    elif "物聯網" in industry or "製造" in industry:
        suppliers_score = 6.5
        suppliers_notes = "晶片與感測器模組受制於上游供應大廠，供應商議價力中規中矩。"
    else:
        suppliers_score = 4.5
        suppliers_notes = "上游系統模組選擇多元，技術替換難度低，供應商議價力較弱。"
    
    forces = {
        "rivalry": {"score": rivalry_score, "notes": rivalry_notes},
        "new_entrants": {"score": entrants_score, "notes": entrants_notes},
        "substitutes": {"score": substitutes_score, "notes": substitutes_notes},
        "buyers": {"score": buyers_score, "notes": buyers_notes},
        "suppliers": {"score": suppliers_score, "notes": suppliers_notes}
    }
    
    return forces
