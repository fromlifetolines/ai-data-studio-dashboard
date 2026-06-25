"""
AI Data Studio — backend/main.py
FastAPI 後端 API 進入點

啟動方式：
  cd backend
  uvicorn main:app --reload --port 8000

API 文件：
  http://localhost:8000/docs
"""

import os
import json
import asyncio
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── 本地模組 ──────────────────────────────────────────
from ga4_client import GA4Client, GA4Config
from ai_insight_engine import generate_insight, generate_chat_reply
from gsc_client import GSCClient
from gads_client import GoogleAdsClient
from meta_client import MetaAdsClient
import oauth_manager
import seo_evaluator

# ── App 初始化 ────────────────────────────────────────
app = FastAPI(
    title="AI Data Studio API",
    description="全渠道數據分析後端，串接 GA4 / Search Console / Google Ads / Meta Ads",
    version="1.0.0"
)

# ── CORS（允許前端 GitHub Pages 呼叫）────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 設定檔路徑 ────────────────────────────────────────
SETTINGS_PATH = Path(__file__).parent.parent / "credentials" / "settings.json"
CREDENTIALS_DIR = Path(__file__).parent.parent / "credentials"
CREDENTIALS_DIR.mkdir(exist_ok=True)

# ══════════════════════════════════════════════════════
# Request / Response 資料模型
# ══════════════════════════════════════════════════════

class GA4Settings(BaseModel):
    property_id: str           # 例：properties/123456789
    credentials_json: Optional[str] = None      # Service Account JSON 內容（字串）

class GSCSettings(BaseModel):
    site_url: str

class GAdsSettings(BaseModel):
    customer_id: str
    developer_token: str
    client_id: str
    client_secret: str
    refresh_token: str

class MetaSettings(BaseModel):
    account_id: str
    token: str

class SaveSettingsRequest(BaseModel):
    ga4: Optional[GA4Settings] = None
    gsc: Optional[GSCSettings] = None
    gads: Optional[GAdsSettings] = None
    meta: Optional[MetaSettings] = None
    openai_key: Optional[str] = None
    gemini_key: Optional[str] = None

class ValidateRequest(BaseModel):
    property_id: str
    credentials_json: Optional[str] = None

class GSCValidateRequest(BaseModel):
    site_url: str

class GAdsValidateRequest(BaseModel):
    customer_id: str
    developer_token: str
    client_id: str
    client_secret: str
    refresh_token: str

class MetaValidateRequest(BaseModel):
    account_id: str
    token: str

class AIValidateRequest(BaseModel):
    openai_key: Optional[str] = None
    gemini_key: Optional[str] = None

class CreateProfileRequest(BaseModel):
    name: str

class SwitchProfileRequest(BaseModel):
    profile_id: str

class RenameProfileRequest(BaseModel):
    profile_id: str
    name: str

class AIChatRequest(BaseModel):
    prompt: str

class SEOEvaluateRequest(BaseModel):
    url: str
    competitor_url: Optional[str] = None


# ══════════════════════════════════════════════════════
# 工具函式
# ══════════════════════════════════════════════════════

def load_all_settings() -> dict:
    """讀取本地完整設定檔（包含所有 profiles）"""
    if SETTINGS_PATH.exists():
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 自動升級舊版單一設定檔
            if not isinstance(data, dict) or "profiles" not in data:
                return _upgrade_old_settings(data)
            return data
        except Exception as e:
            print(f"[ERROR] 讀取設定檔失敗，將重置為初始狀態：{e}")
            
    return {
        "active_profile_id": "default",
        "profiles": {
            "default": {
                "id": "default",
                "name": "伯堅股份有限公司"
            }
        }
    }

def _upgrade_old_settings(old_data: dict) -> dict:
    """將舊版單一專案設定檔自動升級為多專案結構"""
    print("[INFO] 檢測到舊版設定檔，正在自動升級為多專案架構...")
    default_profile = {
        "id": "default",
        "name": "伯堅股份有限公司"
    }
    if isinstance(old_data, dict):
        for k, v in old_data.items():
            if k not in ["active_profile_id", "profiles"]:
                default_profile[k] = v
                
    new_data = {
        "active_profile_id": "default",
        "profiles": {
            "default": default_profile
        }
    }
    save_all_settings(new_data)
    
    # 複製舊金鑰
    old_cred = CREDENTIALS_DIR / "service-account.json"
    new_cred = CREDENTIALS_DIR / "service-account-default.json"
    if old_cred.exists() and not new_cred.exists():
        try:
            import shutil
            shutil.copy(old_cred, new_cred)
            print("[INFO] 已成功複製舊金鑰為 service-account-default.json")
        except Exception as e:
            print(f"[WARN] 複製舊金鑰失敗：{e}")
            
    return new_data

def save_all_settings(data: dict):
    """儲存本地完整設定檔"""
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_active_profile_id() -> str:
    """取得目前啟動的專案 ID"""
    config = load_all_settings()
    return config.get("active_profile_id", "default")

def get_active_settings() -> dict:
    """取得目前啟用專案的設定內容"""
    config = load_all_settings()
    act_id = config.get("active_profile_id", "default")
    # 確保 active_profile_id 存在於 profiles
    if act_id not in config.setdefault("profiles", {}):
        config["profiles"][act_id] = {"id": act_id, "name": "未命名專案"}
        save_all_settings(config)
    return config["profiles"][act_id]

def load_settings() -> dict:
    """相容舊端點：讀取當前啟用專案的設定"""
    return get_active_settings()

def save_settings(data: dict):
    """相容舊端點：儲存設定到目前啟用專案"""
    config = load_all_settings()
    act_id = config.get("active_profile_id", "default")
    config.setdefault("profiles", {})[act_id] = data
    save_all_settings(config)

def check_and_increment_gemini_quota() -> None:
    """檢查並增加 Gemini API 呼叫的每日額度限制，防範耗用過量 Token"""
    from datetime import date
    config = load_all_settings()
    act_id = config.get("active_profile_id", "default")
    profile = config.setdefault("profiles", {}).setdefault(act_id, {})
    
    today_str = str(date.today())
    last_date = profile.get("last_gemini_call_date", "")
    daily_count = profile.get("daily_gemini_calls", 0)
    
    if last_date != today_str:
        daily_count = 0
        profile["last_gemini_call_date"] = today_str
        
    # 限制一天最多 50 次呼叫
    max_daily_calls = 50
    if daily_count >= max_daily_calls:
        raise ValueError(f"已達到每日 AI 呼叫限制（每天最多 {max_daily_calls} 次），以防消耗過多 Token。請明天再試！")
        
    profile["daily_gemini_calls"] = daily_count + 1
    save_all_settings(config)

def get_credentials_path(profile_id: Optional[str] = None) -> Optional[Path]:
    """取得特定專案或當前啟用專案的 Service Account JSON 檔案路徑"""
    if profile_id is None:
        profile_id = get_active_profile_id()
    path = CREDENTIALS_DIR / f"service-account-{profile_id}.json"
    if path.exists():
        return path
    
    # 向後相容回退
    if profile_id == "default":
        old_path = CREDENTIALS_DIR / "service-account.json"
        if old_path.exists():
            return old_path
            
    return None

# ══════════════════════════════════════════════════════
# API 路由
# ══════════════════════════════════════════════════════

# ── 健康檢查 ──────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    """健康檢查 + 設定狀態"""
    settings = load_settings()
    auth = oauth_manager.get_auth_status()
    oauth_ok = auth["authenticated"]
    # 向後相容：如果沒有 OAuth，檢查舊 service account
    cred_path = get_credentials_path() if not oauth_ok else None

    return {
        "status": "ok",
        "version": "1.0.0",
        "config": {
            "ga4_configured":          bool(settings.get("ga4_property_id")) and (oauth_ok or cred_path is not None),
            "ga4_property_id":         settings.get("ga4_property_id", ""),
            "openai_configured":       bool(settings.get("openai_key") or os.getenv("OPENAI_API_KEY")),
            "gemini_configured":       bool(settings.get("gemini_key") or os.getenv("GEMINI_API_KEY")),
            "oauth_authenticated":     oauth_ok,
            "oauth_email":             auth.get("email"),
            "credentials_file_exists": oauth_ok or cred_path is not None,
            "gsc_configured":          bool(settings.get("gsc_site_url")) and (oauth_ok or cred_path is not None),
            "gads_configured":         bool(settings.get("gads_customer_id")),
            "meta_configured":         bool(settings.get("meta_account_id")),
            "demo_mode":              not (bool(settings.get("ga4_property_id")) and (oauth_ok or cred_path is not None)),
        }
    }

# ── OAuth 認證 ────────────────────────────────────────
@app.get("/api/auth/status")
async def auth_status():
    """回傳目前 OAuth 授權狀態"""
    return oauth_manager.get_auth_status()

@app.post("/api/auth/login")
async def auth_login():
    """
    啟動 OAuth 授權流程。
    會自動開啟瀏覽器到 Google 登入頁面。
    這個端點是同步的，最多等 60 秒，完成後回傳 email。
    """
    try:
        result = await asyncio.to_thread(oauth_manager.start_auth_flow)
        email = result.get("email", "")
        # 儲存 email 到 token 檔案
        if email:
            oauth_manager.save_email_to_token(email)
        return {"success": True, "email": email, "message": f"授權成功！帳號：{email}"}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"授權失敗：{str(e)}")

@app.post("/api/auth/logout")
async def auth_logout():
    """清除儲存的 OAuth token（登出）"""
    await asyncio.to_thread(oauth_manager.revoke_credentials)
    return {"success": True, "message": "已登出，OAuth token 已清除"}

@app.get("/api/google/sites")
async def get_google_sites():
    """獲取目前 OAuth 帳號有權限的 Search Console 網站清單"""
    oauth_creds = oauth_manager.get_credentials()
    if not oauth_creds:
        raise HTTPException(status_code=401, detail="Google 帳號未連結，請先進行授權")
        
    try:
        import google.auth.transport.requests
        request = google.auth.transport.requests.Request()
        await asyncio.to_thread(oauth_creds.refresh, request)
        token = oauth_creds.token
        
        headers = {"Authorization": f"Bearer {token}"}
        url = "https://www.googleapis.com/webmasters/v3/sites"
        
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            
        if resp.status_code == 200:
            data = resp.json()
            sites = [s.get("siteUrl") for s in data.get("siteEntry", [])]
            return {"success": True, "sites": sites}
        else:
            raise HTTPException(status_code=resp.status_code, detail=f"GSC 服務錯誤: {resp.text}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/google/properties")
async def get_google_properties():
    """獲取目前 OAuth 帳號有權限的 GA4 資源清單"""
    oauth_creds = oauth_manager.get_credentials()
    if not oauth_creds:
        raise HTTPException(status_code=401, detail="Google 帳號未連結，請先進行授權")
        
    try:
        import google.auth.transport.requests
        request = google.auth.transport.requests.Request()
        await asyncio.to_thread(oauth_creds.refresh, request)
        token = oauth_creds.token
        
        headers = {"Authorization": f"Bearer {token}"}
        url = "https://analyticsadmin.googleapis.com/v1beta/accountSummaries"
        
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            
        if resp.status_code == 200:
            data = resp.json()
            properties = []
            for acc in data.get("accountSummaries", []):
                acc_name = acc.get("displayName", "未命名帳戶")
                for prop in acc.get("propertySummaries", []):
                    properties.append({
                        "id": prop.get("property"), # properties/123456
                        "name": prop.get("displayName", "未命名資源"),
                        "account_name": acc_name
                    })
            return {"success": True, "properties": properties}
        else:
            # 如果是 API 未啟用 (403)，回傳特定錯誤，方便前端顯示引導啟用的連結
            resp_data = resp.json()
            error_msg = resp_data.get("error", {}).get("message", "")
            if resp.status_code == 403 and "Analytics Admin API" in error_msg:
                # 取得啟用的 URL
                activation_url = "https://console.developers.google.com/apis/api/analyticsadmin.googleapis.com/overview"
                for detail in resp_data.get("error", {}).get("details", []):
                    if detail.get("metadata", {}).get("activationUrl"):
                        activation_url = detail.get("metadata", {}).get("activationUrl")
                        break
                return {
                    "success": False,
                    "code": "API_DISABLED",
                    "activation_url": activation_url,
                    "detail": "Google Analytics Admin API 尚未在您的 Google Cloud 專案中啟用。請點擊連結啟用後重試。"
                }
            raise HTTPException(status_code=resp.status_code, detail=f"GA4 Admin 服務錯誤: {resp.text}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── 專案/多公司管理 ────────────────────────────────────
@app.get("/api/profiles")
async def get_profiles():
    """獲取專案/公司列表，以及當前啟用的專案 ID"""
    config = load_all_settings()
    profiles_dict = config.get("profiles", {})
    
    list_profiles = []
    for pid, p in profiles_dict.items():
        cred_path = get_credentials_path(pid)
        list_profiles.append({
            "id": pid,
            "name": p.get("name", "未命名專案"),
            "ga4_configured": bool(p.get("ga4_property_id")) and cred_path is not None,
            "gsc_configured": bool(p.get("gsc_site_url")) and cred_path is not None,
            "gads_configured": bool(p.get("gads_customer_id")),
            "meta_configured": bool(p.get("meta_account_id"))
        })
        
    return {
        "active_profile_id": config.get("active_profile_id", "default"),
        "profiles": list_profiles
    }

@app.post("/api/profiles/create")
async def create_profile(req: CreateProfileRequest):
    """建立新專案，並自動切換為作用專案"""
    import uuid
    config = load_all_settings()
    
    profile_id = f"profile_{str(uuid.uuid4())[:8]}"
    
    new_profile = {
        "id": profile_id,
        "name": req.name.strip(),
        "ga4_property_id": "",
        "gsc_site_url": "",
        "gads_customer_id": "",
        "gads_developer_token": "",
        "gads_client_id": "",
        "gads_client_secret": "",
        "gads_refresh_token": "",
        "meta_account_id": "",
        "meta_token": "",
        "openai_key": ""
    }
    
    config.setdefault("profiles", {})[profile_id] = new_profile
    config["active_profile_id"] = profile_id
    save_all_settings(config)
    
    return {"success": True, "profile_id": profile_id, "name": req.name}

@app.post("/api/profiles/switch")
async def switch_profile(req: SwitchProfileRequest):
    """切換當前作用的專案"""
    config = load_all_settings()
    if req.profile_id not in config.get("profiles", {}):
        raise HTTPException(status_code=404, detail="找不到指定的專案。")
        
    config["active_profile_id"] = req.profile_id
    save_all_settings(config)
    return {"success": True, "active_profile_id": req.profile_id}

@app.post("/api/profiles/rename")
async def rename_profile(req: RenameProfileRequest):
    """重新命名指定專案/公司"""
    config = load_all_settings()
    if req.profile_id not in config.get("profiles", {}):
        raise HTTPException(status_code=404, detail="找不到指定的專案。")
    
    new_name = req.name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="專案名稱不能為空。")
        
    config["profiles"][req.profile_id]["name"] = new_name
    save_all_settings(config)
    return {"success": True, "profile_id": req.profile_id, "name": new_name}

@app.delete("/api/profiles/{profile_id}")
async def delete_profile(profile_id: str):
    """刪除專案，如果刪除的是 active，會自動退回 default"""
    config = load_all_settings()
    if profile_id not in config.get("profiles", {}):
        raise HTTPException(status_code=404, detail="找不到指定的專案。")
        
    if profile_id == "default":
        raise HTTPException(status_code=400, detail="無法刪除預設專案。")
        
    # 刪除設定
    del config["profiles"][profile_id]
    
    # 刪除金鑰檔案
    cred_path = CREDENTIALS_DIR / f"service-account-{profile_id}.json"
    if cred_path.exists():
        try:
            cred_path.unlink()
        except Exception as e:
            print(f"[WARN] 刪除金鑰檔案失敗：{e}")
            
    # 若刪除的是當前專案，切換回 default
    if config.get("active_profile_id") == profile_id:
        config["active_profile_id"] = "default"
        
    save_all_settings(config)
    return {"success": True, "message": "專案已刪除"}

# ── 儲存設定 ──────────────────────────────────────────
@app.post("/api/settings/save")
async def save_api_settings(req: SaveSettingsRequest):
    """
    儲存 GA4 Property ID、Service Account JSON、OpenAI Key、GSC、Google Ads、Meta Ads 設定
    這是用戶在「設定頁面」填完表單後呼叫的端點
    """
    settings = load_settings()

    if req.ga4:
        # 標準化 Property ID 格式
        prop_id = req.ga4.property_id.strip()
        if not prop_id.startswith("properties/"):
            prop_id = f"properties/{prop_id}"
        settings["ga4_property_id"] = prop_id

        # 儲存 Service Account JSON 到 credentials/ 目錄 (如果提供了)；若清空則刪除對應檔案以退回 OAuth
        active_id = get_active_profile_id()
        cred_path = CREDENTIALS_DIR / f"service-account-{active_id}.json"
        
        if req.ga4.credentials_json and req.ga4.credentials_json.strip():
            try:
                parsed = json.loads(req.ga4.credentials_json)
                with open(cred_path, "w", encoding="utf-8") as f:
                    json.dump(parsed, f, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Service Account JSON 格式錯誤，請確認內容是完整的 JSON 格式。")
        else:
            # 清空時，刪除實體檔案以切換回 OAuth 模式
            if cred_path.exists():
                try:
                    cred_path.unlink()
                except Exception as e:
                    print(f"[WARN] 刪除金鑰檔失敗: {e}")
            if active_id == "default":
                old_path = CREDENTIALS_DIR / "service-account.json"
                if old_path.exists():
                    try:
                        old_path.unlink()
                    except Exception as e:
                        print(f"[WARN] 刪除舊版金鑰檔失敗: {e}")

    if req.gsc:
        settings["gsc_site_url"] = req.gsc.site_url.strip()

    if req.gads:
        settings["gads_customer_id"] = req.gads.customer_id.strip()
        settings["gads_developer_token"] = req.gads.developer_token.strip()
        settings["gads_client_id"] = req.gads.client_id.strip()
        settings["gads_client_secret"] = req.gads.client_secret.strip()
        settings["gads_refresh_token"] = req.gads.refresh_token.strip()

    if req.meta:
        settings["meta_account_id"] = req.meta.account_id.strip()
        settings["meta_token"] = req.meta.token.strip()

    if req.openai_key is not None:
        settings["openai_key"] = req.openai_key.strip()

    if req.gemini_key is not None:
        settings["gemini_key"] = req.gemini_key.strip()

    save_settings(settings)
    return {"success": True, "message": "設定已儲存"}

# ── 驗證 GA4 連線 ─────────────────────────────────────
@app.post("/api/settings/validate-ga4")
async def validate_ga4(req: ValidateRequest):
    """
    驗證 GA4 Property ID + 授權是否能成功連線。
    如果已有 OAuth 就用 OAuth，否則嘗試使用樔上傳的 Service Account JSON。
    """
    try:
        prop_id = req.property_id
        if not prop_id.startswith("properties/"):
            prop_id = f"properties/{prop_id}"

        # 優先使用傳入的 Service Account JSON 進行驗證，其次使用 OAuth，最後使用已存的金鑰檔
        if req.credentials_json and req.credentials_json.strip():
            active_id = get_active_profile_id()
            temp_path = CREDENTIALS_DIR / f"service-account-{active_id}.json"
            parsed = json.loads(req.credentials_json)
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=2)
            config = GA4Config(
                property_id=prop_id,
                credentials_path=str(temp_path)
            )
        else:
            oauth_creds = oauth_manager.get_credentials()
            if oauth_creds:
                config = GA4Config(
                    property_id=prop_id,
                    oauth_credentials=oauth_creds
                )
            else:
                cred_path = get_credentials_path()
                if cred_path:
                    config = GA4Config(
                        property_id=prop_id,
                        credentials_path=str(cred_path)
                    )
                else:
                    raise HTTPException(status_code=400, detail="請先連結 Google 帳號，或上傳 Service Account JSON")

        client = GA4Client(config)
        result = client.test_connection()
        return {"success": True, "message": "GA4 連線成功！", "property_name": result.get("name", "")}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Service Account JSON 格式錯誤")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"連線失敗：{str(e)}")

# ── 驗證 Search Console 連線 ───────────────────────────
@app.post("/api/settings/validate-gsc")
async def validate_gsc(req: GSCValidateRequest):
    """驗證 Search Console 連線"""
    try:
        oauth_creds = oauth_manager.get_credentials()
        if oauth_creds:
            client = GSCClient(site_url=req.site_url, oauth_credentials=oauth_creds)
        else:
            cred_path = get_credentials_path()
            if not cred_path:
                raise HTTPException(status_code=400, detail="請先連結 Google 帳號，或先設定 GA4 Service Account")
            client = GSCClient(site_url=req.site_url, credentials_path=str(cred_path))
        result = client.test_connection()
        return {"success": True, "message": f"Search Console 連線成功！已連接到 {result['site']}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"連線失敗：{str(e)}")

# ── 驗證 Google Ads 連線 ─────────────────────────────
@app.post("/api/settings/validate-gads")
async def validate_gads(req: GAdsValidateRequest):
    """
    驗證 Google Ads 連線
    """
    try:
        client = GoogleAdsClient(
            customer_id=req.customer_id,
            developer_token=req.developer_token,
            client_id=req.client_id,
            client_secret=req.client_secret,
            refresh_token=req.refresh_token
        )
        result = client.test_connection()
        return {"success": True, "message": f"Google Ads 連線成功！客戶 ID: {result['customer_id']}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"連線失敗：{str(e)}")

# ── 驗證 Meta Ads 連線 ───────────────────────────────
@app.post("/api/settings/validate-meta")
async def validate_meta(req: MetaValidateRequest):
    """
    驗證 Meta Ads 連線
    """
    try:
        client = MetaAdsClient(
            ad_account_id=req.account_id,
            access_token=req.token
        )
        result = client.test_connection()
        return {"success": True, "message": f"Meta Ads 連線成功！帳戶名稱: {result['name']}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"連線失敗：{str(e)}")

# ── 驗證 AI 金鑰連線 ────────────────────────────────
@app.post("/api/settings/validate-ai")
async def validate_ai(req: AIValidateRequest):
    """
    驗證 OpenAI Key 與 Gemini API Key 的有效性，確保其能成功與 AI 伺服器對接。
    """
    if not req.openai_key and not req.gemini_key:
        raise HTTPException(status_code=400, detail="請提供至少一個金鑰以進行驗證。")
        
    errors = []
    
    # 驗證 Gemini Key
    if req.gemini_key:
        try:
            # 呼叫 call_gemini 做一次極簡對接測試
            from ai_insight_engine import call_gemini
            await asyncio.to_thread(
                call_gemini, "Hello", req.gemini_key, 5
            )
        except Exception as e:
            errors.append(f"Gemini API 驗證失敗：{str(e)}")
            
    # 驗證 OpenAI Key
    if req.openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=req.openai_key)
            # 建立一個極小 Token 的對談測試
            await asyncio.to_thread(
                client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=1
            )
        except Exception as e:
            errors.append(f"OpenAI API 驗證失敗：{str(e)}")
            
    if errors:
        raise HTTPException(status_code=400, detail="；".join(errors))
        
    return {"success": True, "message": "AI 連線與金鑰驗證成功！"}

# ── 讀取目前設定 ──────────────────────────────────────
@app.get("/api/settings")
async def get_settings():
    """讀取目前的設定狀態（不回傳敏感資訊）"""
    settings = load_settings()
    cred_path = get_credentials_path()
    auth = oauth_manager.get_auth_status()
    oauth_ok = auth["authenticated"]

    return {
        "ga4_property_id":         settings.get("ga4_property_id", ""),
        "ga4_configured":          bool(settings.get("ga4_property_id")) and (oauth_ok or cred_path is not None),
        "openai_configured":       bool(settings.get("openai_key") or os.getenv("OPENAI_API_KEY")),
        "gemini_key":              settings.get("gemini_key", ""),
        "gemini_configured":       bool(settings.get("gemini_key") or os.getenv("GEMINI_API_KEY")),
        "credentials_file_exists": oauth_ok or cred_path is not None,
        "google_email":            auth.get("email", ""),
        "gsc_site_url":            settings.get("gsc_site_url", ""),
        "gsc_configured":          bool(settings.get("gsc_site_url")) and (oauth_ok or cred_path is not None),
        "gads_customer_id":        settings.get("gads_customer_id", ""),
        "gads_developer_token":    settings.get("gads_developer_token", ""),
        "gads_client_id":          settings.get("gads_client_id", ""),
        "gads_client_secret":      settings.get("gads_client_secret", ""),
        "gads_refresh_token":      settings.get("gads_refresh_token", ""),
        "gads_configured":         bool(settings.get("gads_customer_id")),
        "meta_account_id":         settings.get("meta_account_id", ""),
        "meta_token":              settings.get("meta_token", ""),
        "meta_configured":         bool(settings.get("meta_account_id"))
    }

# ── 完整 Dashboard 數據 ───────────────────────────────
@app.get("/api/dashboard")
async def get_dashboard(
    start_date: str = "30daysAgo",
    end_date:   str = "today"
):
    """
    主要 API：回傳完整 Dashboard 所需的所有數據
    前端 dashboard.js 呼叫這個端點

    Query params:
      start_date: 例 "7daysAgo", "30daysAgo", "2025-01-01"
      end_date:   例 "today", "2025-06-08"
    """
    settings = load_settings()
    cred_path = get_credentials_path()
    auth_status = oauth_manager.get_auth_status()
    oauth_ok = auth_status["authenticated"]
    oauth_creds = oauth_manager.get_credentials() if oauth_ok else None

    has_ga4 = bool(settings.get("ga4_property_id")) and (oauth_ok or cred_path is not None)
    has_gsc = bool(settings.get("gsc_site_url")) and (oauth_ok or cred_path is not None)
    has_gads = bool(settings.get("gads_customer_id"))
    has_meta = bool(settings.get("meta_account_id"))

    # ── Demo Mode：如果所有管道都沒有設定 credentials，則返回假數據 ──
    if not (has_ga4 or has_gsc or has_gads or has_meta):
        return JSONResponse(content={
            "mode": "demo",
            "message": "目前為 Demo 模式。請至「設定」頁面完成任一資料源串接以顯示真實數據。",
            "data": _get_demo_data()
        })

    # ── 真實模式：呼叫 GA4 / GSC / Ads API ────────────────
    try:
        # 1. 準備各種 Clients
        ga4_client = None
        if settings.get("ga4_property_id"):
            if cred_path:
                config = GA4Config(
                    property_id=settings["ga4_property_id"],
                    credentials_path=str(cred_path)
                )
                ga4_client = GA4Client(config)
            elif oauth_creds:
                config = GA4Config(
                    property_id=settings["ga4_property_id"],
                    oauth_credentials=oauth_creds
                )
                ga4_client = GA4Client(config)

        gsc_client = None
        if settings.get("gsc_site_url"):
            if cred_path:
                gsc_client = GSCClient(site_url=settings["gsc_site_url"], credentials_path=str(cred_path))
            elif oauth_creds:
                gsc_client = GSCClient(site_url=settings["gsc_site_url"], oauth_credentials=oauth_creds)

        gads_client = None
        if settings.get("gads_customer_id") and settings.get("gads_developer_token"):
            gads_client = GoogleAdsClient(
                customer_id=settings["gads_customer_id"],
                developer_token=settings["gads_developer_token"],
                client_id=settings.get("gads_client_id", ""),
                client_secret=settings.get("gads_client_secret", ""),
                refresh_token=settings.get("gads_refresh_token", "")
            )

        meta_client = None
        if settings.get("meta_account_id") and settings.get("meta_token"):
            meta_client = MetaAdsClient(
                ad_account_id=settings["meta_account_id"],
                access_token=settings["meta_token"]
            )

        # 2. 並行拉取數據
        tasks = []
        
        # GA4 Tasks
        if ga4_client:
            tasks.append(asyncio.to_thread(ga4_client.get_overview, start_date, end_date))
            tasks.append(asyncio.to_thread(ga4_client.get_sessions_trend, start_date, end_date))
            tasks.append(asyncio.to_thread(ga4_client.get_traffic_sources, start_date, end_date))
            tasks.append(asyncio.to_thread(ga4_client.get_top_pages, start_date, end_date))
            tasks.append(asyncio.to_thread(ga4_client.get_device_breakdown, start_date, end_date))
        else:
            tasks.extend([None, None, None, None, None])

        # GSC Tasks
        if gsc_client:
            tasks.append(asyncio.to_thread(gsc_client.get_keywords_report, start_date, end_date))
            tasks.append(asyncio.to_thread(gsc_client.get_daily_trends, start_date, end_date))
            tasks.append(asyncio.to_thread(gsc_client.get_search_type_breakdown, start_date, end_date))
            tasks.append(asyncio.to_thread(gsc_client.query_search_analytics, start_date, end_date, []))
        else:
            tasks.extend([None, None, None, None])

        # GAds Tasks
        if gads_client:
            tasks.append(asyncio.to_thread(gads_client.get_campaigns_report, start_date, end_date))
            tasks.append(asyncio.to_thread(gads_client.get_daily_trends, start_date, end_date))
        else:
            tasks.extend([None, None])

        # Meta Tasks
        if meta_client:
            tasks.append(asyncio.to_thread(meta_client.get_campaigns_report, start_date, end_date))
            tasks.append(asyncio.to_thread(meta_client.get_daily_trends, start_date, end_date))
        else:
            tasks.extend([None, None])

        # 執行 Tasks
        # 過濾非 None 任務來並行執行，以防 exceptions
        exec_tasks = [t for t in tasks if t is not None]
        raw_results = await asyncio.gather(*exec_tasks, return_exceptions=True)
        
        # 還原到對應位置
        results = []
        result_idx = 0
        for t in tasks:
            if t is None:
                results.append(None)
            else:
                r = raw_results[result_idx]
                if isinstance(r, Exception):
                    print(f"[WARN] 數據拉取失敗：{r}")
                    results.append(None)
                else:
                    results.append(r)
                result_idx += 1

        # 展開結果
        ga4_overview, ga4_sessions_trend, ga4_traffic_sources, ga4_top_pages, ga4_device = results[0:5]
        gsc_kws, gsc_trend, gsc_search_type, gsc_overview = results[5:9]
        gads_campaigns, gads_trend = results[9:11]
        meta_campaigns, meta_trend = results[11:13]

        demo = _get_demo_data()

        # 3. 處理 GA4 數據
        if ga4_client:
            if not ga4_overview:
                ga4_overview = {}
            sessions_val = f"{ga4_overview.get('sessions', 0):,}" if "sessions" in ga4_overview else "0"
            sessions_delta = ga4_overview.get("sessions_delta", "—")
            sessions_trend = "up" if "+" in sessions_delta else "down" if "-" in sessions_delta else "flat"

            users_val = f"{ga4_overview.get('users', 0):,}" if "users" in ga4_overview else "0"
            users_delta = ga4_overview.get("users_delta", "—")
            users_trend = "up" if "+" in users_delta else "down" if "-" in users_delta else "flat"

            s_trend = ga4_sessions_trend.get("sessions_trend", []) if ga4_sessions_trend else []
            u_trend = ga4_sessions_trend.get("users_trend", []) if ga4_sessions_trend else []
            nu_trend = ga4_sessions_trend.get("new_users_trend", []) if ga4_sessions_trend else []

            t_sources = ga4_traffic_sources if ga4_traffic_sources else []
            dev_data = ga4_device if ga4_device else []
            pages_data = ga4_top_pages if ga4_top_pages else []
        else:
            sessions_val = "—"
            sessions_delta = "—"
            sessions_trend = "flat"
            users_val = "—"
            users_delta = "—"
            users_trend = "flat"
            s_trend = []
            u_trend = []
            nu_trend = []
            t_sources = []
            dev_data = []
            pages_data = []

        # 4. 處理 GSC 數據
        if gsc_client:
            kws = gsc_kws if gsc_kws is not None else []
            
            # 從 gsc_overview (dimensions=[]) 拿絕對精確的站點總體資料，解決與 Web UI 的落差
            gsc_clicks = 0
            gsc_imps = 0
            gsc_ctr = 0.0
            gsc_pos = 0.0
            if gsc_overview and isinstance(gsc_overview, list) and len(gsc_overview) > 0:
                row = gsc_overview[0]
                gsc_clicks = int(row.get("clicks", 0))
                gsc_imps = int(row.get("impressions", 0))
                gsc_ctr = float(row.get("ctr", 0.0)) * 100
                gsc_pos = float(row.get("position", 0.0))
                
            imp_val = f"{gsc_imps:,}" if gsc_imps > 0 else "0"
            imp_delta = "—"
            imp_trend = "flat"

            ssc_imp = gsc_trend.get("ssc_imp", []) if gsc_trend else []
            ssc_click = gsc_trend.get("ssc_click", []) if gsc_trend else []
            search_type = gsc_search_type if gsc_search_type else []
        else:
            kws = []
            imp_val = "—"
            imp_delta = "—"
            imp_trend = "flat"
            ssc_imp = []
            ssc_click = []
            search_type = []

        # 5. 處理廣告數據 (Google Ads & Meta Ads)
        channels = []
        total_spend = 0.0
        total_rev = 0.0
        
        # Google Ads
        gads_spend = 0.0
        gads_imp = 0
        gads_clicks = 0
        gads_conv = 0.0
        gads_rev = 0.0
        
        if gads_client:
            if gads_campaigns:
                for c in gads_campaigns:
                    gads_spend += c["spend"]
                    gads_imp += c["imp"]
                    gads_clicks += c["click"]
                    gads_conv += c["conv"]
                    gads_rev += c["spend"] * c["roas"]
            
            total_spend += gads_spend
            total_rev += gads_rev
            
            gads_roas = gads_rev / gads_spend if gads_spend > 0 else 0.0
            gads_cpa = gads_spend / gads_conv if gads_conv > 0 else 0.0
            channels.append({
                "name": "Google Ads",
                "icon": "ti-brand-google",
                "icon_bg": "#EFF6FF",
                "icon_color": "#1d4ed8",
                "spend": f"${gads_spend:,.0f}",
                "imp": f"{gads_imp/1000:.1f}K" if gads_imp >= 1000 else str(gads_imp),
                "click": f"{gads_clicks:,}",
                "conv": f"{gads_conv:,.0f}",
                "cpa": f"${gads_cpa:.1f}",
                "roas": f"{gads_roas:.2f}×",
                "status": "good" if gads_roas >= 3.0 else "warn" if gads_roas >= 1.5 else "bad"
            })
        else:
            channels.append({
                "name": "Google Ads (未連線)",
                "icon": "ti-brand-google",
                "icon_bg": "#F3F4F6",
                "icon_color": "#9ca3af",
                "spend": "—",
                "imp": "—",
                "click": "—",
                "conv": "—",
                "cpa": "—",
                "roas": "—",
                "status": "bad"
            })

        # Meta Ads
        meta_spend = 0.0
        meta_imp = 0
        meta_clicks = 0
        meta_conv = 0.0
        meta_rev = 0.0
        
        if meta_client:
            if meta_campaigns:
                for c in meta_campaigns:
                    meta_spend += c["spend"]
                    meta_imp += c["imp"]
                    meta_clicks += c["click"]
                    meta_conv += c["conv"]
                    meta_rev += c["spend"] * c["roas"]
                
            total_spend += meta_spend
            total_rev += meta_rev
            
            meta_roas = meta_rev / meta_spend if meta_spend > 0 else 0.0
            meta_cpa = meta_spend / meta_conv if meta_conv > 0 else 0.0
            channels.append({
                "name": "Meta Ads",
                "icon": "ti-brand-facebook",
                "icon_bg": "#F5F3FF",
                "icon_color": "#6d28d9",
                "spend": f"${meta_spend:,.0f}",
                "imp": f"{meta_imp/1000:.1f}K" if meta_imp >= 1000 else str(meta_imp),
                "click": f"{meta_clicks:,}",
                "conv": f"{meta_conv:,.0f}",
                "cpa": f"${meta_cpa:.1f}",
                "roas": f"{meta_roas:.2f}×",
                "status": "good" if meta_roas >= 3.0 else "warn" if meta_roas >= 1.5 else "bad"
            })
        else:
            channels.append({
                "name": "Meta Ads (未連線)",
                "icon": "ti-brand-facebook",
                "icon_bg": "#F3F4F6",
                "icon_color": "#9ca3af",
                "spend": "—",
                "imp": "—",
                "click": "—",
                "conv": "—",
                "cpa": "—",
                "roas": "—",
                "status": "bad"
            })

        # YouTube Ads
        if gads_client:
            channels.append({
                "name": "YouTube Ads",
                "icon": "ti-brand-youtube",
                "icon_bg": "#FEF2F2",
                "icon_color": "#dc2626",
                "spend": "$0",
                "imp": "0",
                "click": "0",
                "conv": "0",
                "cpa": "$0.0",
                "roas": "0.00×",
                "status": "bad"
            })
        else:
            channels.append({
                "name": "YouTube Ads (未連線)",
                "icon": "ti-brand-youtube",
                "icon_bg": "#F3F4F6",
                "icon_color": "#9ca3af",
                "spend": "—",
                "imp": "—",
                "click": "—",
                "conv": "—",
                "cpa": "—",
                "roas": "—",
                "status": "bad"
            })

        # ROAS KPI
        roas_val = f"{total_rev / total_spend:.2f}×" if total_spend > 0 else "—"
        
        # Budget breakdown
        if total_spend > 0:
            gads_pct = round(gads_spend / total_spend * 100)
            meta_pct = round(meta_spend / total_spend * 100)
            yt_pct = 100 - gads_pct - meta_pct
        else:
            gads_pct, meta_pct, yt_pct = 0, 0, 0
        
        budget = [
            {"label": "Google", "value": gads_pct, "color": "#2563EB"},
            {"label": "Meta", "value": meta_pct, "color": "#6b7280"},
            {"label": "YouTube", "value": yt_pct, "color": "#d1d5db"}
        ]

        # Daily advertising trends
        ad_spend_trend = []
        ad_rev_trend = []
        
        if gads_client or meta_client:
            merged_daily = {}
            if gads_trend and gads_trend.get("labels"):
                for idx, lbl in enumerate(gads_trend["labels"]):
                    merged_daily[lbl] = {
                        "spend": gads_trend["spend_trend"][idx],
                        "revenue": gads_trend["revenue_trend"][idx]
                    }
            if meta_trend and meta_trend.get("labels"):
                for idx, lbl in enumerate(meta_trend["labels"]):
                    if lbl not in merged_daily:
                        merged_daily[lbl] = {"spend": 0.0, "revenue": 0.0}
                    merged_daily[lbl]["spend"] += meta_trend["spend_trend"][idx]
                    merged_daily[lbl]["revenue"] += meta_trend["revenue_trend"][idx]
            
            if merged_daily:
                sorted_lbls = sorted(merged_daily.keys())
                # 取最近 14 天數據
                for lbl in sorted_lbls[-14:]:
                    ad_spend_trend.append(round(merged_daily[lbl]["spend"] / 1000.0, 1))
                    ad_rev_trend.append(round(merged_daily[lbl]["revenue"] / 1000.0, 1))
            else:
                # 即使 API 返回為空，也提供 0 的長度為 14 的趨勢，而不是示範數據
                ad_spend_trend = [0.0] * 14
                ad_rev_trend = [0.0] * 14
        else:
            ad_spend_trend = [0.0] * 14
            ad_rev_trend = [0.0] * 14

        # Calculate other sub-page metrics for GA4
        avg_duration_val = "—"
        bounce_rate_val = "—"
        new_users_ratio_val = "—"
        conversions_rate_val = "—"
        pages_per_sess_val = "—"
        conversions_val = "—"
        if ga4_client and ga4_overview:
            avg_duration_val = ga4_overview.get("avg_duration", "—")
            bounce_rate_val = ga4_overview.get("bounce_rate", "—")
            pages_per_sess_val = ga4_overview.get("pages_per_sess", "—")
            conversions_val = f"{ga4_overview.get('conversions', 0):,}"
            
            ga4_users = ga4_overview.get('users', 0)
            if ga4_users > 0:
                new_users_ratio_val = f"{ga4_overview.get('new_users', 0) / ga4_users * 100:.1f}%"
            
            ga4_sessions = ga4_overview.get('sessions', 0)
            if ga4_sessions > 0:
                conversions_rate_val = f"{ga4_overview.get('conversions', 0) / ga4_sessions * 100:.2f}%"

        # Calculate GSC metrics
        clicks_val = "—"
        ctr_val = "—"
        rank_val = "—"
        if gsc_client:
            clicks_val = f"{gsc_clicks:,}" if gsc_clicks > 0 else "0"
            ctr_val = f"{gsc_ctr:.2f}%" if gsc_ctr > 0 else "0.00%"
            rank_val = f"#{gsc_pos:.1f}" if gsc_pos > 0 else "—"

        # Calculate Ads metrics
        ad_spend_val = f"${total_spend:,.0f}" if total_spend > 0 else "—"
        ad_rev_val = f"${total_rev:,.0f}" if total_rev > 0 else "—"
        ad_conv_val = f"{gads_conv + meta_conv:,.0f}" if (gads_client or meta_client) else "—"
        
        ad_cpc_val = "—"
        ad_cpa_val = "—"
        ad_imp_val = "—"
        
        total_clicks = gads_clicks + meta_clicks
        if total_clicks > 0:
            ad_cpc_val = f"${total_spend / total_clicks:.2f}"
        
        total_conv = gads_conv + meta_conv
        if total_conv > 0:
            ad_cpa_val = f"${total_spend / total_conv:.1f}"
            
        total_imp = gads_imp + meta_imp
        if total_imp >= 1000000:
            ad_imp_val = f"{total_imp / 1000000:.2f}M"
        elif total_imp > 0:
            ad_imp_val = f"{total_imp / 1000:.1f}K"
        elif gads_client or meta_client:
            ad_imp_val = "0"

        # KPIs
        kpis = {
            "sessions":          {"value": sessions_val, "delta": sessions_delta, "trend": sessions_trend},
            "users":             {"value": users_val,    "delta": users_delta,    "trend": users_trend},
            "impressions":       {"value": imp_val,      "delta": imp_delta,      "trend": imp_trend},
            "roas":              {"value": roas_val,     "delta": "—",            "trend": "flat"},
            
            # GA4 sub-page KPIs
            "avg_duration":      {"value": avg_duration_val, "delta": "—", "trend": "flat"},
            "bounce_rate":       {"value": bounce_rate_val,  "delta": "—", "trend": "flat"},
            "new_users_ratio":   {"value": new_users_ratio_val, "delta": "—", "trend": "flat"},
            "conversions_rate":  {"value": conversions_rate_val, "delta": "—", "trend": "flat"},
            "pages_per_sess":    {"value": pages_per_sess_val, "delta": "—", "trend": "flat"},
            "conversions":       {"value": conversions_val,  "delta": "—", "trend": "flat"},
            
            # GSC sub-page KPIs
            "clicks":            {"value": clicks_val,   "delta": "—", "trend": "flat"},
            "ctr":               {"value": ctr_val,      "delta": "—", "trend": "flat"},
            "rank":              {"value": rank_val,     "delta": "—", "trend": "flat"},
            
            # Ads sub-page KPIs
            "ad_spend":          {"value": ad_spend_val, "delta": "—", "trend": "flat"},
            "ad_rev":            {"value": ad_rev_val,   "delta": "—", "trend": "flat"},
            "ad_conv":           {"value": ad_conv_val,  "delta": "—", "trend": "flat"},
            "ad_cpc":            {"value": ad_cpc_val,   "delta": "—", "trend": "flat"},
            "ad_cpa":            {"value": ad_cpa_val,   "delta": "—", "trend": "flat"},
            "ad_imp":            {"value": ad_imp_val,   "delta": "—", "trend": "flat"},
        }

        # 6. AI 洞察
        openai_key = settings.get("openai_key") or os.getenv("OPENAI_API_KEY", "")
        gemini_key = settings.get("gemini_key") or os.getenv("GEMINI_API_KEY", "")
        ai_summary = ""
        if openai_key or gemini_key:
            try:
                if gemini_key:
                    check_and_increment_gemini_quota()
                temp_analytics_data = {
                    "overview": ga4_overview,
                    "sessions_trend": ga4_sessions_trend,
                    "traffic_sources": t_sources,
                    "top_pages": pages_data,
                    "device": dev_data,
                    "keywords": kws,
                    "channels": channels
                }
                ai_summary = await asyncio.to_thread(
                    generate_insight, temp_analytics_data, openai_key, gemini_key
                )
            except Exception as e:
                err_msg = str(e)
                print(f"[WARN] AI 洞察生成失敗：{err_msg}")
                if "429" in err_msg or "quota" in err_msg.lower() or "limit" in err_msg.lower() or "exhausted" in err_msg.lower():
                    ai_summary = (
                        "⚠️ <strong>AI 額度限制</strong>：您的 Gemini/OpenAI API 金鑰已達到免費方案的調用次數限制 (每日額度 20 次已用罄)。"
                        "請稍候再試，或點擊頁面右上角的<strong>「設定 (⚙️)」</strong>按鈕更新或升級您的 API 金鑰，以享有流暢的行銷顧問摘要服務。"
                    )
                else:
                    ai_summary = f"⚠️ <strong>AI 分析服務異常</strong>：請確認您的 API 金鑰效性或連線狀態。(錯誤原因: {err_msg})"

        labels = ga4_sessions_trend.get("labels", []) if (ga4_sessions_trend and isinstance(ga4_sessions_trend, dict)) else demo.get("labels", [])
        data_payload = {
            "ai_summary": ai_summary or f"已成功串接真實數據！工作階段共 {ga4_overview.get('sessions', 0):,} 次，自然點擊 {sum(ssc_click):,} 次，廣告總花費 ${total_spend:,.0f}，全渠道 ROAS {roas_val}。",
            "labels": labels,
            "kpis": kpis,
            "sessions_trend": s_trend,
            "users_trend": u_trend,
            "new_users_trend": nu_trend,
            "traffic_source": t_sources,
            "device": dev_data,
            "pages": pages_data,
            "keywords": kws,
            "ssc_imp": ssc_imp,
            "ssc_click": ssc_click,
            "search_type": search_type,
            "channels": channels,
            "ad_revenue": ad_rev_trend,
            "ad_spend": ad_spend_trend,
            "budget": budget,
            "gads_campaigns": gads_campaigns if gads_campaigns is not None else [],
            "meta_campaigns": meta_campaigns if meta_campaigns is not None else [],
        }

        return JSONResponse(content={
            "mode": "live",
            "data": data_payload
        })

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"數據撈取失敗：{str(e)}。請確認設定資訊與 API 金鑰是否正確。"
        )

# ── 單獨 GA4 端點 ─────────────────────────────────────
@app.get("/api/ga4")
async def get_ga4_data(
    metric:     str = "sessions",
    start_date: str = "30daysAgo",
    end_date:   str = "today"
):
    """取得特定 GA4 指標數據"""
    settings = load_settings()
    cred_path = get_credentials_path()

    if not settings.get("ga4_property_id") or not cred_path:
        raise HTTPException(status_code=400, detail="尚未設定 GA4，請先完成串接設定。")

    config = GA4Config(
        property_id=settings["ga4_property_id"],
        credentials_path=str(cred_path)
    )
    client = GA4Client(config)

    try:
        data = client.get_metric(metric, start_date, end_date)
        return {"metric": metric, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── AI 洞察端點 ───────────────────────────────────────
@app.get("/api/ai-insight")
async def get_ai_insight():
    """取得最新 AI 洞察文字"""
    settings = load_settings()
    openai_key = settings.get("openai_key") or os.getenv("OPENAI_API_KEY", "")

    if not openai_key:
        return {"insight": "請設定 OpenAI API Key 以啟用 AI 洞察功能。", "mode": "no_key"}

    # 這裡可以從快取讀取，避免每次都重新呼叫 AI
    return {"insight": "AI 洞察功能已啟用。請呼叫 /api/dashboard 取得完整分析。", "mode": "ready"}

@app.post("/api/ai/chat")
async def ai_chat(req: AIChatRequest):
    """
    接收前端 Prompt，結合當前作用專案數據的 Context，交由 OpenAI 進行分析回答
    """
    settings = load_settings()
    openai_key = settings.get("openai_key") or os.getenv("OPENAI_API_KEY", "")
    gemini_key = settings.get("gemini_key") or os.getenv("GEMINI_API_KEY", "")

    # 讀取當前數據上下文
    cred_path = get_credentials_path()

    context_data = {}
    if not settings.get("ga4_property_id") or not cred_path:
        # Demo 模式數據上下文
        context_data = {
            "mode": "demo",
            "project_name": settings.get("name", "伯堅股份有限公司"),
            "kpis": {
                "sessions": "38,241 (較上週 +9.4%)",
                "users": "28,109 (較上週 +5.2%)",
                "impressions": "182K (較上週 +12%)",
                "roas": "3.61×"
            },
            "top_pages": [
                {"path": "/", "views": 12401, "bounce_rate": "38%", "conversions": "4.2%", "status": "良好"},
                {"path": "/pricing", "views": 7832, "bounce_rate": "78%", "conversions": "1.8%", "status": "待改進"},
                {"path": "/blog/ga4-guide", "views": 5210, "bounce_rate": "41%", "conversions": "2.9%", "status": "良好"}
            ],
            "top_keywords": [
                {"keyword": "數據分析工具", "impressions": 28400, "clicks": 1477, "rank": "#4.0", "trend": "+2"},
                {"keyword": "GA4 教學", "impressions": 19200, "clicks": 1306, "rank": "#3.2", "trend": "+3"},
                {"keyword": "網站流量分析", "impressions": 15800, "clicks": 616, "rank": "#6.1", "trend": "−1"}
            ],
            "channels": [
                {"channel": "Google Ads", "spend": "$68,200", "clicks": "18,400", "conversions": "1,140", "roas": "4.2×"},
                {"channel": "Meta Ads", "spend": "$42,300", "clicks": "11,200", "conversions": "580", "roas": "2.8×"}
            ]
        }
    else:
        # 真實模式數據上下文
        try:
            config = GA4Config(
                property_id=settings["ga4_property_id"],
                credentials_path=str(cred_path)
            )
            ga4_client = GA4Client(config)
            ga4_overview = ga4_client.get_overview("30daysAgo", "today")
            top_pages = ga4_client.get_top_pages("30daysAgo", "today")

            context_data = {
                "mode": "live",
                "project_name": settings.get("name", "未命名專案"),
                "ga4_overview": ga4_overview,
                "top_pages": top_pages[:5] if top_pages else []
            }

            # 加上 GSC / GAds / Meta 設定狀態
            context_data["gsc_configured"] = bool(settings.get("gsc_site_url"))
            context_data["gads_configured"] = bool(settings.get("gads_customer_id"))
            context_data["meta_configured"] = bool(settings.get("meta_account_id"))

        except Exception as e:
            context_data = {
                "mode": "live_error",
                "error": str(e),
                "message": "已啟用真實數據，但部分 API 呼叫失敗"
            }

    # 調用 OpenAI / Gemini 生成回答
    if not openai_key and not gemini_key:
        demo_answers = {
            "分析 /pricing 頁面跳出率高的原因並給出具體優化建議": """
### 📊 /pricing 頁面跳出率分析與優化建議

根據 Demo 數據，**/pricing（價格頁面）** 的瀏覽量為 **7,832 次**，但跳出率高達 **78%**，且轉換率僅有 **1.8%**。這是非常危險的訊號，代表大量有付費意圖的用戶在看到價格後直接離開。

#### 🔍 潛在原因診斷
1. **價值主張傳遞不足**：用戶進入定價頁後，沒有一眼看明白付費版與免費版的差異。
2. **缺乏信任背書**：價格頁面沒有常見問題（FAQ）或客戶案例，導致用戶產生疑慮。
3. **CTA（行動呼籲）不夠明顯**：定價方案的按鈕不突出或流程過於繁瑣。

#### 💡 具體優化建議
1. **精簡定價卡片**：將方案限制在 3 個以內，並在最推薦的方案上標註「最受歡迎」或「熱門」。
2. **新增「常見問題 FAQ」區塊**：在定價表下方直接回答「可以退款嗎？」、「如何開立發票？」等用戶結帳前最在意的問題。
3. **強化 CTA 與價值證明**：在按鈕下方加上「14 天免費試用，無需信用卡」或「隨時可取消」以降低用戶防備心。
""",
            "幫我找出本週最值得優先處理的行銷問題，條列說明": """
### 🎯 本週優先行銷優化項目

目前有兩個核心問題需要優先處理：

1. **價格頁面 (/pricing) 的高跳出率 (78%)**：
   * **影響**：阻礙了潛在付費客戶的轉換。
   * **優先級**：🔥 極高（直接影響營收）。
   * **動作**：簡化定價比較表、增設 14 天免費試用期。

2. **Meta Ads 的 ROAS 下降 (從 3.2 降至 2.8)**：
   * **影響**：廣告投放效率變差，花費增加但營收成長變緩。
   * **優先級**：⚡ 高。
   * **動作**：檢視廣告受眾是否有重疊現象，或更換新的廣告素材，並排除過去 30 天內已轉換的用戶。
""",
            "根據這份數據，我的網站下一步應該優化哪些地方？": """
### 🚀 網站下一步優化指南

根據當前全渠道數據，您的網站下一階段應從以下兩個維度著手：

#### 1. SEO 內容與關鍵字佈局
* 關鍵字「**數據分析工具**」排名為 **#4.0**（點擊率 5.2%），屬於極佳的導流詞。建議在首頁或核心產品頁面中加強與此關鍵字相關的 H1/H2 標題與內文比重，力求衝入前三名（CTR 將能倍增）。
* 「**網站流量分析**」排名下跌了 1 名（#6.1），需要新增內容並進行內部連結更新。

#### 2. 付費廣告預算調整
* **Google Ads** 表現優異（ROAS 4.2x），而 **Meta Ads**（ROAS 2.8x）與 **YouTube Ads**（ROAS 1.9x）表現相對疲軟。
* 建議在下週將 YouTube Ads 的預算調降 15%-20%，並將該部分預算轉移至 Google Ads 關鍵字廣告以最大化整體 ROAS。
"""
        }

        # 針對特定彈窗的分析按鈕提供對應解答
        for prompt_key, answer in demo_answers.items():
            if prompt_key in req.prompt:
                return {"reply": answer, "mode": "demo_mock"}

        # 模糊匹配彈窗分析
        if "pricing" in req.prompt:
            return {"reply": demo_answers["分析 /pricing 頁面跳出率高的原因並給出具體優化建議"], "mode": "demo_mock"}
        elif "關鍵字" in req.prompt or "SEO" in req.prompt:
            return {"reply": demo_answers["根據這份數據，我的網站下一步應該優化哪些地方？"], "mode": "demo_mock"}
        elif "廣告" in req.prompt or "ROAS" in req.prompt:
            return {"reply": demo_answers["幫我找出本週最值得優先處理的行銷問題，條列說明"], "mode": "demo_mock"}

        # 若是自訂問答，回傳提示需要 API key
        return {
            "reply": """
### 💡 啟用 AI 行銷顧問

目前尚未設定 OpenAI 或 Gemini API Key，無法進行即時的自訂問答。

**請依以下步驟啟用完整功能：**
1. 前往右上角「**設定**」頁面。
2. 在 **STEP 5：AI 洞察與智慧建議** 欄位中貼上您的 `OpenAI API Key` 或 `Gemini API Key`。
3. 儲存設定後，AI 行銷顧問即可根據您的**真實網站數據**，提供量身打造的行銷洞察！
""",
            "mode": "no_key"
        }

    try:
        if gemini_key:
            check_and_increment_gemini_quota()
        reply = await asyncio.to_thread(
            generate_chat_reply, req.prompt, context_data, openai_key, gemini_key
        )
        return {"reply": reply, "mode": "live"}
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "quota" in err_msg.lower() or "limit" in err_msg.lower() or "exhausted" in err_msg.lower():
            friendly_err = (
                "⚠️ AI 行銷顧問對話額度已用完。您目前使用的 Gemini API Key (免費版) 限制每日最多調用 20 次。 "
                "請點擊右上角「設定」按鈕更換您的 API 金鑰，或於稍後再試。"
            )
            raise HTTPException(status_code=429, detail=friendly_err)
        else:
            raise HTTPException(status_code=500, detail=f"AI 分析失敗：{err_msg}")

@app.post("/api/seo/evaluate")
async def evaluate_seo_endpoint(req: SEOEvaluateRequest):
    """三維搜尋曝光測評 API 進入點"""
    settings = get_active_settings()
    gemini_key = settings.get("gemini_key", "")
    
    # 執行評估
    result = await asyncio.to_thread(
        seo_evaluator.run_full_evaluation, req.url, gemini_key
    )
    
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "未知錯誤"))
        
    # 處理競品對比 (如果提供的話)
    competitor_result = None
    if req.competitor_url:
        comp_res = await asyncio.to_thread(
            seo_evaluator.run_full_evaluation, req.competitor_url, gemini_key
        )
        if comp_res.get("success", False):
            competitor_result = comp_res
            
    return {
        "primary": result,
        "competitor": competitor_result
    }

# ══════════════════════════════════════════════════════
# Demo 數據（沒有 credentials 時使用）
# ══════════════════════════════════════════════════════

def _get_demo_data() -> dict:
    """回傳 Demo 模式假數據，與前端 MOCK 對應"""
    return {
        "ai_summary": "這是 <strong>Demo 模式</strong>，目前顯示的是示範數據。請前往「設定」頁面串接你的 GA4 帳號，即可看到真實數據與 AI 分析。",
        "labels": ["5/26","5/27","5/28","5/29","5/30","5/31","6/1","6/2","6/3","6/4","6/5","6/6","6/7","6/8"],
        "kpis": {
            "sessions":    {"value": "38,241", "delta": "+9.4%", "trend": "up"},
            "users":       {"value": "28,109", "delta": "+5.2%", "trend": "up"},
            "impressions": {"value": "182K",   "delta": "+12%",  "trend": "up"},
            "roas":        {"value": "3.61×",  "delta": "—",     "trend": "flat"},
        },
        "sessions_trend":  [2400,2800,2600,3100,3300,3800,3600,3200,3700,4000,4300,4100,4500,4700],
        "users_trend":     [1800,2100,1950,2300,2450,2800,2650,2400,2800,3000,3200,3100,3400,3500],
        "new_users_trend": [1100,1300,1200,1500,1600,1900,1750,1500,1750,1900,2000,1950,2100,2200],
        "traffic_source": [
            {"label": "自然搜尋", "value": 61, "color": "#2563EB"},
            {"label": "直接流量", "value": 18, "color": "#6b7280"},
            {"label": "社群媒體", "value": 12, "color": "#93c5fd"},
            {"label": "其他",     "value":  9, "color": "#e5e7eb"},
        ],
        "device": [
            {"label": "手機", "value": 58, "color": "#2563EB"},
            {"label": "桌機", "value": 34, "color": "#6b7280"},
            {"label": "平板", "value":  8, "color": "#d1d5db"},
        ],
        "pages": [
            {"path": "/",               "views": 12401, "unique": 9820,  "time": "3:12", "bounce": "38%", "conv": "4.2%", "status": "good"},
            {"path": "/pricing",        "views": 7832,  "unique": 6140,  "time": "1:05", "bounce": "78%", "conv": "1.8%", "status": "bad"},
            {"path": "/blog/ga4-guide", "views": 5210,  "unique": 4890,  "time": "4:28", "bounce": "41%", "conv": "2.9%", "status": "good"},
            {"path": "/features",       "views": 3980,  "unique": 3200,  "time": "2:50", "bounce": "45%", "conv": "3.1%", "status": "warn"},
            {"path": "/docs",           "views": 2140,  "unique": 1980,  "time": "5:10", "bounce": "33%", "conv": "6.4%", "status": "good"},
        ],
        "keywords": [
            {"kw": "數據分析工具",          "imp": 28400, "click": 1477, "ctr": "5.2%", "rank": "#4.0", "trend": "+2", "opp": "進入首頁", "opp_type": "good"},
            {"kw": "GA4 教學",              "imp": 19200, "click": 1306, "ctr": "6.8%", "rank": "#3.2", "trend": "+3", "opp": "搶 Top3",  "opp_type": "good"},
            {"kw": "網站流量分析",          "imp": 15800, "click":  616, "ctr": "3.9%", "rank": "#6.1", "trend": "−1", "opp": "加強內容", "opp_type": "warn"},
            {"kw": "google analytics 設定", "imp": 11400, "click":  240, "ctr": "2.1%", "rank": "#12",  "trend": "+5", "opp": "有潛力",   "opp_type": "warn"},
            {"kw": "SEO 工具推薦",          "imp":  9600, "click":  173, "ctr": "1.8%", "rank": "#18",  "trend": "—",  "opp": "待衝刺",   "opp_type": "bad"},
        ],
        "ssc_imp":    [11000,12500,12000,13800,14200,15000,14500,13200,14800,16000,17000,16500,18000,18200],
        "ssc_click":  [420,490,460,530,550,590,570,510,570,620,660,640,690,692],
        "search_type": [
            {"label": "網頁", "value": 83, "color": "#2563EB"},
            {"label": "圖片", "value": 10, "color": "#6b7280"},
            {"label": "影片", "value":  7, "color": "#d1d5db"},
        ],
        "channels": [
            {"name": "Google Ads",  "icon": "ti-brand-google",   "icon_bg": "#EFF6FF", "icon_color": "#1d4ed8", "spend": "$68,200", "imp": "520K",  "click": "18,400", "conv": "1,140", "cpa": "$59.8",  "roas": "4.2×", "status": "good"},
            {"name": "Meta Ads",    "icon": "ti-brand-facebook", "icon_bg": "#F5F3FF", "icon_color": "#6d28d9", "spend": "$42,300", "imp": "890K",  "click": "11,200", "conv": "580",   "cpa": "$72.9",  "roas": "2.8×", "status": "warn"},
            {"name": "YouTube Ads", "icon": "ti-brand-youtube",  "icon_bg": "#FFF7ED", "icon_color": "#c2410c", "spend": "$14,000", "imp": "1.2M",  "click": "4,800",  "conv": "122",   "cpa": "$114.8", "roas": "1.9×", "status": "bad"},
        ],
        "ad_revenue": [29,33,31,36,39,44,42,38,43,47,50,49,53,56],
        "ad_spend":   [7.5,8,8,9,10,11,9.5,8.8,10,12,13,12,13,14],
        "budget": [
            {"label": "Google",  "value": 55, "color": "#2563EB"},
            {"label": "Meta",    "value": 34, "color": "#6b7280"},
            {"label": "YouTube", "value": 11, "color": "#d1d5db"},
        ],
        "gads_campaigns": [
            {"name": "Google_Search_品牌詞專案", "spend": 28400, "imp": 120000, "click": 8400, "conv": 620, "cpa": 45.8, "roas": 4.8, "status": "good", "campaign_status": "ENABLED"},
            {"name": "Google_Display_核心受眾開發", "spend": 19800, "imp": 250000, "click": 6200, "conv": 280, "cpa": 70.7, "roas": 3.2, "status": "good", "campaign_status": "ENABLED"},
            {"name": "Google_PerformanceMax_全品類導購", "spend": 20000, "imp": 150000, "click": 3800, "conv": 240, "cpa": 83.3, "roas": 4.1, "status": "good", "campaign_status": "ENABLED"},
        ],
        "meta_campaigns": [
            {"name": "Meta_Conversion_女裝春季新品", "spend": 25000, "imp": 420000, "click": 6800, "conv": 380, "cpa": 65.8, "roas": 3.1, "status": "good"},
            {"name": "Meta_Traffic_官網流量導流", "spend": 8300, "imp": 280000, "click": 3100, "conv": 80, "cpa": 103.7, "roas": 1.2, "status": "bad"},
            {"name": "Meta_Conversion_節慶促銷再行銷", "spend": 9000, "imp": 190000, "click": 1300, "conv": 120, "cpa": 75.0, "roas": 3.5, "status": "good"},
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
