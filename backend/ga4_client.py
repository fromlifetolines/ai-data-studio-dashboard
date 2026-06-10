"""
AI Data Studio — backend/ga4_client.py
GA4 Data API 封裝模組

依賴：
  google-analytics-data

安裝：
  pip install google-analytics-data
"""

from dataclasses import dataclass
from typing import Optional
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Metric, Dimension, OrderBy, Filter, FilterExpression
)
from google.oauth2 import service_account


@dataclass
class GA4Config:
    property_id: str      # 格式：properties/123456789
    credentials_path: str # Service Account JSON 路徑


class GA4Client:
    def __init__(self, config: GA4Config):
        self.property_id = config.property_id
        credentials = service_account.Credentials.from_service_account_file(
            config.credentials_path,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"]
        )
        self.client = BetaAnalyticsDataClient(credentials=credentials)

    # ── 連線測試 ────────────────────────────────────
    def test_connection(self) -> dict:
        """測試 GA4 連線是否成功，回傳 Property 基本資訊"""
        req = RunReportRequest(
            property=self.property_id,
            date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
            metrics=[Metric(name="sessions")],
        )
        resp = self.client.run_report(req)
        return {"name": self.property_id, "rows": len(resp.rows)}

    # ── 總覽 KPI ────────────────────────────────────
    def get_overview(self, start_date: str = "30daysAgo", end_date: str = "today") -> dict:
        """
        取得核心 KPI：
        工作階段、不重複用戶、平均停留時間、跳出率、
        新用戶、轉換率、每次工作階段頁數
        """
        req = RunReportRequest(
            property=self.property_id,
            date_ranges=[
                DateRange(start_date=start_date, end_date=end_date),
                DateRange(start_date=f"{self._days_ago(start_date)*2}daysAgo",
                          end_date=f"{self._days_ago(start_date)}daysAgo"),  # 前期比較
            ],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="newUsers"),
                Metric(name="averageSessionDuration"),
                Metric(name="bounceRate"),
                Metric(name="screenPageViewsPerSession"),
                Metric(name="conversions"),
            ],
        )
        resp = self.client.run_report(req)

        def parse_row(row):
            vals = [v.value for v in row.metric_values]
            return {
                "sessions":       int(float(vals[0])),
                "users":          int(float(vals[1])),
                "new_users":      int(float(vals[2])),
                "avg_duration":   self._fmt_duration(float(vals[3])),
                "bounce_rate":    f"{float(vals[4]) * 100:.1f}%",
                "pages_per_sess": f"{float(vals[5]):.1f}",
                "conversions":    int(float(vals[6])),
            }

        current  = parse_row(resp.rows[0]) if resp.rows else {}
        previous = parse_row(resp.rows[1]) if len(resp.rows) > 1 else {}

        # 計算增減幅
        if current and previous:
            current["sessions_delta"]  = self._pct_delta(current["sessions"], previous["sessions"])
            current["users_delta"]     = self._pct_delta(current["users"],    previous["users"])
            current["conv_delta"]      = self._pct_delta(current["conversions"], previous["conversions"])

        return current

    # ── 工作階段趨勢（14天每日數據）──────────────────
    def get_sessions_trend(self, start_date: str = "13daysAgo", end_date: str = "today") -> dict:
        """取得每日工作階段、用戶、新用戶數，用於趨勢折線圖"""
        req = RunReportRequest(
            property=self.property_id,
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="newUsers"),
            ],
            dimensions=[Dimension(name="date")],
            order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))],
        )
        resp = self.client.run_report(req)

        dates, sessions, users, new_users = [], [], [], []
        for row in resp.rows:
            raw_date = row.dimension_values[0].value   # 格式：20250601
            dates.append(f"{raw_date[4:6]}/{raw_date[6:8]}")
            vals = row.metric_values
            sessions.append(int(float(vals[0].value)))
            users.append(int(float(vals[1].value)))
            new_users.append(int(float(vals[2].value)))

        return {
            "labels":           dates,
            "sessions_trend":   sessions,
            "users_trend":      users,
            "new_users_trend":  new_users,
        }

    # ── 流量來源 ────────────────────────────────────
    def get_traffic_sources(self, start_date: str = "30daysAgo", end_date: str = "today") -> list:
        """取得流量來源分佈（自然搜尋、付費、直接、社群等）"""
        req = RunReportRequest(
            property=self.property_id,
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            metrics=[Metric(name="sessions")],
            dimensions=[Dimension(name="sessionDefaultChannelGrouping")],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        )
        resp = self.client.run_report(req)

        total = sum(int(float(r.metric_values[0].value)) for r in resp.rows)
        colors = ["#2563EB", "#6b7280", "#93c5fd", "#e5e7eb", "#fbbf24", "#34d399"]
        result = []
        for i, row in enumerate(resp.rows[:6]):
            sessions = int(float(row.metric_values[0].value))
            pct = round(sessions / total * 100) if total > 0 else 0
            result.append({
                "label": row.dimension_values[0].value,
                "value": pct,
                "color": colors[i % len(colors)],
            })
        return result

    # ── 熱門頁面 ────────────────────────────────────
    def get_top_pages(self, start_date: str = "30daysAgo", end_date: str = "today", limit: int = 20) -> list:
        """取得熱門頁面列表，包含瀏覽量、跳出率、停留時間"""
        req = RunReportRequest(
            property=self.property_id,
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            metrics=[
                Metric(name="screenPageViews"),
                Metric(name="totalUsers"),
                Metric(name="averageSessionDuration"),
                Metric(name="bounceRate"),
                Metric(name="conversions"),
            ],
            dimensions=[Dimension(name="pagePath")],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)],
            limit=limit,
        )
        resp = self.client.run_report(req)

        pages = []
        for row in resp.rows:
            vals = row.metric_values
            views    = int(float(vals[0].value))
            unique   = int(float(vals[1].value))
            duration = float(vals[2].value)
            bounce   = float(vals[3].value) * 100
            conv     = float(vals[4].value)
            conv_rate = (conv / views * 100) if views > 0 else 0

            # 判斷狀態
            if bounce > 65:
                status = "bad"
            elif bounce > 50:
                status = "warn"
            else:
                status = "good"

            pages.append({
                "path":   row.dimension_values[0].value,
                "views":  views,
                "unique": unique,
                "time":   self._fmt_duration(duration),
                "bounce": f"{bounce:.1f}%",
                "conv":   f"{conv_rate:.1f}%",
                "status": status,
            })
        return pages

    # ── 裝置分佈 ────────────────────────────────────
    def get_device_breakdown(self, start_date: str = "30daysAgo", end_date: str = "today") -> list:
        """取得裝置類型分佈（手機 / 桌機 / 平板）"""
        req = RunReportRequest(
            property=self.property_id,
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            metrics=[Metric(name="sessions")],
            dimensions=[Dimension(name="deviceCategory")],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        )
        resp = self.client.run_report(req)

        total = sum(int(float(r.metric_values[0].value)) for r in resp.rows)
        color_map = {"mobile": "#2563EB", "desktop": "#6b7280", "tablet": "#d1d5db"}
        label_map = {"mobile": "手機",    "desktop": "桌機",    "tablet": "平板"}

        return [
            {
                "label": label_map.get(row.dimension_values[0].value, row.dimension_values[0].value),
                "value": round(int(float(row.metric_values[0].value)) / total * 100) if total > 0 else 0,
                "color": color_map.get(row.dimension_values[0].value, "#e5e7eb"),
            }
            for row in resp.rows
        ]

    # ── 取得單一指標 ─────────────────────────────────
    def get_metric(self, metric_name: str, start_date: str, end_date: str) -> list:
        """通用方法：取得特定指標的每日數據"""
        metric_map = {
            "sessions":  "sessions",
            "users":     "totalUsers",
            "pageviews": "screenPageViews",
            "bounce":    "bounceRate",
        }
        ga4_metric = metric_map.get(metric_name, metric_name)

        req = RunReportRequest(
            property=self.property_id,
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            metrics=[Metric(name=ga4_metric)],
            dimensions=[Dimension(name="date")],
            order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))],
        )
        resp = self.client.run_report(req)
        return [
            {
                "date":  row.dimension_values[0].value,
                "value": float(row.metric_values[0].value),
            }
            for row in resp.rows
        ]

    # ── 工具函式 ─────────────────────────────────────
    @staticmethod
    def _fmt_duration(seconds: float) -> str:
        """秒數轉 m:ss 格式"""
        s = int(seconds)
        return f"{s // 60}:{s % 60:02d}"

    @staticmethod
    def _pct_delta(current: float, previous: float) -> str:
        """計算百分比增減"""
        if previous == 0:
            return "—"
        delta = (current - previous) / previous * 100
        sign = "+" if delta >= 0 else ""
        return f"{sign}{delta:.1f}%"

    @staticmethod
    def _days_ago(date_str: str) -> int:
        """從 '30daysAgo' 解析天數，預設 30"""
        if "daysAgo" in date_str:
            return int(date_str.replace("daysAgo", ""))
        return 30
