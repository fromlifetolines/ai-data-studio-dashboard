"""
AI Data Studio — backend/gsc_client.py
Google Search Console API 封裝模組
"""

import re
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional
import httpx
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as OAuthCredentials
import google.auth.transport.requests

class GSCClient:
    def __init__(self, site_url: str, credentials_path: Optional[str] = None,
                 oauth_credentials: Optional[OAuthCredentials] = None):
        # 自動校正網站 URL
        site_url = site_url.strip()
        if not site_url.startswith("http://") and not site_url.startswith("https://") and not site_url.startswith("sc-domain:"):
            self.site_url = f"sc-domain:{site_url}"
        else:
            self.site_url = site_url

        if oauth_credentials:
            # 新方式：OAuth 個人帳號
            self.credentials = oauth_credentials
        elif credentials_path:
            # 舊方式：Service Account JSON
            self.credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
            )
        else:
            raise ValueError("GSCClient 需要提供 credentials_path 或 oauth_credentials 其中一個")

    def _get_access_token(self) -> str:
        """獲取存取權杖"""
        request = google.auth.transport.requests.Request()
        self.credentials.refresh(request)
        return self.credentials.token

    def test_connection(self) -> dict:
        """測試 GSC 連線是否成功"""
        try:
            token = self._get_access_token()
            encoded_site = urllib.parse.quote_plus(self.site_url)
            url = f"https://www.googleapis.com/webmasters/v3/sites/{encoded_site}"
            headers = {"Authorization": f"Bearer {token}"}
            
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, headers=headers)
                
            if resp.status_code == 200:
                return {"success": True, "site": self.site_url}
            else:
                raise Exception(f"API 回傳錯誤 (HTTP {resp.status_code}): {resp.text}")
        except Exception as e:
            raise Exception(f"無法連線至 Search Console，請確認服務帳戶已加入該資源並給予權限。錯誤資訊：{str(e)}")

    def _parse_date(self, date_str: str) -> str:
        """將相對日期 (例如 30daysAgo) 轉為 YYYY-MM-DD"""
        today = datetime.now()
        if date_str == "today":
            return today.strftime("%Y-%m-%d")
        elif date_str == "yesterday":
            return (today - timedelta(days=1)).strftime("%Y-%m-%d")
        
        match = re.match(r"(\d+)daysAgo", date_str)
        if match:
            days = int(match.group(1))
            return (today - timedelta(days=days)).strftime("%Y-%m-%d")
            
        if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            return date_str
            
        return today.strftime("%Y-%m-%d")

    def query_search_analytics(self, start_date: str, end_date: str, dimensions: list, row_limit: int = 10, search_type: str = "web") -> list:
        """呼叫 Search Console query API"""
        token = self._get_access_token()
        encoded_site = urllib.parse.quote_plus(self.site_url)
        url = f"https://www.googleapis.com/webmasters/v3/sites/{encoded_site}/searchAnalytics/query"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "startDate": self._parse_date(start_date),
            "endDate": self._parse_date(end_date),
            "dimensions": dimensions,
            "rowLimit": row_limit,
            "searchType": search_type
        }
        
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            
        if resp.status_code != 200:
            # 若發生錯誤，回傳空清單，避免阻斷整個 Dashboard 載入
            print(f"[GSC Client Error] {resp.text}")
            return []
            
        return resp.json().get("rows", [])

    def get_keywords_report(self, start_date: str = "30daysAgo", end_date: str = "today") -> list:
        """取得熱門關鍵字數據，並計算相對於前期的排名趨勢"""
        # 取得當期關鍵字
        current_rows = self.query_search_analytics(start_date, end_date, ["query"], row_limit=15)
        
        # 取得前期關鍵字做比較，用以計算排名變化
        days = self._get_days_diff(start_date, end_date)
        prev_start = f"{days * 2}daysAgo"
        prev_end = f"{days}daysAgo"
        prev_rows = self.query_search_analytics(prev_start, prev_end, ["query"], row_limit=100)
        
        prev_ranks = {}
        for r in prev_rows:
            if r.get("keys"):
                prev_ranks[r["keys"][0]] = r.get("position", 99.0)

        keywords = []
        for r in current_rows:
            if not r.get("keys"):
                continue
            kw = r["keys"][0]
            clicks = int(r.get("clicks", 0))
            imp = int(r.get("impressions", 0))
            ctr = f"{r.get('ctr', 0) * 100:.1f}%"
            rank = r.get("position", 0.0)
            
            # 計算排名趨勢
            prev_rank = prev_ranks.get(kw)
            if prev_rank is None:
                trend = "—"
            else:
                diff = prev_rank - rank
                if diff > 0.5:
                    trend = f"+{round(diff)}"
                elif diff < -0.5:
                    trend = f"−{round(abs(diff))}"
                else:
                    trend = "—"
            
            # 判斷優化機會 (Opportunity)
            if rank <= 3.0:
                opp = "搶 Top3"
                opp_type = "good"
            elif 3.0 < rank <= 10.0:
                opp = "進入首頁"
                opp_type = "good"
            elif 10.0 < rank <= 20.0:
                opp = "有潛力"
                opp_type = "warn"
            else:
                opp = "待衝刺"
                opp_type = "bad"
                
            keywords.append({
                "kw": kw,
                "imp": imp,
                "click": clicks,
                "ctr": ctr,
                "rank": f"#{rank:.1f}",
                "trend": trend,
                "opp": opp,
                "opp_type": opp_type
            })
            
        return keywords

    def get_daily_trends(self, start_date: str = "13daysAgo", end_date: str = "today") -> dict:
        """取得每日曝光與點擊趨勢"""
        rows = self.query_search_analytics(start_date, end_date, ["date"], row_limit=100)
        # 按日期排序
        rows_sorted = sorted(rows, key=lambda x: x.get("keys", [""])[0])
        
        impressions = []
        clicks = []
        labels = []
        
        for r in rows_sorted:
            if not r.get("keys"):
                continue
            raw_date = r["keys"][0] # 格式：2026-05-26
            # 轉化為 MM/DD
            parts = raw_date.split("-")
            if len(parts) == 3:
                labels.append(f"{parts[1]}/{parts[2]}")
            else:
                labels.append(raw_date)
            impressions.append(int(r.get("impressions", 0)))
            clicks.append(int(r.get("clicks", 0)))
            
        return {
            "labels": labels,
            "ssc_imp": impressions,
            "ssc_click": clicks
        }

    def get_search_type_breakdown(self, start_date: str = "30daysAgo", end_date: str = "today") -> list:
        """取得不同搜尋類型的流量比例 (Web / Image / Video)"""
        # GSC 不支援一筆查詢回傳多種類型，因此分別進行 3 次極快查詢
        web_res = self.query_search_analytics(start_date, end_date, [], row_limit=1, search_type="web")
        img_res = self.query_search_analytics(start_date, end_date, [], row_limit=1, search_type="image")
        vid_res = self.query_search_analytics(start_date, end_date, [], row_limit=1, search_type="video")
        
        web_clicks = web_res[0].get("clicks", 0) if web_res else 0
        img_clicks = img_res[0].get("clicks", 0) if img_res else 0
        vid_clicks = vid_res[0].get("clicks", 0) if vid_res else 0
        
        total = web_clicks + img_clicks + vid_clicks
        if total == 0:
            return [
                {"label": "網頁", "value": 100, "color": "#2563EB"},
                {"label": "圖片", "value": 0, "color": "#6b7280"},
                {"label": "影片", "value": 0, "color": "#d1d5db"}
            ]
            
        return [
            {"label": "網頁", "value": round(web_clicks / total * 100), "color": "#2563EB"},
            {"label": "圖片", "value": round(img_clicks / total * 100), "color": "#6b7280"},
            {"label": "影片", "value": round(vid_clicks / total * 100), "color": "#d1d5db"}
        ]

    def _get_days_diff(self, start_date: str, end_date: str) -> int:
        """計算日期範圍內的天數差"""
        s = self._parse_date(start_date)
        e = self._parse_date(end_date)
        try:
            dt_s = datetime.strptime(s, "%Y-%m-%d")
            dt_e = datetime.strptime(e, "%Y-%m-%d")
            return max((dt_e - dt_s).days, 1)
        except:
            return 30
