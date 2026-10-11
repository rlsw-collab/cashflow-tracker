import streamlit as st
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="個人財務現金流與日曆預測", layout="wide")

st.title("💰 個人財務現金流與結餘預測 (日曆 Layout)")

# 自訂 CSS 樣式
st.markdown("""
<style>
    .day-box {
        border: 1px solid #d0d0d0;
        border-radius: 4px;
        margin-bottom: 12px;
        background-color: #ffffff;
        min-height: 160px;
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
        color: #333333;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 90px;
    }
    .amount-pos {
        color: #000000;
        font-weight: 500;
    }
    .amount-neg {
        color: #D9534F;
        font-weight: bold;
    }
    .end-balance {
        background-color: #F2F2F2;
        border-top: 1px solid #d0d0d0;
        padding: 4px 6px;
        display: flex;
        justify-content: space-between;
        font-size: 11px;
        font-weight: bold;
    }
    .neg-balance-box {
        background-color: #FFECEC !important;
        border: 1px solid #FF4D4D !important;
    }
</style>
""", unsafe_allow_html=True)

# 初始化預設數據
default_data = pd.DataFrame([
    {"Item Name": "Salary", "Amount": 71232.0, "Start Date": datetime.date(2026, 2, 23), "Recursive": False, "End Date": None},
    {"Item Name": "Octopus", "Amount": -200.0, "Start Date": datetime.date(2026, 2, 4), "Recursive": False, "End Date": None},
    {"Item Name": "Cheque 3920", "Amount": -2160.0, "Start Date": datetime.date(2026, 2, 4), "Recursive": False, "End Date": None},
    {"Item Name": "Medical", "Amount": 410.0, "Start Date": datetime.date(2026, 2, 5), "Recursive": False, "End Date": None},
    {"Item Name": "HSBC RED", "Amount": -7240.0, "Start Date": datetime.date(2026, 2, 7), "Recursive": False, "End Date": None},
    {"Item Name": "HSBC EVERYDAY", "Amount": -4571.0, "Start Date": datetime.date(2026, 2, 7), "Recursive": False, "End Date": None},
    {"Item Name": "HSBC VISA", "Amount": -4964.0, "Start Date": datetime.date(2026, 2, 7), "Recursive": False, "End Date": None},
    {"Item Name": "HSBC EASY", "Amount": -1058.0, "Start Date": datetime.date(2026, 2, 7), "Recursive": False, "End Date": None},
    {"Item Name": "HSBC Premier", "Amount": -3867.0, "Start Date": datetime.date(2026, 2, 7), "Recursive": False, "End Date": None},
    {"Item Name": "Cheque 3920", "Amount": -100.0, "Start Date": datetime.date(2026, 2, 9), "Recursive": False, "End Date": None},
    {"Item Name": "Hazel Sch Bus", "Amount": -1370.0, "Start Date": datetime.date(2026, 2, 13), "Recursive": False, "End Date": None},
    {"Item Name": "HSB Enjoy", "Amount": -1266.0, "Start Date": datetime.date(2026, 2, 16), "Recursive": False, "End Date": None},
    {"Item Name": "ATM", "Amount": -800.0, "Start Date": datetime.date(2026, 2, 16), "Recursive": False, "End Date": None},
    {"Item Name": "Helper Salary", "Amount": -5000.0, "Start Date": datetime.date(2026, 2, 19), "Recursive": False, "End Date": None},
    {"Item Name": "BoC Taobao", "Amount": -868.0, "Start Date": datetime.date(2026, 2, 20), "Recursive": False, "End Date": None},
    {"Item Name": "Mortgage", "Amount": -21705.0, "Start Date": datetime.date(2026, 2, 25), "Recursive": False, "End Date": None},
    {"Item Name": "SCB Cathy", "Amount": -60500.0, "Start Date": datetime.date(2026, 2, 26), "Recursive": False, "End Date": None},
    {"Item Name": "Adjust", "Amount": -1.0, "Start Date": datetime.date(2026, 2, 26), "Recursive": False, "End Date": None},
    {"Item Name": "Tax Repay", "Amount": -16757.0, "Start Date": datetime.date(2026, 2, 27), "Recursive": False, "End Date": None},
    {"Item Name": "DBS Compass", "Amount": -695.0, "Start Date": datetime.date(2026, 2, 27), "Recursive": False, "End Date": None},
    {"Item Name": "Interest", "Amount": 82.0, "Start Date": datetime.date(2026, 2, 28), "Recursive": False, "End Date": None},
    {"Item Name": "WLB", "Amount": 1.0, "Start Date": datetime.date(2026, 2, 28), "Recursive": False, "End Date": None},
])

# -----------------------------------------------------------------------------
# 1. 編輯收支項目
# -----------------------------------------------------------------------------
with st.expander("⚙️ 點擊編輯收支項目 (Item Name, Amount, Date, Recursive)", expanded=False):
    edited_df = st.data_editor(
        st.session_state.get("items_df", default_data),
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Item Name": st.column_config.TextColumn("項目名稱", required=True),
            "Amount": st.column_config.NumberColumn("金額 (+收入/-支出)", required=True, format="$%d"),
            "Start Date": st.column_config.DateColumn("開始日期", required=True),
            "Recursive": st.column_config.CheckboxColumn("每月重複?", default=False),
            "End Date": st.column_config.DateColumn("結束日期"),
        },
        key="editor"
    )
    st.session_state["items_df"] = edited_df

# -----------------------------------------------------------------------------
# 2. 控制參數設定
# -----------------------------------------------------------------------------
col_a, col_b, col_c = st.columns(3)
with col_a:
    initial_balance = st.number_input("目前戶口初始結餘 ($):", value=109274.0, step=1000.0)
with col_b:
    start_view_date = st.date_input("查看開始日期:", value=datetime.date(2026, 2, 2))
with col_c:
    weeks_to_show = st.number_input("顯示週數:", value=5, min_value=1, max_value=20)

# 調整為對應週的「星期一」
monday_start = start_view_date - datetime.timedelta(days=start_view_date.weekday())
total_days = weeks_to_show * 7
end_view_date = monday_start + datetime.timedelta(days=total_days - 1)

# -----------------------------------------------------------------------------
# 3. 試算每日變動與結餘
# -----------------------------------------------------------------------------
date_range = [monday_start + datetime.timedelta(days=i) for i in range(total_days)]
daily_items = {d: [] for d in date_range}
daily_change = {d: 0.0 for d in date_range}

if not edited_df.empty:
    for _, row in edited_df.iterrows():
        name = row["Item Name"]
        amt = row["Amount"]
        s_date = row["Start Date"]
        is_rec = row["Recursive"]
        e_date = row["End Date"]
        
        if pd.isna(name) or pd.isna(amt) or pd.isna(s_date):
            continue
            
        amt = float(amt)
        if isinstance(s_date, pd.Timestamp):
            s_date = s_date.date()

        if not is_rec:
            if s_date in daily_items:
                daily_items[s_date].append((name, amt))
                daily_change[s_date] += amt
        else:
            if pd.isna(e_date):
                e_date = end_view_date
            elif isinstance(e_date, pd.Timestamp):
                e_date = e_date.date()
                
            curr = s_date
            while curr <= e_date and curr <= end_view_date:
                if curr in daily_items:
                    daily_items[curr].append((name, amt))
                    daily_change[curr] += amt
                curr += relativedelta(months=1)

# 計算每日累積結餘
daily_balance = {}
current_bal = initial_balance
for d in date_range:
    current_bal += daily_change[d]
    daily_balance[d] = current_bal

# 檢查赤字
neg_days = [d for d, bal in daily_balance.items() if bal < 0]
if neg_days:
    first_neg = neg_days[0]
    st.error(f"🚨 **警告：預計於 `{first_neg.strftime('%d/%m/%Y')}` 戶口結餘出現赤字 (${daily_balance[first_neg]:,.0f})！**")
else:
    st.success("✅ 所選預測期間內戶口結餘維持正常。")

# -----------------------------------------------------------------------------
# 4. 日曆 Layout 渲染
# -----------------------------------------------------------------------------
st.subheader("📅 日曆收支與結餘看板")

# 渲染 MON - SUN 標頭
weekdays = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
cols = st.columns(7)
for idx, day_name in enumerate(weekdays):
    cols[idx].markdown(
        f"<div style='text-align:center; font-weight:bold; background-color:#1F3864; color:white; padding:4px; border-radius:3px; font-size:14px;'>{day_name}</div>", 
        unsafe_allow_html=True
    )

st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

# 按週渲染每日卡片
for w in range(weeks_to_show):
    week_cols = st.columns(7)
    for day_idx in range(7):
        current_date = monday_start + datetime.timedelta(days=w * 7 + day_idx)
        date_str = current_date.strftime("%d/%m/%Y")
        items = daily_items.get(current_date, [])
        bal = daily_balance.get(current_date, 0.0)
        
        # 組合當天收支項目的 HTML
        items_html = ""
        for item_name, amt in items:
            amt_class = "amount-neg" if amt < 0 else "amount-pos"
            items_html += f"<div class='item-row'><span class='item-name' title='{item_name}'>{item_name}</span><span class='{amt_class}'>{amt:,.0f}</span></div>"
        
        # 決定卡片背景色
        box_class = "day-box neg-balance-box" if bal < 0 else "day-box"
        
        # 使用單一無換行的 HTML 字串避免渲染問題
        card_html = (
            f"<div class='{box_class}'>"
            f"<div class='day-header'>{date_str}</div>"
            f"<div class='day-content'>{items_html}</div>"
            f"<div class='end-balance'><span>End Balance</span><span>{bal:,.0f}</span></div>"
            f"</div>"
        )
        
        # 確保正確啟用 unsafe_allow_html
        week_cols[day_idx].markdown(card_html, unsafe_allow_html=True)
