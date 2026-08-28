import os
import time
import datetime
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

# 載入環境變數
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)

from gemini_logger import (
    DB_PATH,
    PRICING,
    MODEL_RATE_LIMITS,
    get_account_display_name,
    get_stats_summary,
    get_recent_logs,
    get_available_accounts,
    get_all_accounts_overview,
    get_rate_limits_status,
    save_rate_limits_snapshot,
    seed_default_official_snapshots,
    get_antigravity_accounts,
    get_antigravity_quota,
    update_antigravity_quota,
    get_deepl_usage,
    log_api_call,
    generate_mock_data
)

# ── Streamlit Page Configuration ──
st.set_page_config(
    page_title="Gemini & Antigravity Quota 監控儀表板",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom Styling (Google AI Studio & Antigravity IDE Dark Theme) ──
st.markdown("""
<style>
    /* 全域背景與文字 */
    .stApp {
        background-color: #0d1117;
        color: #e6edf3;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* 帳號狀態卡片 */
    .account-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }
    .account-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .account-card-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #f0f6fc;
    }
    .account-metric-row {
        display: flex;
        justify-content: space-between;
        font-size: 0.82rem;
        color: #8b949e;
        margin-top: 4px;
    }
    .account-metric-val {
        font-weight: 600;
        color: #38bdf8;
    }

    /* 速率限制頂部區域 */
    .rate-limit-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;
    }
    .rate-limit-title {
        font-size: 1.6rem;
        font-weight: 700;
        color: #ffffff;
    }
    .tier-badge {
        background-color: #21262d;
        border: 1px solid #30363d;
        color: #8b949e;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    /* 警告橫幅 */
    .alert-banner {
        background-color: rgba(239, 68, 68, 0.12);
        border: 1px solid #ef4444;
        border-radius: 8px;
        padding: 12px 16px;
        color: #fca5a5;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 0.92rem;
    }
    
    /* 速率限制表格卡片 */
    .rate-table-container {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 24px;
    }
    .rate-table-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #f0f6fc;
        margin-bottom: 4px;
    }
    .rate-table-sub {
        font-size: 0.82rem;
        color: #8b949e;
        margin-bottom: 16px;
    }
    
    /* 進度條容器與刻度 */
    .progress-track {
        background-color: #21262d;
        border-radius: 4px;
        height: 6px;
        width: 100%;
        overflow: hidden;
        margin-top: 4px;
    }
    .progress-fill-normal {
        background-color: #38bdf8;
        height: 100%;
        border-radius: 4px;
    }
    .progress-fill-exceeded {
        background-color: #ef4444;
        height: 100%;
        border-radius: 4px;
    }
    .progress-fill-warning {
        background-color: #f59e0b;
        height: 100%;
        border-radius: 4px;
    }
    
    /* 指標卡片 */
    .metric-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
        color: #f8fafc;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .metric-title {
        font-size: 0.82rem;
        color: #8b949e;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 1.7rem;
        font-weight: 700;
        margin-top: 4px;
        color: #38bdf8;
    }
    .metric-sub {
        font-size: 0.78rem;
        color: #64748b;
        margin-top: 2px;
    }

    /* 🛸 Antigravity IDE Models & Usage 卡片樣式 */
    .agy-container {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 14px;
        padding: 20px 24px;
        margin-bottom: 24px;
    }
    .agy-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #ffffff;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .agy-subtitle {
        font-size: 0.88rem;
        color: #8b949e;
        margin-bottom: 20px;
    }
    .agy-card {
        background-color: #0d1117;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 14px;
    }
    .agy-card-header {
        font-size: 0.95rem;
        font-weight: 600;
        color: #f0f6fc;
        margin-bottom: 4px;
    }
    .agy-card-desc {
        font-size: 0.82rem;
        color: #8b949e;
    }
    .agy-quota-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 0;
        border-bottom: 1px solid #21262d;
    }
    .agy-quota-row:last-child {
        border-bottom: none;
    }
    .agy-quota-label {
        font-size: 0.92rem;
        font-weight: 600;
        color: #f0f6fc;
    }
    .agy-quota-sub {
        font-size: 0.8rem;
        color: #8b949e;
        margin-top: 2px;
    }
    .agy-badge-pct {
        font-size: 1.15rem;
        font-weight: 700;
        color: #22c55e;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──
st.sidebar.title("🤖 Quota & Rate Monitor")
st.sidebar.caption("Google AI Studio & Antigravity IDE 雙軌配額監控")

# 帳號選擇器 (支援多帳號獨立切換)
available_accounts = get_available_accounts()
account_options_display = {
    "全部帳號 (All Accounts)": "全部帳號 (All Accounts)"
}
for a in available_accounts:
    account_options_display[get_account_display_name(a)] = a

selected_display = st.sidebar.selectbox("🧑‍💼 選擇獨立追蹤帳號 (Project/Key)", list(account_options_display.keys()))
filter_account_name = None if selected_display == "全部帳號 (All Accounts)" else account_options_display[selected_display]
selected_account = selected_display

time_range_choice = st.sidebar.selectbox("⏳ 時間範圍 (Time Range)", ["今日 (Today)", "近 7 天 (7 Days)", "近 28 天 (28 Days)"], index=2)

auto_refresh = st.sidebar.checkbox("⏱️ 每 10 秒自動重新整理", value=False)
if auto_refresh:
    st.sidebar.info("自動刷新模式啟用中")
    time.sleep(0.5)

st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ 工具與維護")
if st.sidebar.button("🎲 產生測試模擬數據 (Seed Mock Data)", width="stretch"):
    generate_mock_data(15)
    st.sidebar.success("已成功產生 15 筆測試日誌數據！")
    st.rerun()

if st.sidebar.button("🔄 載入官方截圖 28 天基準數據", width="stretch"):
    seed_default_official_snapshots()
    st.sidebar.success("已成功載入官方 28 天基準數據！")
    st.rerun()

if st.sidebar.button("🗑️ 清空所有記錄檔", width="stretch"):
    with sqlite3.connect(DB_PATH) as conn:
        conn.cursor().execute("DELETE FROM usage_logs")
        conn.commit()
    st.sidebar.warning("已清空所有 API 呼叫數據。")
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.write("📌 **目前數據庫**:")
st.sidebar.code(str(DB_PATH), language="bash")

# ── Fetch Data ──
stats = get_stats_summary(account_name=filter_account_name, time_range=time_range_choice)
rate_status_list, has_exceeded = get_rate_limits_status(account_name=filter_account_name, time_range=time_range_choice)
agy_quota = get_antigravity_quota()
accounts_overview = get_all_accounts_overview(time_range=time_range_choice)

def load_data():
    if not DB_PATH.exists():
        return pd.DataFrame()
    with sqlite3.connect(DB_PATH) as conn:
        if filter_account_name:
            df = pd.read_sql_query("SELECT * FROM usage_logs WHERE account_name = ? ORDER BY id DESC", conn, params=(filter_account_name,))
        else:
            df = pd.read_sql_query("SELECT * FROM usage_logs ORDER BY id DESC", conn)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df

df = load_data()

# ═══════════════════════════════════════════════════════════════
# 1. 🧑‍💼 各帳號即時狀態總覽橫向矩陣 (Multi-Account Status Grid)
# ═══════════════════════════════════════════════════════════════

range_label = time_range_choice.split(' ')[0]
st.markdown(f"<div style='font-size:1.15rem;font-weight:700;color:#f0f6fc;margin-bottom:10px'>🧑‍💼 3 組帳號即時狀態對比矩陣 ({range_label} Overview)</div>", unsafe_allow_html=True)

acc_cols = st.columns(len(accounts_overview))
for idx, acc_info in enumerate(accounts_overview):
    with acc_cols[idx]:
        is_current = (filter_account_name == acc_info['account_name']) or (filter_account_name is None)
        border_color = "#38bdf8" if filter_account_name == acc_info['account_name'] else "#30363d"
        st.markdown(f"""
        <div class="account-card" style="border-color:{border_color}">
            <div class="account-card-header">
                <span class="account-card-title">🔑 {acc_info['display_name']}</span>
                <span>{acc_info['status']}</span>
            </div>
            <div class="account-metric-row">
                <span>{range_label}請求次數:</span>
                <span class="account-metric-val">{acc_info['today_calls']} 次</span>
            </div>
            <div class="account-metric-row">
                <span>{range_label} Token 用量:</span>
                <span class="account-metric-val">{acc_info['today_tokens']:,}</span>
            </div>
            <div class="account-metric-row">
                <span>{range_label}花費:</span>
                <span style="font-weight:600;color:#4ade80">${acc_info['today_cost']:.4f}</span>
            </div>
            <div class="account-metric-row">
                <span>429 速率限制次數:</span>
                <span style="font-weight:600;color:{'#ef4444' if acc_info['today_429'] > 0 else '#8b949e'}">{acc_info['today_429']} 次</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<hr style='border-color:#30363d;margin:12px 0 20px 0'>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# 2. 頂部導覽切換 (Google AI Studio Rate Limits vs Antigravity IDE)
# ═══════════════════════════════════════════════════════════════

view_mode = st.radio(
    "選擇主要檢視模組",
    [
        "📊 Google AI Studio (10 款模型速率限制)",
        "🛸 Antigravity IDE (Models & Usage 配額追蹤)",
        "🌐 DeepL API (翻譯字數配額監控)"
    ],
    horizontal=True
)

if view_mode == "🛸 Antigravity IDE (Models & Usage 配額追蹤)":
    # ── 多帳號選擇器 ──
    agy_accounts = get_antigravity_accounts()
    col_sel1, col_sel2 = st.columns([3, 1])
    with col_sel1:
        selected_agy_acc = st.radio("👤 切換 Google 帳號配額", agy_accounts, horizontal=True, key="agy_acc_radio")
    with col_sel2:
        st.markdown("<div style='padding-top:25px;'></div>", unsafe_allow_html=True)
        # 取得當前選擇帳號的配額數據
        agy_quota = get_antigravity_quota(selected_agy_acc)

    # ── Antigravity IDE Models & Usage 鏡像介面 ──
    st.markdown(f"""
    <div class="agy-container">
        <div class="agy-title">Models & Usage — <span style="color:#58a6ff;font-size:1.1rem;">{selected_agy_acc}</span> <span style="font-size:1rem;color:#8b949e;cursor:pointer;">🔄</span></div>
        <div class="agy-subtitle">Manage your model quota and credits for {selected_agy_acc}.</div>
    """, unsafe_allow_html=True)

    # 1. Plan Card
    plan_display = agy_quota.get('plan_name', 'Google AI Pro')
    st.markdown(f"""
    <div class="agy-card" style="display:flex;justify-content:space-between;align-items:center;">
        <div>
            <div class="agy-card-header">Your Plan: {plan_display}</div>
            <div class="agy-card-desc">You can upgrade to a Google AI Ultra plan to receive higher rate limits.</div>
        </div>
        <div>
            <span style="background-color:#1d4ed8;color:#ffffff;padding:6px 14px;border-radius:6px;font-size:0.85rem;font-weight:600;">Upgrade</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. Model Credits
    st.markdown("""
    <div class="agy-card" style="display:flex;justify-content:space-between;align-items:center;">
        <div>
            <div class="agy-card-header">Enable AI Credit Overages</div>
            <div class="agy-card-desc">When toggled on, Antigravity IDE will use your AI credits to fulfill model requests once you're out of model quota. Antigravity IDE will always use your model quota first before using AI credits.</div>
        </div>
        <div style="padding-left:16px;">
            <span style="color:#64748b;font-size:1.4rem;">⚪</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3. Gemini Models Section
    st.markdown("<div style='font-size:0.95rem;font-weight:600;color:#f0f6fc;margin:16px 0 8px 0'>Gemini Models ⓘ</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="agy-card">
        <div class="agy-quota-row">
            <div>
                <div class="agy-quota-label">Weekly Limit Remaining</div>
                <div class="agy-quota-sub">You have used some of your weekly limit, it will fully refresh in {agy_quota['gemini_weekly_desc']}.</div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
                <span class="agy-badge-pct">{agy_quota['gemini_weekly_pct']:.0f}%</span>
                <span style="color:#22c55e;font-size:1.3rem;">🟢</span>
            </div>
        </div>
        <div class="agy-quota-row">
            <div>
                <div class="agy-quota-label">Five Hour Limit Remaining</div>
                <div class="agy-quota-sub">You have used some of your 5-hour limit, it will fully refresh in {agy_quota['gemini_5hr_desc']}.</div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
                <span class="agy-badge-pct">{agy_quota['gemini_5hr_pct']:.0f}%</span>
                <span style="color:#22c55e;font-size:1.3rem;">🟢</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 4. Claude and GPT models Section
    st.markdown("<div style='font-size:0.95rem;font-weight:600;color:#f0f6fc;margin:16px 0 8px 0'>Claude and GPT models ⓘ</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="agy-card">
        <div class="agy-quota-row">
            <div>
                <div class="agy-quota-label">Weekly Limit Remaining</div>
                <div class="agy-quota-sub">All weekly limits for Claude and GPT models are available.</div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
                <span class="agy-badge-pct" style="color:#22c55e;">{agy_quota['claude_gpt_weekly_pct']:.0f}%</span>
                <span style="color:#22c55e;font-size:1.3rem;">🟢</span>
            </div>
        </div>
        <div class="agy-quota-row">
            <div>
                <div class="agy-quota-label">Five Hour Limit Remaining</div>
                <div class="agy-quota-sub">All 5-hour limits for Claude and GPT models are available.</div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
                <span class="agy-badge-pct" style="color:#22c55e;">{agy_quota['claude_gpt_5hr_pct']:.0f}%</span>
                <span style="color:#22c55e;font-size:1.3rem;">🟢</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── 校準控制台 ──
    with st.expander(f"🛠️ 校準 【{selected_agy_acc}】 配額數值與重置時間 (Calibration)"):
        st.caption(f"說明：您可在此隨時將 {selected_agy_acc} 在 Antigravity IDE 畫面中的最新剩餘百分比與時間同步寫入系統，系統將自動接續倒數計算。")
        cal_col1, cal_col2 = st.columns(2)
        with cal_col1:
            cal_plan = st.selectbox("方案類型", ["Google AI Pro", "Google AI Ultra", "Google AI Free Tier"], index=0 if agy_quota.get('plan_name') == 'Google AI Pro' else 1)
            cal_w_pct = st.number_input("Gemini 每週剩餘百分比 (%)", min_value=0.0, max_value=100.0, value=float(agy_quota['gemini_weekly_pct']), step=1.0, key="cal_w_pct")
            cal_w_hrs = st.number_input("Gemini 每週重置剩餘小時數 (例如 47 小時 = 1天23小時)", min_value=0.0, max_value=168.0, value=47.0, step=1.0, key="cal_w_hrs")
        with cal_col2:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            cal_h_pct = st.number_input("Gemini 5 小時剩餘百分比 (%)", min_value=0.0, max_value=100.0, value=float(agy_quota['gemini_5hr_pct']), step=1.0, key="cal_h_pct")
            cal_h_mins = st.number_input("Gemini 5 小時重置剩餘分鐘數 (例如 239 分 = 3小時59分)", min_value=0.0, max_value=300.0, value=239.0, step=1.0, key="cal_h_mins")

        if st.button(f"💾 儲存並更新 【{selected_agy_acc}】 配額狀態", type="primary", width="stretch"):
            update_antigravity_quota(
                account_name=selected_agy_acc,
                gemini_weekly_pct=cal_w_pct,
                gemini_weekly_hours=cal_w_hrs,
                gemini_5hr_pct=cal_h_pct,
                gemini_5hr_mins=cal_h_mins,
                plan_name=cal_plan
            )
            st.success(f"✅ 【{selected_agy_acc}】 配額狀態已成功校準更新！")
            st.rerun()

elif view_mode == "🌐 DeepL API (翻譯字數配額監控)":
    # ── DeepL API 翻譯字數監控介面 ──
    deepl_info = get_deepl_usage()
    
    st.markdown("""
    <div class="agy-container">
        <div class="agy-title">DeepL Translation Quota <span style="font-size:1rem;color:#8b949e;cursor:pointer;">🔄</span></div>
        <div class="agy-subtitle">即時監控 DeepL API 翻譯字數消耗、每月配額上限與剩餘額度。</div>
    """, unsafe_allow_html=True)
    
    # 1. 方案卡片
    st.markdown(f"""
    <div class="agy-card" style="display:flex;justify-content:space-between;align-items:center;">
        <div>
            <div class="agy-card-header">DeepL 方案狀態: {deepl_info['tier']}</div>
            <div class="agy-card-desc">連線狀態: {deepl_info['status_msg']}</div>
        </div>
        <div>
            <span style="background-color:#0f766e;color:#ffffff;padding:6px 14px;border-radius:6px;font-size:0.85rem;font-weight:600;">DeepL API</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 2. 字數統計指標卡片
    d_col1, d_col2, d_col3, d_col4 = st.columns(4)
    with d_col1:
        st.metric("本月已翻譯字數", f"{deepl_info['character_count']:,} 字")
    with d_col2:
        st.metric("每月字數上限", f"{deepl_info['character_limit']:,} 字")
    with d_col3:
        st.metric("剩餘可用字數", f"{deepl_info['remaining_chars']:,} 字")
    with d_col4:
        st.metric("字數消耗比例", f"{deepl_info['usage_pct']:.2f}%")
        
    # 3. 進度條視覺化
    st.markdown("<div style='font-size:0.95rem;font-weight:600;color:#f0f6fc;margin:16px 0 8px 0'>字數額度消耗進度條</div>", unsafe_allow_html=True)
    progress_val = min(1.0, max(0.0, deepl_info['usage_pct'] / 100.0))
    st.progress(progress_val)
    
    if deepl_info['usage_pct'] > 90:
        st.error(f"⚠️ 警告：DeepL 翻譯額度已使用 {deepl_info['usage_pct']}%，即將達到上限！")
    elif deepl_info['usage_pct'] > 75:
        st.warning(f"⚡ 提醒：DeepL 翻譯額度已使用 {deepl_info['usage_pct']}%。")
        
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 4. 即時 DeepL 測試翻譯探針
    with st.expander("⚡ 即時 DeepL 翻譯測試探針 (Live Translation Probe)"):
        st.caption("說明：直接在下方輸入日文或英文文字發送翻譯請求，即時測試 DeepL API 回應速度並即時扣減刷新字數。")
        t_col1, t_col2 = st.columns([3, 1])
        with t_col1:
            sample_text = st.text_area("待翻譯文字 (日文/英文)", value="人工知能と機械学習を活用して、音声認識とリアルタイム翻訳の精度を向上させます。")
        with t_col2:
            target_lang = st.selectbox("目標語言", ["ZH-HANT (繁體中文)", "ZH (簡體/繁體中文)", "EN-US (美式英文)", "JA (日文)"])
            deepl_test_key = st.text_input("DeepL Auth Key (自動載入)", value=os.getenv("DEEPL_API_KEY", ""), type="password")
            
        if st.button("🚀 發送 DeepL 即時翻譯測試", type="primary", width="stretch"):
            if not deepl_test_key.strip():
                st.error("❌ 請先在 .env 中填寫 DEEPL_API_KEY 或在上方輸入金鑰！")
            else:
                import urllib.parse
                import urllib.request
                import json
                import time
                t_start = time.time()
                is_free_key = deepl_test_key.strip().endswith(":fx")
                trans_url = "https://api-free.deepl.com/v2/translate" if is_free_key else "https://api.deepl.com/v2/translate"
                t_lang_code = target_lang.split(" ")[0]
                
                try:
                    payload = urllib.parse.urlencode({
                        "text": sample_text,
                        "target_lang": t_lang_code
                    }).encode("utf-8")
                    req = urllib.request.Request(
                        trans_url,
                        data=payload,
                        headers={
                            "Authorization": f"DeepL-Auth-Key {deepl_test_key.strip()}",
                            "Content-Type": "application/x-www-form-urlencoded"
                        }
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        res_json = json.loads(resp.read().decode("utf-8"))
                        t_latency = round((time.time() - t_start) * 1000, 1)
                        translated_text = res_json["translations"][0]["text"]
                        detected_lang = res_json["translations"][0].get("detected_source_language", "AUTO")
                        
                        st.success(f"✅ 翻譯成功！(耗時: {t_latency}ms | 消耗字數: {len(sample_text)} 字)")
                        st.markdown(f"**偵測語言**: `{detected_lang}` ➔ **目標語言**: `{t_lang_code}`")
                        st.text_area("翻譯結果", value=translated_text, height=100)
                        time.sleep(0.5)
                        st.rerun()
                except Exception as ex:
                    st.error(f"❌ DeepL 翻譯失敗: {ex}")

else:
    # ── Google AI Studio 11 款模型速率限制面板 ──
    st.markdown("""
    <div class="rate-limit-header">
        <span class="rate-limit-title">Gemini API Rate Limit</span>
        <span class="tier-badge">● Free tier</span>
    </div>
    """, unsafe_allow_html=True)

    # 項目與時間範圍選單列 (比照官方 AI Studio 頂部控制列)
    g_c1, g_c2, g_c3 = st.columns([3, 2, 2])
    with g_c1:
        st.markdown(f"**Project**: `{selected_account}`")
    with g_c2:
        st.markdown(f"**Time Range**: `{time_range_choice}`")
    with g_c3:
        st.markdown("<div style='text-align:right;color:#8b949e;font-size:0.85rem;padding-top:4px;'>📊 Peak usage over period</div>", unsafe_allow_html=True)

    # 若有超額，顯示紅色警示橫幅
    if has_exceeded or stats['today_429_count'] > 0:
        st.markdown("""
        <div class="alert-banner">
            <span>🚫</span>
            <div>
                <strong>You have reached a rate limit.</strong> Set up billing to increase your limits and unblock your work.<br>
                <span style="font-size:0.82rem;opacity:0.9;">提示：您已達到免費層每日請求上限 (20 RPD) 或每分鐘速率限制 (5 RPM)。建議自動輪替 API 金鑰或切換至 <strong>Flash Lite (500 RPD / 15 RPM)</strong>。</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 11 款模型速率限制實時表格
    st.markdown(f"""
    <div class="rate-table-container">
        <div class="rate-table-header">Rate limits by model (11 款模型全覆蓋)</div>
        <div class="rate-table-sub">Peak usage per model compared to its limit over the last {time_range_choice.split(' ')[0]} (目前篩選帳號: <strong>{selected_account}</strong>)</div>
    """, unsafe_allow_html=True)

    # 表頭
    h_c1, h_c2, h_c3, h_c4, h_c5, h_c6 = st.columns([2.4, 1.5, 1.8, 1.8, 1.8, 1.2])
    with h_c1: st.markdown("<span style='color:#8b949e;font-size:0.85rem;font-weight:600'>Model</span>", unsafe_allow_html=True)
    with h_c2: st.markdown("<span style='color:#8b949e;font-size:0.85rem;font-weight:600'>Category</span>", unsafe_allow_html=True)
    with h_c3: st.markdown("<span style='color:#8b949e;font-size:0.85rem;font-weight:600'>RPM (Req/min)</span>", unsafe_allow_html=True)
    with h_c4: st.markdown("<span style='color:#8b949e;font-size:0.85rem;font-weight:600'>TPM (Tokens/min)</span>", unsafe_allow_html=True)
    with h_c5: st.markdown("<span style='color:#8b949e;font-size:0.85rem;font-weight:600'>RPD (Req/day)</span>", unsafe_allow_html=True)
    with h_c6: st.markdown("<span style='color:#8b949e;font-size:0.85rem;font-weight:600'>Status</span>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#30363d;margin:6px 0 12px 0'>", unsafe_allow_html=True)

    # 依序呈現 11 款模型數據
    for item in rate_status_list:
        r_c1, r_c2, r_c3, r_c4, r_c5, r_c6 = st.columns([2.4, 1.5, 1.8, 1.8, 1.8, 1.2])
        
        rpm_color_cls = "progress-fill-exceeded" if item['current_rpm'] >= item['max_rpm'] else ("progress-fill-warning" if item['rpm_pct'] >= 80 else "progress-fill-normal")
        rpd_color_cls = "progress-fill-exceeded" if item['current_rpd'] >= item['max_rpd'] else ("progress-fill-warning" if item['rpd_pct'] >= 80 else "progress-fill-normal")
        tpm_color_cls = "progress-fill-exceeded" if item['current_tpm'] >= item['max_tpm'] else "progress-fill-normal"

        rpm_text_color = "#ef4444" if item['current_rpm'] >= item['max_rpm'] else "#f0f6fc"
        rpd_text_color = "#ef4444" if item['current_rpd'] >= item['max_rpd'] else "#f0f6fc"

        if item['current_tpm'] >= 1000:
            tpm_display = f"{item['current_tpm'] / 1000:.2f}K" if (item['current_tpm'] / 1000) % 1 != 0 else f"{int(item['current_tpm'] / 1000)}K"
        else:
            tpm_display = f"{int(item['current_tpm'])}"
        
        max_tpm_display = f"{int(item['max_tpm'] / 1000)}K"

        status_badge = "🔴 已達上限" if item['is_exceeded'] else ("🟡 接近上限" if item['rpd_pct'] >= 80 else "🟢 正常")

        with r_c1:
            st.markdown(f"<span style='font-weight:600;color:#f0f6fc;font-size:0.90rem'>{item['displayName']}</span>", unsafe_allow_html=True)
        with r_c2:
            st.markdown(f"<span style='color:#8b949e;font-size:0.83rem'>{item['category']}</span>", unsafe_allow_html=True)
        with r_c3:
            st.markdown(f"""
            <div style='font-size:0.83rem;color:{rpm_text_color};font-weight:600'>{item['current_rpm']} / {item['max_rpm']}</div>
            <div class="progress-track"><div class="{rpm_color_cls}" style="width:{item['rpm_pct']}%"></div></div>
            """, unsafe_allow_html=True)
        with r_c4:
            st.markdown(f"""
            <div style='font-size:0.83rem;color:#f0f6fc;font-weight:600'>{tpm_display} / {max_tpm_display}</div>
            <div class="progress-track"><div class="{tpm_color_cls}" style="width:{item['tpm_pct']}%"></div></div>
            """, unsafe_allow_html=True)
        with r_c5:
            st.markdown(f"""
            <div style='font-size:0.83rem;color:{rpd_text_color};font-weight:600'>{item['current_rpd']} / {item['max_rpd']}</div>
            <div class="progress-track"><div class="{rpd_color_cls}" style="width:{item['rpd_pct']}%"></div></div>
            """, unsafe_allow_html=True)
        with r_c6:
            st.markdown(f"<span style='font-size:0.80rem'>{status_badge}</span>", unsafe_allow_html=True)
        
        st.markdown("<div style='margin-bottom:6px'></div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Google AI Studio 官方用量校準控制台 ──
    with st.expander(f"🛠️ Google AI Studio 官方用量校準與同步控制台 ({selected_account} / {time_range_choice})"):
        st.caption("說明：Google AI Studio 官方數據涵蓋雲端專案在各端（含網頁版、測試探針與全工具）的統計。在此可隨時校準或同步官方基準快照。")
        cal_btn_col1, cal_btn_col2 = st.columns(2)
        with cal_btn_col1:
            if st.button("⚡ 一鍵同步官方 28 天截圖基準 (shonarmstrong5@gmail.com)", width="stretch"):
                seed_default_official_snapshots()
                st.success("✅ 已成功寫入官方 28 天基準數據！")
                st.rerun()
        with cal_btn_col2:
            st.caption("💡 提示：若切換為近 28 天，將完整鏡像官方 Peak RPM、TPM 與 RPD。")

# ═══════════════════════════════════════════════════════════════
# 3. 核心指標卡片 (Metric Cards)
# ═══════════════════════════════════════════════════════════════

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">今日總呼叫次數 ({selected_account})</div>
        <div class="metric-value">{stats['today_calls']:,} <span style="font-size:1rem;color:#8b949e">次</span></div>
        <div class="metric-sub">歷史總計: {stats['all_calls']:,} 次</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">今日 Token 總用量</div>
        <div class="metric-value">{stats['today_total_tokens']:,} <span style="font-size:1rem;color:#8b949e">tokens</span></div>
        <div class="metric-sub">In: {stats['today_prompt_tokens']:,} | Out: {stats['today_output_tokens']:,}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">今日預估費用 (USD)</div>
        <div class="metric-value" style="color:#4ade80">${stats['today_cost']:.4f}</div>
        <div class="metric-sub">歷史累積: ${stats['all_cost']:.4f}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    err_color = "#ef4444" if stats['today_429_count'] > 0 or stats['today_errors'] > 0 else "#38bdf8"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">今日 429 速率限制 / 報錯</div>
        <div class="metric-value" style="color:{err_color}">{stats['today_429_count']} <span style="font-size:1rem;color:#8b949e">次 429</span></div>
        <div class="metric-sub">其他報錯: {stats['today_errors'] - stats['today_429_count']} 次 | 平均延遲: {stats['today_avg_latency']:.0f} ms</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# 4. 主分頁區塊 (Main Tabs)
# ═══════════════════════════════════════════════════════════════

tab1, tab2, tab3, tab4 = st.tabs(["📈 用量與費用趨勢", "🤖 模型與帳號分析", "📋 API 呼叫日誌", "⚡ Live 探針測試"])

# ── TAB 1: Trends ──
with tab1:
    st.subheader("📈 時間序列趨勢圖")
    if df.empty:
        st.info("💡 目前尚無 API 呼叫紀錄。點擊左側「產生測試模擬數據」即可即時查看圖表效果。")
    else:
        time_frame = st.radio("趨勢聚合單位", ["每小時 (Hourly)", "每日 (Daily)"], horizontal=True)
        
        df_trend = df.copy()
        if "每小時" in time_frame:
            df_trend['time_group'] = df_trend['timestamp'].dt.strftime('%Y-%m-%d %H:00')
        else:
            df_trend['time_group'] = df_trend['timestamp'].dt.strftime('%Y-%m-%d')

        grouped = df_trend.groupby('time_group').agg({
            'prompt_tokens': 'sum',
            'output_tokens': 'sum',
            'total_tokens': 'sum',
            'estimated_cost': 'sum',
            'id': 'count',
            'latency_ms': 'mean'
        }).reset_index()

        col_t1, col_t2 = st.columns(2)
        
        with col_t1:
            st.markdown("#### 🔹 Token 消耗趨勢 (Prompt vs Output)")
            fig_tokens = px.bar(
                grouped, x='time_group', y=['prompt_tokens', 'output_tokens'],
                title="Token 消耗堆疊圖",
                labels={'value': 'Token 數量', 'time_group': '時間', 'variable': '類型'},
                color_discrete_map={'prompt_tokens': '#60a5fa', 'output_tokens': '#c084fc'}
            )
            fig_tokens.update_layout(template="plotly_dark", barmode='stack')
            st.plotly_chart(fig_tokens, width="stretch")

        with col_t2:
            st.markdown("#### 🔹 請求次數與預估費用")
            fig_cost = px.line(
                grouped, x='time_group', y='estimated_cost', text='id',
                title="費用成長趨勢 (USD)",
                labels={'estimated_cost': '費用 (USD)', 'time_group': '時間'},
                markers=True
            )
            fig_cost.update_traces(line_color='#4ade80', marker_size=8)
            fig_cost.update_layout(template="plotly_dark")
            st.plotly_chart(fig_cost, width="stretch")

# ── TAB 2: Model & Account Breakdown ──
with tab2:
    st.subheader("🤖 各模型與帳號呼叫用量分布")
    if df.empty:
        st.info("💡 目前尚無紀錄數據。")
    else:
        col_m1, col_m2 = st.columns(2)

        with col_m1:
            st.markdown("#### 🍰 模型呼叫比例 (Calls by Model)")
            model_group = df.groupby('model_name').agg({'id': 'count'}).reset_index()
            fig_pie = px.pie(
                model_group, values='id', names='model_name',
                hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_pie.update_layout(template="plotly_dark")
            st.plotly_chart(fig_pie, width="stretch")

        with col_m2:
            st.markdown("#### 🧑‍💼 各帳號用量分布 (Calls by Account)")
            if 'account_name' in df.columns:
                acc_group = df.groupby('account_name').agg({'id': 'count', 'total_tokens': 'sum'}).reset_index()
                fig_acc = px.bar(
                    acc_group, x='account_name', y='total_tokens', color='account_name',
                    title="各帳號 Token 總消耗", labels={'total_tokens': 'Token 總數', 'account_name': '帳號名稱'}
                )
                fig_acc.update_layout(template="plotly_dark")
                st.plotly_chart(fig_acc, width="stretch")

        st.markdown("#### 📋 模型統計詳細數據")
        model_detail = df.groupby('model_name').agg({
            'id': 'count',
            'total_tokens': 'sum',
            'estimated_cost': 'sum',
            'latency_ms': 'mean'
        }).reset_index()
        st.dataframe(
            model_detail.rename(columns={
                'model_name': '模型名稱',
                'id': '呼叫次數',
                'total_tokens': '總 Token 消耗',
                'estimated_cost': '總費用 (USD)',
                'latency_ms': '平均回應時間 (ms)'
            }),
            width="stretch"
        )

# ── TAB 3: Logs ──
with tab3:
    st.subheader("📋 Gemini API 詳細呼叫日誌")
    if df.empty:
        st.info("💡 目前尚無日誌。")
    else:
        col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
        with col_f1:
            status_filter = st.selectbox("篩選狀態碼", ["全部", "僅成功 (200)", "僅速率限制 (429)", "僅錯誤 (!=200)"])
        with col_f2:
            model_filter = st.selectbox("篩選模型", ["全部"] + list(df['model_name'].unique()))
        with col_f3:
            search_query = st.text_input("搜尋備註/訊息", "")

        df_filtered = df.copy()
        if status_filter == "僅成功 (200)":
            df_filtered = df_filtered[df_filtered['status_code'] == 200]
        elif status_filter == "僅速率限制 (429)":
            df_filtered = df_filtered[df_filtered['status_code'] == 429]
        elif status_filter == "僅錯誤 (!=200)":
            df_filtered = df_filtered[df_filtered['status_code'] != 200]

        if model_filter != "全部":
            df_filtered = df_filtered[df_filtered['model_name'] == model_filter]

        if search_query:
            df_filtered = df_filtered[
                df_filtered['caller_info'].str.contains(search_query, case=False, na=False) |
                df_filtered['error_message'].str.contains(search_query, case=False, na=False)
            ]

        cols_to_show = ['id', 'timestamp', 'account_name', 'model_name', 'prompt_tokens', 'output_tokens', 'total_tokens', 'latency_ms', 'status_code', 'estimated_cost', 'caller_info', 'error_message']
        existing_cols = [c for c in cols_to_show if c in df_filtered.columns]
        st.dataframe(df_filtered[existing_cols], width="stretch")

# ── TAB 4: Live Probe Tester ──
with tab4:
    st.subheader("⚡ 即時 API 探針與延遲測試 (Live Probe)")
    st.write("說明：選擇您在 `.env` 中設定的帳號金鑰發送測試請求，即時驗證 Token 統計與耗時，並自動寫入數據庫。")

    probe_accounts = {
        "GEMINI_PODCAST_KEY (Podcast挑錯)": os.getenv("GEMINI_PODCAST_KEY", ""),
        "GEMINI_JAV_KEY (日語翻譯)": os.getenv("GEMINI_JAV_KEY", ""),
        "GEMINI_FINANCE_KEY (台股金融)": os.getenv("GEMINI_FINANCE_KEY", ""),
        "GEMINI_BACKUP_KEY_2 (備援金鑰)": os.getenv("GEMINI_BACKUP_KEY_2", "")
    }

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        chosen_acc_label = st.selectbox("選擇測試帳號 (API Key)", list(probe_accounts.keys()))
        selected_key = probe_accounts[chosen_acc_label]
        api_key_input = st.text_input("API Key (自動載入)", value=selected_key, type="password")
    with col_p2:
        model_choice = st.selectbox("測試模型", ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"])
        test_prompt = st.text_area("測試 Prompt", value="請用繁體中文簡要回答：什麼是人工智慧的 RAG 架構？(50字內)")

    if st.button("🚀 發送探針測試請求", type="primary", width="stretch"):
        if not api_key_input:
            st.error("❌ 找不到該帳號的 API Key，請在 .env 中填寫！")
        else:
            st.info("🔄 正在連線至 Gemini API...")
            t0 = time.time()
            account_tag = chosen_acc_label.split(" ")[0]
            try:
                from google import genai
                client = genai.Client(api_key=api_key_input)
                response = client.models.generate_content(
                    model=model_choice,
                    contents=test_prompt
                )
                latency = (time.time() - t0) * 1000.0
                
                p_tok = getattr(response.usage_metadata, 'prompt_token_count', 0) if hasattr(response, 'usage_metadata') else 0
                o_tok = getattr(response.usage_metadata, 'candidates_token_count', 0) if hasattr(response, 'usage_metadata') else 0
                text_out = response.text

                log_api_call(
                    model_name=model_choice,
                    prompt_tokens=p_tok,
                    output_tokens=o_tok,
                    latency_ms=latency,
                    status_code=200,
                    caller_info="Live Probe Test",
                    account_name=account_tag
                )

                st.success(f"✅ 請求成功！(耗時: {latency:.1f} ms | In: {p_tok} tokens | Out: {o_tok} tokens)")
                st.markdown("##### 💬 回應內容:")
                st.write(text_out)
                st.rerun()

            except Exception as ex:
                latency = (time.time() - t0) * 1000.0
                status_code = 429 if "429" in str(ex) or "RESOURCE_EXHAUSTED" in str(ex) else 500
                log_api_call(
                    model_name=model_choice,
                    prompt_tokens=0,
                    output_tokens=0,
                    latency_ms=latency,
                    status_code=status_code,
                    error_message=str(ex),
                    caller_info="Live Probe Test Error",
                    account_name=account_tag
                )
                st.error(f"❌ 請求失敗 (狀態碼 {status_code}): {ex}")
