"""
AI Data Studio — backend/seo_evaluator.py
核心職責：
1. 抓取目標網頁 HTML。
2. 進行技術 SEO (6項)、AI 搜尋引擎優化 GEO (6項)、回答引擎優化 AEO (6項) 的真實評測。
3. 調用 Gemini/OpenAI 生成真實優化建議。
"""

import re
import urllib.parse
import httpx
from typing import Optional, Dict, List, Any

# 引入 AI 洞察引擎中的 call_gemini 或 OpenAI
try:
    from ai_insight_engine import call_gemini
except ImportError:
    call_gemini = None

def fetch_html(url: str) -> str:
    """真實抓取目標 URL 的 HTML"""
    # 確保有 scheme
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True, verify=False) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.text
            else:
                return f"Error: Status code {resp.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"


def evaluate_seo(html: str, url: str) -> Dict[str, Any]:
    """
    傳統 SEO 評分 (6子項)
    1. Title 完整性 (max 20)
    2. Meta Description 存在性 (max 20)
    3. OpenGraph 標記 (max 15)
    4. HTTPS 安全性 (max 15)
    5. 行動裝置視埠 viewport (max 15)
    6. 網頁連結優化 (max 15)
    """
    scores = {}
    details = {}
    
    # 1. Title
    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if title_match:
        title = title_match.group(1).strip()
        if len(title) >= 10:
            scores["title"] = 20
            details["title"] = f"優良 (長度 {len(title)} 字，內容為: '{title}')"
        else:
            scores["title"] = 10
            details["title"] = f"待改進 (標題過短或為空，僅 {len(title)} 字)"
    else:
        scores["title"] = 0
        details["title"] = "嚴重缺失 (未偵測到 <title> 標籤)"

    # 2. Meta Description
    desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', html, re.IGNORECASE)
    if not desc_match:
        desc_match = re.search(r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']', html, re.IGNORECASE)
        
    if desc_match:
        desc = desc_match.group(1).strip()
        if len(desc) >= 30:
            scores["desc"] = 20
            details["desc"] = f"優良 (長度 {len(desc)} 字)"
        else:
            scores["desc"] = 12
            details["desc"] = f"待改善 (描述長度不足，僅 {len(desc)} 字)"
    else:
        scores["desc"] = 0
        details["desc"] = "嚴重缺失 (未偵測到 description 描述)"

    # 3. OpenGraph (og:title, og:description, og:image 等)
    og_matches = re.findall(r'property=["\']og:(.*?)["\']', html, re.IGNORECASE)
    if len(og_matches) >= 3:
        scores["og"] = 15
        details["og"] = f"優良 (偵測到 {len(og_matches)} 項 OpenGraph 社群標記)"
    elif len(og_matches) > 0:
        scores["og"] = 8
        details["og"] = f"普通 (僅偵測到 {len(og_matches)} 項 OpenGraph 標記，建議補齊)"
    else:
        scores["og"] = 0
        details["og"] = "缺乏 (未偵測到任何 Facebook/Line 分享必備的 og: 標記)"

    # 4. HTTPS 安全性
    is_https = url.lower().startswith("https://")
    scores["https"] = 15 if is_https else 0
    details["https"] = "安全 (已使用 HTTPS 加密連線)" if is_https else "高風險 (未使用安全加密 HTTPS 連線)"

    # 5. Mobile viewport
    viewport_match = re.search(r'<meta\s+name=["\']viewport["\']', html, re.IGNORECASE)
    scores["viewport"] = 15 if viewport_match else 0
    details["viewport"] = "已就緒 (已設定 viewport 響應式佈局標記)" if viewport_match else "缺失 (無 viewport 標記，手機版畫面可能縮水)"

    # 6. Alt tags on images
    img_tags = re.findall(r'<img\s+[^>]*>', html, re.IGNORECASE)
    imgs_with_alt = [img for img in img_tags if "alt=" in img.lower()]
    if not img_tags:
        scores["images"] = 15
        details["images"] = "無圖片 (頁面無圖片，無須 alt 檢測)"
    else:
        pct = len(imgs_with_alt) / len(img_tags)
        scores["images"] = int(pct * 15)
        details["images"] = f"已設置 {len(imgs_with_alt)}/{len(img_tags)} 張圖片的 Alt 替代文字 ({int(pct*100)}%)"

    total = sum(scores.values())
    return {
        "score": total,
        "items": [
            {"name": "網頁標題 Title", "score": scores["title"], "max": 20, "desc": details["title"], "code": "<title>您的網站首頁標題</title>", "importance": "這是搜尋引擎最看重的排名因子，代表您頁面的主旨。"},
            {"name": "網頁描述 Description", "score": scores["desc"], "max": 20, "desc": details["desc"], "code": '<meta name="description" content="您的品牌與核心業務介紹，建議 80-120 字。">', "importance": "影響搜尋結果頁(SERP)中的摘要，吸引用戶點擊的核心。"},
            {"name": "社群標記 OpenGraph", "score": scores["og"], "max": 15, "desc": details["og"], "code": '<meta property="og:title" content="分享時顯示的標題">\n<meta property="og:type" content="website">\n<meta property="og:image" content="分享縮圖.jpg">', "importance": "當網頁被分享到 LINE、Facebook 時，是否能呈現漂亮吸引人的精美卡片。"},
            {"name": "HTTPS 安全加密", "score": scores["https"], "max": 15, "desc": details["https"], "code": "請聯絡網域代管商安裝 SSL 憑證，並強制 301 轉址到 https://...", "importance": "保護用戶隱私與交易安全，也是 Google 排序算法的硬性要求。"},
            {"name": "行動優先 Viewport", "score": scores["viewport"], "max": 15, "desc": details["viewport"], "code": '<meta name="viewport" content="width=device-width, initial-scale=1.0">', "importance": "宣告此網頁支援手機與平板縮放，是 Google 行動優先索引的評測基石。"},
            {"name": "圖片 Alt 替代文字", "score": scores["images"], "max": 15, "desc": details["images"], "code": '<img src="banner.jpg" alt="伯堅數位看板展示 - 行銷儀表板主畫面">', "importance": "協助 Google 機器人讀懂圖片內容，也是提升圖片搜尋排名的核心。"}
        ]
    }

def evaluate_geo(html: str, url: str) -> Dict[str, Any]:
    """
    AI 搜尋引擎優化 GEO 評分 (6子項)
    1. Schema 結構化資料完整度 (JSON-LD) (max 20)
    2. E-E-A-T 作者/品牌信譽宣告 (max 20)
    3. 聯絡資訊與實體公司證明 (max 15)
    4. AI 爬蟲許可設定 (Robots.txt 友善) (max 15)
    5. 外鏈信譽指標與引用連結 (max 15)
    6. 內容豐富度與長字數比重 (max 15)
    """
    scores = {}
    details = {}

    # 1. Schema 結構化資料 (檢索 <script type="application/ld+json">)
    ld_json_matches = re.findall(r'<script\s+type=["\']application/ld\+json["\']\s*>(.*?)</script>', html, re.IGNORECASE | re.DOTALL)
    if ld_json_matches:
        scores["schema"] = 20
        # 簡單解析 schema 類型
        types = []
        for content in ld_json_matches:
            found_types = re.findall(r'"@type"\s*:\s*["\'](.*?)["\']', content)
            types.extend(found_types)
        types_str = ", ".join(list(set(types))[:3])
        details["schema"] = f"優良 (已埋設 {len(ld_json_matches)} 組 JSON-LD 結構化資料，包含: {types_str})"
    else:
        scores["schema"] = 0
        details["schema"] = "嚴重缺失 (未偵測到任何 JSON-LD 結構化標記，AI 搜尋難以準確抓取實體資訊)"

    # 2. E-E-A-T (檢查是否有 author, about, privacy policy, 專業人士簽章等)
    has_privacy = "隱私權" in html or "privacy" in html.lower()
    has_about = "關於我們" in html or "about" in html.lower()
    if has_privacy and has_about:
        scores["eeat"] = 20
        details["eeat"] = "健全 (頁面包含「關於我們」與「隱私權政策」，符合 AI 搜尋對資訊透明度的要求)"
    elif has_privacy or has_about:
        scores["eeat"] = 12
        details["eeat"] = "普通 (僅有「關於」或「隱私政策」之一，建議兩者皆具備)"
    else:
        scores["eeat"] = 0
        details["eeat"] = "薄弱 (無企業品牌/創作者資訊，難以建立 AI 的信任評分 E-E-A-T)"

    # 3. 聯絡資訊與實體公司 (網址、Email、電話)
    has_contact = re.search(r"(聯絡|電話|tel:|email|信箱|地址|遠路|市路|@[\w.-]+\.\w+)", html, re.IGNORECASE)
    scores["contact"] = 15 if has_contact else 0
    details["contact"] = "完整 (包含電話、Email 或地址，AI 可有效將其識別為真實商業實體)" if has_contact else "缺失 (未發現明顯聯絡方式或地址，AI 可能降低商業信任度)"

    # 4. Robots.txt / GPTbot 友善度 (此處對 url 本身無法直連 robots.txt 時提供預防指引，並檢測 html 的 noindex 標籤)
    has_noindex = "noindex" in html.lower()
    scores["robots"] = 0 if has_noindex else 15
    details["robots"] = "正常 (未設置 noindex 標籤，允許各大 AI 爬蟲進行資料索引)" if not has_noindex else "警告 (設置了 noindex，將完全阻擋 AI 機器人收錄！)"

    # 5. 出站引用連結 (External citations)
    ext_links = re.findall(r'href=["\'](https?://[^"\']+)["\']', html, re.IGNORECASE)
    # 過濾同網域連結
    parsed_url = urllib.parse.urlparse(url)
    domain = parsed_url.netloc
    filtered_ext = [link for link in ext_links if domain not in link]
    if len(filtered_ext) >= 2:
        scores["citations"] = 15
        details["citations"] = f"優良 (發現 {len(filtered_ext)} 個出站权威引用連結，有助於 AI 關聯外部權威實體)"
    else:
        scores["citations"] = 8
        details["citations"] = "普通 (出站引用過少，建議在提及數據或專業觀點時，適度超連結至維基百科或大型媒體)"

    # 6. 內容長度
    text_content = re.sub(r"<[^>]*>", "", html)
    text_content = re.sub(r"\s+", "", text_content)
    length = len(text_content)
    if length >= 1200:
        scores["length"] = 15
        details["length"] = f"充足 (內容純文字長度約 {length} 字，能提供 AI 足夠上下文)"
    elif length >= 500:
        scores["length"] = 10
        details["length"] = f"中等 (純文字長度 {length} 字，對深度問答解答力稍嫌不足)"
    else:
        scores["length"] = 5
        details["length"] = f"過短 (網頁內容極少僅 {length} 字，幾乎無法被 AI 當作有效參考來源)"

    total = sum(scores.values())
    return {
        "score": total,
        "items": [
            {"name": "LD-JSON 結構化", "score": scores["schema"], "max": 20, "desc": details["schema"], "code": '<script type="application/ld+json">\n{\n  "@context": "https://schema.org",\n  "@type": "Organization",\n  "name": "公司名稱",\n  "url": "https://site.com"\n}\n</script>', "importance": "AI（如 ChatGPT/Perplexity）會優先抓取 Schema 結構化資料，這是建立網頁語意關聯的最快途徑。"},
            {"name": "E-E-A-T 信譽宣告", "score": scores["eeat"], "max": 20, "desc": details["eeat"], "code": "在選單或頁尾增設「關於我們 (About Us)」與「隱私權政策 (Privacy Policy)」連結，並在文章標註專家作者名。", "importance": "這是 AI 判定資訊可靠度的核心算法，缺乏此架構的網站極易被判定為低質量垃圾訊息。"},
            {"name": "實體商業關聯", "score": scores["contact"], "max": 15, "desc": details["contact"], "code": "在頁尾或聯絡頁面，以純文字完整寫出：【公司地址】、【客服專線】與【客服信箱】。", "importance": "AI 會將純文字的實體地址、電話與 Google Maps/工商登記比對，確認您的網站隸屬於真實品牌。"},
            {"name": "AI 爬蟲存取權", "score": scores["robots"], "max": 15, "desc": details["robots"], "code": "確保您的 robots.txt 檔案中，**不要**阻擋：\nUser-agent: GPTBot\nUser-agent: ClaudeBot\nUser-agent: Google-Extended", "importance": "如果直接拒絕 AI 爬蟲，您的網站將永遠不會出現在 AI 搜尋引擎的引用連結中。"},
            {"name": "權威出站引用", "score": scores["citations"], "max": 15, "desc": details["citations"], "code": '<a href="https://zh.wikipedia.org/wiki/..." target="_blank">參考資料：維基百科說明</a>', "importance": "引用第三方數據、論文或政府資訊，有助於 AI 的語意網絡將您的網站與高品質客觀知識進行綁定。"},
            {"name": "上下文豐富度", "score": scores["length"], "max": 15, "desc": details["length"], "code": "增加深度專業解析文字，為網頁內容充實更多專有名詞定義與關聯性解答（建議單頁長度大於 1,200 字）。", "importance": "長內容能為 LLM 提供更多 Token 的上下文，提高它被當成 AI 答案來源的提取機率。"}
        ]
    }

def evaluate_aeo(html: str, url: str) -> Dict[str, Any]:
    """
    回答引擎優化 AEO 評分 (6子項)
    1. 40-60字直接回答段落 (Featured Snippet 親和度) (max 20)
    2. FAQ 問答結構設計 (max 20)
    3. H2 / H3 問答式標題 (max 15)
    4. 結構化條列清單 (ol / ul / table) (max 15)
    5. PAA (People Also Ask) 相關主題覆蓋 (max 15)
    6. 語意簡明度與易讀性 (Lighthouse Readable) (max 15)
    """
    scores = {}
    details = {}

    # 1. 40-60字直接回答 (檢查 H2/H3 下方的緊鄰文字段落長度是否剛好符合問答)
    p_tags = re.findall(r"<p[^>]*>(.*?)</p>", html, re.IGNORECASE | re.DOTALL)
    has_snippet_ready = False
    for p in p_tags:
        clean_p = re.sub(r"<[^>]*>", "", p).strip()
        # 中文字數在 50~120 字之間，或英文字數在 40~60 字之間 (對應 Google Snippet 最愛抓取的答案長度)
        if 40 <= len(clean_p) <= 120:
            has_snippet_ready = True
            break
    
    scores["snippet"] = 20 if has_snippet_ready else 8
    details["snippet"] = "已就緒 (偵測到長度介於 50-120 字的簡潔段落，極易被 Google 擷取為精選摘要)" if has_snippet_ready else "缺乏 (內容段落大多過長或過短，難以被直接提取為零位置精選解答)"

    # 2. FAQ 結構
    has_faq = "faq" in html.lower() or "問與答" in html or "常見問題" in html
    scores["faq"] = 20 if has_faq else 5
    details["faq"] = "健全 (網頁內包含常見問題 (FAQ) 的標籤或關鍵詞)" if has_faq else "缺失 (無 FAQ 專區，無法提供直接的問答格式予搜尋引擎)"

    # 3. H2/H3 問答標題 (檢查是否存在「如何」、「什麼是」、「為什麼」、「怎麼做」等問句)
    h_tags = re.findall(r"<h[23][^>]*>(.*?)</h[23]>", html, re.IGNORECASE | re.DOTALL)
    has_questions = False
    question_count = 0
    for h in h_tags:
        clean_h = re.sub(r"<[^>]*>", "", h).strip()
        if any(q in clean_h for q in ["如何", "什麼是", "為什麼", "怎麼", "哪裡", "多少", "what", "how", "why"]):
            has_questions = True
            question_count += 1
            
    scores["headers"] = 15 if has_questions else 5
    details["headers"] = f"優良 (偵測到 {question_count} 個問句形式的 H2/H3 標題，完美對應使用者的搜尋意圖)" if has_questions else "不足 (標題多為單詞，缺乏引導 AI 直接提取解答的問答式結構)"

    # 4. 條列清單 (ol / ul / table)
    has_list = "<ul" in html.lower() or "<ol" in html.lower() or "<table" in html.lower()
    scores["list"] = 15 if has_list else 0
    details["list"] = "已就緒 (使用 <ul>/<ol> 清單或表格，搜尋引擎偏好擷取此結構作為步驟型解答)" if has_list else "缺失 (缺乏條列式清單或表格，影響結構化答案的提取機率)"

    # 5. PAA 相關主題覆盖 (檢查關鍵詞多樣性)
    keyword_diversity = len(re.findall(r"(功能|教學|推薦|步驟|評價|費用|優缺點|分析)", html))
    if keyword_diversity >= 4:
        scores["paa"] = 15
        details["paa"] = f"廣泛 (覆蓋了 {keyword_diversity} 種常見使用者意圖，有助於切入 PAA 「其他人也問了」版位)"
    else:
        scores["paa"] = 8
        details["paa"] = "普通 (覆蓋的使用者搜尋維度較窄，應加入常見的主題分支)"

    # 6. 語意簡明度與易讀性 (Lighthouse Readable)
    text_content = re.sub(r"<[^>]*>", "", html)
    text_content = re.sub(r"\s+", "", text_content)
    sentences = re.split(r"[。！？\.\?!]", text_content)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 0]
    avg_sentence_len = sum(len(s) for s in sentences) / max(len(sentences), 1)
    
    if avg_sentence_len <= 35:
        scores["readability"] = 15
        details["readability"] = f"優良 (平均句長僅 {int(avg_sentence_len)} 字，文筆簡明流暢，易於 AEO 語音及文字摘要提取)"
    elif avg_sentence_len <= 60:
        scores["readability"] = 10
        details["readability"] = f"普通 (平均句長 {int(avg_sentence_len)} 字，包含部分長難句，建議拆分為短句以提升可讀性)"
    else:
        scores["readability"] = 5
        details["readability"] = f"待改善 (平均句長達 {int(avg_sentence_len)} 字，句子過於冗長，AI 語意分析及摘要擷取難度高)"

    total = sum(scores.values())
    return {
        "score": total,
        "items": [
            {"name": "問答精華段落", "score": scores["snippet"], "max": 20, "desc": details["snippet"], "code": '<p><strong>[什麼是XX]</strong>：XX是指...，具有...功能，通常用於...</p>', "importance": "精選摘要 (Featured Snippet) 偏好提取字數介於 50-100 字、結構為「定義+關鍵字+核心解答」的精華第一段落。"},
            {"name": "FAQ 問答設置", "score": scores["faq"], "max": 20, "desc": details["faq"], "code": "在網頁底部增設 FAQ 區塊，列出 3-5 個使用者最常詢問的相關問答。", "importance": "直接的問句加答案能被 AI 模組直接讀取，大幅提升在 AI 介面中被引述為答案的機會。"},
            {"name": "問答式 H2/H3", "score": scores["headers"], "max": 15, "desc": details["headers"], "code": '<h2>GA4 資源 ID 如何取得？三個步驟搞定</h2>', "importance": "搜尋用戶大多使用問句搜尋。H2/H3 採用問答句型，能使搜尋引擎更容易將您的標題與用戶提問進行精準比對。"},
            {"name": "條列步驟與表格", "score": scores["list"], "max": 15, "desc": details["list"], "code": '<ol>\n  <li>步驟一：...</li>\n  <li>步驟二：...</li>\n</ol>', "importance": "在介紹操作流程時，多用有序清單 `<ol>`；在比較規格時多用表格 `<table>`，搜尋引擎最愛抓取此類標記並呈現在搜尋結果最上方。"},
            {"name": "PAA 主題覆蓋度", "score": scores["paa"], "max": 15, "desc": details["paa"], "code": "增加「優缺點比較」、「費用方案」、「安裝教學」等延伸段落，以完整覆蓋使用者的各種搜尋維度。", "importance": "搜尋結果頁的「其他人也問了 (People Also Ask)」是巨大的免費流量入口，覆蓋多維度意圖才能搶佔此版位。"},
            {"name": "語意易讀與簡明性", "score": scores["readability"], "max": 15, "desc": details["readability"], "code": "避免使用極長且無標點符號的複雜長句，多使用主謂賓結構清晰的短句撰寫網頁內容。", "importance": "AEO 引擎是將內容轉換成語音或極簡回答給用戶，文字越直白易懂，越容易被挑選。"}
        ]
    }

def run_full_evaluation(url: str, gemini_key: str = "") -> Dict[str, Any]:
    """執行完整三維評測"""
    html = fetch_html(url)
    
    if "Error:" in html:
        # 爬取失敗時回傳預設結構（但附帶錯誤提示），維持公信力
        return {
            "success": False,
            "error": html,
            "url": url
        }

    seo_res = evaluate_seo(html, url)
    geo_res = evaluate_geo(html, url)
    aeo_res = evaluate_aeo(html, url)

    # 4. 調用 AI 生成診斷建議
    ai_advice = ""
    if gemini_key and call_gemini:
        # 使用真實 Gemini API，產出具備強大公信力與實體網站診斷的中文分析
        prompt = f"""
你是一位頂級的 AI SEO (包含 GEO 與 AEO) 優化專家。請針對以下實測診斷結果，為網站 {url} 產出具體、立即可落實的「網頁診斷與改善優化建議書」。

實測分數：
- 傳統 SEO 評分：{seo_res["score"]}/100
- AI 搜尋 GEO 評分：{geo_res["score"]}/100
- 回答引擎 AEO 評分：{aeo_res["score"]}/100

網頁部分 HTML 結構摘要 (長度約 2500 字)：
{html[:2500]}

請用繁體中文，格式化為：
1. **主要缺點診斷**：點出最嚴重的 2-3 個問題。
2. **具體修改方案**：寫出針對這些缺點的 HTML 改動、Schema 範例、或內容調整建議，要有公信力，不可有廢話。
3. 總字數約 300-400 字，採用專業但好讀的 Markdown 列點格式。
不要加任何前言或結尾詞，直接以 markdown 回傳。
"""
        try:
            ai_advice = call_gemini(prompt, gemini_key, max_tokens=1000)
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "quota" in err_msg.lower() or "limit" in err_msg.lower() or "exhausted" in err_msg.lower():
                ai_advice = (
                    "⚠️ **AI 建議暫時無法生成**：您目前使用的 Gemini API 金鑰已達到免費版限制（每日最多 20 次調用）。\n\n"
                    "**建議解決方案**：\n"
                    "1. 請前往右上角的 **「設定」** 頁面，更換為您的付費版 API 金鑰，或使用其他未超額的免費金鑰。\n"
                    "2. 由於免費版有每分鐘與每日限制，您可以等待一段時間後再重試。\n\n"
                    "*(💡 提示：您現在依然可以點擊左側的各個子指標卡片，查看離線狀態下的程式碼優化與修復方案。)*"
                )
            else:
                ai_advice = f"AI 優化建議生成失敗：{err_msg}\n\n(但您依然可以點擊下方子項目卡片查看靜態修復指引)"
    else:
        # 靜態 fallback 建議
        ai_advice = f"""
### 💡 實時優化診斷報告 ({url})

目前尚未設定您的 AI API Key，以下為系統規則產出的實施指南：

1. **Schema 結構化資料優化**：本網頁檢測為 {geo_res['items'][0]['desc']}。建議您在網頁中加入 `Organization` 或 `WebSite` 的 JSON-LD 結構化資料，有助於 ChatGPT、Claude 引用。
2. **Featured Snippet 問答佈局**：檢測結果為 {aeo_res['items'][0]['desc']}。建議在重要小標題下方放置 50-80 字的主旨直答。
3. **行動優先與安全防護**：本網頁的 HTTPS 安全為 {seo_res['items'][3]['desc']}，Viewport 行動佈局為 {seo_res['items'][4]['desc']}。

**💡 提示**：前往「設定」頁面輸入 Gemini API 金鑰後，即可調用 AI 為此網頁進行深度語意健檢，產出最真實的客製化程式碼修復方案。
"""

    return {
        "success": True,
        "url": url,
        "scores": {
            "seo": seo_res["score"],
            "geo": geo_res["score"],
            "aeo": aeo_res["score"]
        },
        "seo_report": seo_res["items"],
        "geo_report": geo_res["items"],
        "aeo_report": aeo_res["items"],
        "ai_advice": ai_advice
    }
