import sqlite3
import time
import json
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

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

# --- Google AI Studio Free Tier Limits Definition ---
MODEL_RATE_LIMITS = {
    "gemini-3.7-flash": {"displayName": "Gemini 3.7 Flash", "category": "Text-out models", "rpm": 5, "tpm": 250000, "rpd": 20},
    "gemini-3.6-flash": {"displayName": "Gemini 3.6 Flash", "category": "Text-out models", "rpm": 5, "tpm": 250000, "rpd": 20},
    "gemini-3.5-flash": {"displayName": "Gemini 3.5 Flash", "category": "Text-out models", "rpm": 5, "tpm": 250000, "rpd": 20},
    "gemini-2.5-flash": {"displayName": "Gemini 2.5 Flash", "category": "Text-out models", "rpm": 5, "tpm": 250000, "rpd": 20},
    "gemini-3.5-flash-lite": {"displayName": "Gemini 3.5 Flash Lite", "category": "Text-out models", "rpm": 15, "tpm": 250000, "rpd": 500},
    "gemini-3.1-flash-lite": {"displayName": "Gemini 3.1 Flash Lite", "category": "Text-out models", "rpm": 15, "tpm": 250000, "rpd": 500},
    "gemini-2.5-flash-lite": {"displayName": "Gemini 2.5 Flash Lite", "category": "Text-out models", "rpm": 15, "tpm": 250000, "rpd": 500},
    "antigravity": {"displayName": "Antigravity", "category": "Agents", "rpm": 60, "tpm": 100000, "rpd": 100},
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
        
        # 檢查並自動遷移舊版資料表 (追加 account_name 欄位)
        cursor.execute("PRAGMA table_info(usage_logs)")
        cols = [col[1] for col in cursor.fetchall()]
        if "account_name" not in cols:
            cursor.execute("ALTER TABLE usage_logs ADD COLUMN account_name TEXT DEFAULT '預設帳號'")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON usage_logs(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_model ON usage_logs(model_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_account ON usage_logs(account_name)")
        conn.commit()

init_db()

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
def get_available_accounts() -> list:
    """取得資料庫中已記錄的所有帳號名稱"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT account_name FROM usage_logs WHERE account_name IS NOT NULL AND account_name != ''")
        rows = cursor.fetchall()
        accounts = [r[0] for r in rows]
        if not accounts:
            accounts = ["預設帳號"]
        return accounts

def get_recent_logs(limit: int = 100, account_name: Optional[str] = None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if account_name and account_name != "全部帳號":
            cursor.execute("SELECT * FROM usage_logs WHERE account_name = ? ORDER BY id DESC LIMIT ?", (account_name, limit))
        else:
            cursor.execute("SELECT * FROM usage_logs ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

def get_stats_summary(account_name: Optional[str] = None):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        today_str = datetime.date.today().isoformat()
        
        filter_sql = "AND account_name = ?" if (account_name and account_name != "全部帳號") else ""
        params_today = [today_str, account_name] if filter_sql else [today_str]
        params_all = [account_name] if filter_sql else []

        cursor.execute(f"""
            SELECT 
                COUNT(*),
                SUM(prompt_tokens),
                SUM(output_tokens),
                SUM(total_tokens),
                SUM(estimated_cost),
                AVG(latency_ms),
                SUM(CASE WHEN status_code = 429 THEN 1 ELSE 0 END),
                SUM(CASE WHEN status_code != 200 THEN 1 ELSE 0 END)
            FROM usage_logs
            WHERE date(timestamp) = ? {filter_sql}
        """, params_today)
        today_row = cursor.fetchone()
        
        cursor.execute(f"""
            SELECT 
                COUNT(*),
                SUM(prompt_tokens),
                SUM(output_tokens),
                SUM(total_tokens),
                SUM(estimated_cost)
            FROM usage_logs
            WHERE 1=1 {filter_sql}
        """, params_all)
        all_row = cursor.fetchone()

        return {
            "today_calls": today_row[0] or 0,
            "today_prompt_tokens": today_row[1] or 0,
            "today_output_tokens": today_row[2] or 0,
            "today_total_tokens": today_row[3] or 0,
            "today_cost": round(today_row[4] or 0.0, 4),
            "today_avg_latency": round(today_row[5] or 0.0, 1),
            "today_429_count": today_row[6] or 0,
            "today_errors": today_row[7] or 0,
            "all_calls": all_row[0] or 0,
            "all_total_tokens": all_row[3] or 0,
            "all_cost": round(all_row[4] or 0.0, 4)
        }

def get_rate_limits_status(account_name: Optional[str] = None):
    """
    計算並傳回各模型的 RPM, TPM, RPD 實時用量與配額上限狀態 (比照 Google AI Studio 介面)
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        today_str = datetime.date.today().isoformat()
        one_min_ago = (datetime.datetime.now() - datetime.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")

        filter_acc = "AND account_name = ?" if (account_name and account_name != "全部帳號") else ""
        
        status_list = []
        has_exceeded = False

        for model_id, limits in MODEL_RATE_LIMITS.items():
            # 1. 查詢今日 RPD
            params_rpd = [today_str, model_id, account_name] if filter_acc else [today_str, model_id]
            cursor.execute(f"""
                SELECT COUNT(*), SUM(total_tokens)
                FROM usage_logs
                WHERE date(timestamp) = ? AND model_name = ? {filter_acc}
            """, params_rpd)
            rpd_row = cursor.fetchone()
            current_rpd = rpd_row[0] or 0
            today_tokens = rpd_row[1] or 0

            # 2. 查詢當前 1 分鐘內的即時 RPM 與 TPM
            params_min = [one_min_ago, model_id, account_name] if filter_acc else [one_min_ago, model_id]
            cursor.execute(f"""
                SELECT COUNT(*), SUM(total_tokens)
                FROM usage_logs
                WHERE timestamp >= ? AND model_name = ? {filter_acc}
            """, params_min)
            min_row = cursor.fetchone()
            current_rpm = min_row[0] or 0
            current_tpm = min_row[1] or 0

            # 3. 檢查最近是否有 429 錯誤
            cursor.execute(f"""
                SELECT COUNT(*)
                FROM usage_logs
                WHERE date(timestamp) = ? AND model_name = ? AND status_code = 429 {filter_acc}
            """, params_rpd)
            recent_429 = cursor.fetchone()[0] or 0

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
    accounts = ["Whisper_correction", "Whiskey_correction", "GEMINI_API_KEY_3"]
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
