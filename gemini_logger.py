import os
import sqlite3
import time
import json
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

try:
    from dotenv import load_dotenv
    for env_candidate in [
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent / ".env",
        Path("/Users/windfox/Github-Sync/.env")
    ]:
        if env_candidate.exists():
            load_dotenv(dotenv_path=env_candidate)
            break
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "gemini_usage.db"
PRICING_PATH = BASE_DIR / "model_pricing.json"

# --- Pricing Table Loader ---
def load_pricing() -> Dict[str, Dict[str, float]]:
    if PRICING_PATH.exists():
        try:
            with open(PRICING_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "default": {"input_per_1m": 0.10, "output_per_1m": 0.40}
    }

PRICING = load_pricing()

# --- Google AI Studio Free Tier Limits Definition (All Models) ---
MODEL_RATE_LIMITS = {
    "gemini-3.8-flash": {
        "displayName": "Gemini 3.8 Flash",
        "category": "Text-out models",
        "rpm": 5, "tpm": 250000, "rpd": 20,
        "aliases": ["gemini-3.8-flash", "gemini-3.8"]
    },
    "gemini-3.7-flash": {
        "displayName": "Gemini 3.7 Flash",
        "category": "Text-out models",
        "rpm": 5, "tpm": 250000, "rpd": 20,
        "aliases": ["gemini-3.7-flash", "gemini-3.7"]
    },
    "gemini-3.6-flash": {
        "displayName": "Gemini 3.6 Flash",
        "category": "Text-out models",
        "rpm": 5, "tpm": 250000, "rpd": 20,
        "aliases": ["gemini-3.6-flash", "gemini-3.6"]
    },
    "gemini-2.5-flash": {
        "displayName": "Gemini 2.5 Flash",
        "category": "Text-out models",
        "rpm": 5, "tpm": 250000, "rpd": 20,
        "aliases": ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    },
    "gemini-3.5-flash": {
        "displayName": "Gemini 3.5 Flash",
        "category": "Text-out models",
        "rpm": 5, "tpm": 250000, "rpd": 20,
        "aliases": ["gemini-3.5-flash", "gemini-3.5"]
    },
    "gemini-3.1-flash-lite": {
        "displayName": "Gemini 3.1 Flash Lite",
        "category": "Text-out models",
        "rpm": 15, "tpm": 250000, "rpd": 500,
        "aliases": ["gemini-3.1-flash-lite", "gemini-3.1-lite"]
    },
    "gemini-3.5-flash-lite": {
        "displayName": "Gemini 3.5 Flash Lite",
        "category": "Text-out models",
        "rpm": 15, "tpm": 250000, "rpd": 500,
        "aliases": ["gemini-3.5-flash-lite", "gemini-2.0-flash-lite", "gemini-2.5-flash-lite"]
    },
    "antigravity": {
        "displayName": "Antigravity",
        "category": "Agents",
        "rpm": 60, "tpm": 100000, "rpd": 100,
        "aliases": ["antigravity", "agy", "agent-system"]
    },
    "nano-banana-pro": {
        "displayName": "Nano Banana Pro (Gemini 3 Pro Image)",
        "category": "Image models",
        "rpm": 5, "tpm": 100000, "rpd": 20,
        "aliases": ["nano-banana-pro", "gemini-3-pro-image", "imagen-3.0", "imagen-3"]
    },
    "gemini-3.1-pro": {
        "displayName": "Gemini 3.1 Pro",
        "category": "Text-out models",
        "rpm": 2, "tpm": 32000, "rpd": 50,
        "aliases": ["gemini-3.1-pro", "gemini-1.5-pro", "gemini-2.0-pro-exp"]
    },
    "nano-banana-2": {
        "displayName": "Nano Banana 2 (Gemini 3.1 Flash Image)",
        "category": "Image models",
        "rpm": 10, "tpm": 100000, "rpd": 50,
        "aliases": ["nano-banana-2", "gemini-3.1-flash-image"]
    },
    "nano-banana-2-lite": {
        "displayName": "Nano Banana 2 Lite (Gemini 3.1 Flash Lite Image)",
        "category": "Image models",
        "rpm": 15, "tpm": 100000, "rpd": 100,
        "aliases": ["nano-banana-2-lite", "gemini-3.1-flash-lite-image"]
    }
}

# --- Database Initialization & Migration ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT (datetime('now', 'localtime')),
                model_name TEXT NOT NULL,
                prompt_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                latency_ms REAL DEFAULT 0.0,
                status_code INTEGER DEFAULT 200,
                estimated_cost REAL DEFAULT 0.0,
                error_message TEXT DEFAULT '',
                caller_info TEXT DEFAULT '',
                account_name TEXT DEFAULT '預設帳號'
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS antigravity_quota (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT UNIQUE DEFAULT 'Google 帳號 1 (主要)',
                plan_name TEXT DEFAULT 'Google AI Pro',
                credit_overages INTEGER DEFAULT 0,
                gemini_weekly_pct REAL DEFAULT 86.0,
                gemini_weekly_refresh_seconds INTEGER DEFAULT 169200,
                gemini_5hr_pct REAL DEFAULT 92.0,
                gemini_5hr_refresh_seconds INTEGER DEFAULT 15840,
                claude_gpt_weekly_pct REAL DEFAULT 100.0,
                claude_gpt_5hr_pct REAL DEFAULT 100.0,
                updated_at DATETIME DEFAULT (datetime('now', 'localtime'))
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_limits_snapshot (
                account_name TEXT,
                time_range TEXT,
                model_id TEXT,
                current_rpm INTEGER DEFAULT 0,
                current_tpm REAL DEFAULT 0.0,
                current_rpd INTEGER DEFAULT 0,
                updated_at DATETIME DEFAULT (datetime('now', 'localtime')),
                PRIMARY KEY (account_name, time_range, model_id)
            )
        """)
        
        # 檢查並自動遷移舊版資料表 (追加 account_name 欄位)
        cursor.execute("PRAGMA table_info(usage_logs)")
        cols = [col[1] for col in cursor.fetchall()]
        if "account_name" not in cols:
            cursor.execute("ALTER TABLE usage_logs ADD COLUMN account_name TEXT DEFAULT '預設帳號'")

        cursor.execute("PRAGMA table_info(antigravity_quota)")
        agy_cols = [col[1] for col in cursor.fetchall()]
        if "account_name" not in agy_cols:
            cursor.execute("ALTER TABLE antigravity_quota ADD COLUMN account_name TEXT DEFAULT 'Google 帳號 1 (主要)'")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON usage_logs(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_model ON usage_logs(model_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_account ON usage_logs(account_name)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_agy_account ON antigravity_quota(account_name)")

        # 初始化預設 3 組 Google 帳號 Antigravity 配額資料 (若無資料)
        cursor.execute("SELECT COUNT(*) FROM antigravity_quota")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO antigravity_quota (
                    id, account_name, plan_name, credit_overages,
                    gemini_weekly_pct, gemini_weekly_refresh_seconds,
                    gemini_5hr_pct, gemini_5hr_refresh_seconds,
                    claude_gpt_weekly_pct, claude_gpt_5hr_pct, updated_at
                ) VALUES 
                (1, 'Google 帳號 1 (主要)', 'Google AI Pro', 0, 86.0, 169200, 92.0, 15840, 100.0, 100.0, datetime('now', 'localtime')),
                (2, 'Google 帳號 2 (備用/工作)', 'Google AI Pro', 0, 100.0, 604800, 100.0, 18000, 100.0, 100.0, datetime('now', 'localtime')),
                (3, 'Google 帳號 3 (備用)', 'Google AI Pro', 0, 100.0, 604800, 100.0, 18000, 100.0, 100.0, datetime('now', 'localtime'))
            """)

        conn.commit()

init_db()

# --- Antigravity Quota Helpers ---
def get_antigravity_accounts() -> list:
    """取得所有已記錄的 Antigravity Google 帳號清單 (優先採用 .env 中的 Email 設定，支援 3 組以上帳號)"""
    import os
    try:
        from dotenv import load_dotenv
        for env_candidate in [
            BASE_DIR.parent / ".env",
            BASE_DIR / ".env",
            Path("/Users/windfox/Github-Sync/.env")
        ]:
            if env_candidate.exists():
                load_dotenv(dotenv_path=env_candidate, override=True)
                break
    except Exception:
        pass

    # 讀取 .env 中的所有 Google 帳號 Email 設定 (支援 GOOGLE_ACCOUNT_1_EMAIL ~ GOOGLE_ACCOUNT_N_EMAIL 及別名)
    configured_emails = []
    for i in range(1, 10):
        email = (os.getenv(f"GOOGLE_ACCOUNT_{i}_EMAIL") or os.getenv(f"GOOGLE_EMAIL_{i}") or "").strip()
        if email:
            configured_emails.append(email)
        elif i <= 3:
            default_labels = [
                "Google 帳號 1 (主要)",
                "Google 帳號 2 (備用/工作)",
                "Google 帳號 3 (備用)"
            ]
            configured_emails.append(default_labels[i - 1])

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # 確保 UNIQUE 索引存在
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_agy_account ON antigravity_quota(account_name)")

        # 暫時加上前綴以防止帳號名稱 UNIQUE 衝突 (如順序調換時)
        cursor.execute("UPDATE antigravity_quota SET account_name = '__agy_temp__' || id")
        
        for idx, acc_email in enumerate(configured_emails, start=1):
            cursor.execute("SELECT id FROM antigravity_quota WHERE id = ?", (idx,))
            if cursor.fetchone():
                cursor.execute("UPDATE antigravity_quota SET account_name = ? WHERE id = ?", (acc_email, idx))
            else:
                cursor.execute("""
                    INSERT INTO antigravity_quota (
                        id, account_name, plan_name, credit_overages,
                        gemini_weekly_pct, gemini_weekly_refresh_seconds,
                        gemini_5hr_pct, gemini_5hr_refresh_seconds,
                        claude_gpt_weekly_pct, claude_gpt_5hr_pct, updated_at
                    ) VALUES (?, ?, 'Google AI Pro', 0, 100.0, 604800, 100.0, 18000, 100.0, 100.0, datetime('now', 'localtime'))
                """, (idx, acc_email))

        # 刪除多餘的過期佔位行
        cursor.execute("DELETE FROM antigravity_quota WHERE id > ?", (len(configured_emails),))
        conn.commit()

        cursor.execute("SELECT account_name FROM antigravity_quota ORDER BY id ASC")
        rows = cursor.fetchall()
        accounts = [r[0] for r in rows if r[0]]
        return accounts if accounts else configured_emails

def get_antigravity_quota(account_name: str = None) -> dict:
    """取得指定 Antigravity IDE 帳號當前模型配額狀態與倒數資訊"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if account_name:
            cursor.execute("SELECT * FROM antigravity_quota WHERE account_name = ? LIMIT 1", (account_name,))
        else:
            cursor.execute("SELECT * FROM antigravity_quota ORDER BY id ASC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            return {
                "account_name": account_name or "Google 帳號 1 (主要)",
                "plan_name": "Google AI Pro",
                "credit_overages": 0,
                "gemini_weekly_pct": 100.0,
                "gemini_weekly_desc": "7 days, 0 hours",
                "gemini_5hr_pct": 100.0,
                "gemini_5hr_desc": "5 hours, 0 minutes",
                "claude_gpt_weekly_pct": 100.0,
                "claude_gpt_5hr_pct": 100.0,
                "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        data = dict(row)
        # 計算動態倒數
        try:
            updated_dt = datetime.datetime.strptime(data["updated_at"], "%Y-%m-%d %H:%M:%S")
            elapsed = (datetime.datetime.now() - updated_dt).total_seconds()
        except Exception:
            elapsed = 0

        w_rem = max(0, data["gemini_weekly_refresh_seconds"] - int(elapsed))
        h_rem = max(0, data["gemini_5hr_refresh_seconds"] - int(elapsed))

        w_days = w_rem // 86400
        w_hours = (w_rem % 86400) // 3600
        data["gemini_weekly_desc"] = f"{w_days} day{'s' if w_days > 1 else ''}, {w_hours} hours" if w_rem > 0 else "Fully Refreshed"

        h_hours = h_rem // 3600
        h_mins = (h_rem % 3600) // 60
        data["gemini_5hr_desc"] = f"{h_hours} hours, {h_mins} minutes" if h_rem > 0 else "Fully Refreshed"

        return data

def update_antigravity_quota(
    account_name: str,
    gemini_weekly_pct: float,
    gemini_weekly_hours: float,
    gemini_5hr_pct: float,
    gemini_5hr_mins: float,
    plan_name: str = "Google AI Pro",
    credit_overages: int = 0
):
    """更新/校準指定 Antigravity 帳號配額數據"""
    weekly_sec = int(gemini_weekly_hours * 3600)
    fivehr_sec = int(gemini_5hr_mins * 60)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_agy_account ON antigravity_quota(account_name)")
        cursor.execute("""
            UPDATE antigravity_quota SET
                plan_name = ?,
                credit_overages = ?,
                gemini_weekly_pct = ?,
                gemini_weekly_refresh_seconds = ?,
                gemini_5hr_pct = ?,
                gemini_5hr_refresh_seconds = ?,
                updated_at = datetime('now', 'localtime')
            WHERE account_name = ?
        """, (plan_name, credit_overages, gemini_weekly_pct, weekly_sec, gemini_5hr_pct, fivehr_sec, account_name))
        
        if cursor.rowcount == 0:
            cursor.execute("""
                INSERT INTO antigravity_quota (
                    account_name, plan_name, credit_overages,
                    gemini_weekly_pct, gemini_weekly_refresh_seconds,
                    gemini_5hr_pct, gemini_5hr_refresh_seconds,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
            """, (account_name, plan_name, credit_overages, gemini_weekly_pct, weekly_sec, gemini_5hr_pct, fivehr_sec))
        conn.commit()

# --- DeepL Quota & Usage Helpers ---
def get_deepl_usage(auth_key: Optional[str] = None) -> dict:
    """
    向 DeepL API 查詢當前帳號的翻譯字數配額與剩餘狀況
    支援 Free Tier (以 :fx 結尾) 與 Pro Tier
    """
    import urllib.request
    import urllib.error
    import json

    key = (auth_key or os.getenv("DEEPL_API_KEY") or "").strip()
    if not key:
        return {
            "configured": False,
            "status_msg": "未在 .env 設定 DEEPL_API_KEY",
            "character_count": 0,
            "character_limit": 500000,
            "usage_pct": 0.0,
            "remaining_chars": 500000,
            "tier": "未設定"
        }

    is_free = key.endswith(":fx")
    api_url = "https://api-free.deepl.com/v2/usage" if is_free else "https://api.deepl.com/v2/usage"

    try:
        req = urllib.request.Request(
            api_url,
            headers={
                "Authorization": f"DeepL-Auth-Key {key}",
                "User-Agent": "AI_Quota_Monitor/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
            count = data.get("character_count", 0)
            limit = data.get("character_limit", 500000)
            pct = round((count / limit * 100), 2) if limit > 0 else 0.0
            return {
                "configured": True,
                "status_msg": "正常連線",
                "character_count": count,
                "character_limit": limit,
                "usage_pct": pct,
                "remaining_chars": max(0, limit - count),
                "tier": "Free (免費方案 50萬字/月)" if is_free else "Pro (付費方案)"
            }
    except urllib.error.HTTPError as e:
        return {
            "configured": True,
            "status_msg": f"DeepL API 錯誤 HTTP {e.code}: {e.reason}",
            "character_count": 0,
            "character_limit": 500000,
            "usage_pct": 0.0,
            "remaining_chars": 0,
            "tier": "金鑰無效或權限不足"
        }
    except Exception as e:
        return {
            "configured": True,
            "status_msg": f"連線異常: {e}",
            "character_count": 0,
            "character_limit": 500000,
            "usage_pct": 0.0,
            "remaining_chars": 0,
            "tier": "連線失敗"
        }

# --- Cost Calculator ---
def calculate_cost(model_name: str, prompt_tokens: int, output_tokens: int) -> float:
    rates = PRICING.get(model_name, PRICING.get("default", {"input_per_1m": 0.10, "output_per_1m": 0.40}))
    cost = (prompt_tokens / 1_000_000 * rates["input_per_1m"]) + (output_tokens / 1_000_000 * rates["output_per_1m"])
    return round(cost, 6)

def log_file_error(msg: str):
    """寫入錯誤日誌至 logs/error.log"""
    try:
        log_dir = BASE_DIR / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_dir / "error.log", "a", encoding="utf-8") as f:
            f.write(f"[{now_str}] {msg}\n")
    except Exception:
        pass

# --- Core Logging Function ---
def log_api_call(
    model_name: str,
    prompt_tokens: int = 0,
    output_tokens: int = 0,
    latency_ms: float = 0.0,
    status_code: int = 200,
    error_message: str = "",
    caller_info: str = "",
    account_name: str = "預設帳號"
) -> int:
    """Logs a single Gemini API call to SQLite with account tracking."""
    if status_code != 200 or error_message:
        log_file_error(f"Account: {account_name} | Model: {model_name} | Status: {status_code} | Msg: {error_message}")
    total_tokens = prompt_tokens + output_tokens
    cost = calculate_cost(model_name, prompt_tokens, output_tokens)
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO usage_logs (
                model_name, prompt_tokens, output_tokens, total_tokens,
                latency_ms, status_code, estimated_cost, error_message, caller_info, account_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            model_name, prompt_tokens, output_tokens, total_tokens,
            round(latency_ms, 2), status_code, cost, error_message, caller_info, account_name
        ))
        conn.commit()
        return cursor.lastrowid

def log_gemini_response(response: Any, model_name: str, start_time: float, caller_info: str = "", account_name: str = "預設帳號"):
    """Utility helper to extract tokens from a google-genai response object and log it."""
    latency_ms = (time.time() - start_time) * 1000.0
    prompt_tokens = 0
    output_tokens = 0
    
    try:
        if hasattr(response, 'usage_metadata'):
            meta = response.usage_metadata
            prompt_tokens = getattr(meta, 'prompt_token_count', 0) or 0
            output_tokens = getattr(meta, 'candidates_token_count', 0) or 0
    except Exception:
        pass
        
    return log_api_call(
        model_name=model_name,
        prompt_tokens=prompt_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        status_code=200,
        caller_info=caller_info,
        account_name=account_name
    )

# --- Database Query Helpers ---
def get_account_display_name(acc_name: str) -> str:
    """轉換帳號/Key名稱為友善顯示名稱 (精確綁定所屬 Google 帳號 Email 與用途)"""
    email_1 = os.getenv("GOOGLE_ACCOUNT_1_EMAIL", "shonarmstrong5@gmail.com")
    email_2 = os.getenv("GOOGLE_ACCOUNT_2_EMAIL", "dandyzuko2@gmail.com")
    
    mapping = {
        "GEMINI_PODCAST_KEY": f"GEMINI_PODCAST_KEY (Podcast挑錯 1 / {email_1})",
        "GEMINI_PODCAST_KEY2": f"GEMINI_PODCAST_KEY2 (Podcast挑錯 2 / {email_1})",
        "GEMINI_JAV_KEY": f"GEMINI_JAV_KEY (日語翻譯 / {email_1})",
        "GEMINI_JAV_TRANSLATE_2_KEY": f"GEMINI_JAV_TRANSLATE_2_KEY (日語翻譯2 / {email_1})",
        "GEMINI_FINANCE_KEY": f"GEMINI_FINANCE_KEY (台股金融 / {email_1})",
        "GEMINI_BACKUP_KEY_2": f"GEMINI_BACKUP_KEY_2 (備援金鑰 / {email_2})"
    }
    return mapping.get(acc_name, acc_name)

def get_available_accounts() -> list:
    """取得所有帳號名稱（結合 .env 中的金鑰名稱與資料庫記錄）"""
    accounts = []
    # 1. 檢查 .env
    for var in [
        "GEMINI_PODCAST_KEY",
        "GEMINI_PODCAST_KEY2",
        "GEMINI_JAV_KEY",
        "GEMINI_JAV_TRANSLATE_2_KEY",
        "GEMINI_FINANCE_KEY",
        "GEMINI_BACKUP_KEY_2"
    ]:
        if os.getenv(var) and os.getenv(var).strip():
            if var not in accounts:
                accounts.append(var)
    # 2. 檢查資料庫
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT account_name FROM usage_logs WHERE account_name IS NOT NULL AND account_name != ''")
        for r in cursor.fetchall():
            if r[0] not in accounts:
                accounts.append(r[0])
    if not accounts:
        accounts = ["GEMINI_PODCAST_KEY", "GEMINI_PODCAST_KEY2", "GEMINI_JAV_KEY", "GEMINI_JAV_TRANSLATE_2_KEY", "GEMINI_FINANCE_KEY", "GEMINI_BACKUP_KEY_2"]
    return accounts

def seed_default_official_snapshots():
    """初始化官方 Google AI Studio 截圖基準數據 (針對所有同屬 shonarmstrong5@gmail.com 的 Key 與帳號)"""
    official_28d = {
        "gemini-3.7-flash": {"rpm": 6, "tpm": 150040.0, "rpd": 20},
        "gemini-3.6-flash": {"rpm": 3, "tpm": 14220.0, "rpd": 11},
        "gemini-2.5-flash": {"rpm": 2, "tpm": 8.0, "rpd": 5},
        "gemini-3.5-flash": {"rpm": 2, "tpm": 135850.0, "rpd": 20},
        "gemini-3.1-flash-lite": {"rpm": 1, "tpm": 5.0, "rpd": 1},
        "gemini-3.5-flash-lite": {"rpm": 1, "tpm": 7350.0, "rpd": 1},
        "antigravity": {"rpm": 0, "tpm": 0.0, "rpd": 0},
        "nano-banana-pro": {"rpm": 0, "tpm": 0.0, "rpd": 0},
        "gemini-3.1-pro": {"rpm": 0, "tpm": 0.0, "rpd": 0},
        "nano-banana-2": {"rpm": 0, "tpm": 0.0, "rpd": 0},
        "nano-banana-2-lite": {"rpm": 0, "tpm": 0.0, "rpd": 0},
    }
    email_1 = os.getenv("GOOGLE_ACCOUNT_1_EMAIL", "shonarmstrong5@gmail.com")
    target_keys = [
        "GEMINI_PODCAST_KEY",
        "GEMINI_JAV_KEY",
        "GEMINI_JAV_TRANSLATE_2_KEY",
        "GEMINI_FINANCE_KEY",
        "Whisper_correction",
        email_1
    ]
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        for m_id, vals in official_28d.items():
            for acc in target_keys:
                cursor.execute("""
                    INSERT INTO rate_limits_snapshot (account_name, time_range, model_id, current_rpm, current_tpm, current_rpd, updated_at)
                    VALUES (?, '28 Days', ?, ?, ?, ?, datetime('now', 'localtime'))
                    ON CONFLICT(account_name, time_range, model_id) DO UPDATE SET
                        current_rpm = excluded.current_rpm,
                        current_tpm = excluded.current_tpm,
                        current_rpd = excluded.current_rpd,
                        updated_at = datetime('now', 'localtime')
                """, (acc, m_id, vals["rpm"], vals["tpm"], vals["rpd"]))
        conn.commit()

def save_rate_limits_snapshot(account_name: str, time_range: str, rate_dict: dict):
    """保存/校準特定帳號在特定時間區間內的官方 Rate Limits 數據快照"""
    range_key = "28 Days" if "28" in time_range else ("7 Days" if "7" in time_range else "Today")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        for m_id, vals in rate_dict.items():
            cursor.execute("""
                INSERT INTO rate_limits_snapshot (account_name, time_range, model_id, current_rpm, current_tpm, current_rpd, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
                ON CONFLICT(account_name, time_range, model_id) DO UPDATE SET
                    current_rpm = excluded.current_rpm,
                    current_tpm = excluded.current_tpm,
                    current_rpd = excluded.current_rpd,
                    updated_at = datetime('now', 'localtime')
            """, (account_name, range_key, m_id, vals.get("rpm", 0), vals.get("tpm", 0.0), vals.get("rpd", 0)))
        conn.commit()

def get_all_accounts_overview(time_range: str = "今日 (Today)") -> list:
    """傳回所有帳號用量、Token、花費與 429 狀態總覽矩陣"""
    accounts = get_available_accounts()
    overview = []
    for acc in accounts:
        st = get_stats_summary(account_name=acc, time_range=time_range)
        overview.append({
            "account_name": acc,
            "display_name": get_account_display_name(acc),
            "today_calls": st["today_calls"],
            "today_tokens": st["today_total_tokens"],
            "today_cost": st["today_cost"],
            "today_429": st["today_429_count"],
            "today_errors": st["today_errors"],
            "status": "🔴 429 限制" if st["today_429_count"] > 0 else "🟢 正常"
        })
    return overview

def get_recent_logs(limit: int = 100, account_name: Optional[str] = None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if account_name and account_name != "全部帳號":
            cursor.execute("SELECT * FROM usage_logs WHERE account_name = ? ORDER BY id DESC LIMIT ?", (account_name, limit))
        else:
            cursor.execute("SELECT * FROM usage_logs ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

def get_stats_summary(account_name: Optional[str] = None, time_range: str = "今日 (Today)"):
    """取得特定時間範圍與特定帳號的統計數據"""
    if "28" in time_range:
        date_filter = "datetime(timestamp) >= datetime('now', '-28 days', 'localtime')"
    elif "7" in time_range:
        date_filter = "datetime(timestamp) >= datetime('now', '-7 days', 'localtime')"
    else:
        date_filter = "date(timestamp) = date('now', 'localtime')"

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        filter_acc = "AND account_name = ?" if (account_name and account_name != "全部帳號") else ""
        params = [account_name] if filter_acc else []

        cursor.execute(f"""
            SELECT 
                COUNT(*),
                SUM(prompt_tokens),
                SUM(output_tokens),
                SUM(total_tokens),
                SUM(estimated_cost),
                AVG(latency_ms),
                SUM(CASE WHEN status_code = 429 THEN 1 ELSE 0 END),
                SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END)
            FROM usage_logs
            WHERE {date_filter} {filter_acc}
        """, params)
        range_row = cursor.fetchone()
        
        cursor.execute(f"""
            SELECT 
                COUNT(*),
                SUM(prompt_tokens),
                SUM(output_tokens),
                SUM(total_tokens),
                SUM(estimated_cost)
            FROM usage_logs
            WHERE 1=1 {filter_acc}
        """, params)
        all_row = cursor.fetchone()

        return {
            "today_calls": range_row[0] or 0,
            "today_prompt_tokens": range_row[1] or 0,
            "today_output_tokens": range_row[2] or 0,
            "today_total_tokens": range_row[3] or 0,
            "today_cost": round(range_row[4] or 0.0, 4),
            "today_avg_latency": round(range_row[5] or 0.0, 1),
            "today_429_count": range_row[6] or 0,
            "today_errors": range_row[7] or 0,
            "all_calls": all_row[0] or 0,
            "all_total_tokens": all_row[3] or 0,
            "all_cost": round(all_row[4] or 0.0, 4)
        }

def get_rate_limits_status(account_name: Optional[str] = None, time_range: str = "今日 (Today)"):
    """
    計算並傳回各模型的 RPM, TPM, RPD 實時用量與配額上限狀態 (比照 Google AI Studio 介面，涵蓋全部 11 款模型)
    支援讀取 Rate Limits Snapshot 與本機資料庫最新用量疊加，並自動映射所屬 Google 帳號的官方快照
    """
    if "28" in time_range:
        date_filter = "datetime(timestamp) >= datetime('now', '-28 days', 'localtime')"
        range_key = "28 Days"
    elif "7" in time_range:
        date_filter = "datetime(timestamp) >= datetime('now', '-7 days', 'localtime')"
        range_key = "7 Days"
    else:
        date_filter = "date(timestamp) = date('now', 'localtime')"
        range_key = "Today"

    email_1 = os.getenv("GOOGLE_ACCOUNT_1_EMAIL", "shonarmstrong5@gmail.com")
    email_2 = os.getenv("GOOGLE_ACCOUNT_2_EMAIL", "dandyzuko2@gmail.com")
    account_email_map = {
        "GEMINI_PODCAST_KEY": email_1,
        "GEMINI_JAV_KEY": email_1,
        "GEMINI_JAV_TRANSLATE_2_KEY": email_1,
        "GEMINI_FINANCE_KEY": email_1,
        "Whisper_correction": email_1,
        "GEMINI_BACKUP_KEY_2": email_2
    }

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 讀取快照基準 (若個別 Key 無專屬快照，則向上繼承所屬 Google 帳號 Email 的基準)
        snapshot_data = {}
        if account_name and account_name != "全部帳號":
            mapped_email = account_email_map.get(account_name, email_1)
            target_accs = [account_name, mapped_email]
        else:
            target_accs = [email_1, "GEMINI_PODCAST_KEY", "shonarmstrong5@gmail.com"]
        
        for t_acc in target_accs:
            cursor.execute("""
                SELECT model_id, current_rpm, current_tpm, current_rpd
                FROM rate_limits_snapshot
                WHERE account_name = ? AND time_range = ?
            """, (t_acc, range_key))
            for row in cursor.fetchall():
                snapshot_data[row["model_id"]] = dict(row)
            if snapshot_data:
                break

        filter_acc = "AND account_name = ?" if (account_name and account_name != "全部帳號") else ""
        status_list = []
        has_exceeded = False

        for model_id, limits in MODEL_RATE_LIMITS.items():
            aliases = limits.get("aliases", [model_id])
            placeholders = ",".join(["?"] * len(aliases))

            # 1. 查詢該模型在該時間區間內的呼叫次數 (RPD)
            params_rpd = aliases + ([account_name] if filter_acc else [])
            cursor.execute(f"""
                SELECT COUNT(*), SUM(total_tokens)
                FROM usage_logs
                WHERE {date_filter} AND model_name IN ({placeholders}) {filter_acc}
            """, params_rpd)
            rpd_row = cursor.fetchone()
            logged_rpd = rpd_row[0] or 0
            logged_tokens = rpd_row[1] or 0

            # 2. 查詢該模型在該時間區間內的 Peak RPM 與 Peak TPM (按每分鐘分組取最大值)
            cursor.execute(f"""
                SELECT COUNT(*) as min_cnt, SUM(total_tokens) as min_tok
                FROM usage_logs
                WHERE {date_filter} AND model_name IN ({placeholders}) {filter_acc}
                GROUP BY strftime('%Y-%m-%d %H:%M', timestamp)
                ORDER BY min_cnt DESC LIMIT 1
            """, params_rpd)
            peak_row = cursor.fetchone()
            logged_peak_rpm = peak_row[0] if peak_row else 0
            logged_peak_tpm = peak_row[1] if peak_row else 0

            # 3. 檢查最近是否有 429 錯誤
            cursor.execute(f"""
                SELECT COUNT(*)
                FROM usage_logs
                WHERE {date_filter} AND model_name IN ({placeholders}) AND status_code = 429 {filter_acc}
            """, params_rpd)
            recent_429 = cursor.fetchone()[0] or 0

            # 合併快照數據（若有手動或官方基準快照）
            snap = snapshot_data.get(model_id, {})
            base_rpm = snap.get("current_rpm", 0)
            base_tpm = snap.get("current_tpm", 0.0)
            base_rpd = snap.get("current_rpd", 0)

            current_rpm = max(base_rpm, logged_peak_rpm)
            current_tpm = max(base_tpm, logged_peak_tpm)
            current_rpd = base_rpd + logged_rpd

            # 計算百分比與狀態
            rpd_pct = min((current_rpd / limits["rpd"]) * 100.0, 100.0) if limits["rpd"] > 0 else 0
            rpm_pct = min((current_rpm / limits["rpm"]) * 100.0, 100.0) if limits["rpm"] > 0 else 0
            tpm_pct = min((current_tpm / limits["tpm"]) * 100.0, 100.0) if limits["tpm"] > 0 else 0

            is_exceeded = (current_rpd >= limits["rpd"]) or (current_rpm >= limits["rpm"]) or (recent_429 > 0)
            if is_exceeded:
                has_exceeded = True

            status_list.append({
                "model_id": model_id,
                "displayName": limits["displayName"],
                "category": limits["category"],
                "current_rpm": current_rpm,
                "max_rpm": limits["rpm"],
                "rpm_pct": rpm_pct,
                "current_tpm": current_tpm,
                "max_tpm": limits["tpm"],
                "tpm_pct": tpm_pct,
                "current_rpd": current_rpd,
                "max_rpd": limits["rpd"],
                "rpd_pct": rpd_pct,
                "recent_429": recent_429,
                "is_exceeded": is_exceeded
            })

        return status_list, has_exceeded

# --- Mock Data Generator for Testing ---
def generate_mock_data(count: int = 15):
    import random
    models = ["gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]
    accounts = ["GEMINI_PODCAST_KEY", "GEMINI_JAV_KEY", "GEMINI_JAV_TRANSLATE_2_KEY", "GEMINI_FINANCE_KEY", "GEMINI_BACKUP_KEY_2"]
    statuses = [200, 200, 200, 200, 200, 429, 200, 500]
    
    for _ in range(count):
        m = random.choice(models)
        acc = random.choice(accounts)
        p_tok = random.randint(150, 4500)
        o_tok = random.randint(50, 1200)
        st = random.choice(statuses)
        lat = random.uniform(250.0, 3200.0) if st == 200 else random.uniform(50.0, 300.0)
        err = "429 Rate limit exceeded" if st == 429 else ("500 Internal server error" if st == 500 else "")
        log_api_call(
            model_name=m,
            prompt_tokens=p_tok,
            output_tokens=o_tok,
            latency_ms=lat,
            status_code=st,
            error_message=err,
            caller_info="Mock Data Seed",
            account_name=acc
        )

if __name__ == "__main__":
    print("Database initialized at:", DB_PATH)
    stats = get_stats_summary()
    print("Current Stats Summary:", stats)
    limits, exceeded = get_rate_limits_status()
    print("Rate Limits Status count:", len(limits), "Exceeded:", exceeded)
