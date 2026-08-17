import os
import time
import datetime
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from gemini_logger import (
    DB_PATH,
    PRICING,
    get_stats_summary,
    get_recent_logs,
    log_api_call,
    generate_mock_data
)

# ── Streamlit Page Configuration ──
st.set_page_config(
    page_title="Gemini API 使用狀況監控儀表板",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Styling ──
st.markdown("""
<style>
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 12px;
        color: #f8fafc;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .metric-title {
        font-size: 0.85rem;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        margin-top: 4px;
        color: #38bdf8;
    }
    .metric-sub {
        font-size: 0.8rem;
        color: #64748b;
        margin-top: 2px;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──
st.sidebar.title("🤖 Gemini Monitor")
st.sidebar.caption("即時 API 呼叫監控與 Token 用量分析系統")

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
stats = get_stats_summary()

# Load all rows into DataFrame
def load_data():
    if not DB_PATH.exists():
        return pd.DataFrame()
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query("SELECT * FROM usage_logs ORDER BY id DESC", conn)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df

df = load_data()

# ── Header ──
st.title("📊 Gemini API 使用狀況監控儀表板")
st.caption("即時統計 Gemini API 的請求次數、Token 消耗、延遲率、429 速率限制與預估費用")

st.markdown("<br>", unsafe_allow_html=True)

# ── Metric Cards ──
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">今日總呼叫次數</div>
        <div class="metric-value">{stats['today_calls']:,} <span style="font-size:1rem;color:#94a3b8">次</span></div>
        <div class="metric-sub">歷史總計: {stats['all_calls']:,} 次</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">今日 Token 總用量</div>
        <div class="metric-value">{stats['today_total_tokens']:,} <span style="font-size:1rem;color:#94a3b8">tokens</span></div>
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
        <div class="metric-value" style="color:{err_color}">{stats['today_429_count']} <span style="font-size:1rem;color:#94a3b8">次 429</span></div>
        <div class="metric-sub">其他報錯: {stats['today_errors'] - stats['today_429_count']} 次 | 平均延遲: {stats['today_avg_latency']:.0f} ms</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Main Tabs ──
tab1, tab2, tab3, tab4 = st.tabs(["📈 用量與費用趨勢", "🤖 模型用量分析", "📋 API 呼叫日誌", "⚡ Live 探針測試"])

# ── TAB 1: Trends ──
with tab1:
    st.subheader("📈 時間序列趨勢圖")
    if df.empty:
        st.info("💡 目前尚無 API 呼叫紀錄。點擊左側「產生測試模擬數據」即可即時查看圖表效果。")
    else:
        # Group by Date or Hour
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

# ── TAB 2: Model Breakdown ──
with tab2:
    st.subheader("🤖 各 Gemini 模型呼叫與 Token 分布")
    if df.empty:
        st.info("💡 目前尚無紀錄數據。")
    else:
        model_group = df.groupby('model_name').agg({
            'id': 'count',
            'total_tokens': 'sum',
            'estimated_cost': 'sum',
            'latency_ms': 'mean'
        }).reset_index()

        col_m1, col_m2 = st.columns(2)

        with col_m1:
            st.markdown("#### 🍰 模型呼叫比例 (Calls Distribution)")
            fig_pie = px.pie(
                model_group, values='id', names='model_name',
                hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_pie.update_layout(template="plotly_dark")
            st.plotly_chart(fig_pie, width="stretch")

        with col_m2:
            st.markdown("#### 📊 各模型花費 (Estimated Cost by Model)")
            fig_bar = px.bar(
                model_group, x='model_name', y='estimated_cost',
                color='model_name', title="模型花費排行 (USD)",
                labels={'estimated_cost': '預估費用 (USD)', 'model_name': '模型名稱'},
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            fig_bar.update_layout(template="plotly_dark")
            st.plotly_chart(fig_bar, width="stretch")

        st.markdown("#### 📋 模型統計詳細數據")
        st.dataframe(
            model_group.rename(columns={
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

        st.dataframe(
            df_filtered[['id', 'timestamp', 'model_name', 'prompt_tokens', 'output_tokens', 'total_tokens', 'latency_ms', 'status_code', 'estimated_cost', 'caller_info', 'error_message']],
            width="stretch"
        )

# ── TAB 4: Live Probe Tester ──
with tab4:
    st.subheader("⚡ 即時 API 探針與延遲測試 (Live Probe)")
    st.write("說明：透過您的 `GOOGLE_API_KEY` 發送測試請求，即時驗證 Token 統計與耗時，並自動寫入數據庫。")

    api_key_input = st.text_input("GOOGLE_API_KEY", value=os.getenv("GOOGLE_API_KEY", ""), type="password")
    model_choice = st.selectbox("測試模型", ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-lite"])
    test_prompt = st.text_area("測試 Prompt", value="請用繁體中文簡要回答：什麼是人工智慧的 RAG 架構？(100字內)")

    if st.button("🚀 發送探針測試請求", type="primary", width="stretch"):
        if not api_key_input:
            st.error("❌ 請輸入 GOOGLE_API_KEY 後再進行測試！")
        else:
            st.info("🔄 正在連線至 Gemini API...")
            t0 = time.time()
            try:
                # Import google.generativeai or google-genai
                try:
                    from google import genai
                    client = genai.Client(api_key=api_key_input)
                    response = client.models.generate_content(
                        model=model_choice,
                        contents=test_prompt
                    )
                    latency = (time.time() - t0) * 1000.0
                    
                    # Extract tokens
                    p_tok = getattr(response.usage_metadata, 'prompt_token_count', 0) if hasattr(response, 'usage_metadata') else 0
                    o_tok = getattr(response.usage_metadata, 'candidates_token_count', 0) if hasattr(response, 'usage_metadata') else 0
                    text_out = response.text
                except Exception as e1:
                    # Fallback to google.generativeai
                    import google.generativeai as genai_legacy
                    genai_legacy.configure(api_key=api_key_input)
                    m = genai_legacy.GenerativeModel(model_choice)
                    response = m.generate_content(test_prompt)
                    latency = (time.time() - t0) * 1000.0
                    p_tok = getattr(response.usage_metadata, 'prompt_token_count', 0) if hasattr(response, 'usage_metadata') else 0
                    o_tok = getattr(response.usage_metadata, 'candidates_token_count', 0) if hasattr(response, 'usage_metadata') else 0
                    text_out = response.text

                # Log to DB
                log_id = log_api_call(
                    model_name=model_choice,
                    prompt_tokens=p_tok,
                    output_tokens=o_tok,
                    latency_ms=latency,
                    status_code=200,
                    caller_info="Live Probe Test"
                )

                st.success(f"✅ 請求成功！(耗時: {latency:.1f} ms | Input: {p_tok} tokens | Output: {o_tok} tokens)")
                st.markdown("##### 💬 回應內容:")
                st.write(text_out)
                st.rerun()

            except Exception as ex:
                latency = (time.time() - t0) * 1000.0
                status_code = 429 if "429" in str(ex) or "Quota" in str(ex) else 500
                log_api_call(
                    model_name=model_choice,
                    prompt_tokens=0,
                    output_tokens=0,
                    latency_ms=latency,
                    status_code=status_code,
                    error_message=str(ex),
                    caller_info="Live Probe Test Error"
                )
                st.error(f"❌ 請求失敗 (狀態碼 {status_code}): {ex}")
