# 📊 AI_Quota_Monitor — AI 配額守護與 API 監控系統

[![GitHub Repository](https://img.shields.io/badge/GitHub-AI__Quota__Monitor-blue?logo=github)](https://github.com/wcs0703/AI_Quota_Monitor.git)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-brightgreen)](https://github.com/wcs0703/AI_Quota_Monitor.git)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://github.com/wcs0703/AI_Quota_Monitor.git)

**專案名稱**：`AI_Quota_Monitor`  
**GitHub 倉庫**：[`https://github.com/wcs0703/AI_Quota_Monitor.git`](https://github.com/wcs0703/AI_Quota_Monitor.git)  
**專案定位**：專為 AI 模型（Gemini / LLM）打造的跨平台 **Model 配額保活守護 (Keep-Alive)**、**即時使用量監控**、**成本計算** 與 **HTTP 異常追蹤系統**。

## 📅 發行日期
`2026-08-17` (專案更名為 AI_Quota_Monitor，整合跨平台 Model Quota 守護與 5 小時保活機制)

---

## 🎯 專案兩大核心功能

### 1. 🛡️ 跨平台 Model Quota 守護程式 (`quota_keepalive.py`)
* **核心任務**：定時（預設每 4.5 小時）自動對 AI 模型發送極簡請求（1 字元），消耗 ~1 Token（成本 < $0.000001）。
* **保活機制原理**：主流 AI 模型的速率限制（Rate Limit）通常以 **5 小時窗口** 計算。若長時間未使用，5 小時重置倒數計時器不會啟動；透過定期微小 Ping，**可提前啟動 5 小時重置倒數**，避免臨時重度使用時重置時間被往後延。
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

## 🔄 系統架構與作業流程 (Architecture & Workflow)

```mermaid
graph TD
    subgraph 🛡️ 守護保活模組
        K1[定時器 4.5 小時觸發] --> K2[quota_keepalive.py 發送 1 Token 極簡請求]
        K2 -->|啟動 5 小時配額倒數| K3[Gemini API 雲端模型]
        K2 -->|記錄保活數據| DB[(gemini_usage.db SQLite)]
        K2 -->|輸出文字紀錄| LOG[logs/keepalive.log]
    end

    subgraph 📊 監控儀表板模組
        A[外部應用程式/腳本呼叫 API] --> B[gemini_logger.py 記錄 Token / 延遲 / 狀態碼]
        B --> C[讀取 model_pricing.json 計算成本]
        C --> DB
        DB --> E[app_monitor.py 讀取數據]
        E --> F[Streamlit Web 控制台視覺化呈現]
    end
```

---

## 🏗️ 檔案結構清單

| 檔案/資料夾名稱 | 內容說明 | 適用平台 |
| :--- | :--- | :--- |
| **`quota_keepalive.py`** | 跨平台 Quota 保活守護核心程式（純 Python HTTP 實作） | macOS / Windows / Linux |
| **`start_keepalive.command`** | macOS Finder 雙擊即啟動保活程式 | macOS |
| **`start_keepalive.sh`** | 終端機或背景常駐執行腳本 (`nohup`) | macOS / Linux |
| **`start_keepalive.bat`** | Windows 雙擊即啟動保活批次檔 | Windows |
| **`app_monitor.py`** | Streamlit 視覺化監控儀表板前端 | 跨平台 Web |
| **`gemini_logger.py`** | SQLite 紀錄核心與成本計算邏輯 | 後端日誌模組 |
| **`model_pricing.json`** | Gemini 模型最新計價設定字典 | 費率設定 |
| **`gemini_usage.db`** | 本機 SQLite 數據庫檔 | 資料儲存 |
| **`start_monitor.command`** | macOS Finder 雙擊啟動 Streamlit 儀表板 | macOS |
| **`start_monitor.sh`** | 終端機啟動 Streamlit 儀表板 | macOS / Linux |
| **`logs/`** | 存放保活日誌 (`keepalive.log`) 與異常日誌 (`error.log`) | 本地日誌 |

---

## 🚀 跨平台使用指南

### 1. 啟動 Model Quota 保活守護程式

#### 🍎 macOS
* **方式一（最直覺）**：直接在 Finder 雙擊 [`start_keepalive.command`](file:///Users/windfox/Github-Sync/AI_Quota_Monitor/start_keepalive.command)。
* **方式二（背景常駐執行）**：
  ```bash
  cd /Users/windfox/Github-Sync/AI_Quota_Monitor
  nohup ./start_keepalive.sh > logs/keepalive.log 2>&1 &
  ```

#### 🪟 Windows
* **方式一**：直接雙擊執行 `start_keepalive.bat`。
* **方式二（命令提示字元 / PowerShell）**：
  ```powershell
  python quota_keepalive.py
  ```

#### 🐧 Linux
```bash
nohup python3 quota_keepalive.py > logs/keepalive.log 2>&1 &
```

#### 🔍 單次測試 Ping
任何系統隨時可下達以下指令進行單次連線測試：
```bash
python quota_keepalive.py --once
```

---

### 2. 啟動 Streamlit 監控儀表板

* **macOS**：雙擊 [`start_monitor.command`](file:///Users/windfox/Github-Sync/AI_Quota_Monitor/start_monitor.command) 或執行 `./start_monitor.sh`。
* **Windows / Linux**：
  ```bash
  streamlit run app_monitor.py --server.port 8502
  ```
* 瀏覽器自動開啟 `http://localhost:8502` 即可檢視所有 API 呼叫、成本累計與 Keep-Alive 保活歷程。

---

## ⚙️ 環境變數與設定

本系統會自動依序從以下路徑讀取金鑰，無需繁瑣配置：
1. `AI_Quota_Monitor/.env`
2. `Github-Sync/.env`
3. `Whisper-Podcast/.env`

支援的金鑰變數名稱：
```ini
GEMINI_API_KEY=AIzaSy...
# 或
GOOGLE_API_KEY=AIzaSy...
```

---

## 📝 改版紀錄 (Changelog)

| 日期 | 版本 / 改版範圍 | 詳細說明 |
| :--- | :--- | :--- |
| **2026-08-17** | **更名 AI_Quota_Monitor 與保活整合** | 1. 專案由 `Gemini_Monitor` 正式更名為 `AI_Quota_Monitor`，並連接 GitHub 倉庫 `https://github.com/wcs0703/AI_Quota_Monitor.git`。<br>2. 開發 `quota_keepalive.py` 跨平台保活程式，定時（每 4.5 小時）自動發送 1 Token 極簡請求，提前啟動 5 小時配額重置窗口。<br>3. 採用純 Python 標準庫 (urllib)，完全免除第三方 SDK 相依性。<br>4. 支援 macOS (`start_keepalive.command`/`.sh`) 與 Windows (`start_keepalive.bat`) 一鍵啟動。<br>5. 修復 `gemini_logger.py` 異常處理並整合 Keep-Alive 數據寫入 SQLite。 |
| **2026-08-08** | **專案初版建立** | 1. 正式完成 Gemini API 數據日誌記錄核心 (`gemini_logger.py`) 與本機 SQLite 數據庫 (`gemini_usage.db`)。<br>2. 建立 Streamlit 視覺化監控儀表板 (`app_monitor.py`)，即時統計 Token 消耗、估算 USD 成本與延遲分析。<br>3. 導入 Live API Probe 測試介面與 HTTP 429 速率限制追蹤。 |
