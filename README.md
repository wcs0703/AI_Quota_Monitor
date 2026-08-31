# 📊 AI_Quota_Monitor — AI 配額守護與 API 監控系統

**專案名稱**：AI_Quota_Monitor  
**GitHub 倉庫**：https://github.com/wcs0703/AI_Quota_Monitor.git  
**支援平台**：macOS / Windows / Linux  
**專案定位**：專為 AI 模型（Gemini / LLM）打造的跨平台 **Model 配額維持 (Keep-Alive)**、**即時使用量監控**、**成本計算** 與 **HTTP 異常追蹤系統**。

## 📅 發行日期
2026-08-31 (全面極簡化：移除外層 Shell 腳本，統一為純 Python 跨平台進入點)

---

## 🎯 專案兩大核心功能

### 1. 🛡️ 跨平台 Model Quota 守護程式 (quota_keepalive.py)
* **核心任務**：定時（預設每 4.5 小時）自動對 AI 模型發送極簡請求（1 字元），消耗 ~1 Token（成本 < .000001）。
* **配額維持原理**：主流 AI 模型的速率限制（Rate Limit）通常以 **5 小時窗口** 計算。若長時間未使用，5 小時重置倒數計時器不會啟動；透過定期微小 Ping，**可提前啟動 5 小時重置倒數**，避免臨時重度使用時重置時間被往後延。
* **零相依跨平台**：採用純 Python 標準庫 (urllib.request) 實作 HTTP 請求，完全無第三方 SDK 相依性，在 **macOS / Windows / Linux** 皆可直接執行。
* **日誌與資料庫追蹤**：每次 Ping 結果自動寫入 gemini_usage.db SQLite 資料庫（標記來源為 Quota_KeepAlive）與 logs/keepalive.log。

### 2. 📊 Streamlit API 使用量與成本監控儀表板 (pp_monitor.py & gemini_logger.py)
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
| **quota_keepalive.py** | 跨平台 Quota 守護與維持核心程式（純 Python HTTP 實作） | macOS / Windows / Linux |
| **pp_monitor.py** | Streamlit 視覺化監控儀表板前端 | 跨平台 Web |
| **gemini_logger.py** | SQLite 紀錄核心與成本計算邏輯 | 後端日誌模組 |
| **model_pricing.json** | Gemini 模型最新計價設定字典 | 費率設定 |
| **gemini_usage.db** | 本機 SQLite 數據庫檔 | 資料儲存 |
| **logs/** | 存放維持紀錄 (keepalive.log) 與異常日誌 (error.log) | 本地日誌 |

---

## 🚀 跨平台使用指南 (Antigravity IDE / 終端機通用)

### 1. 啟動 Model Quota 守護維持程式
支援在任何平台（macOS / Windows / Linux）透過標準 Python 直接執行：
`ash
python quota_keepalive.py
`
* **背景常駐執行 (macOS / Linux)**：
  `ash
  nohup python quota_keepalive.py > logs/keepalive.log 2>&1 &
  `
* **單次連線測試 Ping**：
  `ash
  python quota_keepalive.py --once
  `

---

### 2. 啟動 Streamlit 視覺化監控儀表板
`ash
streamlit run app_monitor.py --server.port 8502
`
* 瀏覽器自動開啟 http://localhost:8502 即可檢視所有 API 呼叫、成本累計、DeepL 翻譯字數與 Keep-Alive 定時喚醒紀錄。

---

## 📝 改版紀錄 (Changelog)

| 改版日期 | 版本重點 | 詳細更新說明 |
| :--- | :--- | :--- |
| **2026-08-31** | **工作區架構全面極簡化 (Option A - Pure Python CLI)** | 1. **全面移除平台外層 Shell 腳本**：徹底移除 .bat、.sh 與 .command 包裝腳本，消除跨平台維護負擔與編碼差異。<br>2. **統一 Python 跨平台進入點**：全流程標準化為 python quota_keepalive.py 與 streamlit run app_monitor.py，原生支援 Antigravity IDE 與跨平台終端機。 |
| **2026-08-28** | **Google AI Studio 官方截圖數據同步 & 金鑰帳號精確映射** | 1. **精確綁定 API Key 與 Google 帳號歸屬**：依據 Google AI Studio 控制台截圖，精確校正 Whisper_correction、GEMINI_API_KEY、JAV_Translate 與 Whiskey_correction 帳號映射。<br>2. **防止資料庫 UNIQUE 衝突與佔位殘留**：在同步帳號 Email 時導入安全更新機制。<br>3. **官方 28 天基準同步 (Rate Limits Snapshot)**：新增 gemini-3.6-flash 獨立模型與 
ate_limits_snapshot 快照表。 |
| **2026-08-27** | **DeepL API 翻譯字數監控 & 多 Google 帳號 Antigravity 鏡像升級** | 1. **新增 DeepL API 翻譯配額監控模組**：自動查詢每月 50 萬字消耗進度與剩餘字數。<br>2. **升級 Antigravity 鏡像儀表板**：支援多 Google 帳號獨立切換與雙軌 Quota 各別校準。 |
| **2026-08-17** | **更名 AI_Quota_Monitor 與配額維持整合** | 1. 專案由 Gemini_Monitor 正式更名為 AI_Quota_Monitor。<br>2. 開發 quota_keepalive.py 跨平台守護程式，定時自動發送 1 Token 極簡請求。<br>3. 採用純 Python 標準庫 (urllib)，完全免除第三方 SDK 相依性。 |
| **2026-08-08** | **專案初版建立** | 1. 正式完成 Gemini API 數據日誌記錄核心 (gemini_logger.py) 與本機 SQLite 數據庫 (gemini_usage.db)。<br>2. 建立 Streamlit 視覺化監控儀表板 (pp_monitor.py)。 |
