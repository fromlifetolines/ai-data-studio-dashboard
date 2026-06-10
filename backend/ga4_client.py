"""
GA4 數據撈取模組
若 credentials 未設定，自動回傳 mock 數據供開發使用。
"""

import os
from pathlib import Path
from typing import Any

CREDENTIALS_DIR = Path(__file__).resolve().parent.parent / "credentials"
SERVICE_ACCOUNT_FILE = CREDENTIALS_DIR / "service-account.json"
GA4_PROPERTY_ID = os.getenv("GA4_PROPERTY_ID", "")


def _mock_ga4_data() -> dict[str, Any]:
    """開發用 mock 數據，結構與真實 API 回傳一致。"""
    return {
        "source": "mock",
        "traffic_sources": {
            "labels": ["Organic Search", "Paid Social", "Paid Search", "Direct", "Referral"],
            "values": [45, 25, 20, 7, 3],
        },
        "daily_metrics": {
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "sessions": [3200, 4100, 3800, 4500, 5200, 6100, 5800],
            "conversions": [42, 58, 51, 67, 82, 95, 88],
        },
        "summary": {
            "total_sessions": 32700,
            "total_users": 28400,
            "bounce_rate": 42.3,
            "avg_session_duration": "2m 34s",
            "conversions": 483,
            "conversion_rate": 1.48,
        },
    }


def fetch_ga4_data(property_id: str | None = None) -> dict[str, Any]:
    """
    從 GA4 Data API 撈取流量與轉換數據。
    若無 credentials 或 property_id，回傳 mock 數據。
    """
    pid = property_id or GA4_PROPERTY_ID
    if not pid or not SERVICE_ACCOUNT_FILE.exists():
        return _mock_ga4_data()

    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            DateRange,
            Dimension,
            Metric,
            RunReportRequest,
        )
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_file(
            str(SERVICE_ACCOUNT_FILE),
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        )
        client = BetaAnalyticsDataClient(credentials=credentials)

        # 流量來源
        source_request = RunReportRequest(
            property=f"properties/{pid}",
            date_ranges=[DateRange(start_date="28daysAgo", end_date="today")],
            dimensions=[Dimension(name="sessionDefaultChannelGroup")],
            metrics=[Metric(name="sessions")],
        )
        source_response = client.run_report(source_request)

        labels, values = [], []
        for row in source_response.rows:
            labels.append(row.dimension_values[0].value)
            values.append(int(row.metric_values[0].value))

        # 每日趨勢
        daily_request = RunReportRequest(
            property=f"properties/{pid}",
            date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
            dimensions=[Dimension(name="date")],
            metrics=[
                Metric(name="sessions"),
                Metric(name="conversions"),
            ],
        )
        daily_response = client.run_report(daily_request)

        daily_labels, sessions, conversions = [], [], []
        for row in daily_response.rows:
            daily_labels.append(row.dimension_values[0].value[-4:])
            sessions.append(int(row.metric_values[0].value))
            conversions.append(int(row.metric_values[1].value))

        # 摘要
        summary_request = RunReportRequest(
            property=f"properties/{pid}",
            date_ranges=[DateRange(start_date="28daysAgo", end_date="today")],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="bounceRate"),
                Metric(name="averageSessionDuration"),
                Metric(name="conversions"),
            ],
        )
        summary_response = client.run_report(summary_request)
        row = summary_response.rows[0] if summary_response.rows else None

        summary = {
            "total_sessions": int(row.metric_values[0].value) if row else 0,
            "total_users": int(row.metric_values[1].value) if row else 0,
            "bounce_rate": round(float(row.metric_values[2].value) * 100, 1) if row else 0,
            "avg_session_duration": _format_duration(float(row.metric_values[3].value)) if row else "0s",
            "conversions": int(row.metric_values[4].value) if row else 0,
            "conversion_rate": 0,
        }
        if summary["total_sessions"] > 0:
            summary["conversion_rate"] = round(
                summary["conversions"] / summary["total_sessions"] * 100, 2
            )

        return {
            "source": "ga4",
            "traffic_sources": {"labels": labels, "values": values},
            "daily_metrics": {
                "labels": daily_labels,
                "sessions": sessions,
                "conversions": conversions,
            },
            "summary": summary,
        }

    except Exception as e:
        data = _mock_ga4_data()
        data["source"] = "mock"
        data["error"] = str(e)
        return data


def _format_duration(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"
