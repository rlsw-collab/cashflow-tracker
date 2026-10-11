import streamlit as st
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="個人財務現金流與日曆預測", layout="wide")

st.title("💰 個人財務現金流與結餘預測")

# -----------------------------------------------------------------------------
# 1. Session State 初始化數據
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
    st.write(" ") # 垂直對齊
    st.write(" ")
    # 需求：點擊 "TODAY" 按鈕立刻跳回今日
    if st.button("📅 TODAY (回到今日)", use_container_width=True):
        st.session_state["view_date"] = datetime.date.today()
        st.rerun()

with col_start:
    start_view_date = st.date_input("查看開始日期:", value=st.session_state["view_date"], key="input_view_date")
    st.session_state["view_date"] = start_view_date

with col_months:
    months_offset = st.number_input("顯示月數 (範圍: -12 至 12 個月):", value=1, min_value=-12, max_value=12, step=1)

# -----------------------------------------------------------------------------
# 3. 直覺試算表 - 可直接在表格修改 (In-place Editing) 與 Drag & Drop
# -----------------------------------------------------------------------------
st.subheader("📋 收支清單編輯器 (可直接於格仔內修改、拖曳/複製貼上)")

# 將 Data 轉為 DataFrame 供編輯器使用
raw_df = pd.DataFrame(st.session_state["items_list"])

# 需求：直接在網格內修改，無需彈出新視窗
edited_df = st.data_editor(
    raw_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "id": None, # 隱藏 ID
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

# 同步更新 session_state
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
            daily_items[s_date].append(f"{name}: {amt:+,.0f}")
            daily_change[s_date] += amt
    else:
        curr = s_date
        while curr <= date_range[-1]:
            if curr in daily_items:
                daily_items[curr].append(f"{name}: {amt:+,.0f}")
                daily_change[curr] += amt
            curr += relativedelta(months=1)

# 計算每日 Balance
daily_start_bal = {}
daily_end_bal = {}
curr_bal = 109274.0 # 預設起始值

for d in date_range:
    daily_start_bal[d] = curr_bal
    end_b = curr_bal + daily_change[d]
    daily_end_bal[d] = end_b
    curr_bal = end_b

# 赤字警示
neg_days = [d for d, bal in daily_end_bal.items() if bal < 0]
if neg_days:
    first_neg = neg_days[0]
    st.error(f"🚨 **警告：預計於 `{first_neg.strftime('%d/%m/%Y')}` 戶口結餘出現赤字 (${daily_end_bal[first_neg]:,.0f})！**")
else:
    st.success("✅ 所選預測期間內戶口結餘維持正常。")

# -----------------------------------------------------------------------------
# 5. 日曆看板展示 (含正數綠色、負數紅色樣式)
# -----------------------------------------------------------------------------
st.subheader("📅 日曆現金流看板")

weekday_map = {0: "M", 1: "T", 2: "W", 3: "T", 4: "F", 5: "S", 6: "S"}

# 建立日曆視覺化表格數據
calendar_rows = []
total_weeks = len(date_range) // 7

for w in range(total_weeks):
    start_row = {"Row_Type": "Start Balance"}
    items_row = {"Row_Type": "Items"}
    end_row = {"Row_Type": "End Balance"}
    
    for day_idx in range(7):
        current_date = date_range[w * 7 + day_idx]
        col_name = f"{current_date.strftime('%d/%m/%Y')} ({weekday_map[current_date.weekday()]})"
        
        start_row[col_name] = daily_start_bal[current_date]
        items_row[col_name] = "\n".join(daily_items[current_date]) if daily_items[current_date] else "-"
        end_row[col_name] = daily_end_bal[current_date]
        
    calendar_rows.extend([start_row, items_row, end_row])

cal_df = pd.DataFrame(calendar_rows).set_index("Row_Type")

# 需求：正數顯示綠色 (Green)，負數顯示紅色 (Red)
def highlight_amounts(val):
    if isinstance(val, (int, float)):
        if val < 0:
            return "color: #D9534F; font-weight: bold; background-color: #FFECEC;"
        elif val > 0:
            return "color: #2E7D32; font-weight: bold;"
    return ""

st.dataframe(
    cal_df.style.map(highlight_amounts),
    use_container_width=True,
    height=450
)
