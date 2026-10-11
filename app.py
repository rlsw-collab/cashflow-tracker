import streamlit as st
import pandas as pd
import datetime
import json
import os
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="個人財務現金流與日曆預測", layout="wide")

st.title("💰 個人財務現金流與結餘預測")

DATA_FILE = "data.json"

# -----------------------------------------------------------------------------
# 1. 檔案持久化讀寫邏輯 (JSON 儲存，關閉瀏覽器資料絕不遺失)
# -----------------------------------------------------------------------------
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 轉回 dataframe 格式
                df = pd.DataFrame(data.get("items", []))
                if not df.empty and "start_date" in df.columns:
                    df["start_date"] = pd.to_datetime(df["start_date"]).dt.date
                return df, data.get("base_initial_balance", 109274.0)
        except Exception:
            pass

    # 預設 initial 數據
    default_items = pd.DataFrame([
        {"id": 1, "name": "Salary", "amount": 70000.0, "start_date": datetime.date(2026, 10, 5), "recursive": True},
        {"id": 2, "name": "Octopus", "amount": -200.0, "start_date": datetime.date(2026, 10, 6), "recursive": False},
        {"id": 3, "name": "Medical", "amount": 410.0, "start_date": datetime.date(2026, 10, 7), "recursive": False},
    ])
    return default_items, 109274.0

def save_data(df, base_bal):
    df_copy = df.copy()
    if not df_copy.empty and "start_date" in df_copy.columns:
        df_copy["start_date"] = df_copy["start_date"].astype(str)
    
    save_content = {
        "base_initial_balance": base_bal,
        "items": df_copy.to_dict("records")
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(save_content, f, ensure_ascii=False, indent=2)

# 初始化載入數據
if "items_df" not in st.session_state or "base_initial_balance" not in st.session_state:
    items_df, base_bal = load_data()
    st.session_state["items_df"] = items_df
    st.session_state["base_initial_balance"] = base_bal

if "view_date" not in st.session_state:
    st.session_state["view_date"] = datetime.date.today()

# -----------------------------------------------------------------------------
# 2. 控制頂欄 (含 TODAY 按鈕、預設前後 12 個月)
# -----------------------------------------------------------------------------
col_today, col_start, col_months, col_bal = st.columns([1.5, 2, 2, 2])

with col_today:
    st.write(" ")
    st.write(" ")
    if st.button("📅 TODAY (跳至今日)", use_container_width=True):
        st.session_state["view_date"] = datetime.date.today()
        st.rerun()

with col_start:
    start_view_date = st.date_input("查看基準日期:", value=st.session_state["view_date"], key="input_view_date")
    st.session_state["view_date"] = start_view_date

with col_months:
    # 預設為 12 個月 (前後各 12 個月，共 25 個月全景)
    months_offset = st.number_input("顯示月數範圍 (前後月數):", value=12, min_value=1, max_value=24, step=1)

with col_bal:
    init_bal = st.number_input("起始戶口結餘 ($):", value=st.session_state["base_initial_balance"], step=1000.0)
    if init_bal != st.session_state["base_initial_balance"]:
        st.session_state["base_initial_balance"] = init_bal
        save_data(st.session_state["items_df"], init_bal)
        st.rerun()

# -----------------------------------------------------------------------------
# 3. 直覺收支項目編輯器 (支援 Drag & Drop、批次複製貼上、格仔直接改金額/名稱)
# -----------------------------------------------------------------------------
with st.expander("📝 收支項目列表編輯器 (支援 Drag & Drop 拖曳 / 格仔直接修改 / 批次新增與刪除)", expanded=True):
    edited_df = st.data_editor(
        st.session_state["items_df"],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "id": None,
            "name": st.column_config.TextColumn("項目名稱 (Item Name)", required=True),
            "amount": st.column_config.NumberColumn("金額 (+收入/-支出)", required=True, format="$%d"),
            "start_date": st.column_config.DateColumn("日期 (Date)", required=True),
            "recursive": st.column_config.CheckboxColumn("每月重複 (Recursive)?", default=False),
        },
        key="main_editor"
    )
    
    # 檢查數據是否有變更，有變更時立刻儲存至 data.json 檔案
    if not edited_df.equals(st.session_state["items_df"]):
        st.session_state["items_df"] = edited_df
        save_data(edited_df, st.session_state["base_initial_balance"])
        st.rerun()

# -----------------------------------------------------------------------------
# 4. 現金流與連動結餘計算邏輯
# -----------------------------------------------------------------------------
today = start_view_date
calc_start_date = today - relativedelta(months=months_offset)
calc_end_date = today + relativedelta(months=months_offset)

calc_start = calc_start_date - datetime.timedelta(days=calc_start_date.weekday())
calc_end = calc_end_date + datetime.timedelta(days=(6 - calc_end_date.weekday()))

total_days = (calc_end - calc_start).days + 1
date_range = [calc_start + datetime.timedelta(days=i) for i in range(total_days)]
date_strs = [d.strftime("%Y-%m-%d") for d in date_range]

daily_items = {d_str: [] for d_str in date_strs}
daily_change = {d_str: 0.0 for d_str in date_strs}

# 展開計算所有項目
for _, row in st.session_state["items_df"].iterrows():
    name = row.get("name")
    amt = row.get("amount")
    s_date = row.get("start_date")
    is_rec = row.get("recursive", False)

    if pd.isna(name) or pd.isna(amt) or pd.isna(s_date):
        continue

    amt = float(amt)
    if isinstance(s_date, pd.Timestamp) or isinstance(s_date, datetime.datetime):
        s_date = s_date.date()
    s_date_str = s_date.strftime("%Y-%m-%d")

    if not is_rec:
        if s_date_str in daily_items:
            daily_items[s_date_str].append((name, amt))
            daily_change[s_date_str] += amt
    else:
        curr = s_date
        while curr <= date_range[-1]:
            curr_str = curr.strftime("%Y-%m-%d")
            if curr_str in daily_items:
                daily_items[curr_str].append((name, amt))
                daily_change[curr_str] += amt
            curr += relativedelta(months=1)

# 連動算每日 Start & End Balance
daily_start_bal = {}
daily_end_bal = {}
curr_bal = st.session_state["base_initial_balance"]

for d_str in date_strs:
    daily_start_bal[d_str] = curr_bal
    end_b = curr_bal + daily_change[d_str]
    daily_end_bal[d_str] = end_b
    curr_bal = end_b

# 赤字警示
neg_days = [d for d, bal in daily_end_bal.items() if bal < 0]
if neg_days:
    st.error(f"🚨 **赤字警告：預計於 `{neg_days[0]}` 戶口結餘將出現赤字 (${daily_end_bal[neg_days[0]]:,.0f})！**")

# -----------------------------------------------------------------------------
# 5. 日曆現金流看板 (卡片風格、今日橙色標頭、正綠負紅)
# -----------------------------------------------------------------------------
st.subheader("📅 日曆現金流看板")

st.markdown("""
<style>
    .day-box {
        border: 1px solid #d0d0d0;
        border-radius: 5px;
        margin-bottom: 8px;
        background-color: #ffffff;
        min-height: 155px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .day-header {
        background-color: #1F3864;
        color: white;
        text-align: center;
        font-weight: bold;
        padding: 4px 2px;
        font-size: 13px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    .day-header.today-header {
        background-color: #FF8C00 !important;
    }
    .start-balance {
        background-color: #EBF1F5;
        border-bottom: 1px solid #d0d0d0;
        padding: 2px 6px;
        display: flex;
        justify-content: space-between;
        font-size: 11px;
        color: #444;
    }
    .day-content {
        padding: 6px;
        font-size: 12px;
        flex-grow: 1;
    }
    .item-row {
        display: flex;
        justify-content: space-between;
        margin-bottom: 3px;
        font-family: monospace;
    }
    .item-name {
        color: #333;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 80px;
    }
    .amount-pos { color: #2E7D32; font-weight: bold; }
    .amount-neg { color: #D9534F; font-weight: bold; }
    .end-balance {
        background-color: #F2F2F2;
        border-top: 1px solid #d0d0d0;
        padding: 4px 6px;
        display: flex;
        justify-content: space-between;
        font-size: 11px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

today_str = datetime.date.today().strftime("%Y-%m-%d")
weekday_map = {0: "M", 1: "T", 2: "W", 3: "T", 4: "F", 5: "S", 6: "S"}
total_weeks = len(date_range) // 7

for w in range(total_weeks):
    week_cols = st.columns(7)
    for day_idx in range(7):
        current_date = date_range[w * 7 + day_idx]
        d_str = current_date.strftime("%Y-%m-%d")
        
        day_code = weekday_map[current_date.weekday()]
        date_str = f"{current_date.strftime('%d/%m/%Y')} ({day_code})"
        
        items = daily_items.get(d_str, [])
        start_b = daily_start_bal.get(d_str, 0.0)
        end_b = daily_end_bal.get(d_str, 0.0)
        
        # 組合當日項目的 HTML
        items_html = ""
        for item_name, amt in items:
            amt_class = "amount-neg" if amt < 0 else "amount-pos"
            items_html += f"<div class='item-row'><span class='item-name' title='{item_name}'>{item_name}</span><span class='{amt_class}'>{amt:+,.0f}</span></div>"
        
        # 今日 Header 橙色高亮
        header_class = "day-header today-header" if d_str == today_str else "day-header"
        end_bal_class = "amount-neg" if end_b < 0 else "amount-pos"
        
        card_html = (
            f"<div class='day-box'>"
            f"<div class='{header_class}'>{date_str}</div>"
            f"<div class='start-balance'><span>Start Bal</span><span>{start_b:,.0f}</span></div>"
            f"<div class='day-content'>{items_html}</div>"
            f"<div class='end-balance'><span>End Balance</span><span class='{end_bal_class}'>{end_b:,.0f}</span></div>"
            f"</div>"
        )
        
        week_cols[day_idx].markdown(card_html, unsafe_allow_html=True)
