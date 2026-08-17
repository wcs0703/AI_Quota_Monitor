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

# --- Database Initialization ---
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
                caller_info TEXT DEFAULT ''
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON usage_logs(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_model ON usage_logs(model_name)")
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
    caller_info: str = ""
) -> int:
    """Logs a single Gemini API call to SQLite."""
    if status_code != 200 or error_message:
        log_file_error(f"Model: {model_name} | Status: {status_code} | Msg: {error_message}")
    total_tokens = prompt_tokens + output_tokens
    cost = calculate_cost(model_name, prompt_tokens, output_tokens)
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO usage_logs (
                model_name, prompt_tokens, output_tokens, total_tokens,
                latency_ms, status_code, estimated_cost, error_message, caller_info
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            model_name, prompt_tokens, output_tokens, total_tokens,
            round(latency_ms, 2), status_code, cost, error_message, caller_info
        ))
        conn.commit()
        return cursor.lastrowid

def log_gemini_response(response: Any, model_name: str, start_time: float, caller_info: str = ""):
    """Utility helper to extract tokens from a google-genai / google.generativeai response object and log it."""
    latency_ms = (time.time() - start_time) * 1000.0
    prompt_tokens = 0
    output_tokens = 0
    
    # Try google-genai / google.generativeai attributes
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
        caller_info=caller_info
    )

# --- Database Query Helpers ---
def get_recent_logs(limit: int = 100):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usage_logs ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

def get_stats_summary():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Today
        today_str = datetime.date.today().isoformat()
        cursor.execute("""
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
            WHERE date(timestamp) = ?
        """, (today_str,))
        today_row = cursor.fetchone()
        
        # All time
        cursor.execute("""
            SELECT 
                COUNT(*),
                SUM(prompt_tokens),
                SUM(output_tokens),
                SUM(total_tokens),
                SUM(estimated_cost)
            FROM usage_logs
        """)
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

# --- Mock Data Generator for Testing ---
def generate_mock_data(count: int = 15):
    import random
    models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-lite"]
    statuses = [200, 200, 200, 200, 200, 429, 200, 500]
    
    for _ in range(count):
        m = random.choice(models)
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
            caller_info="Mock Data Seed"
        )

if __name__ == "__main__":
    print("Database initialized at:", DB_PATH)
    stats = get_stats_summary()
    print("Current Stats Summary:", stats)
