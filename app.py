import streamlit as st
import streamlit.components.v1 as components
import json
import os
import datetime

st.set_page_config(page_title="個人財務現金流與日曆預測", layout="wide")

DATA_FILE = "data.json"

# -----------------------------------------------------------------------------
# 1. 讀寫數據 (data.json 永久保存)
# -----------------------------------------------------------------------------
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "base_initial_balance": 109274.0,
        "items": [
            {"id": 1, "name": "Salary", "amount": 70000.0, "start_date": "2026-10-05", "recursive": True},
            {"id": 2, "name": "Octopus", "amount": -200.0, "start_date": "2026-10-06", "recursive": False},
            {"id": 3, "name": "Medical", "amount": 410.0, "start_date": "2026-10-07", "recursive": False}
        ]
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data_store = load_data()

# 接收前端 JavaScript 回傳的數據並存檔
if "save_payload" in st.query_params:
    try:
        payload_str = st.query_params["save_payload"]
        updated_data = json.loads(payload_str)
        save_data(updated_data)
        st.query_params.clear()
        st.rerun()
    except Exception:
        st.query_params.clear()

initial_json_str = json.dumps(data_store)

# -----------------------------------------------------------------------------
# 2. 前端 100% 互動式日曆 App (支持網格內 Drag/Drop, 直接編輯, + / - 號)
# -----------------------------------------------------------------------------
html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0; padding: 10px; background-color: #f8f9fa;
        }}
        .top-bar {{
            position: sticky; top: 0; z-index: 100; background: #ffffff;
            padding: 12px; margin-bottom: 15px; border-bottom: 1px solid #ddd;
            display: flex; gap: 15px; align-items: center; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        .btn-today {{
            background-color: #FF8C00; color: white; border: none;
            padding: 8px 16px; font-weight: bold; border-radius: 4px;
            cursor: pointer; font-size: 13px;
        }}
        .btn-today:hover {{ background-color: #E07B00; }}
        .grid-container {{
            display: grid; grid-template-columns: repeat(7, 1fr); gap: 8px;
        }}
        .day-box {{
            border: 1px solid #d0d0d0; border-radius: 6px; background-color: #ffffff;
            min-height: 160px; display: flex; flex-direction: column;
            justify-content: space-between; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .day-box.drag-over {{
            border: 2px dashed #1F3864 !important; background-color: #eef4fc !important;
        }}
        .day-header {{
            background-color: #1F3864; color: white; font-weight: bold;
            padding: 5px 8px; font-size: 12px; border-top-left-radius: 5px;
            border-top-right-radius: 5px; display: flex; justify-content: space-between; align-items: center;
        }}
        .day-header.today-header {{ background-color: #FF8C00 !important; }}
        .add-btn {{
            background: rgba(255,255,255,0.3); border: none; color: white;
            border-radius: 3px; cursor: pointer; font-weight: bold; font-size: 12px; padding: 0 5px;
        }}
        .add-btn:hover {{ background: rgba(255,255,255,0.6); }}
        .start-balance {{
            background-color: #EBF1F5; border-bottom: 1px solid #d0d0d0;
            padding: 3px 6px; display: flex; justify-content: space-between; font-size: 11px; color: #444;
        }}
        .day-content {{ padding: 5px; font-size: 11px; flex-grow: 1; }}
        .item-row {{
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 3px; padding: 2px 4px; border-radius: 3px;
            background-color: #f8f9fa; border: 1px solid #e9ecef; cursor: grab;
        }}
        .item-row:active {{ cursor: grabbing; }}
        .item-left {{ display: flex; align-items: center; gap: 3px; }}
        .item-name {{
            color: #333; outline: none; max-width: 70px; overflow: hidden;
            text-overflow: ellipsis; white-space: nowrap;
        }}
        .item-name:focus, .item-amt:focus {{
            background-color: #ffffcc; border-radius: 2px; padding: 0 2px;
        }}
        .amount-pos {{ color: #2E7D32; font-weight: bold; outline: none; }}
        .amount-neg {{ color: #D9534F; font-weight: bold; outline: none; }}
        .end-balance {{
            background-color: #F2F2F2; border-top: 1px solid #d0d0d0;
            padding: 3px 6px; display: flex; justify-content: space-between; font-size: 11px; font-weight: bold;
        }}
        .rec-icon {{ cursor: pointer; font-size: 10px; opacity: 0.3; }}
        .rec-icon.active {{ opacity: 1.0; color: #1F3864; font-weight: bold; }}
        .del-btn {{ color: #bbb; cursor: pointer; font-size: 10px; margin-left: 3px; }}
        .del-btn:hover {{ color: #D9534F; }}
    </style>
</head>
<body>

<div class="top-bar">
    <button class="btn-today" onclick="scrollToToday()">📅 TODAY (跳至今日)</button>
    <label style="font-size:12px;">起始結餘 ($): 
        <input type="number" id="initBalInput" style="width:100px; padding:3px;" onchange="updateInitBal(this.value)">
    </label>
</div>

<div class="grid-container" id="grid"></div>

<script>
    let store = JSON.parse(localStorage.getItem('cashflow_db')) || {initial_json_str};
    document.getElementById('initBalInput').value = store.base_initial_balance;

    const todayStr = new Date().toISOString().split('T')[0];

    function saveStore() {{
        localStorage.setItem('cashflow_db', JSON.stringify(store));
        // 同步回傳 Python
        const url = new URL(window.parent.location.href);
        url.searchParams.set('save_payload', JSON.stringify(store));
        window.parent.location.href = url.href;
    }}

    function updateInitBal(val) {{
        store.base_initial_balance = parseFloat(val) || 0;
        renderCalendar();
        saveStore();
    }}

    // 產生前後 12 個月日期範圍
    function generateDates() {{
        const dates = [];
        const curr = new Date();
        const startDate = new Date(curr.getFullYear(), curr.getMonth() - 12, 1);
        const endDate = new Date(curr.getFullYear(), curr.getMonth() + 13, 0);

        // 對齊週一
        const dayOfWeek = startDate.getDay();
        const diff = (dayOfWeek === 0 ? -6 : 1) - dayOfWeek;
        startDate.setDate(startDate.getDate() + diff);

        let d = new Date(startDate);
        while (d <= endDate) {{
            dates.push(new Date(d));
            d.setDate(d.getDate() + 1);
        }}
        return dates;
    }}

    function renderCalendar() {{
        const grid = document.getElementById('grid');
        grid.innerHTML = '';
        const dates = generateDates();

        // 建立每日變動與連動 Balance 試算
        const dailyChange = {{}};
        const dailyItems = {{}};

        dates.forEach(d => {{
            const dStr = d.toISOString().split('T')[0];
            dailyChange[dStr] = 0;
            dailyItems[dStr] = [];
        }});

        store.items.forEach(item => {{
            const amt = parseFloat(item.amount) || 0;
            if (!item.recursive) {{
                if (dailyChange[item.start_date] !== undefined) {{
                    dailyChange[item.start_date] += amt;
                    dailyItems[item.start_date].push(item);
                }}
            }} else {{
                // 每月重複展平
                let sD = new Date(item.start_date);
                dates.forEach(d => {{
                    if (d >= sD && d.getDate() === sD.getDate()) {{
                        const dStr = d.toISOString().split('T')[0];
                        dailyChange[dStr] += amt;
                        dailyItems[dStr].push({{...item, instance_date: dStr}});
                    }}
                }});
            }}
        }});

        let currBal = store.base_initial_balance;
        const weekdayMap = ["S", "M", "T", "W", "T", "F", "S"];

        dates.forEach(d => {{
            const dStr = d.toISOString().split('T')[0];
            const startBal = currBal;
            const change = dailyChange[dStr] || 0;
            const endBal = startBal + change;
            currBal = endBal;

            const isToday = (dStr === todayStr);
            const dayCode = weekdayMap[d.getDay()];
            const dateLabel = `${{String(d.getDate()).padStart(2, '0')}}/${{String(d.getMonth()+1).padStart(2, '0')}}/${{d.getFullYear()}} (${{dayCode}})`;

            const box = document.createElement('div');
            box.className = 'day-box';
            box.id = 'day-' + dStr;

            // 1. Header (今日顯示橙色)
            const header = document.createElement('div');
            header.className = isToday ? 'day-header today-header' : 'day-header';
            header.innerHTML = `<span>${{dateLabel}}</span><button class="add-btn" onclick="addItem('${{dStr}}')">+</button>`;
            box.appendChild(header);

            // 2. Start Balance
            const sbDiv = document.createElement('div');
            sbDiv.className = 'start-balance';
            sbDiv.innerHTML = `<span>Start Bal</span><span>${{Math.round(startBal).toLocaleString()}}</span>`;
            box.appendChild(sbDiv);

            // 3. Items & Drag/Drop
            const content = document.createElement('div');
            content.className = 'day-content';

            box.addEventListener('dragover', (e) => {{ e.preventDefault(); box.classList.add('drag-over'); }});
            box.addEventListener('dragleave', () => {{ box.classList.remove('drag-over'); }});
            box.addEventListener('drop', (e) => {{
                e.preventDefault();
                box.classList.remove('drag-over');
                const itemId = e.dataTransfer.getData('text/plain');
                if (itemId) {{
                    moveItem(parseInt(itemId), dStr);
                }}
            }});

            (dailyItems[dStr] || []).forEach(item => {{
                const row = document.createElement('div');
                row.className = 'item-row';
                row.draggable = true;
                row.addEventListener('dragstart', (e) => {{
                    e.dataTransfer.setData('text/plain', item.id);
                }});

                const left = document.createElement('div');
                left.className = 'item-left';

                const recIcon = document.createElement('span');
                recIcon.className = item.recursive ? 'rec-icon active' : 'rec-icon';
                recIcon.innerText = '🔄';
                recIcon.onclick = () => toggleRec(item.id);

                const nameSpan = document.createElement('span');
                nameSpan.className = 'item-name';
                nameSpan.contentEditable = true;
                nameSpan.innerText = item.name;
                nameSpan.onblur = () => updateName(item.id, nameSpan.innerText);

                left.appendChild(recIcon);
                left.appendChild(nameSpan);

                const right = document.createElement('div');
                right.style.display = 'flex'; right.style.alignItems = 'center';

                const amtSpan = document.createElement('span');
                amtSpan.className = item.amount < 0 ? 'amount-neg item-amt' : 'amount-pos item-amt';
                amtSpan.contentEditable = true;
                amtSpan.innerText = (item.amount >= 0 ? '+' : '') + Math.round(item.amount).toLocaleString();
                amtSpan.onblur = () => updateAmt(item.id, amtSpan.innerText);

                const delBtn = document.createElement('span');
                delBtn.className = 'del-btn';
                delBtn.innerText = '✖';
                delBtn.onclick = () => deleteItem(item.id);

                right.appendChild(amtSpan);
                right.appendChild(delBtn);

                row.appendChild(left);
                row.appendChild(right);
                content.appendChild(row);
            }});

            box.appendChild(content);

            // 4. End Balance
            const ebDiv = document.createElement('div');
            ebDiv.className = 'end-balance';
            const ebClass = endBal < 0 ? 'amount-neg' : 'amount-pos';
            ebDiv.innerHTML = `<span>End Balance</span><span class="${{ebClass}}">${{Math.round(endBal).toLocaleString()}}</span>`;
            box.appendChild(ebDiv);

            grid.appendChild(box);
        }});
    }}

    // Actions
    function addItem(dateStr) {{
        const newId = store.items.length ? Math.max(...store.items.map(i => i.id)) + 1 : 1;
        store.items.push({{ id: newId, name: "New Item", amount: -100, start_date: dateStr, recursive: false }});
        renderCalendar();
        saveStore();
    }}

    function moveItem(id, newDate) {{
        const item = store.items.find(i => i.id === id);
        if (item) {{
            item.start_date = newDate;
            renderCalendar();
            saveStore();
        }}
    }}

    function updateName(id, newName) {{
        const item = store.items.find(i => i.id === id);
        if (item && newName.trim()) {{
            item.name = newName.trim();
            saveStore();
        }}
    }}

    function updateAmt(id, rawAmt) {{
        const item = store.items.find(i => i.id === id);
        const val = parseFloat(rawAmt.replace(/,/g, '').replace(/\+/g, ''));
        if (item && !isNaN(val)) {{
            item.amount = val;
            renderCalendar();
            saveStore();
        }}
    }}

    function toggleRec(id) {{
        const item = store.items.find(i => i.id === id);
        if (item) {{
            item.recursive = !item.recursive;
            renderCalendar();
            saveStore();
        }}
    }}

    function deleteItem(id) {{
        store.items = store.items.filter(i => i.id !== id);
        renderCalendar();
        saveStore();
    }}

    function scrollToToday() {{
        const elem = document.getElementById('day-' + todayStr);
        if (elem) elem.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    }}

    renderCalendar();
</script>
</body>
</html>
"""

components.html(html_content, height=1200, scrolling=True)
