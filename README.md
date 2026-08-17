# 📊 AI_Quota_Monitor — AI 配額守護與 API 監控系統

**專案名稱**：`AI_Quota_Monitor`  
**專案定位**：專為 AI 模型（Gemini / LLM）打造的跨平台 **Model 配額保活守護 (Keep-Alive)**、**即時使用量監控**、**成本計算** 與 **HTTP 異常追蹤系統**。

## 📅 發行日期
`2026-08-17` (專案更名為 AI_Quota_Monitor，整合跨平台 Model Quota 守護與 5 小時保活機制)

---

## 🎯 專案兩大核心功能

### 1. 🛡️ 跨平台 Model Quota 守護程式 (`quota_keepalive.py`)
* **核心任務**：定時（預設每 4.5 小時）自動對 AI 模型發送極簡請求（1 字元），消耗 ~1 Token（成本 < $0.000001）。
* **機制優勢**：提前觸發 5 小時配額重置窗口（5-Hour Reset Window），避免重度使用時配額重置被往後延。
* **零依賴跨平台**：採用純 Python 標準庫 HTTP 請求，完全無第三方 SDK 相依性，在 **macOS / Windows / Linux** 皆可直接執行。
* **日誌追蹤**：每次 Ping 結果自動寫入 `gemini_usage.db` SQLite 資料庫與 `logs/keepalive.log`。

### 2. 📊 Streamlit API 使用量與成本監控儀表板 (`app_monitor.py` & `gemini_logger.py`)
* **核心任務**：提供視覺化圖表分析與 API 實時測試探針。
* **重點功能**：
    * **數據總覽卡片**：即時顯示總呼叫次數、總 Token 消耗量、估算總成本與平均延遲。
    * **趨勢分析圖**：依模型與時間序列呈現 Token 消耗曲線。
    * **異常追蹤**：完整紀錄 HTTP 狀態碼與錯誤訊息（如 HTTP 429 Rate Limit）。
    * **Live API Probe**：提供前端測試按鈕，可手動對指定模型發送 Request 並即時檢視回傳效能與 Token 統計。

---

## 🏗️ 檔案結構清單

| 檔案名稱 | 說明 | 適用平台 |
| :--- | :--- | :--- |
| **`quota_keepalive.py`** | 跨平台 Quota 保活守護核心程式 | macOS / Windows / Linux |
| **`start_keepalive.sh`** | 終端機或背景常駐啟動腳本 | macOS / Linux |
| **`start_keepalive.command`** | Finder 雙擊啟動腳本 | macOS |
| **`start_keepalive.bat`** | 雙擊啟動批次檔 | Windows |
| **`app_monitor.py`** | Streamlit 視覺化監控儀表板前端 | 跨平台 Web |
| **`gemini_logger.py`** | SQLite 紀錄核心與成本計算邏輯 | 後端日誌模組 |
| **`model_pricing.json`** | Gemini 模型最新計價設定 | 費率字典 |
| **`gemini_usage.db`** | 本地 SQLite 數據庫檔 | 資料儲存 |
| **`start_monitor.sh` / `.command`** | 啟動 Streamlit 監控儀表板 | macOS / Linux |

---

## 🚀 使用方式

### 1. 啟動 Model Quota 保活守護程式

* **macOS 雙擊啟動**：
  直接雙擊 [`start_keepalive.command`](file:///Users/windfox/Github-Sync/AI_Quota_Monitor/start_keepalive.command)。
* **macOS / Linux 背景常駐執行**：
  ```bash
  nohup ./start_keepalive.sh > logs/keepalive.log 2>&1 &
  ```
* **Windows 啟動**：
  雙擊執行 `start_keepalive.bat` 或在 CMD/PowerShell 執行：
  ```powershell
  python quota_keepalive.py
  ```
* **單次測試 Ping**：
  ```bash
  python quota_keepalive.py --once
  ```

---

### 2. 啟動 Streamlit 監控儀表板

* **macOS**：雙擊 [`start_monitor.command`](file:///Users/windfox/Github-Sync/AI_Quota_Monitor/start_monitor.command) 或執行 `./start_monitor.sh`。
* 瀏覽器自動開啟 `http://localhost:8502` 即可檢視所有 API 呼叫與 Keep-Alive 歷程。

---

## 📝 改版紀錄 (Changelog)

| 日期 | 版本 / 改版範圍 | 詳細說明 |
| :--- | :--- | :--- |
| **2026-08-17** | **跨平台 Model Quota 守護整合** | 1. 開發 `quota_keepalive.py` 跨平台保活程式，定時（每 4.5 小時）自動發送 1 Token 極簡請求，提前啟動 5 小時配額重置窗口。<br>2. 採用純 Python 標準庫 (urllib)，完全免除第三方 SDK 相依性。<br>3. 支援 macOS (`start_keepalive.command`/`.sh`) 與 Windows (`start_keepalive.bat`) 一鍵啟動。<br>4. 修復 `gemini_logger.py` 異常處理並整合 Keep-Alive 數據寫入 SQLite。 |
| **2026-08-08** | **專案初版建立** | 1. 正式完成 Gemini API 數據日誌記錄核心 (`gemini_logger.py`) 與本機 SQLite 數據庫 (`gemini_usage.db`)。<br>2. 建立 Streamlit 視覺化監控儀表板 (`app_monitor.py`)，即時統計 Token 消耗、估算 USD 成本與延遲分析。<br>3. 導入 Live API Probe 測試介面與 HTTP 429 速率限制追蹤。 |

