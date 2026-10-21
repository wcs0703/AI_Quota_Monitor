# 📊 AI_Quota_Monitor — AI 配額守護與 API 監控系統

**專案名稱**：AI_Quota_Monitor  
**GitHub 倉庫**：https://github.com/wcs0703/AI_Quota_Monitor.git  
**支援平台**：macOS / Windows / Linux  
**專案定位**：專為 AI 模型（Gemini / LLM）打造的跨平台 **Model 配額維持 (Keep-Alive)**、**即時使用量監控**、**成本計算** 與 **HTTP 異常追蹤系統**。

## 📅 發行日期
`2026-08-31` (完整保留與維護 Windows `.bat` 與 macOS/Linux `.sh` / `.command` 一鍵啟動腳本，並支援純 Python 跨平台進入點)

---

## 🎯 專案兩大核心功能

### 1. 🛡️ 跨平台 Model Quota 守護程式 (`quota_keepalive.py`)
* **核心任務**：定時（預設每 4.5 小時）自動對 AI 模型發送極簡請求（1 字元），消耗 ~1 Token（成本 < $0.000001）。
* **配額維持原理**：主流 AI 模型的速率限制（Rate Limit）通常以 **5 小時窗口** 計算。若長時間未使用，5 小時重置倒數計時器不會啟動；透過定期微小 Ping，**可提前啟動 5 小時重置倒數**，避免臨時重度使用時重置時間被往後延。
* **零相依跨平台**：採用純 Python 標準庫 (`urllib.request`) 實作 HTTP 請求，完全無第三方 SDK 相依性，在 **macOS / Windows / Linux** 皆可直接執行。
* **日誌與資料庫追蹤**：每次 Ping 結果自動寫入 `gemini_usage.db` SQLite 資料庫（標記來源為 `Quota_KeepAlive`）與 `logs/keepalive.log`。

### 2. 📊 Streamlit API 使用量與成本監控儀表板 (`app_monitor.py` & `gemini_logger.py`)
* **核心任務**：提供視覺化圖表分析與 API 實時測試探針。
* **重點功能**：
    * **數據總覽卡片**：即時顯示今日與歷史總呼叫次數、總 Token 消耗量、估算總成本與平均延遲。
    * **趨勢分析圖**：依模型與時間序列呈現 Token 消耗曲線與用量分佈。
    * **異常追蹤**：完整紀錄 HTTP 狀態碼與錯誤訊息（包含 HTTP 429 速率限制頻率）。
    * **Live API Probe**：提供前端測試介面，可手動對指定模型發送 Request 並即時檢視回傳效能與 Token 統計。

---

## 🏗️ 檔案結構清單

| 檔案/資料夾名稱 | 內容說明 | 適用平台 |
| :--- | :--- | :--- |
| **[`start_monitor.bat`](./start_monitor.bat)** | Windows 儀表板一鍵啟動腳本 (Streamlit Port 8502) | Windows |
| **[`start_monitor.sh`](./start_monitor.sh)** | macOS / Linux 儀表板一鍵啟動腳本 | macOS / Linux |
| **[`start_monitor.command`](./start_monitor.command)** | macOS 訪達 (Finder) 雙擊一鍵啟動腳本 | macOS |
| **[`start_keepalive.py`](./start_keepalive.py)** | 跨平台 Quota 守護維持一鍵啟動腳本 (自動偵測 .venv) | macOS / Windows / Linux |
| **[`start_keepalive.bat`](./start_keepalive.bat)** | Windows Quota 守護維持一鍵啟動腳本 | Windows |
| **[`start_keepalive.sh`](./start_keepalive.sh)** | macOS / Linux Quota 守護維持一鍵啟動腳本 | macOS / Linux |
| **[`start_keepalive.command`](./start_keepalive.command)** | macOS 訪達 (Finder) 雙擊 Quota 守護啟動腳本 | macOS |
| **[`quota_keepalive.py`](./quota_keepalive.py)** | 跨平台 Quota 守護與維持核心程式（純 Python HTTP 實作） | macOS / Windows / Linux |
| **[`app_monitor.py`](./app_monitor.py)** | Streamlit 視覺化監控儀表板前端 | 跨平台 Web |
| **[`gemini_logger.py`](./gemini_logger.py)** | SQLite 紀錄核心與成本計算邏輯 | 後端日誌模組 |
| **[`model_pricing.json`](./model_pricing.json)** | Gemini 模型最新計價設定字典 | 費率設定 |
| **`gemini_usage.db`** | 本機 SQLite 資料庫檔 | 資料儲存 |
| **`logs/`** | 存放維持紀錄 (`keepalive.log`) 與異常日誌 (`error.log`) | 本地日誌 |

---

## 🚀 啟動指南 (一鍵腳本 & 終端機通用)

### 1. 啟動 Streamlit 視覺化監控儀表板 (Port 8502)

* **🪟 Windows**：
  * 直接雙擊 **[`start_monitor.bat`](./start_monitor.bat)**，或在終端機執行：
    ```powershell
    cd D:\Github-Sync\AI_Quota_Monitor
    .\start_monitor.bat
    ```
* **🍎 macOS / Linux**：
  * 直接雙擊 **[`start_monitor.command`](./start_monitor.command)**，或在終端機執行：
    ```bash
    cd ~/Github-Sync/AI_Quota_Monitor
    ./start_monitor.sh
    ```
* **💻 跨平台 Python 命令行指令**：
  ```bash
  streamlit run app_monitor.py --server.port 8502
  ```
  * 瀏覽器自動開啟 `http://localhost:8502` 即可檢視所有 API 呼叫、成本累計、DeepL 翻譯字數與 Keep-Alive 定時喚醒紀錄。

---

### 2. 啟動 Model Quota 守護維持程式 (`start_keepalive.py` / `quota_keepalive.py`)

* **💻 跨平台 Python 一鍵啟動 (推薦，自動載入 .venv)**：
  ```bash
  python start_keepalive.py
  ```
  * **單次連線測試 Ping**：
    ```bash
    python start_keepalive.py --once
    ```
  * **背景常駐執行 (macOS / Linux)**：
    ```bash
    nohup python start_keepalive.py > logs/keepalive.log 2>&1 &
    ```
* **🪟 Windows**：
  * 直接雙擊 **[`start_keepalive.bat`](./start_keepalive.bat)**，或在終端機執行：
    ```powershell
    cd D:\Github-Sync\AI_Quota_Monitor
    .\start_keepalive.bat
    ```
* **🍎 macOS / Linux**：
  * 直接雙擊 **[`start_keepalive.command`](./start_keepalive.command)**，或在終端機執行：
    ```bash
    cd ~/Github-Sync/AI_Quota_Monitor
    ./start_keepalive.sh
    ```

---

## 📝 改版紀錄 (Changelog)

| 改版日期 | 版本重點 | 詳細更新說明 |
| :--- | :--- | :--- |
| **2026-10-21** | **新增跨平台 Python 守護啟動腳本 (`start_keepalive.py`)** | 1. **Python 啟動腳本化**：新增 [`start_keepalive.py`](./start_keepalive.py)，自動偵測工作區 `.venv` 虛擬環境（支援 macOS/Linux/Windows），解決 Windows 系統無法直接執行 Shell 腳本的痛點。<br>2. **雙軌相容相輔相成**：保留 [`start_keepalive.sh`](./start_keepalive.sh) 與 [`start_keepalive.bat`](./start_keepalive.bat) 並重定向至 `start_keepalive.py`，保持既有快捷啟動腳本無縫銜接。 |
| **2026-08-31** | **完整保留跨平台一鍵啟動腳本 & 修復多金鑰官方快照繼承映射** | 1. **全套腳本還原與強化**：完整提供 [`start_monitor.bat`](./start_monitor.bat)、[`start_monitor.sh`](./start_monitor.sh)、[`start_monitor.command`](./start_monitor.command)、[`start_keepalive.bat`](./start_keepalive.bat)、[`start_keepalive.sh`](./start_keepalive.sh) 與 [`start_keepalive.command`](./start_keepalive.command)。<br>2. **修復個別金鑰快照繼承**：優化 `gemini_logger.py` 中的 `get_rate_limits_status` 與 `seed_default_official_snapshots`，讓同屬主要 Google 帳號 (`shonarmstrong5@gmail.com`) 的所有子金鑰（如 `GEMINI_JAV_KEY`、`GEMINI_FINANCE_KEY` 等）在切換至個別帳號時，能智慧繼承母帳號的 28 天官方速率限制快照基準，並精確累加各金鑰之本機獨立呼叫流量。 |
| **2026-08-28** | **Google AI Studio 官方截圖數據同步 & 金鑰帳號精確映射** | 1. **精確綁定 API Key 與 Google 帳號歸屬**：依據 Google AI Studio 控制台截圖，精確校正 Whisper_correction、GEMINI_API_KEY、JAV_Translate 與 Whiskey_correction 帳號映射。<br>2. **防止資料庫 UNIQUE 衝突與佔位殘留**：在同步帳號 Email 時導入安全更新機制。<br>3. **官方 28 天基準同步 (Rate Limits Snapshot)**：新增 gemini-3.6-flash 獨立模型與 rate_limits_snapshot 快照表。 |
| **2026-08-27** | **DeepL API 翻譯字數監控 & 多 Google 帳號 Antigravity 鏡像升級** | 1. **新增 DeepL API 翻譯配額監控模組**：自動查詢每月 50 萬字消耗進度與剩餘字數。<br>2. **升級 Antigravity 鏡像儀表板**：支援多 Google 帳號獨立切換與雙軌 Quota 各別校準。 |
| **2026-08-17** | **更名 AI_Quota_Monitor 與配額維持整合** | 1. 專案由 Gemini_Monitor 正式更名為 AI_Quota_Monitor。<br>2. 開發 quota_keepalive.py 跨平台守護程式，定時自動發送 1 Token 極簡請求。<br>3. 採用純 Python 標準庫 (urllib)，完全免除第三方 SDK 相依性。 |
| **2026-08-08** | **專案初版建立** | 1. 正式完成 Gemini API 數據日誌記錄核心 (gemini_logger.py) 與本機 SQLite 數據庫 (gemini_usage.db)。<br>2. 建立 Streamlit 視覺化監控儀表板 (app_monitor.py)。 |
