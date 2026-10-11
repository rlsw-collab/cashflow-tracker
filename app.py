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
        margin-bottom: 5px;
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

# -----------------------------------------------------------------------------
# Session State 初始化數據結構
# -----------------------------------------------------------------------------
if "base_initial_balance" not in st.session_state:
    st.session_state["base_initial_balance"] = 109274.0

if "balance_overrides" not in st.session_state:
    st.session_state["balance_overrides"] = {}  # {date: new_start_balance}

if "items_list" not in st.session_state:
    # 預設項目資料
    st.session_state["items_list"] = [
        {"id": 1, "name": "Salary", "amount": 71232.0, "start_date": datetime.date(2026, 2, 23), "recursive": False, "end_date": None},
        {"id": 2, "name": "Octopus", "amount": -200.0, "start_date": datetime.date(2026, 2, 4), "recursive": False, "end_date": None},
        {"id": 3, "name": "Cheque 3920", "amount": -2160.0, "start_date": datetime.date(2026, 2, 4), "recursive": False, "end_date": None},
        {"id": 4, "name": "Medical", "amount": 410.0, "start_date": datetime.date(2026, 2, 5), "recursive": False, "end_date": None},
        {"id": 5, "name": "HSBC RED", "amount": -7240.0, "start_date": datetime.date(2026, 2, 7), "recursive": False, "end_date": None},
        {"id": 6, "name": "HSBC EVERYDAY", "amount": -4571.0, "start_date": datetime.date(2026, 2, 7), "recursive": False, "end_date": None},
        {"id": 7, "name": "HSBC VISA", "amount": -4964.0, "start_date": datetime.date(2026, 2, 7), "recursive": False, "end_date": None},
        {"id": 8, "name": "HSBC EASY", "amount": -1058.0, "start_date": datetime.date(2026, 2, 7), "recursive": False, "end_date": None},
        {"id": 9, "name": "HSBC Premier", "amount": -3867.0, "start_date": datetime.date(2026, 2, 7), "recursive": False, "end_date": None},
    ]

# -----------------------------------------------------------------------------
# 控制選單：查看開始日期與顯示月數
# -----------------------------------------------------------------------------
col_start, col_months = st.columns(2)

with col_start:
    start_view_date = st.date_input("查看開始日期:", value=datetime.date.today())

with col_months:
    months_offset = st.number_input("顯示月數 (範圍: -12 至 12 個月):", value=1, min_value=-12, max_value=12, step=1)

# 計算對應的開始與結束日期
monday_start = start_view_date - datetime.timedelta(days=start_view_date.weekday())

if months_offset >= 0:
    target_end_date = monday_start + relativedelta(months=months_offset)
    calc_start = monday_start
    calc_end = target_end_date
else:
    target_start_date = monday_start + relativedelta(months=months_offset)
    calc_start = target_start_date - datetime.timedelta(days=target_start_date.weekday())
    calc_end = monday_start + datetime.timedelta(days=6)

# 補齊天數至滿一整週 (以週日結尾)
total_days = (calc_end - calc_start).days + 1
if total_days % 7 != 0:
    total_days += (7 - (total_days % 7))

date_range = [calc_start + datetime.timedelta(days=i) for i in range(total_days)]

# -----------------------------------------------------------------------------
# 現金流計算 (含 Start Balance 手動覆蓋 & Item 計算)
# -----------------------------------------------------------------------------
daily_items = {d: [] for d in date_range}
daily_change = {d: 0.0 for d in date_range}

for item in st.session_state["items_list"]:
    name = item["name"]
    amt = item["amount"]
    s_date = item["start_date"]
    is_rec = item["recursive"]
    e_date = item.get("end_date")

    if not is_rec:
        if s_date in daily_items:
            daily_items[s_date].append(item)
            daily_change[s_date] += amt
    else:
        if not e_date:
            e_date = date_range[-1]
        curr = s_date
        while curr <= e_date and curr <= date_range[-1]:
            if curr in daily_items:
                daily_items[curr].append(item)
                daily_change[curr] += amt
            curr += relativedelta(months=1)

# 計算每日 Start Balance 與 End Balance
daily_start_balance = {}
daily_end_balance = {}

current_bal = st.session_state["base_initial_balance"]

for d in date_range:
    if d in st.session_state["balance_overrides"]:
        current_bal = st.session_state["balance_overrides"][d]

    daily_start_balance[d] = current_bal
    end_bal = current_bal + daily_change[d]
    daily_end_balance[d] = end_bal
    current_bal = end_bal

# 赤字警示
neg_days = [d for d, bal in daily_end_balance.items() if bal < 0]
if neg_days:
    first_neg = neg_days[0]
    st.error(f"🚨 **警告：預計於 `{first_neg.strftime('%d/%m/%Y')}` 戶口結餘出現赤字 (${daily_end_balance[first_neg]:,.0f})！**")
else:
    st.success("✅ 所選預測期間內戶口結餘維持正常。")

# -----------------------------------------------------------------------------
# 渲染日曆看板 (以 7 天為一列，標頭附帶星期縮寫)
# -----------------------------------------------------------------------------
st.subheader("📅 日曆收支與結餘看板")

weekday_map = {0: "M", 1: "T", 2: "W", 3: "T", 4: "F", 5: "S", 6: "S"}
total_weeks = len(date_range) // 7

for w in range(total_weeks):
    week_cols = st.columns(7)
    for day_idx in range(7):
        current_date = date_range[w * 7 + day_idx]
        
        day_code = weekday_map[current_date.weekday()]
        date_str = f"{current_date.strftime('%d/%m/%Y')} ({day_code})"
        
        items = daily_items.get(current_date, [])
        start_bal = daily_start_balance.get(current_date, 0.0)
        end_bal = daily_end_balance.get(current_date, 0.0)
        
        # 修正此處的 HTML 拼字字串 (避免在 f-string 內部使用跳脫字元 \ )
        items_html = ""
        for item in items:
            item_name = item["name"]
            amt = item["amount"]
            amt_class = "amount-neg" if amt < 0 else "amount-pos"
            items_html += f"<div class='item-row'><span class='item-name' title='{item_name}'>{item_name}</span><span class='{amt_class}'>{amt:,.0f}</span></div>"
        
        box_class = "day-box neg-balance-box" if end_bal < 0 else "day-box"
        
        card_html = (
            f"<div class='{box_class}'>"
            f"<div class='day-header'>{date_str}</div>"
            f"<div class='start-balance'><span>Start Bal</span><span>{start_bal:,.0f}</span></div>"
            f"<div class='day-content'>{items_html}</div>"
            f"<div class='end-balance'><span>End Balance</span><span>{end_bal:,.0f}</span></div>"
            f"</div>"
        )
        
        with week_cols[day_idx]:
            st.markdown(card_html, unsafe_allow_html=True)
            
            with st.popover("✏️ 編輯該日", use_container_width=True):
                st.caption(f"📅 **修改 {date_str} 資料**")
                
                # 1. 修改當日 Start Balance
                new_start = st.number_input(
                    "修改當日 Start Balance:",
                    value=float(start_bal),
                    key=f"sb_{current_date}"
                )
                if st.button("儲存 Start Balance", key=f"btn_sb_{current_date}"):
                    st.session_state["balance_overrides"][current_date] = new_start
                    st.rerun()

                st.divider()
                
                # 2. 新增當日收支項目
                st.markdown("**➕ 新增當日項目**")
                add_name = st.text_input("項目名稱:", key=f"an_{current_date}")
                add_amt = st.number_input("金額 (+收入/-支出):", value=0.0, key=f"aa_{current_date}")
                add_rec = st.checkbox("每月重複?", key=f"ar_{current_date}")
                
                if st.button("新增項目", key=f"btn_add_{current_date}"):
                    if add_name.strip():
                        new_id = max([x["id"] for x in st.session_state["items_list"]], default=0) + 1
                        st.session_state["items_list"].append({
                            "id": new_id,
                            "name": add_name,
                            "amount": add_amt,
                            "start_date": current_date,
                            "recursive": add_rec,
                            "end_date": None
                        })
                        st.rerun()

                # 3. 刪除已有項目
                if items:
                    st.divider()
                    st.markdown("**🗑️ 刪除當日項目**")
                    for it in items:
                        col_it1, col_it2 = st.columns([3, 1])
                        col_it1.write(f"{it['name']}: `${it['amount']:,.0f}`")
                        if col_it2.button("刪除", key=f"del_{current_date}_{it['id']}"):
                            st.session_state["items_list"] = [x for x in st.session_state["items_list"] if x["id"] != it["id"]]
                            st.rerun()
