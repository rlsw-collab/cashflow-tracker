import streamlit as st
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta
import plotly.express as px

# 頁面基本設定
st.set_page_config(page_title="個人財務現金流預測", layout="wide")

st.title("💰 個人財務現金流與結餘預測工具")

# 初始化 Session State 儲存資料
if "items" not in st.session_state:
    st.session_state.items = []

# -----------------------------------------------------------------------------
# 1. 側邊欄：輸入收入與支出項目
# -----------------------------------------------------------------------------
st.sidebar.header("➕ 新增收支項目")

item_name = st.sidebar.text_input("項目名稱 (Item Name)", value="")
item_amount = st.sidebar.number_input("金額 (Item Amount)", value=0.0, step=100.0, help="正數為收入，負數為支出")
item_date = st.sidebar.date_input("開始日期 (Item Date)", value=datetime.date.today())
is_recursive = st.sidebar.checkbox("每月重複 (Monthly Recursive)", value=False)

end_date = None
if is_recursive:
    end_date = st.sidebar.date_input("結束日期 (End Date)", value=datetime.date.today() + relativedelta(years=1))

if st.sidebar.button("新增項目"):
    if item_name.strip() == "":
        st.sidebar.error("請輸入項目名稱！")
    else:
        st.session_state.items.append({
            "name": item_name,
            "amount": item_amount,
            "start_date": item_date,
            "is_recursive": is_recursive,
            "end_date": end_date
        })
        st.sidebar.success(f"已新增：{item_name}")

# -----------------------------------------------------------------------------
# 2. 顯示與管理已輸入的項目
# -----------------------------------------------------------------------------
st.subheader("📋 已設定收支項目")

if st.session_state.items:
    items_df = pd.DataFrame(st.session_state.items)
    st.dataframe(items_df, use_container_width=True)
    
    if st.button("清空所有項目"):
        st.session_state.items = []
        st.experimental_rerun()
else:
    st.info("目前尚未建立任何收支項目，請由左側邊欄新增。")

# -----------------------------------------------------------------------------
# 3. 現金流與每日結餘計算邏輯
# -----------------------------------------------------------------------------
st.subheader("📊 財務預測與警示")

# 設定預設初始戶口結餘與預測時間範圍
col1, col2, col3 = st.columns(3)
with col1:
    initial_balance = st.number_input("目前戶口初始結餘 ($):", value=10000.0, step=1000.0)
with col2:
    forecast_days = st.number_input("預測天數 (天):", value=180, min_value=30, max_value=730)

if st.session_state.items:
    start_sim_date = datetime.date.today()
    end_sim_date = start_sim_date + datetime.timedelta(days=int(forecast_days))
    
    # 建立每日日期範圍
    date_range = pd.date_range(start=start_sim_date, end=end_sim_date)
    daily_df = pd.DataFrame({"Date": date_range.date})
    daily_df["Daily_Change"] = 0.0
    
    # 展開所有明細到具體日期
    for item in st.session_state.items:
        amt = item["amount"]
        s_date = item["start_date"]
        
        if not item["is_recursive"]:
            # 單次收支
            daily_df.loc[daily_df["Date"] == s_date, "Daily_Change"] += amt
        else:
            # 每月重複收支
            e_date = item["end_date"]
            curr = s_date
            while curr <= e_date and curr <= end_sim_date:
                if curr >= start_sim_date:
                    daily_df.loc[daily_df["Date"] == curr, "Daily_Change"] += amt
                curr += relativedelta(months=1)

    # 計算累計每日結餘
    daily_df["Balance"] = initial_balance + daily_df["Daily_Change"].cumsum()

    # 檢查入不敷出（結餘出現負數）的日期
    negative_balances = daily_df[daily_df["Balance"] < 0]
    
    if not negative_balances.empty:
        first_negative_date = negative_balances.iloc[0]["Date"]
        first_negative_bal = negative_balances.iloc[0]["Balance"]
        st.error(f"⚠️ **警告：預計於 `{first_negative_date}` 戶口結餘將出現負數 (${first_negative_bal:,.2f})！**")
    else:
        st.success("✅ 在預測期間內，戶口結餘維持正常，未出現赤字。")

    # 折線圖顯示結餘走勢
    fig = px.line(
        daily_df, 
        x="Date", 
        y="Balance", 
        title="每日預測戶口結餘走勢",
        labels={"Balance": "戶口結餘 ($)", "Date": "日期"}
    )
    # 加入 0 元紅線標示赤字警戒線
    fig.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="赤字線 (0元)")
    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------------------------------
    # 4. 日曆/明細檢視 (Calendar / Daily View)
    # -----------------------------------------------------------------------------
    st.subheader("🗓️ 每日結餘明細表")
    st.dataframe(
        daily_df.style.applymap(
            lambda val: "background-color: #ffcccc" if val < 0 else "", 
            subset=["Balance"]
        ),
        use_container_width=True
    )