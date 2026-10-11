import streamlit as st
import streamlit.components.v1 as components
import json
import os

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
        "overrides": {},
        "items": [
            {"id": 1, "name": "Salary", "amount": 70000.0, "start_date": "2026-10-05", "end_date": "2027-10-05", "recursive": True, "exceptions": []},
            {"id": 2, "name": "Octopus", "amount": -200.0, "start_date": "2026-10-06", "end_date": "", "recursive": False, "exceptions": []},
            {"id": 3, "name": "Medical", "amount": 410.0, "start_date": "2026-10-07", "end_date": "", "recursive": False, "exceptions": []}
        ]
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data_store = load_data()

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
# 2. 前端 100% 互動式日曆 App
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
            padding: 10px 15px; margin-bottom: 15px; border-bottom: 1px solid #ddd;
            display: flex; gap: 15px; align-items: center; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            flex-wrap: wrap;
        }}
        .btn-action {{
            background-color: #FF8C00; color: white; border: none;
            padding: 7px 14px; font-weight: bold; border-radius: 4px;
            cursor: pointer; font-size: 13px;
        }}
        .btn-action:hover {{ background-color: #E07B00; }}
        .btn-secondary {{
            background-color: #6c757d; color: white; border: none;
            padding: 7px 14px; font-weight: bold; border-radius: 4px;
            cursor: pointer; font-size: 13px;
        }}
        .btn-secondary:hover {{ background-color: #5a6268; }}
        .search-input {{
            padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;
            font-size: 13px; width: 180px;
        }}
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
        .editable-sb {{ outline: none; cursor: pointer; border-bottom: 1px dashed #888; }}
        .editable-sb:focus {{ background-color: #ffffcc; border-radius: 2px; }}
        .day-content {{ padding: 5px; font-size: 11px; flex-grow: 1; }}
        .item-row {{
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 3px; padding: 2px 4px; border-radius: 3px;
            background-color: #f8f9fa; border: 1px solid #e9ecef; cursor: grab;
        }}
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
        .modal-overlay {{
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.5); z-index: 1000;
            justify-content: center; align-items: center;
        }}
        .modal-box {{
            background: white; padding: 20px; border-radius: 8px; width: 340px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.25); text-align: left; font-size: 13px;
        }}
        .modal-title {{ font-weight: bold; font-size: 15px; margin-bottom: 12px; color: #1F3864; }}
        .modal-field {{ margin-bottom: 10px; }}
        .modal-field label {{ display: block; font-weight: bold; margin-bottom: 3px; font-size: 12px; }}
        .modal-field input {{ width: 95%; padding: 5px; border: 1px solid #ccc; border-radius: 4px; }}
        .modal-btns {{ display: flex; justify-content: flex-end; gap: 8px; margin-top: 15px; }}
        .modal-btn {{ padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }}
        .btn-confirm {{ background-color: #1F3864; color: white; }}
        .btn-cancel {{ background-color: #ccc; color: #333; }}
        .btn-danger {{ background-color: #D9534F; color: white; }}
    </style>
</head>
<body>

<div class="top-bar">
    <button class="btn-action" onclick="scrollToToday()">📅 TODAY (跳至今日)</button>
    <button class="btn-secondary" id="undoBtn" onclick="undoStep()" disabled>↩️ Undo (0/10)</button>
    <input type="text" class="search-input" id="searchInput" placeholder="🔍 搜尋項目 (如: Salary)" oninput="onSearchChange(this.value)">
</div>

<div class="grid-container" id="grid"></div>

<!-- Recursive 設定視窗 Modal -->
<div class="modal-overlay" id="recSettingsModal">
    <div class="modal-box">
        <div class="modal-title">🔄 設定重複條件 (Recursive)</div>
        <div class="modal-field">
            <label>開始日期 (Start Date):</label>
            <input type="date" id="modalRecStartDate">
        </div>
        <div class="modal-field">
            <label>結束日期 (End Date, 留空為永久):</label>
            <input type="date" id="modalRecEndDate">
        </div>
        <div class="modal-btns">
            <button class="modal-btn btn-cancel" onclick="closeModal('recSettingsModal')">取消</button>
            <button class="modal-btn btn-confirm" onclick="saveRecSettings()">儲存</button>
        </div>
    </div>
</div>

<!-- 修改 Recursive 金額確認 Modal -->
<div class="modal-overlay" id="recAmtConfirmModal">
    <div class="modal-box">
        <div class="modal-title">⚠️ 修改重複項目金額</div>
        <p>這是一個每月重複項目，請選擇更新範圍：</p>
        <div class="modal-btns">
            <button class="modal-btn btn-cancel" onclick="confirmRecAmtUpdate('single')">僅修改本次</button>
            <button class="modal-btn btn-confirm" onclick="confirmRecAmtUpdate('future')">更新日後所有 (保留過去)</button>
        </div>
    </div>
</div>

<!-- 刪除確認 Modal -->
<div class="modal-overlay" id="deleteConfirmModal">
    <div class="modal-box">
        <div class="modal-title">🗑️ 確認刪除項目</div>
        <p id="deleteConfirmMsg">確定要刪除此項目嗎？</p>
        <div class="modal-btns">
            <button class="modal-btn btn-cancel" onclick="closeModal('deleteConfirmModal')">取消</button>
            <button class="modal-btn btn-danger" onclick="executeDelete()">確認刪除</button>
        </div>
    </div>
</div>

<script>
    let store = JSON.parse(localStorage.getItem('cashflow_db')) || {initial_json_str};
    if (!store.overrides) store.overrides = {{}};

    const historyStack = [];
    const MAX_HISTORY = 10;

    function pushHistory() {{
        if (historyStack.length >= MAX_HISTORY) historyStack.shift();
        historyStack.push(JSON.stringify(store));
        updateUndoBtn();
    }}

    function undoStep() {{
        if (historyStack.length > 0) {{
            store = JSON.parse(historyStack.pop());
            updateUndoBtn();
            renderCalendar();
            saveStore(false);
        }}
    }}

    function updateUndoBtn() {{
        const btn = document.getElementById('undoBtn');
        btn.disabled = historyStack.length === 0;
        btn.innerText = `↩️ Undo (${{historyStack.length}}/10)`;
    }}

    function saveStore(recordHistory = true) {{
        if (recordHistory) pushHistory();
        localStorage.setItem('cashflow_db', JSON.stringify(store));
        const url = new URL(window.parent.location.href);
        url.searchParams.set('save_payload', JSON.stringify(store));
        window.parent.location.href = url.href;
    }}

    const todayStr = new Date().toISOString().split('T')[0];
    let searchKeyword = "";

    function onSearchChange(val) {{
        searchKeyword = val.trim().toLowerCase();
        renderCalendar();
    }}

    function closeModal(id) {{
        document.getElementById(id).style.display = 'none';
    }}

    function generateDates() {{
        const dates = [];
        const curr = new Date();
        const startDate = new Date(curr.getFullYear(), curr.getMonth() - 12, 1);
        const endDate = new Date(curr.getFullYear(), curr.getMonth() + 13, 0);

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

        const dailyChange = {{}};
        const dailyItems = {{}};

        dates.forEach(d => {{
            const dStr = d.toISOString().split('T')[0];
            dailyChange[dStr] = 0;
            dailyItems[dStr] = [];
        }});

        store.items.forEach(item => {{
            const amt = parseFloat(item.amount) || 0;
            if (!item.exceptions) item.exceptions = [];

            if (!item.recursive) {{
                if (dailyChange[item.start_date] !== undefined) {{
                    dailyChange[item.start_date] += amt;
                    dailyItems[item.start_date].push(item);
                }}
            }} else {{
                let sD = new Date(item.start_date);
                let eD = item.end_date ? new Date(item.end_date) : null;
                dates.forEach(d => {{
                    if (d >= sD && (!eD || d <= eD) && d.getDate() === sD.getDate()) {{
                        const dStr = d.toISOString().split('T')[0];
                        
                        // 修正關鍵：如果該日期已被列為例外 (Exception Date)，則跳過不顯示原本的重複項目
                        if (!item.exceptions.includes(dStr)) {{
                            dailyChange[dStr] += amt;
                            dailyItems[dStr].push({{...item, instance_date: dStr}});
                        }}
                    }}
                }});
            }}
        }});

        const totalWeeks = Math.ceil(dates.length / 7);
        const activeWeeks = [];

        for (let w = 0; w < totalWeeks; w++) {{
            let weekHasMatch = false;
            for (let dayIdx = 0; dayIdx < 7; dayIdx++) {{
                const dIndex = w * 7 + dayIdx;
                if (dIndex < dates.length) {{
                    const dStr = dates[dIndex].toISOString().split('T')[0];
                    const items = dailyItems[dStr] || [];
                    if (!searchKeyword) {{
                        weekHasMatch = true;
                    }} else if (items.some(i => i.name.toLowerCase().includes(searchKeyword))) {{
                        weekHasMatch = true;
                    }}
                }}
            }}
            activeWeeks[w] = weekHasMatch;
        }}

        let currBal = store.base_initial_balance;
        const weekdayMap = ["S", "M", "T", "W", "T", "F", "S"];

        dates.forEach((d, index) => {{
            const weekIndex = Math.floor(index / 7);
            const dStr = d.toISOString().split('T')[0];

            if (store.overrides[dStr] !== undefined) {{
                currBal = parseFloat(store.overrides[dStr]);
            }}

            const startBal = currBal;
            const change = dailyChange[dStr] || 0;
            const endBal = startBal + change;
            currBal = endBal;

            if (!activeWeeks[weekIndex]) return;

            const isToday = (dStr === todayStr);
            const dayCode = weekdayMap[d.getDay()];
            const dateLabel = `${{String(d.getDate()).padStart(2, '0')}}/${{String(d.getMonth()+1).padStart(2, '0')}}/${{d.getFullYear()}} (${{dayCode}})`;

            const box = document.createElement('div');
            box.className = 'day-box';
            box.id = 'day-' + dStr;

            const header = document.createElement('div');
            header.className = isToday ? 'day-header today-header' : 'day-header';
            header.innerHTML = `<span>${{dateLabel}}</span><button class="add-btn" onclick="addItem('${{dStr}}')">+</button>`;
            box.appendChild(header);

            const sbDiv = document.createElement('div');
            sbDiv.className = 'start-balance';
            sbDiv.innerHTML = `<span>Start Bal</span><span class="editable-sb" contenteditable="true" onblur="updateStartBal('${{dStr}}', this.innerText)" title="點擊修改當日 Start Balance">${{Math.round(startBal).toLocaleString()}}</span>`;
            box.appendChild(sbDiv);

            const content = document.createElement('div');
            content.className = 'day-content';

            box.addEventListener('dragover', (e) => {{ e.preventDefault(); box.classList.add('drag-over'); }});
            box.addEventListener('dragleave', () => {{ box.classList.remove('drag-over'); }});
            box.addEventListener('drop', (e) => {{
                e.preventDefault();
                box.classList.remove('drag-over');
                const rawData = e.dataTransfer.getData('text/plain');
                if (rawData) {{
                    const [itemId, sourceDate] = rawData.split('|');
                    moveItem(parseInt(itemId), sourceDate, dStr);
                }}
            }});

            (dailyItems[dStr] || []).forEach(item => {{
                const row = document.createElement('div');
                row.className = 'item-row';
                row.draggable = true;
                row.addEventListener('dragstart', (e) => {{
                    const srcDate = item.instance_date || item.start_date;
                    e.dataTransfer.setData('text/plain', `${{item.id}}|${{srcDate}}`);
                }});

                const left = document.createElement('div');
                left.className = 'item-left';

                const recIcon = document.createElement('span');
                recIcon.className = item.recursive ? 'rec-icon active' : 'rec-icon';
                recIcon.innerText = '🔄';
                recIcon.title = '點擊設定重複條件';
                recIcon.onclick = () => openRecModal(item.id);

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
                amtSpan.onblur = () => handleAmtEdit(item.id, item.instance_date || item.start_date, amtSpan.innerText);

                const delBtn = document.createElement('span');
                delBtn.className = 'del-btn';
                delBtn.innerText = '✖';
                delBtn.onclick = () => promptDelete(item.id, item.name, item.instance_date || item.start_date, item.recursive);

                right.appendChild(amtSpan);
                right.appendChild(delBtn);

                row.appendChild(left);
                row.appendChild(right);
                content.appendChild(row);
            }});

            box.appendChild(content);

            const ebDiv = document.createElement('div');
            ebDiv.className = 'end-balance';
            const ebClass = endBal < 0 ? 'amount-neg' : 'amount-pos';
            ebDiv.innerHTML = `<span>End Balance</span><span class="${{ebClass}}">${{Math.round(endBal).toLocaleString()}}</span>`;
            box.appendChild(ebDiv);

            grid.appendChild(box);
        }});
    }}

    // --- 修正後的 DRAG AND DROP：如果是 Recursive 項目拖曳，將原日期加入例外並在目標日期新增單次項目 ---
    function moveItem(id, sourceDate, newDate) {{
        const item = store.items.find(i => i.id === id);
        if (!item) return;

        if (!item.recursive) {{
            item.start_date = newDate;
        }} else {{
            if (!item.exceptions) item.exceptions = [];
            if (!item.exceptions.includes(sourceDate)) {{
                item.exceptions.push(sourceDate); // 原日期不再顯示該重複項目
            }}
            const newId = store.items.length ? Math.max(...store.items.map(i => i.id)) + 1 : 1;
            store.items.push({{
                id: newId,
                name: item.name,
                amount: item.amount,
                start_date: newDate,
                end_date: "",
                recursive: false,
                exceptions: []
            }});
        }}
        renderCalendar();
        saveStore();
    }}

    // --- 修正後的修改金額邏輯 ---
    let pendingAmtEdit = null;

    function handleAmtEdit(id, currentDate, rawAmt) {{
        const item = store.items.find(i => i.id === id);
        const val = parseFloat(rawAmt.replace(/,/g, '').replace(/\+/g, ''));
        if (item && !isNaN(val) && val !== item.amount) {{
            if (item.recursive) {{
                pendingAmtEdit = {{ id, currentDate, val }};
                document.getElementById('recAmtConfirmModal').style.display = 'flex';
            }} else {{
                item.amount = val;
                renderCalendar();
                saveStore();
            }}
        }}
    }}

    function confirmRecAmtUpdate(mode) {{
        closeModal('recAmtConfirmModal');
        if (!pendingAmtEdit) return;

        const {{ id, currentDate, val }} = pendingAmtEdit;
        const target = store.items.find(i => i.id === id);

        if (target) {{
            if (mode === 'single') {{
                // 僅修改本次：將原 Recursive 項目的 currentDate 加入 exceptions 列表，並建立獨立單次項目
                if (!target.exceptions) target.exceptions = [];
                if (!target.exceptions.includes(currentDate)) {{
                    target.exceptions.push(currentDate);
                }}

                const newId = store.items.length ? Math.max(...store.items.map(i => i.id)) + 1 : 1;
                store.items.push({{
                    id: newId,
                    name: target.name,
                    amount: val,
                    start_date: currentDate,
                    end_date: "",
                    recursive: false,
                    exceptions: []
                }});
            }} else if (mode === 'future') {{
                // 更新日後所有：截斷原項目結束日期，並從今日建立新金額的 Recursive 項目
                const prevDateObj = new Date(currentDate);
                prevDateObj.setDate(prevDateObj.getDate() - 1);
                const prevDateStr = prevDateObj.toISOString().split('T')[0];

                target.end_date = prevDateStr;

                const newId = store.items.length ? Math.max(...store.items.map(i => i.id)) + 1 : 1;
                store.items.push({{
                    id: newId,
                    name: target.name,
                    amount: val,
                    start_date: currentDate,
                    end_date: "",
                    recursive: true,
                    exceptions: []
                }});
            }}
        }}
        pendingAmtEdit = null;
        renderCalendar();
        saveStore();
    }}

    // --- 刪除邏輯：若刪除的是 Recursive 的單日，則加入 exceptions ---
    let deletingInfo = null;
    function promptDelete(id, name, currentDate, isRecursive) {{
        deletingInfo = {{ id, name, currentDate, isRecursive }};
        document.getElementById('deleteConfirmMsg').innerText = `確定要刪除項目 "${{name}}" 嗎？`;
        document.getElementById('deleteConfirmModal').style.display = 'flex';
    }}

    function executeDelete() {{
        closeModal('deleteConfirmModal');
        if (deletingInfo) {{
            const {{ id, currentDate, isRecursive }} = deletingInfo;
            const target = store.items.find(i => i.id === id);
            if (target) {{
                if (!isRecursive) {{
                    store.items = store.items.filter(i => i.id !== id);
                }} else {{
                    if (!target.exceptions) target.exceptions = [];
                    if (!target.exceptions.includes(currentDate)) {{
                        target.exceptions.push(currentDate);
                    }}
                }}
            }}
            deletingInfo = null;
            renderCalendar();
            saveStore();
        }}
    }}

    function updateStartBal(dateStr, rawVal) {{
        const val = parseFloat(rawVal.replace(/,/g, '').replace(/\+/g, ''));
        if (!isNaN(val)) {{
            store.overrides[dateStr] = val;
            renderCalendar();
            saveStore();
        }}
    }}

    let editingRecItemId = null;
    function openRecModal(id) {{
        editingRecItemId = id;
        const item = store.items.find(i => i.id === id);
        if (item) {{
            document.getElementById('modalRecStartDate').value = item.start_date || todayStr;
            document.getElementById('modalRecEndDate').value = item.end_date || '';
            document.getElementById('recSettingsModal').style.display = 'flex';
        }}
    }}

    function saveRecSettings() {{
        const item = store.items.find(i => i.id === editingRecItemId);
        if (item) {{
            item.recursive = true;
            item.start_date = document.getElementById('modalRecStartDate').value;
            item.end_date = document.getElementById('modalRecEndDate').value;
            closeModal('recSettingsModal');
            renderCalendar();
            saveStore();
        }}
    }}

    function addItem(dateStr) {{
        const newId = store.items.length ? Math.max(...store.items.map(i => i.id)) + 1 : 1;
        store.items.push({{ id: newId, name: "New Item", amount: -100, start_date: dateStr, end_date: "", recursive: false, exceptions: [] }});
        renderCalendar();
        saveStore();
    }}

    function updateName(id, newName) {{
        const item = store.items.find(i => i.id === id);
        if (item && newName.trim()) {{
            item.name = newName.trim();
            saveStore();
        }}
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
