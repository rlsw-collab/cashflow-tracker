import streamlit as st
import streamlit.components.v1 as components
import json
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="個人財務現金流與日曆預測", layout="wide")

st.title("💰 個人財務現金流與結餘預測")

# -----------------------------------------------------------------------------
# 1. Session State 數據中心 (確保所有編輯都能永久儲存)
# -----------------------------------------------------------------------------
if "view_date" not in st.session_state:
    st.session_state["view_date"] = datetime.date.today()

if "base_initial_balance" not in st.session_state:
    st.session_state["base_initial_balance"] = 109274.0

if "items_list" not in st.session_state:
    st.session_state["items_list"] = [
        {"id": 1, "name": "Salary", "amount": 70000.0, "start_date": "2026-10-05", "recursive": True},
        {"id": 2, "name": "Octopus", "amount": -200.0, "start_date": "2026-10-06", "recursive": False},
        {"id": 3, "name": "Medical", "amount": 410.0, "start_date": "2026-10-07", "recursive": False},
    ]

# 處理前端傳回的事件動作 (Action Query)
if "action" in st.query_params:
    try:
        action = st.query_params["action"]
        
        # 1. Drag & Drop 移動位置
        if action == "move_item":
            item_id = int(st.query_params["itemId"])
            new_date = st.query_params["newDate"]
            for it in st.session_state["items_list"]:
                if it["id"] == item_id:
                    it["start_date"] = new_date

        # 2. 修改名稱
        elif action == "update_name":
            item_id = int(st.query_params["itemId"])
            new_name = st.query_params["name"]
            for it in st.session_state["items_list"]:
                if it["id"] == item_id:
                    it["name"] = new_name

        # 3. 修改金額 (含更新日後所有項目)
        elif action == "update_amount":
            item_id = int(st.query_params["itemId"])
            new_amt = float(st.query_params["amount"])
            update_future = st.query_params.get("updateAllFuture") == "true"
            
            target_item = None
            for it in st.session_state["items_list"]:
                if it["id"] == item_id:
                    target_item = it
                    it["amount"] = new_amt
                    break
            
            # 若為 Recursive 且選擇更新日後項目
            if target_item and target_item.get("recursive") and update_future:
                # 自動更新同名同金額的未來連動項目
                for it in st.session_state["items_list"]:
                    if it["name"] == target_item["name"] and it["start_date"] >= target_item["start_date"]:
                        it["amount"] = new_amt

        # 4. 切換每月重複 (Recursive)
        elif action == "toggle_recursive":
            item_id = int(st.query_params["itemId"])
            for it in st.session_state["items_list"]:
                if it["id"] == item_id:
                    it["recursive"] = not it.get("recursive", False)

        # 5. 按 + 號新增項目
        elif action == "add_item":
            target_date = st.query_params["date"]
            new_id = max([x["id"] for x in st.session_state["items_list"]], default=0) + 1
            st.session_state["items_list"].append({
                "id": new_id,
                "name": "New Item",
                "amount": -100.0,
                "start_date": target_date,
                "recursive": False
            })

        # 6. 按 ✖ 刪除項目
        elif action == "delete_item":
            item_id = int(st.query_params["itemId"])
            st.session_state["items_list"] = [x for x in st.session_state["items_list"] if x["id"] != item_id]

    except Exception as e:
        pass
    finally:
        st.query_params.clear()
        st.rerun()

# -----------------------------------------------------------------------------
# 2. 控制欄位
# -----------------------------------------------------------------------------
col_start, col_months, col_bal = st.columns([2, 2, 2])

with col_start:
    start_view_date = st.date_input("查看基準日期 (今日):", value=st.session_state["view_date"], key="input_view_date")
    st.session_state["view_date"] = start_view_date

with col_months:
    # 需求 5：預設 12 個月（出到前 12 個月 至 後 12 個月）
    months_offset = st.number_input("顯示月數範圍 (前後月數):", value=12, min_value=1, max_value=24, step=1)

with col_bal:
    init_bal = st.number_input("起始戶口結餘 ($):", value=st.session_state["base_initial_balance"], step=1000.0)
    st.session_state["base_initial_balance"] = init_bal

# -----------------------------------------------------------------------------
# 3. 日期範圍試算 (需求 5: 今日前 12 個月 ~ 今日後 12 個月)
# -----------------------------------------------------------------------------
today = start_view_date
calc_start_date = today - relativedelta(months=months_offset)
calc_end_date = today + relativedelta(months=months_offset)

# 調整對齊至週一開始與週日結束
calc_start = calc_start_date - datetime.timedelta(days=calc_start_date.weekday())
calc_end = calc_end_date + datetime.timedelta(days=(6 - calc_end_date.weekday()))

total_days = (calc_end - calc_start).days + 1
date_range = [calc_start + datetime.timedelta(days=i) for i in range(total_days)]
date_strs = [d.strftime("%Y-%m-%d") for d in date_range]

# 試算每日項目與連動金額
daily_items = {d_str: [] for d_str in date_strs}
daily_change = {d_str: 0.0 for d_str in date_strs}

for item in st.session_state["items_list"]:
    s_date = item.get("start_date")
    amt = float(item.get("amount", 0))
    is_rec = item.get("recursive", False)

    if not is_rec:
        if s_date in daily_items:
            daily_items[s_date].append(item)
            daily_change[s_date] += amt
    else:
        try:
            s_dt = datetime.datetime.strptime(s_date, "%Y-%m-%d").date()
            curr = s_dt
            while curr <= date_range[-1]:
                curr_str = curr.strftime("%Y-%m-%d")
                if curr_str in daily_items:
                    item_instance = dict(item)
                    item_instance["instance_date"] = curr_str
                    daily_items[curr_str].append(item_instance)
                    daily_change[curr_str] += amt
                curr += relativedelta(months=1)
        except Exception:
            pass

# 連動計算 Start & End Balance
daily_start_bal = {}
daily_end_bal = {}
curr_bal = st.session_state["base_initial_balance"]

for d_str in date_strs:
    daily_start_bal[d_str] = curr_bal
    end_b = curr_bal + daily_change[d_str]
    daily_end_bal[d_str] = end_b
    curr_bal = end_b

# -----------------------------------------------------------------------------
# 4. 構建前端月曆資料
# -----------------------------------------------------------------------------
today_str = datetime.date.today().strftime("%Y-%m-%d")
weekday_map = {0: "M", 1: "T", 2: "W", 3: "T", 4: "F", 5: "S", 6: "S"}

calendar_data = []
for d in date_range:
    d_str = d.strftime("%Y-%m-%d")
    day_code = weekday_map[d.weekday()]
    label_str = f"{d.strftime('%d/%m/%Y')} ({day_code})"
    
    calendar_data.append({
        "date_str": d_str,
        "label": label_str,
        "is_today": (d_str == today_str),
        "start_bal": daily_start_bal[d_str],
        "end_bal": daily_end_bal[d_str],
        "items": daily_items[d_str]
    })

data_json_str = json.dumps(calendar_data)

# -----------------------------------------------------------------------------
# 5. 前端 JavaScript & CSS (含 Drag & Drop / TODAY 自動捲動 / 彈窗確認)
# -----------------------------------------------------------------------------
st.subheader("📅 日曆現金流看板")

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
        .top-bar {{
            position: sticky;
            top: 0;
            z-index: 100;
            background: white;
            padding: 10px 0;
            margin-bottom: 15px;
            border-bottom: 1px solid #ddd;
        }}
        .btn-today {{
            background-color: #FF8C00;
            color: white;
            border: none;
            padding: 8px 18px;
            font-weight: bold;
            border-radius: 4px;
            cursor: pointer;
            box-shadow: 0 2px 4px rgba(0,0,0,0.15);
        }}
        .btn-today:hover {{
            background-color: #E07B00;
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
            min-height: 170px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }}
        .day-box.drag-over {{
            border: 2px dashed #1F3864 !important;
            background-color: #f0f4f9 !important;
        }}
        .day-header {{
            background-color: #1F3864;
            color: white;
            font-weight: bold;
            padding: 5px 8px;
            font-size: 13px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        /* 今日 Header 變為醒目橙色 */
        .day-header.today-header {{
            background-color: #FF8C00 !important;
        }}
        .add-btn {{
            background: rgba(255,255,255,0.3);
            border: none;
            color: white;
            border-radius: 3px;
            cursor: pointer;
            font-weight: bold;
            font-size: 13px;
            padding: 1px 6px;
        }}
        .add-btn:hover {{
            background: rgba(255,255,255,0.6);
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
            align-items: center;
            margin-bottom: 4px;
            padding: 3px 4px;
            border-radius: 3px;
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            cursor: grab;
        }}
        .item-left {{
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        .item-name {{
            color: #333333;
            outline: none;
            max-width: 75px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .item-name:focus, .item-amt:focus {{
            background-color: #ffffcc;
            border-radius: 2px;
            padding: 0 2px;
        }}
        .amount-pos {{ color: #2E7D32; font-weight: bold; outline: none; }}
        .amount-neg {{ color: #D9534F; font-weight: bold; outline: none; }}
        .end-balance {{
            background-color: #F2F2F2;
            border-top: 1px solid #d0d0d0;
            padding: 4px 6px;
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            font-weight: bold;
        }}
        .rec-icon {{
            cursor: pointer;
            font-size: 11px;
            opacity: 0.3;
        }}
        .rec-icon.active {{
            opacity: 1.0;
            color: #1F3864;
            font-weight: bold;
        }}
        .del-btn {{
            color: #aaa;
            cursor: pointer;
            font-size: 11px;
            margin-left: 4px;
        }}
        .del-btn:hover {{ color: #D9534F; }}
        .modal-overlay {{
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }}
        .modal-box {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            width: 320px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
            text-align: center;
        }}
        .modal-btn {{
            margin: 10px 4px 0 4px;
            padding: 6px 14px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }}
        .modal-btn-confirm {{ background-color: #1F3864; color: white; }}
        .modal-btn-cancel {{ background-color: #ccc; color: #333; }}
    </style>
</head>
<body>

<div class="top-bar">
    <!-- 需求 3：TODAY 按鈕，自動 Scroll 到今日並顯示橙色 Header -->
    <button class="btn-today" onclick="scrollToToday()">📅 TODAY (跳至今日)</button>
</div>

<div class="grid-container" id="grid"></div>

<!-- 需求 4：更新 Recursive 金額的彈窗 -->
<div class="modal-overlay" id="recModal">
    <div class="modal-box">
        <h3>更新重複項目金額</h3>
        <p>這是一個每月重複項目，是否一併更新今日起之後所有重複項目的金額？</p>
        <button class="modal-btn modal-btn-confirm" onclick="confirmRecUpdate(true)">是 (更新日後所有)</button>
        <button class="modal-btn modal-btn-cancel" onclick="confirmRecUpdate(false)">否 (僅更新本次)</button>
    </div>
</div>

<script>
    const data = {data_json_str};
    const grid = document.getElementById('grid');
    let pendingRecUpdate = null;

    function renderGrid() {{
        grid.innerHTML = '';
        data.forEach(day => {{
            const box = document.createElement('div');
            box.className = 'day-box';
            box.id = 'day-' + day.date_str;

            // 1. Header (需求 3: 今日 Header 橙色)
            const header = document.createElement('div');
            header.className = day.is_today ? 'day-header today-header' : 'day-header';
            
            const dateLabel = document.createElement('span');
            dateLabel.innerText = day.label;
            
            // 需求 1: 加號 (+) 新增 Item
            const addBtn = document.createElement('button');
            addBtn.className = 'add-btn';
            addBtn.innerText = '+';
            addBtn.title = '新增收支項目';
            addBtn.onclick = () => {{
                sendAction({{ action: 'add_item', date: day.date_str }});
            }};

            header.appendChild(dateLabel);
            header.appendChild(addBtn);
            box.appendChild(header);

            // 2. Start Balance
            const startBalDiv = document.createElement('div');
            startBalDiv.className = 'start-balance';
            startBalDiv.innerHTML = `<span>Start Bal</span><span>${{Math.round(day.start_bal).toLocaleString()}}</span>`;
            box.appendChild(startBalDiv);

            // 3. Items & Drag/Drop (需求 2: 拖拽到目標地點並放開儲存)
            const content = document.createElement('div');
            content.className = 'day-content';

            box.addEventListener('dragover', (e) => {{ e.preventDefault(); box.classList.add('drag-over'); }});
            box.addEventListener('dragleave', () => {{ box.classList.remove('drag-over'); }});
            box.addEventListener('drop', (e) => {{
                e.preventDefault();
                box.classList.remove('drag-over');
                const itemId = e.dataTransfer.getData('text/plain');
                if (itemId) {{
                    sendAction({{ action: 'move_item', itemId: parseInt(itemId), newDate: day.date_str }});
                }}
            }});

            day.items.forEach(item => {{
                const itemRow = document.createElement('div');
                itemRow.className = 'item-row';
                itemRow.draggable = true;

                itemRow.addEventListener('dragstart', (e) => {{
                    e.dataTransfer.setData('text/plain', item.id);
                }});

                const leftDiv = document.createElement('div');
                leftDiv.className = 'item-left';

                const recIcon = document.createElement('span');
                recIcon.className = item.recursive ? 'rec-icon active' : 'rec-icon';
                recIcon.innerText = '🔄';
                recIcon.title = '切換每月重複';
                recIcon.onclick = () => {{
                    sendAction({{ action: 'toggle_recursive', itemId: item.id }});
                }};

                const nameSpan = document.createElement('span');
                nameSpan.className = 'item-name';
                nameSpan.contentEditable = true;
                nameSpan.innerText = item.name;
                nameSpan.onblur = () => {{
                    const newName = nameSpan.innerText.trim();
                    if (newName && newName !== item.name) {{
                        sendAction({{ action: 'update_name', itemId: item.id, name: newName }});
                    }}
                }};

                leftDiv.appendChild(recIcon);
                leftDiv.appendChild(nameSpan);

                const rightDiv = document.createElement('div');
                rightDiv.style.display = 'flex';
                rightDiv.style.alignItems = 'center';

                // 需求 3 & 4: 金額修改與更新確認
                const amtSpan = document.createElement('span');
                amtSpan.className = item.amount < 0 ? 'amount-neg item-amt' : 'amount-pos item-amt';
                amtSpan.contentEditable = true;
                amtSpan.innerText = (item.amount >= 0 ? '+' : '') + Math.round(item.amount).toLocaleString();
                amtSpan.onblur = () => {{
                    const rawVal = amtSpan.innerText.replace(/,/g, '').replace(/\+/g, '').trim();
                    const newAmt = parseFloat(rawVal);
                    if (!isNaN(newAmt) && newAmt !== item.amount) {{
                        if (item.recursive) {{
                            pendingRecUpdate = {{ itemId: item.id, newAmt: newAmt }};
                            document.getElementById('recModal').style.display = 'flex';
                        }} else {{
                            sendAction({{ action: 'update_amount', itemId: item.id, amount: newAmt }});
                        }}
                    }}
                }};

                const delBtn = document.createElement('span');
                delBtn.className = 'del-btn';
                delBtn.innerText = '✖';
                delBtn.title = '刪除項目';
                delBtn.onclick = () => {{
                    sendAction({{ action: 'delete_item', itemId: item.id }});
                }};

                rightDiv.appendChild(amtSpan);
                rightDiv.appendChild(delBtn);

                itemRow.appendChild(leftDiv);
                itemRow.appendChild(rightDiv);
                content.appendChild(itemRow);
            }});

            box.appendChild(content);

            // 4. End Balance
            const endBalDiv = document.createElement('div');
            endBalDiv.className = 'end-balance';
            const endBalClass = day.end_bal < 0 ? 'amount-neg' : 'amount-pos';
            endBalDiv.innerHTML = `<span>End Balance</span><span class="${{endBalClass}}">${{Math.round(day.end_bal).toLocaleString()}}</span>`;
            box.appendChild(endBalDiv);

            grid.appendChild(box);
        }});
    }}

    // 需求 3：Scroll 到今日位置
    function scrollToToday() {{
        const todayElem = document.getElementById('day-' + '{today_str}');
        if (todayElem) {{
            todayElem.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        }} else {{
            alert('今天的日期不在當前顯示的視圖範圍內。');
        }}
    }}

    function confirmRecUpdate(updateAllFuture) {{
        document.getElementById('recModal').style.display = 'none';
        if (pendingRecUpdate) {{
            sendAction({{
                action: 'update_amount',
                itemId: pendingRecUpdate.itemId,
                amount: pendingRecUpdate.newAmt,
                updateAllFuture: updateAllFuture
            }});
            pendingRecUpdate = null;
        }}
    }}

    // 事件通知傳遞機制
    function sendAction(params) {{
        const url = new URL(window.parent.location.href);
        Object.keys(params).forEach(key => url.searchParams.set(key, params[key]));
        window.parent.location.href = url.href;
    }}

    renderGrid();
</script>
</body>
</html>
"""

# 計算動態高度避免雙滾輪
calculated_height = (total_days // 7) * 210 + 100
components.html(custom_html, height=calculated_height, scrolling=True)

# -----------------------------------------------------------------------------
# 6. 備用數據管理表 (可作一次過批次匯入/刪除)
# -----------------------------------------------------------------------------
with st.expander("🛠️ 數據管理備用清單 (如需批次編輯可在此修改)", expanded=False):
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
    if st.button("儲存並套用所有變更"):
        st.session_state["items_list"] = edited_df.to_dict("records")
        st.rerun()
