"""
AI Data Studio — backend/meta_client.py
Meta Marketing API 封裝模組
"""

import json
import re
from datetime import datetime, timedelta
import httpx

class MetaAdsClient:
    def __init__(self, ad_account_id: str, access_token: str):
        # 標準化廣告帳號 ID，必須以 act_ 開頭
        acc_id = ad_account_id.strip()
        if not acc_id.startswith("act_"):
            self.ad_account_id = f"act_{acc_id}"
        else:
            self.ad_account_id = acc_id
            
        self.access_token = access_token.strip()
        self.api_version = "v19.0"

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
        """測試 Meta Ads 連線是否成功"""
        try:
            url = f"https://graph.facebook.com/{self.api_version}/{self.ad_account_id}"
            params = {
                "access_token": self.access_token,
                "fields": "name,account_id"
            }
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, params=params)
                
            if resp.status_code == 200:
                data = resp.json()
                return {"success": True, "name": data.get("name", self.ad_account_id)}
            else:
                raise Exception(f"API 回傳錯誤 (HTTP {resp.status_code}): {resp.text}")
        except Exception as e:
            raise Exception(f"Meta Ads 連線失敗，請確認 Access Token 與廣告帳號 ID 是否正確。錯誤資訊：{str(e)}")

    def _get_action_value(self, actions: list, action_type: str = "purchase") -> float:
        """從 Meta actions 欄位中提取特定類型的數值"""
        if not actions or not isinstance(actions, list):
            return 0.0
        for act in actions:
            if act.get("action_type") == action_type:
                return float(act.get("value", 0.0))
        # 備用：若找不到精確的 purchase，尋找包含 purchase 的欄位
        for act in actions:
            if "purchase" in act.get("action_type", ""):
                return float(act.get("value", 0.0))
        return 0.0

    def get_campaigns_report(self, start_date: str = "30daysAgo", end_date: str = "today") -> list:
        """取得 Campaign 表現報告"""
        s = self._parse_date(start_date)
        e = self._parse_date(end_date)
        
        url = f"https://graph.facebook.com/{self.api_version}/{self.ad_account_id}/insights"
        params = {
            "access_token": self.access_token,
            "level": "campaign",
            "fields": "campaign_name,spend,impressions,clicks,actions,purchase_roas",
            "time_range": json.dumps({"since": s, "until": e}),
            "limit": 50
        }
        
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, params=params)
            
        if resp.status_code != 200:
            print(f"[Meta Ads Client Error] {resp.text}")
            return []
            
        data = resp.json().get("data", [])
        
        campaigns = []
        for item in data:
            name = item.get("campaign_name", "未命名廣告")
            spend = float(item.get("spend", 0.0))
            imp = int(item.get("impressions", 0))
            click = int(item.get("clicks", 0))
            
            # 解析轉換次數
            conv = self._get_action_value(item.get("actions", []), "purchase")
            if conv == 0.0:
                # 嘗試拿 `offsite_conversion.fb_pixel_purchase`
                conv = self._get_action_value(item.get("actions", []), "offsite_conversion.fb_pixel_purchase")
            
            # 解析 ROAS
            roas = self._get_action_value(item.get("purchase_roas", []), "purchase")
            if roas == 0.0 and spend > 0:
                # 備用計算：如果 actions 裡面有購買金額，可以用來除以 spend。這裡暫時使用 Meta 回傳值或 fallback。
                pass
                
            cpa = spend / conv if conv > 0 else 0.0
            
            status_show = "good" if roas >= 3.0 else "warn" if roas >= 1.5 else "bad"
            
            campaigns.append({
                "name": name,
                "spend": spend,
                "imp": imp,
                "click": click,
                "conv": conv,
                "cpa": cpa,
                "roas": roas,
                "status": status_show
            })
            
        return campaigns

    def get_daily_trends(self, start_date: str = "13daysAgo", end_date: str = "today") -> dict:
        """取得每日花費與轉換金額趨勢"""
        s = self._parse_date(start_date)
        e = self._parse_date(end_date)
        
        url = f"https://graph.facebook.com/{self.api_version}/{self.ad_account_id}/insights"
        params = {
            "access_token": self.access_token,
            "level": "account",
            "fields": "spend,action_values",
            "time_range": json.dumps({"since": s, "until": e}),
            "time_increment": 1,
            "limit": 100
        }
        
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, params=params)
            
        if resp.status_code != 200:
            print(f"[Meta Ads Client Error] {resp.text}")
            return {"labels": [], "spend_trend": [], "revenue_trend": []}
            
        data = resp.json().get("data", [])
        # 按日期排序
        data_sorted = sorted(data, key=lambda x: x.get("date_start", ""))
        
        labels = []
        spend_trend = []
        revenue_trend = []
        
        for item in data_sorted:
            date_str = item.get("date_start", "")
            if not date_str:
                continue
            parts = date_str.split("-")
            labels.append(f"{parts[1]}/{parts[2]}" if len(parts) == 3 else date_str)
            
            spend = float(item.get("spend", 0.0))
            # 轉換價值 (購買金額)
            revenue = self._get_action_value(item.get("action_values", []), "purchase")
            if revenue == 0.0:
                revenue = self._get_action_value(item.get("action_values", []), "offsite_conversion.fb_pixel_purchase")
                
            spend_trend.append(round(spend, 2))
            revenue_trend.append(round(revenue, 2))
            
        return {
            "labels": labels,
            "spend_trend": spend_trend,
            "revenue_trend": revenue_trend
        }
