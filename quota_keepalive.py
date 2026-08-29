#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quota_keepalive.py
=============================================================================
跨平台 Model Quota 守護與維持程式 (macOS / Windows / Linux 通用)

功能說明：
1. 定時（預設每 4.5 小時）自動對 Gemini 模型發送極簡請求（1 字元），消耗 ~1 Token。
2. 提前啟動 5 小時配額重置週期（5-Hour Reset Window），避免重度使用時配額重置被往後延。
3. 採用純 Python 標準庫 (urllib.request)，零第三方 SDK 相依性，跨平台 100% 開箱即用。
4. 每次 Ping 結果自動寫入本機 SQLite 資料庫 (gemini_usage.db) 與 logs/keepalive.log。
5. 支援「單次執行模式 (--once)」，方便配合系統排程 (cron/Task Scheduler) 呼叫。

使用方式：
    python quota_keepalive.py              # 常駐守護模式（預設每 4.5 小時觸發一次）
    python quota_keepalive.py --once       # 僅執行單次測試 Ping
    python quota_keepalive.py --hours 4    # 自訂間隔為每 4 小時
=============================================================================
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# 確保在 Windows CP950 主機環境下輸出 Emoji 符號不崩潰
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 設定路徑
BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = BASE_DIR.parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
KEEPALIVE_LOG_FILE = LOGS_DIR / "keepalive.log"

# 導入 dotenv
try:
    from dotenv import load_dotenv
    for env_path in [
        BASE_DIR / ".env",
        WORKSPACE_DIR / ".env",
        WORKSPACE_DIR / "Whisper-Podcast" / ".env",
    ]:
        if env_path.exists():
            load_dotenv(env_path)
    load_dotenv()
except ImportError:
    pass

# 導入本地 gemini_logger 紀錄模組
try:
    from gemini_logger import log_api_call
except ImportError:
    log_api_call = None

def get_all_gemini_keys() -> dict:
    """取得所有已在 .env 中設定的 Gemini API 金鑰清單"""
    keys = {}
    for var_name in ["GEMINI_PODCAST_KEY", "GEMINI_JAV_KEY", "GEMINI_JAV_TRANSLATE_2_KEY", "GEMINI_FINANCE_KEY", "GEMINI_BACKUP_KEY_2"]:
        val = os.getenv(var_name)
        if val and val.strip() and val.strip() not in keys.values():
            keys[var_name] = val.strip()
    return keys

def write_log(msg: str):
    """寫入本地文字日誌並輸出至終端機"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{now_str}] {msg}"
    print(formatted)
    try:
        with open(KEEPALIVE_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception as e:
        print(f"⚠️ 寫入日誌檔失敗: {e}")

def ping_single_account(account_name: str, api_key: str, model_name: str = "gemini-3.6-flash") -> bool:
    """針對單一帳號發送 1 Token 的極簡請求，並記錄至 SQLite 與文字日誌"""
    models_to_try = [model_name, "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash"]
    # 去重且保持順序
    models_chain = []
    for m in models_to_try:
        if m not in models_chain:
            models_chain.append(m)

    for current_model in models_chain:
        start_time = time.time()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": "1"}]}],
            "generationConfig": {"maxOutputTokens": 1}
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                latency_ms = (time.time() - start_time) * 1000.0
                status_code = response.status
                res_body = json.loads(response.read().decode("utf-8"))

                usage = res_body.get("usageMetadata", {})
                prompt_tokens = usage.get("promptTokenCount", 1) or 1
                output_tokens = usage.get("candidatesTokenCount", 1) or 1

                reply_text = ""
                candidates = res_body.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts:
                        reply_text = parts[0].get("text", "").strip()

                if log_api_call:
                    log_api_call(
                        model_name=current_model,
                        prompt_tokens=prompt_tokens,
                        output_tokens=output_tokens,
                        latency_ms=latency_ms,
                        status_code=200,
                        caller_info="Quota_KeepAlive",
                        account_name=account_name
                    )

                write_log(f"  ✅ [{account_name}] Keep-Alive 成功！模型: {current_model} | 耗時: {latency_ms:.1f}ms | 配額週期已啟用")
                return True

        except urllib.error.HTTPError as e:
            latency_ms = (time.time() - start_time) * 1000.0
            status_code = e.code
            err_msg = f"HTTP {status_code}: {e.reason}"
            try:
                err_detail = json.loads(e.read().decode("utf-8"))
                err_msg = err_detail.get("error", {}).get("message", err_msg)
            except Exception:
                pass

            # 若 404 (模型下架) 或 503 (伺服器滿載)，嘗試 fallback 鏈的下一個模型
            if status_code in (404, 503) and current_model != models_chain[-1]:
                continue

            if log_api_call:
                log_api_call(
                    model_name=current_model,
                    prompt_tokens=0,
                    output_tokens=0,
                    latency_ms=latency_ms,
                    status_code=status_code,
                    error_message=err_msg,
                    caller_info="Quota_KeepAlive",
                    account_name=account_name
                )

            write_log(f"  ❌ [{account_name}] Keep-Alive 失敗 (狀態碼: {status_code}): {err_msg}")
            return False

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000.0
            err_msg = str(e)
            if log_api_call:
                log_api_call(
                    model_name=current_model,
                    prompt_tokens=0,
                    output_tokens=0,
                    latency_ms=latency_ms,
                    status_code=500,
                    error_message=err_msg,
                    caller_info="Quota_KeepAlive",
                    account_name=account_name
                )

            write_log(f"  ❌ [{account_name}] Keep-Alive 例外錯誤: {err_msg}")
            return False

    return False

def send_ping(model_name: str = "gemini-3.6-flash") -> bool:
    """對所有在 .env 中設定的 Gemini 帳號發送 Keep-Alive 測試"""
    accounts = get_all_gemini_keys()
    if not accounts:
        write_log("❌ 找不到任何 Gemini API Key，請確認根目錄 .env 設定！")
        return False

    write_log(f"🔍 正在對 {len(accounts)} 個 Gemini 帳號發送 Keep-Alive Ping (模型: {model_name})...")
    all_success = True
    for acc_name, key in accounts.items():
        ok = ping_single_account(acc_name, key, model_name)
        if not ok:
            all_success = False
        time.sleep(1)
    return all_success

def run_daemon(hours: float, model_name: str):
    """常駐守護迴圈"""
    interval_seconds = int(hours * 3600)
    print("\n" + "═" * 70)
    print("🛡️  Gemini Model Quota 守護與維持系統 (Keep-Alive Daemon)")
    print(f"⏰ 檢查週期：每 {hours} 小時 (約 {interval_seconds} 秒) 自動觸發一次")
    print(f"🤖 目標模型：{model_name}")
    print(f"📂 日誌路徑：{KEEPALIVE_LOG_FILE}")
    print("═" * 70 + "\n")

    # 啟動時先執行第一次測試
    write_log("🚀 守護程式啟動，執行初次 Keep-Alive Ping...")
    send_ping(model_name)

    while True:
        try:
            next_time = datetime.now() + timedelta(seconds=interval_seconds)
            write_log(f"⏳ 進入休眠，下次觸發預計於: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
            time.sleep(interval_seconds)
            send_ping(model_name)
        except KeyboardInterrupt:
            write_log("👋 收到中斷訊號，Quota 守護程式已手動安全停止。")
            break
        except Exception as e:
            write_log(f"⚠️ 迴圈異常: {e}，將於 60 秒後重試...")
            time.sleep(60)

def main():
    parser = argparse.ArgumentParser(description="Gemini Model Quota Keep-Alive 守護程式")
    parser.add_argument("--hours", type=float, default=4.5, help="觸發間隔小時數 (預設 4.5 小時)")
    parser.add_argument("--model", type=str, default="gemini-3.6-flash", help="目標測試模型 (預設 gemini-3.6-flash)")
    parser.add_argument("--once", action="store_true", help="僅執行單次 Ping 後立即結束")
    args = parser.parse_args()

    if args.once:
        print(f"🔍 正在對 {args.model} 發送單次 Keep-Alive 測試...")
        success = send_ping(args.model)
        sys.exit(0 if success else 1)
    else:
        run_daemon(args.hours, args.model)

if __name__ == "__main__":
    main()
