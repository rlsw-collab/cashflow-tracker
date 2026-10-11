import streamlit as st
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="個人財務現金流與日曆預測", layout="wide")

st.title("💰 個人財務現金流與結餘預測")

# -----------------------------------------------------------------------------
# 1. Session State 初始化數據結構
# -----------------------------------------------------------------------------
if "view_date" not in st.session_state:
    st.session_state["view_date"] = datetime.date.today()

if "items_list" not in st.session_state:
    st.session_state["items_list"] = [
        {"id": 1, "name": "Salary", "amount": 71232.0, "start_date": datetime.date(2026, 2, 23), "recursive": False},
        {"id": 2, "name": "Octopus", "amount": -200.0, "start_date": datetime.date(2026, 2, 4), "recursive": False},
        {"id": 3, "name": "Cheque 3920", "amount": -2160.0, "start_date": datetime.date(2026, 2, 4), "recursive": False},
        {"id": 4, "name": "Medical", "amount": 410.0, "start_date": datetime.date(2026, 2, 5), "recursive": False},
        {"id": 5, "name": "HSBC RED", "amount": -7240.0, "start_date": datetime.date(2026, 2, 7), "recursive": False},
        {"id": 6, "name": "HSBC EVERYDAY", "amount": -4571.0, "start_date": datetime.date(2026, 2, 7), "recursive": False},
        {"id": 7, "name": "HSBC VISA", "amount": -4964.0, "start_date": datetime.date(2026, 2, 7), "recursive": False},
        {"id": 8, "name": "HSBC EASY", "amount": -1058.0, "start_date": datetime.date(2026, 2, 7), "recursive": False},
        {"id": 9, "name": "HSBC Premier", "amount": -3867.0, "start_date": datetime.date(2026, 2, 7), "recursive": False},
    ]

# -----------------------------------------------------------------------------
# 2. 控制欄位 (含 TODAY 按鈕)
# -----------------------------------------------------------------------------
col_today, col_start, col_months = st.columns([1, 2, 2])

with col_today:
    st.write(" ")
    st.write(" ")
    if st.button("📅 TODAY (回到今日)", use_container_width=True):
        st.session_state["view_date"] = datetime.date.today()
        st.rerun()

with col_start:
    start_view_date = st.date_input("查看開始日期:", value=st.session_state["view_date"], key="input_view_date")
    st.session_state["view_date"] = start_view_date

with col_months:
    months_offset = st.number_input("顯示月數 (範圍: -12 至 12 個月):", value=1, min_value=-12, max_value=12, step=1)

# -----------------------------------------------------------------------------
# 3. 直覺試算表 (支援格仔內直接修改與 Drag & Drop)
# -----------------------------------------------------------------------------
st.subheader("📋 收支清單編輯器 (可直接於格仔內修改、拖曳/複製貼上)")

raw_df = pd.DataFrame(st.session_state["items_list"])

edited_df = st.data_editor(
    raw_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "id": None,
        "name": st.column_config.TextColumn("項目名稱 (Item Name)", required=True),
        "amount": st.column_config.NumberColumn(
            "金額 (Amount)", 
            required=True, 
            format="$%d",
            help="正數為收入，負數為支出"
        ),
        "start_date": st.column_config.DateColumn("日期 (Date)", required=True),
        "recursive": st.column_config.CheckboxColumn("每月重複?", default=False),
    },
    key="main_data_editor"
)

updated_items = edited_df.to_dict("records")
st.session_state["items_list"] = updated_items

# -----------------------------------------------------------------------------
# 4. 試算每日 Start / End Balance
# -----------------------------------------------------------------------------
monday_start = start_view_date - datetime.timedelta(days=start_view_date.weekday())

if months_offset >= 0:
    target_end_date = monday_start + relativedelta(months=months_offset)
    calc_start = monday_start
    calc_end = target_end_date
else:
    target_start_date = monday_start + relativedelta(months=months_offset)
    calc_start = target_start_date - datetime.timedelta(days=target_start_date.weekday())
    calc_end = monday_start + datetime.timedelta(days=6)

total_days = (calc_end - calc_start).days + 1
if total_days % 7 != 0:
    total_days += (7 - (total_days % 7))

date_range = [calc_start + datetime.timedelta(days=i) for i in range(total_days)]

daily_items = {d: [] for d in date_range}
daily_change = {d: 0.0 for d in date_range}

for item in st.session_state["items_list"]:
    name = item.get("name")
    amt = item.get("amount")
    s_date = item.get("start_date")
    is_rec = item.get("recursive", False)

    if not name or pd.isna(amt) or not s_date:
        continue
        
    if isinstance(s_date, pd.Timestamp):
        s_date = s_date.date()
    amt = float(amt)

    if not is_rec:
        if s_date in daily_items:
            daily_items[s_date].append((name, amt))
            daily_change[s_date] += amt
    else:
        curr = s_date
        while curr <= date_range[-1]:
            if curr in daily_items:
                daily_items[curr].append((name, amt))
                daily_change[curr] += amt
            curr += relativedelta(months=1)

daily_start_bal = {}
daily_end_bal = {}
curr_bal = 109274.0

for d in date_range:
    daily_start_bal[d] = curr_bal
    end_b = curr_bal + daily_change[d]
    daily_end_bal[d] = end_b
    curr_bal = end_b

# -----------------------------------------------------------------------------
# 5. HTML 卡片網格 (修正 KeyError 並且兼顧正綠負紅、卡片 Layout)
# -----------------------------------------------------------------------------
st.subheader("📅 日曆現金流看板")

# CSS 樣式：正數綠色 (#2E7D32)，負數紅色 (#D9534F)
st.markdown("""
<style>
    .day-box {
        border: 1px solid #d0d0d0;
        border-radius: 4px;
        margin-bottom: 8px;
        background-color: #ffffff;
        min-height: 150px;
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
        border-top-left-radius: 3px;
        border-top-right-radius: 3px;
    }
    .start-balance {
        background-color: #EBF1F5;
        border-bottom: 1px solid #d0d0d0;
        padding: 2px 6px;
        display: flex;
        justify-content: space-between;
        font-size: 11px;
        color: #444444;
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
        max-width: 85px;
    }
    .amount-pos {
        color: #2E7D32;
        font-weight: bold;
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

weekday_map = {0: "M", 1: "T", 2: "W", 3: "T", 4: "F", 5: "S", 6: "S"}
total_weeks = len(date_range) // 7

for w in range(total_weeks):
    week_cols = st.columns(7)
    for day_idx in range(7):
        current_date = date_range[w * 7 + day_idx]
        
        day_code = weekday_map[current_date.weekday()]
        date_str = f"{current_date.strftime('%d/%m/%Y')} ({day_code})"
        
        items = daily_items.get(current_date, [])
        start_b = daily_start_bal.get(current_date, 0.0)
        end_b = daily_end_bal.get(current_date, 0.0)
        
        # 組合當日項目的 HTML，正數套用 amount-pos (綠色)，負數套用 amount-neg (紅色)
        items_html = ""
        for item_name, amt in items:
            amt_class = "amount-neg" if amt < 0 else "amount-pos"
            items_html += f"<div class='item-row'><span class='item-name' title='{item_name}'>{item_name}</span><span class='{amt_class}'>{amt:+,.0f}</span></div>"
        
        box_class = "day-box neg-balance-box" if end_b < 0 else "day-box"
        
        # End Balance 顏色判斷
        end_bal_class = "amount-neg" if end_b < 0 else "amount-pos"
        
        card_html = (
            f"<div class='{box_class}'>"
            f"<div class='day-header'>{date_str}</div>"
            f"<div class='start-balance'><span>Start Bal</span><span>{start_b:,.0f}</span></div>"
            f"<div class='day-content'>{items_html}</div>"
            f"<div class='end-balance'><span>End Balance</span><span class='{end_bal_class}'>{end_b:,.0f}</span></div>"
            f"</div>"
        )
        
        week_cols[day_idx].markdown(card_html, unsafe_allow_html=True)
