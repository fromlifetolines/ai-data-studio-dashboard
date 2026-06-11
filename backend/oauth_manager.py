"""
AI Data Studio — backend/oauth_manager.py
Google OAuth 2.0 個人帳號認證管理

使用 howardhuang720818@gmail.com 等個人 Google 帳號
授權存取 GA4 / Search Console，無需服務帳號。
"""

import json
import webbrowser
from pathlib import Path
from typing import Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# 所需的 API 權限範圍
SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# 檔案路徑
CREDENTIALS_DIR = Path(__file__).parent.parent / "credentials"
CLIENT_SECRET_PATH = CREDENTIALS_DIR / "client_secret.json"
TOKEN_PATH = CREDENTIALS_DIR / "oauth_token.json"


def get_credentials() -> Optional[Credentials]:
    """
    取得有效的 OAuth credentials。
    - 若已有 token 且有效，直接返回
    - 若 token 過期，用 refresh_token 自動刷新
    - 若無 token，返回 None（需先呼叫 start_auth_flow）
    """
    if not TOKEN_PATH.exists():
        return None

    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    except Exception as e:
        print(f"[OAuth] 讀取 token 失敗：{e}")
        return None

    # Token 有效，直接返回
    if creds and creds.valid:
        return creds

    # Token 過期但有 refresh_token，自動刷新
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_token(creds)
            print("[OAuth] Token 已自動刷新")
            return creds
        except Exception as e:
            print(f"[OAuth] Token 刷新失敗：{e}")
            TOKEN_PATH.unlink(missing_ok=True)
            return None

    return None


def start_auth_flow() -> dict:
    """
    啟動 OAuth 授權流程。
    開啟瀏覽器讓使用者登入 Google 帳號並授權，
    成功後儲存 token 到本地檔案。
    回傳 {"success": True, "email": "..."}
    """
    if not CLIENT_SECRET_PATH.exists():
        raise FileNotFoundError(
            f"找不到 client_secret.json，請確認檔案在：{CLIENT_SECRET_PATH}"
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRET_PATH),
        scopes=SCOPES
    )

    # 在本機啟動一個臨時 HTTP server 接收 callback
    # redirect_uri 自動設為 http://localhost:PORT
    creds = flow.run_local_server(
        port=0,           # 自動選可用的 port
        prompt="consent", # 每次都顯示授權畫面（方便切換帳號）
        open_browser=True,
    )

    _save_token(creds)
    email = _get_email_from_token(creds)
    print(f"[OAuth] 授權成功！帳號：{email}")
    return {"success": True, "email": email}


def revoke_credentials():
    """清除本地儲存的 token（登出）"""
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
        print("[OAuth] Token 已清除")


def get_auth_status() -> dict:
    """
    取得目前的授權狀態。
    回傳 {"authenticated": bool, "email": str | None}
    """
    creds = get_credentials()
    if creds is None:
        return {"authenticated": False, "email": None}
    email = _get_email_from_token(creds)
    return {"authenticated": True, "email": email}


def _save_token(creds: Credentials):
    """將 credentials 序列化儲存到本地檔案"""
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
    }
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump(token_data, f, ensure_ascii=False, indent=2)


def _get_email_from_token(creds: Credentials) -> Optional[str]:
    """從 token 中提取使用者 Email（透過 id_token 或 userinfo API）"""
    try:
        # 方法一：從 id_token 中讀取（最快）
        if hasattr(creds, "id_token") and creds.id_token:
            import base64, json as _json
            payload = creds.id_token.split(".")[1]
            # 補齊 base64 padding
            payload += "=" * (4 - len(payload) % 4)
            data = _json.loads(base64.urlsafe_b64decode(payload))
            if "email" in data:
                return data["email"]
    except Exception:
        pass

    try:
        # 方法二：從 token 檔案讀取已儲存的 email
        if TOKEN_PATH.exists():
            with open(TOKEN_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "email" in data:
                return data["email"]
    except Exception:
        pass

    return None


def save_email_to_token(email: str):
    """在 token 檔案中額外儲存 email 欄位"""
    if TOKEN_PATH.exists():
        try:
            with open(TOKEN_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["email"] = email
            with open(TOKEN_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[OAuth] 儲存 email 失敗：{e}")
