import streamlit as st
import streamlit.components.v1 as components
import json
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
        {"id": 1, "name": "Salary", "amount": 70000.0, "start_date": "2026-10-05", "recursive": False},
        {"id": 2, "name": "Octopus", "amount": -200.0, "start_date": "2026-10-06", "recursive": False},
        {"id": 3, "name": "Medical", "amount": 410.0, "start_date": "2026-10-07", "recursive": False},
    ]

if "base_initial_balance" not in st.session_state:
    st.session_state["base_initial_balance"] = 109274.0

# -----------------------------------------------------------------------------
# 2. 控制欄位 (TODAY 按鈕、查看日期、顯示月數)
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
# 3. 試算每日 Start Balance, Daily Items, End Balance
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
date_strs = [d.strftime("%Y-%m-%d") for d in date_range]

daily_items = {d_str: [] for d_str in date_strs}
daily_change = {d_str: 0.0 for d_str in date_strs}

for item in st.session_state["items_list"]:
    s_date = item.get("start_date")
    amt = float(item.get("amount", 0))
    
    if s_date in daily_items:
        daily_items[s_date].append(item)
        daily_change[s_date] += amt

# 計算連動結餘
daily_start_bal = {}
daily_end_bal = {}
curr_bal = st.session_state["base_initial_balance"]

for d_str in date_strs:
    daily_start_bal[d_str] = curr_bal
    end_b = curr_bal + daily_change[d_str]
    daily_end_bal[d_str] = end_b
    curr_bal = end_b

# 赤字警告
neg_days = [d for d, bal in daily_end_bal.items() if bal < 0]
if neg_days:
    st.error(f"🚨 **警告：預計於 `{neg_days[0]}` 戶口結餘出現赤字 (${daily_end_bal[neg_days[0]]:,.0f})！**")
else:
    st.success("✅ 所選預測期間內戶口結餘維繫正常。")

# -----------------------------------------------------------------------------
# 4. 前端可拖曳與直接編輯的可視化 Calendar 組件
# -----------------------------------------------------------------------------
st.subheader("📅 日曆現金流看板 (可直接拖曳項目／點擊修改金額與名稱)")

# 構建傳給 HTML 組件的 JSON 資料構造
calendar_data = []
weekday_map = {0: "M", 1: "T", 2: "W", 3: "T", 4: "F", 5: "S", 6: "S"}

for d in date_range:
    d_str = d.strftime("%Y-%m-%d")
    day_code = weekday_map[d.weekday()]
    label_str = f"{d.strftime('%d/%m/%Y')} ({day_code})"
    
    calendar_data.append({
        "date_str": d_str,
        "label": label_str,
        "start_bal": daily_start_bal[d_str],
        "end_bal": daily_end_bal[d_str],
        "items": daily_items[d_str]
    })

# 將資料編碼為 JSON 字串傳給前端
data_json_str = json.dumps(calendar_data)

# 原生 HTML5 + CSS + JavaScript Component
custom_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 10px;
            background-color: transparent;
        }}
        .grid-container {{
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 10px;
        }}
        .day-box {{
            border: 1px solid #d0d0d0;
            border-radius: 6px;
            background-color: #ffffff;
            min-height: 160px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            transition: border-color 0.2s, background-color 0.2s;
        }}
        .day-box.drag-over {{
            border: 2px dashed #1F3864 !important;
            background-color: #f0f4f9 !important;
        }}
        .day-header {{
            background-color: #1F3864;
            color: white;
            text-align: center;
            font-weight: bold;
            padding: 5px 2px;
            font-size: 13px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
        }}
        .start-balance {{
            background-color: #EBF1F5;
            border-bottom: 1px solid #d0d0d0;
            padding: 3px 6px;
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            color: #444444;
        }}
        .day-content {{
            padding: 6px;
            font-size: 12px;
            flex-grow: 1;
        }}
        .item-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
            padding: 3px 4px;
            border-radius: 3px;
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            cursor: grab;
            user-select: none;
        }}
        .item-row:active {{
            cursor: grabbing;
        }}
        .item-name {{
            color: #333333;
            outline: none;
            max-width: 80px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .item-name:focus, .item-amt:focus, .editable-bal:focus {{
            background-color: #ffffcc;
            border-radius: 2px;
            padding: 0 2px;
        }}
        .amount-pos {{
            color: #2E7D32;
            font-weight: bold;
            outline: none;
        }}
        .amount-neg {{
            color: #D9534F;
            font-weight: bold;
            outline: none;
        }}
        .end-balance {{
            background-color: #F2F2F2;
            border-top: 1px solid #d0d0d0;
            padding: 4px 6px;
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            font-weight: bold;
        }}
        .neg-box {{
            background-color: #FFECEC !important;
            border: 1px solid #FF4D4D !important;
        }}
    </style>
</head>
<body>

<div class="grid-container" id="grid"></div>

<script>
    const data = {data_json_str};
    const grid = document.getElementById('grid');

    function renderGrid() {{
        grid.innerHTML = '';
        data.forEach(day => {{
            const isNeg = day.end_bal < 0;
            const boxClass = isNeg ? 'day-box neg-box' : 'day-box';
            const endBalClass = isNeg ? 'amount-neg' : 'amount-pos';

            const box = document.createElement('div');
            box.className = boxClass;
            box.dataset.date = day.date_str;

            // Drag & Drop 事件處理
            box.addEventListener('dragover', (e) => {{
                e.preventDefault();
                box.classList.add('drag-over');
            }});
            box.addEventListener('dragleave', () => {{
                box.classList.remove('drag-over');
            }});
            box.addEventListener('drop', (e) => {{
                e.preventDefault();
                box.classList.remove('drag-over');
                const itemId = e.dataTransfer.getData('text/plain');
                if (itemId) {{
                    window.parent.postMessage({{
                        type: 'streamlit:setItemState',
                        action: 'move_item',
                        itemId: parseInt(itemId),
                        newDate: day.date_str
                    }}, '*');
                }}
            }});

            // 1. Header
            const header = document.createElement('div');
            header.className = 'day-header';
            header.innerText = day.label;
            box.appendChild(header);

            // 2. Start Balance
            const startBalDiv = document.createElement('div');
            startBalDiv.className = 'start-balance';
            startBalDiv.innerHTML = `<span>Start Bal</span><span class="editable-bal" contenteditable="true" data-date="${{day.date_str}}">${{Math.round(day.start_bal).toLocaleString()}}</span>`;
            box.appendChild(startBalDiv);

            // 3. Day Content (Items)
            const content = document.createElement('div');
            content.className = 'day-content';

            day.items.forEach(item => {{
                const itemRow = document.createElement('div');
                itemRow.className = 'item-row';
                itemRow.draggable = true;

                itemRow.addEventListener('dragstart', (e) => {{
                    e.dataTransfer.setData('text/plain', item.id);
                }});

                const nameSpan = document.createElement('span');
                nameSpan.className = 'item-name';
                nameSpan.contentEditable = true;
                nameSpan.innerText = item.name;
                nameSpan.addEventListener('blur', () => {{
                    const newName = nameSpan.innerText.trim();
                    if (newName && newName !== item.name) {{
                        window.parent.postMessage({{
                            type: 'streamlit:setItemState',
                            action: 'update_item',
                            itemId: item.id,
                            fieldName: 'name',
                            newValue: newName
                        }}, '*');
                    }}
                }});

                const amtSpan = document.createElement('span');
                amtSpan.className = item.amount < 0 ? 'amount-neg item-amt' : 'amount-pos item-amt';
                amtSpan.contentEditable = true;
                amtSpan.innerText = (item.amount >= 0 ? '+' : '') + Math.round(item.amount).toLocaleString();
                amtSpan.addEventListener('blur', () => {{
                    const rawVal = amtSpan.innerText.replace(/,/g, '').replace(/\+/g, '').trim();
                    const newAmt = parseFloat(rawVal);
                    if (!isNaN(newAmt) && newAmt !== item.amount) {{
                        window.parent.postMessage({{
                            type: 'streamlit:setItemState',
                            action: 'update_item',
                            itemId: item.id,
                            fieldName: 'amount',
                            newValue: newAmt
                        }}, '*');
                    }}
                }});

                itemRow.appendChild(nameSpan);
                itemRow.appendChild(amtSpan);
                content.appendChild(itemRow);
            }});

            box.appendChild(content);

            // 4. End Balance
            const endBalDiv = document.createElement('div');
            endBalDiv.className = 'end-balance';
            endBalDiv.innerHTML = `<span>End Balance</span><span class="${{endBalClass}}">${{Math.round(day.end_bal).toLocaleString()}}</span>`;
            box.appendChild(endBalDiv);

            grid.appendChild(box);
        }});
    }}

    renderGrid();
</script>
</body>
</html>
"""

# 計算動態 Height 避免雙滾輪
calculated_height = (total_days // 7) * 200 + 40
components.html(custom_html, height=calculated_height, scrolling=True)

# -----------------------------------------------------------------------------
# 5. 表格編輯備用區 (快速新增/移除項目)
# -----------------------------------------------------------------------------
with st.expander("🛠️ 收支清單備用管理表 (新增/刪除項目)", expanded=False):
    raw_df = pd.DataFrame(st.session_state["items_list"])
    edited_df = st.data_editor(
        raw_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "id": None,
            "name": st.column_config.TextColumn("項目名稱", required=True),
            "amount": st.column_config.NumberColumn("金額", required=True, format="$%d"),
            "start_date": st.column_config.DateColumn("日期", required=True),
            "recursive": st.column_config.CheckboxColumn("每月重複?", default=False),
        },
        key="backup_editor"
    )
    if st.button("儲存項目變更"):
        st.session_state["items_list"] = edited_df.to_dict("records")
        st.rerun()
