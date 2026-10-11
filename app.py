import streamlit as st
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta
import plotly.express as px

st.set_page_config(page_title="個人財務現金流預測", layout="wide")

st.title("💰 個人財務現金流與結餘預測工具")

# 初始化預設數據結構
default_data = pd.DataFrame([
    {
        "Item Name": "薪水收入",
        "Amount": 30000.0,
        "Start Date": datetime.date.today(),
        "Recursive": True,
        "End Date": datetime.date.today() + relativedelta(years=1)
    },
    {
        "Item Name": "租金支出",
        "Amount": -12000.0,
        "Start Date": datetime.date.today(),
        "Recursive": True,
        "End Date": datetime.date.today() + relativedelta(years=1)
    }
])

# -----------------------------------------------------------------------------
# 1. 互動式收支管理表格 (類似 Excel 直覺編輯)
# -----------------------------------------------------------------------------
st.subheader("📋 收支項目清單 (可直接在下方表格修改、新增或刪除)")

# 使用 st.data_editor 提供像 Excel 般的編輯體驗
edited_df = st.data_editor(
    st.session_state.get("items_df", default_data),
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Item Name": st.column_config.TextColumn("項目名稱", required=True),
        "Amount": st.column_config.NumberColumn("金額 (+收入/-支出)", required=True, format="$%.2f"),
        "Start Date": st.column_config.DateColumn("開始日期", required=True),
        "Recursive": st.column_config.CheckboxColumn("每月重複?", default=False),
        "End Date": st.column_config.DateColumn("結束日期 (非重複可留空)"),
    },
    key="editor"
)

# 更新 session_state
st.session_state["items_df"] = edited_df

# -----------------------------------------------------------------------------
# 2. 現金流與每日結餘計算邏輯
# -----------------------------------------------------------------------------
st.subheader("📊 財務預測與赤字警示")

col1, col2 = st.columns(2)
with col1:
    initial_balance = st.number_input("目前戶口初始結餘 ($):", value=10000.0, step=1000.0)
with col2:
    forecast_days = st.number_input("預測天數 (天):", value=180, min_value=30, max_value=730)

if not edited_df.empty:
    start_sim_date = datetime.date.today()
    end_sim_date = start_sim_date + datetime.timedelta(days=int(forecast_days))
    
    # 建立每日日期範圍
    date_range = pd.date_range(start=start_sim_date, end=end_sim_date)
    daily_df = pd.DataFrame({"Date": date_range.date})
    daily_df["Daily_Change"] = 0.0
    
    # 計算收支明細到具體日期
    for _, row in edited_df.iterrows():
        name = row["Item Name"]
        amt = row["Amount"]
        s_date = row["Start Date"]
        is_rec = row["Recursive"]
        e_date = row["End Date"]
        
        # 排除空值或無效資料
        if pd.isna(name) or pd.isna(amt) or pd.isna(s_date):
            continue
            
        amt = float(amt)
        if isinstance(s_date, pd.Timestamp):
            s_date = s_date.date()

        if not is_rec:
            # 單次收支
            daily_df.loc[daily_df["Date"] == s_date, "Daily_Change"] += amt
        else:
            # 每月重複收支
            if pd.isna(e_date):
                e_date = end_sim_date
            elif isinstance(e_date, pd.Timestamp):
                e_date = e_date.date()
                
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
        st.error(f"🚨 **警告：預計於 `{first_negative_date}` 戶口結餘將出現赤字/負數 (${first_negative_bal:,.2f})！**")
    else:
        st.success("✅ 在預測期間內，戶口結餘維持正常，未出現赤字。")

    # 繪製結餘走勢圖
    fig = px.line(
        daily_df, 
        x="Date", 
        y="Balance", 
        title="每日預測戶口結餘走勢",
        labels={"Balance": "戶口結餘 ($)", "Date": "日期"}
    )
    fig.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="赤字線 (0元)")
    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------------------------------
    # 3. 每日明細走勢表
    # -----------------------------------------------------------------------------
    st.subheader("🗓️ 每日結餘明細表")
    
    # 篩選出有變動或結餘出現負數的日曆資料
    st.dataframe(
        daily_df.style.map(
            lambda val: "background-color: #ffcccc; color: red;" if val < 0 else "", 
            subset=["Balance"]
        ),
        use_container_width=True
    )
else:
    st.info("請在上方的表格中新增至少一個收支項目。")
