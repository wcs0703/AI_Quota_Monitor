#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quota_keepalive.py
=============================================================================
跨平台 Model Quota 守護與維持程式 (macOS / Windows / Linux 通用)

功能說明：
1. 定時（預設每 4.5 小時）自動對 Gemini 模型發送極簡請求（1 字元），消耗 ~1 Token。
2. 提前啟動 5 小時配額重置窗口（5-Hour Reset Window），避免重度使用時配額重置被往後延。
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

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

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

def send_ping(model_name: str = "gemini-2.5-flash") -> bool:
    """透過純 HTTP 請求發送 1 Token 的極簡請求，並記錄至 SQLite 與文字日誌"""
    start_time = time.time()
    if not API_KEY:
        write_log("❌ 找不到 GEMINI_API_KEY 或 GOOGLE_API_KEY，請確認 .env 設定！")
        return False

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
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

            # 萃取 Token 使用量
            usage = res_body.get("usageMetadata", {})
            prompt_tokens = usage.get("promptTokenCount", 1) or 1
            output_tokens = usage.get("candidatesTokenCount", 1) or 1

            # 萃取回應文字
            reply_text = ""
            candidates = res_body.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts:
                    reply_text = parts[0].get("text", "").strip()

            # 寫入 SQLite 資料庫
            if log_api_call:
                log_api_call(
                    model_name=model_name,
                    prompt_tokens=prompt_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    status_code=200,
                    caller_info="Quota_KeepAlive"
                )

            write_log(f"✅ Keep-Alive 成功！模型: {model_name} | 耗時: {latency_ms:.1f}ms | 回應: '{reply_text}' | 配額窗口已激活")
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

        if log_api_call:
            log_api_call(
                model_name=model_name,
                prompt_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                status_code=status_code,
                error_message=err_msg,
                caller_info="Quota_KeepAlive"
            )

        write_log(f"❌ Keep-Alive 失敗 (狀態碼: {status_code}): {err_msg}")
        return False

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000.0
        err_msg = str(e)
        if log_api_call:
            log_api_call(
                model_name=model_name,
                prompt_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                status_code=500,
                error_message=err_msg,
                caller_info="Quota_KeepAlive"
            )

        write_log(f"❌ Keep-Alive 例外錯誤: {err_msg}")
        return False

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
    parser.add_argument("--model", type=str, default="gemini-2.5-flash", help="目標測試模型 (預設 gemini-2.5-flash)")
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
