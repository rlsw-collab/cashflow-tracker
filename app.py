import streamlit as st
import streamlit.components.v1 as components
import json
import os

st.set_page_config(page_title="個人財務現金流與日曆預測", layout="wide")

DATA_FILE = "data.json"
APP_PASSWORD = "ck021018"

# -----------------------------------------------------------------------------
# 1. 密碼保護登入驗證關卡
# -----------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 身份驗證")
    pwd_input = st.text_input("請輸入密碼以打開財務管理工具:", type="password")
    if st.button("確認登入", use_container_width=True):
        if pwd_input == APP_PASSWORD:
            st.session_state["authenticated"] = True
            st.success("密碼正確！登入中...")
            st.rerun()
        else:
            st.error("密碼不正確，請重新輸入。")
    st.stop()

# -----------------------------------------------------------------------------
# 2. 讀寫數據 (data.json 永久保存)
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
# 3. 前端 100% 互動式日曆 App (含升級版 刪除 Modal 與 首月計算修正)
# -----------------------------------------------------------------------------
html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0; padding: 10px; background-color: #f8f9fa;
        }}
        .top-bar {{
            position: sticky; top: 0; z-index: 100; background: #ffffff;
            padding: 10px 15px; margin-bottom: 15px; border-bottom: 1px solid #ddd;
            display: flex; gap: 12px; align-items: center; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
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
            font-size: 13px; width: 140px;
        }}
        
        .toggle-wrapper {{
            display: flex; align-items: center; gap: 6px; font-size: 13px;
            font-weight: bold; color: #1F3864; background: #eef4fc;
            padding: 4px 10px; border-radius: 20px; border: 1px solid #cbdcf7;
        }}
        .switch {{
            position: relative; display: inline-block; width: 38px; height: 20px;
        }}
        .switch input {{ opacity: 0; width: 0; height: 0; }}
        .slider {{
            position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
            background-color: #ccc; transition: .3s; border-radius: 20px;
        }}
        .slider:before {{
            position: absolute; content: ""; height: 14px; width: 14px; left: 3px; bottom: 3px;
            background-color: white; transition: .3s; border-radius: 50%;
        }}
        input:checked + .slider {{ background-color: #FF8C00; }}
        input:checked + .slider:before {{ transform: translateX(18px); }}

        .grid-container {{
            display: grid; grid-template-columns: repeat(7, 1fr); gap: 8px;
            transition: all 0.3s ease;
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

        /* 手機 Compact 樣式 */
        body.mobile-view .grid-container {{
            grid-template-columns: repeat(2, 1fr) !important;
            gap: 5px !important;
        }}
        body.mobile-view .day-box {{
            min-height: 110px !important;
            border-radius: 4px !important;
        }}
        body.mobile-view .day-header {{
            padding: 3px 5px !important;
            font-size: 10px !important;
        }}
        body.mobile-view .start-balance, 
        body.mobile-view .end-balance {{
            padding: 2px 4px !important;
            font-size: 9.5px !important;
        }}
        body.mobile-view .day-content {{
            padding: 3px !important;
            font-size: 9.5px !important;
        }}
        body.mobile-view .item-row {{
            margin-bottom: 2px !important;
            padding: 1px 2px !important;
        }}
        body.mobile-view .item-name {{
            max-width: 45px !important;
        }}

        /* 置頂 Sticky Modal */
        .modal-overlay {{
            display: none; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.65); z-index: 999999;
            justify-content: center; align-items: flex-start;
            padding-top: 60px; box-sizing: border-box;
        }}
        .modal-box {{
            background: white; padding: 20px; border-radius: 12px; width: 90%; max-width: 350px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.4); text-align: left; font-size: 13px;
            box-sizing: border-box; position: sticky; top: 80px; z-index: 1000000;
            border: 2px solid #1F3864;
        }}
        .modal-title {{ font-weight: bold; font-size: 16px; margin-bottom: 12px; color: #1F3864; }}
        .modal-field {{ margin-bottom: 12px; }}
        .modal-field label {{ display: block; font-weight: bold; margin-bottom: 4px; font-size: 12px; }}
        .modal-field input {{ width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; font-size: 14px; }}
        .modal-btns {{ display: flex; justify-content: flex-end; gap: 8px; margin-top: 18px; }}
        .modal-btn {{ padding: 10px 16px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 13px; }}
        .btn-confirm {{ background-color: #1F3864; color: white; }}
        .btn-cancel {{ background-color: #e0e0e0; color: #333; }}
        .btn-danger {{ background-color: #D9534F; color: white; }}
    </style>
</head>
<body>

<div class="top-bar">
    <button class="btn-action" onclick="scrollToToday()">📅 TODAY</button>
    <button class="btn-secondary" id="undoBtn" onclick="undoStep()" disabled>↩️ Undo (0/10)</button>
    <input type="text" class="search-input" id="searchInput" placeholder="🔍 搜尋" oninput="onSearchChange(this.value)">
    
    <div class="toggle-wrapper">
        <span>💻 電腦</span>
        <label class="switch">
            <input type="checkbox" id="viewToggle" onchange="toggleViewMode(this.checked)">
            <span class="slider"></span>
        </label>
        <span>📱 手機 (Compact)</span>
    </div>
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
        <p style="margin: 5px 0 15px 0; line-height: 1.4; font-size: 13px;">這是一個每月重複項目，請選擇更新範圍：</p>
        <div class="modal-btns" style="flex-direction: column; gap: 8px;">
            <button class="modal-btn btn-cancel" style="width:100%;" onclick="confirmRecAmtUpdate('single')">僅修改本次</button>
            <button class="modal-btn btn-confirm" style="width:100%;" onclick="confirmRecAmtUpdate('future')">更新日後所有 (保留過去)</button>
        </div>
    </div>
</div>

<!-- 刪除確認 Modal (支援 Recursive：僅刪除本次 vs 刪除本次及往後所有) -->
<div class="modal-overlay" id="deleteConfirmModal">
    <div class="modal-box">
        <div class="modal-title">🗑️ 確認刪除項目</div>
        <p id="deleteConfirmMsg" style="margin: 5px 0 15px 0; font-size: 13px; line-height: 1.4;">確定要刪除此項目嗎？</p>
        <div class="modal-btns" id="deleteModalBtns"></div>
    </div>
</div>

<script>
    let store = JSON.parse(localStorage.getItem('cashflow_db')) || {initial_json_str};
    if (!store.overrides) store.overrides = {{}};

    const savedViewMode = localStorage.getItem('view_mode') === 'mobile';
    document.getElementById('viewToggle').checked = savedViewMode;
    if (savedViewMode) {{
        document.body.classList.add('mobile-view');
    }}

    function toggleViewMode(isMobile) {{
        if (isMobile) {{
            document.body.classList.add('mobile-view');
            localStorage.setItem('view_mode', 'mobile');
        }} else {{
            document.body.classList.remove('mobile-view');
            localStorage.setItem('view_mode', 'desktop');
        }}
    }}

    function openModal(id) {{
        const modal = document.getElementById(id);
        modal.style.display = 'flex';
        const topBar = document.querySelector('.top-bar');
        if (topBar) topBar.scrollIntoView({{ behavior: 'smooth' }});
    }}

    function closeModal(id) {{
        document.getElementById(id).style.display = 'none';
    }}

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

    function getLocalDateString(dateObj = new Date()) {{
        const year = dateObj.getFullYear();
        const month = String(dateObj.getMonth() + 1).padStart(2, '0');
        const day = String(dateObj.getDate()).padStart(2, '0');
        return `${{year}}-${{month}}-${{day}}`;
    }}

    const todayStr = getLocalDateString();
    let searchKeyword = "";

    function onSearchChange(val) {{
        searchKeyword = val.trim().toLowerCase();
        renderCalendar();
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
            const dStr = getLocalDateString(d);
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
                // 需求 2 修正：準確從 start_date 開始計算，避免跳過第一個 Happening 月份
                const [sYear, sMonth, sDay] = item.start_date.split('-').map(Number);
                const sDObj = new Date(sYear, sMonth - 1, sDay);
                let eDObj = item.end_date ? new Date(item.end_date.split('-')[0], item.end_date.split('-')[1] - 1, item.end_date.split('-')[2]) : null;

                dates.forEach(d => {{
                    // 日期必須在開始與結束之間，且「日子 (Date)」一致
                    if (d >= sDObj && (!eDObj || d <= eDObj) && d.getDate() === sDay) {{
                        const dStr = getLocalDateString(d);
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
                    const dStr = getLocalDateString(dates[dIndex]);
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
            const dStr = getLocalDateString(d);

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

    function moveItem(id, sourceDate, newDate) {{
        const item = store.items.find(i => i.id === id);
        if (!item) return;

        if (!item.recursive) {{
            item.start_date = newDate;
        }} else {{
            if (!item.exceptions) item.exceptions = [];
            if (!item.exceptions.includes(sourceDate)) {{
                item.exceptions.push(sourceDate);
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

    let pendingAmtEdit = null;

    function handleAmtEdit(id, currentDate, rawAmt) {{
        const item = store.items.find(i => i.id === id);
        const val = parseFloat(rawAmt.replace(/,/g, '').replace(/\+/g, ''));
        if (item && !isNaN(val) && val !== item.amount) {{
            if (item.recursive) {{
                pendingAmtEdit = {{ id, currentDate, val }};
                openModal('recAmtConfirmModal');
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
                const prevDateObj = new Date(currentDate);
                prevDateObj.setDate(prevDateObj.getDate() - 1);
                const prevDateStr = getLocalDateString(prevDateObj);

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

    // 需求 1 升級：刪除 Confirm Modal 支援 Delete This Item vs Delete This & All Future Items
    let deletingInfo = null;
    function promptDelete(id, name, currentDate, isRecursive) {{
        deletingInfo = {{ id, name, currentDate, isRecursive }};
        const msgElem = document.getElementById('deleteConfirmMsg');
        const btnContainer = document.getElementById('deleteModalBtns');

        if (!isRecursive) {{
            msgElem.innerText = `確定要刪除項目 "${{name}}" 嗎？`;
            btnContainer.style.flexDirection = 'row';
            btnContainer.innerHTML = `
                <button class="modal-btn btn-cancel" onclick="closeModal('deleteConfirmModal')">取消</button>
                <button class="modal-btn btn-danger" onclick="executeDelete('single')">確認刪除</button>
            `;
        }} else {{
            msgElem.innerText = `"${{name}}" 是一個每月重複項目，請選擇刪除範圍：`;
            btnContainer.style.flexDirection = 'column';
            btnContainer.innerHTML = `
                <button class="modal-btn btn-cancel" style="width:100%;" onclick="closeModal('deleteConfirmModal')">取消</button>
                <button class="modal-btn btn-danger" style="width:100%; margin-top:4px;" onclick="executeDelete('single')">僅刪除本次 (Delete This Item)</button>
                <button class="modal-btn btn-danger" style="width:100%; background-color:#8B0000;" onclick="executeDelete('future')">刪除本次及往後所有 (Delete This & All Future)</button>
            `;
        }}
        openModal('deleteConfirmModal');
    }}

    function executeDelete(mode) {{
        closeModal('deleteConfirmModal');
        if (deletingInfo) {{
            const {{ id, currentDate, isRecursive }} = deletingInfo;
            const target = store.items.find(i => i.id === id);

            if (target) {{
                if (!isRecursive) {{
                    store.items = store.items.filter(i => i.id !== id);
                }} else {{
                    if (mode === 'single') {{
                        // 僅刪除本次：紀錄至例外
                        if (!target.exceptions) target.exceptions = [];
                        if (!target.exceptions.includes(currentDate)) {{
                            target.exceptions.push(currentDate);
                        }}
                    }} else if (mode === 'future') {{
                        // 刪除本次及往後所有：截斷結束日期至前一天
                        const prevDateObj = new Date(currentDate);
                        prevDateObj.setDate(prevDateObj.getDate() - 1);
                        target.end_date = getLocalDateString(prevDateObj);
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
            openModal('recSettingsModal');
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
