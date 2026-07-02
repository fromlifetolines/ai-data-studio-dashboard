import json
import logging
from competitor_intelligence import get_comparison_matrix_data
from analyzers.swot_engine import generate_swot_analysis
from analyzers.porter_engine import evaluate_porter_forces

logger = logging.getLogger(__name__)

def generate_markdown_report(project_id: str, project_name: str, gemini_key: str = None) -> str:
    """
    Generate a full markdown report compiling Matrix, SWOT, and Porter analyses.
    """
    matrix = get_comparison_matrix_data(project_id)
    swot = generate_swot_analysis(project_id, matrix, gemini_key)
    porter = evaluate_porter_forces(project_id, matrix)
    
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    md = f"""# 市場與競品情報分析報告 — {project_name}
    
報告生成時間：{today_str}
分析架構：市場競爭矩陣、SWOT 策略分析、波特五力雷達、AI 行動指南

---

## 一、 核心競爭數據矩陣 (Competitor Matrix)

| 品牌廠商 | 網域 (Domain) | 類型 | 月訪客數 | 跳出率 | 平均停留時間 | SEO 關鍵字數 | AI 搜尋提及率 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
"""

    for c in matrix:
        own_marker = " (本公司)" if c["is_own_company"] else ""
        md += f"| {c['name']}{own_marker} | `{c['domain']}` | {c['type']} | {c['monthly_visits']:,} | {c['bounce_rate']*100}% | {c['avg_visit_duration']}s | {c['organic_keywords']:,} | {c['geo']['mention_rate']}% |\n"

    # 2. SWOT Analysis
    md += f"""
## 二、 SWOT 策略分析 (SWOT Analysis)

### 🚀 我們的優勢 (Strengths)
"""
    for s in swot.get("strengths", []):
        md += f"* {s}\n"
        
    md += "\n### ⚠️ 我們的劣勢 (Weaknesses)\n"
    for w in swot.get("weaknesses", []):
        md += f"* {w}\n"
        
    md += "\n### 📈 市場機會 (Opportunities)\n"
    for o in swot.get("opportunities", []):
        md += f"* {o}\n"
        
    md += "\n### ⚡ 面臨威脅 (Threats)\n"
    for t in swot.get("threats", []):
        md += f"* {t}\n"

    # 3. Porter's Five Forces
    md += """
## 三、 波特五力分析 (Porter's Five Forces)
"""
    for force_key, info in porter.items():
        name = {
            "rivalry": "現有競爭者對抗強度",
            "new_entrants": "新進入者威脅",
            "substitutes": "替代品威脅",
            "buyers": "買方議價力",
            "suppliers": "供應商議價力"
        }.get(force_key, force_key)
        
        md += f"\n### {name} (評分: {info['score']}/10)\n* {info['notes']}\n"

    # 4. Action Guide
    md += """
---

## 四、 專業分析師行動建議
* **短期調整 (1-30天)**：密切監控競品關鍵字變化，將廣告預算向高點閱率 (CTR) 與高轉換管道傾斜。
* **中期優化 (30-90天)**：優化本站高流量但高跳出率網頁的導購轉換路徑，建立專題內容提升自然搜尋覆蓋。
* **長期部署 (90天以上)**：深化本站與代理品牌的 JSON-LD 結構化標籤，主動提高在 ChatGPT 與 AI Overviews 等生成式搜尋引擎的提及率 (GEO)。
"""

    return md
