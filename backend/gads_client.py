"""
AI Data Studio — backend/gads_client.py
Google Ads REST API 封裝模組
"""

import re
from datetime import datetime, timedelta
import httpx

class GoogleAdsClient:
    def __init__(self, customer_id: str, developer_token: str, client_id: str, client_secret: str, refresh_token: str):
        # 標準化 Customer ID，移除連字號
        self.customer_id = customer_id.strip().replace("-", "")
        self.developer_token = developer_token.strip()
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.refresh_token = refresh_token.strip()

    def _get_access_token(self) -> str:
        """使用 OAuth2 Refresh Token 刷新獲取 Access Token"""
        url = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, data=payload)
            
        if resp.status_code == 200:
            return resp.json()["access_token"]
        else:
            raise Exception(f"OAuth 刷新失敗 (HTTP {resp.status_code}): {resp.text}")

    def _parse_date(self, date_str: str) -> str:
        """轉換相對日期為 YYYY-MM-DD"""
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

    def test_connection(self) -> dict:
        """測試 Google Ads 連線是否成功"""
        try:
            token = self._get_access_token()
            url = f"https://googleads.googleapis.com/v17/customers/{self.customer_id}/googleAds:search"
            headers = {
                "Authorization": f"Bearer {token}",
                "developer-token": self.developer_token,
                "Content-Type": "application/json"
            }
            # 查一個最簡單的資料
            payload = {
                "query": "SELECT campaign.id FROM campaign LIMIT 1"
            }
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                
            if resp.status_code == 200:
                return {"success": True, "customer_id": self.customer_id}
            else:
                raise Exception(f"API 回傳錯誤 (HTTP {resp.status_code}): {resp.text}")
        except Exception as e:
            raise Exception(f"Google Ads 連線失敗，請確認設定的憑證與客戶 ID 是否正確。錯誤資訊：{str(e)}")

    def query_ads(self, query_str: str) -> list:
        """執行 GAQL 查詢"""
        try:
            token = self._get_access_token()
            url = f"https://googleads.googleapis.com/v17/customers/{self.customer_id}/googleAds:search"
            headers = {
                "Authorization": f"Bearer {token}",
                "developer-token": self.developer_token,
                "Content-Type": "application/json"
            }
            payload = {"query": query_str}
            
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                
            if resp.status_code != 200:
                print(f"[Google Ads Client Error] {resp.text}")
                return []
                
            return resp.json().get("results", [])
        except Exception as e:
            print(f"[Google Ads Client Exception] {str(e)}")
            return []

    def get_campaigns_report(self, start_date: str = "30daysAgo", end_date: str = "today") -> list:
        """取得活動 (Campaign) 表現報告"""
        s = self._parse_date(start_date)
        e = self._parse_date(end_date)
        
        query = f"""
            SELECT 
                campaign.name, 
                campaign.status, 
                metrics.cost_micros, 
                metrics.impressions, 
                metrics.clicks, 
                metrics.conversions, 
                metrics.conversions_value 
            FROM campaign 
            WHERE segments.date BETWEEN '{s}' AND '{e}'
        """
        results = self.query_ads(query)
        
        campaigns = []
        for r in results:
            camp = r.get("campaign", {})
            metrics = r.get("metrics", {})
            
            name = camp.get("name", "未命名廣告")
            status = camp.get("status", "UNKNOWN")
            
            # Google Ads API 回傳的指標多數是字串格式以防溢位
            spend = float(metrics.get("costMicros", 0)) / 1000000.0
            imp = int(metrics.get("impressions", 0))
            click = int(metrics.get("clicks", 0))
            conv = float(metrics.get("conversions", 0.0))
            rev = float(metrics.get("conversionsValue", 0.0))
            
            cpa = spend / conv if conv > 0 else 0.0
            roas = rev / spend if spend > 0 else 0.0
            
            # 轉換為前端展示格式
            status_show = "good" if roas >= 3.0 else "warn" if roas >= 1.5 else "bad"
            
            campaigns.append({
                "name": name,
                "spend": spend,
                "imp": imp,
                "click": click,
                "conv": conv,
                "cpa": cpa,
                "roas": roas,
                "status": status_show,
                "campaign_status": status
            })
            
        return campaigns

    def get_daily_trends(self, start_date: str = "13daysAgo", end_date: str = "today") -> dict:
        """取得每日花費與廣告收益金額趨勢"""
        s = self._parse_date(start_date)
        e = self._parse_date(end_date)
        
        query = f"""
            SELECT 
                segments.date, 
                metrics.cost_micros, 
                metrics.conversions_value 
            FROM campaign 
            WHERE segments.date BETWEEN '{s}' AND '{e}'
        """
        results = self.query_ads(query)
        
        daily_map = {}
        for r in results:
            date_str = r.get("segments", {}).get("date")
            if not date_str:
                continue
            metrics = r.get("metrics", {})
            cost = float(metrics.get("costMicros", 0)) / 1000000.0
            val = float(metrics.get("conversionsValue", 0.0))
            
            if date_str not in daily_map:
                daily_map[date_str] = {"spend": 0.0, "revenue": 0.0}
            daily_map[date_str]["spend"] += cost
            daily_map[date_str]["revenue"] += val
            
        # 排序日期並回傳趨勢列表
        sorted_dates = sorted(daily_map.keys())
        
        labels = []
        spend_trend = []
        revenue_trend = []
        
        for d in sorted_dates:
            parts = d.split("-")
            labels.append(f"{parts[1]}/{parts[2]}" if len(parts) == 3 else d)
            # 轉換為以「千元(K)」為單位以符合 Chart 期待，或依前端格式調整
            spend_trend.append(round(daily_map[d]["spend"], 2))
            revenue_trend.append(round(daily_map[d]["revenue"], 2))
            
        return {
            "labels": labels,
            "spend_trend": spend_trend,
            "revenue_trend": revenue_trend
        }
