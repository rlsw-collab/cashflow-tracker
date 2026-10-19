import streamlit as st
import streamlit.components.v1 as components
import json
import urllib.request

st.set_page_config(page_title="個人財務現金流與日曆預測", layout="wide")

# -----------------------------------------------------------------------------
# 🌐 雲端資料庫 JSONBin.io 設定
# -----------------------------------------------------------------------------
BIN_ID = "6acbb317ac6210605a28324b"
MASTER_KEY = "$2a$10$D2dJpO8iHYdPOHsSUlk05OpudbFsjvV4RtN9DT6xVOqlUQtMPL/eW"
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
# 2. 數據載入
# -----------------------------------------------------------------------------
def load_data_from_cloud():
    url = f"https://api.jsonbin.io/v3/b/{BIN_ID}/latest"
    try:
        req = urllib.request.Request(url)
        req.add_header("X-Master-Key", MASTER_KEY)
        req.add_header("X-Bin-Meta", "false")
        with urllib.request.urlopen(req, timeout=5) as response:
            res = json.loads(response.read().decode("utf-8"))
            rec = res.get("record", res)
            if isinstance(rec, dict) and "base_initial_balance" in rec:
                return rec
    except Exception:
        pass

    return {
        "base_initial_balance": 109274.0,
        "overrides": {},
        "items": [],
        "report_items": ["Salary", "Rent", "Octopus"]
    }

cloud_data = load_data_from_cloud()
initial_json_str = json.dumps(cloud_data)

# -----------------------------------------------------------------------------
# 3. 前端 App (含 Reports 最底部 Monthly Total 加總列)
# -----------------------------------------------------------------------------
html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        html, body {{
            margin: 0; padding: 0;
            height: 100vh; width: 100vw;
            overflow: hidden;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #f8f9fa;
        }}

        #app-wrapper {{
            display: flex; flex-direction: column;
            height: 100vh; width: 100vw; box-sizing: border-box;
        }}

        .top-bar {{
            flex-shrink: 0; background: #ffffff;
            padding: 8px 12px; border-bottom: 1px solid #ddd;
            display: flex; gap: 8px; align-items: center;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
            flex-wrap: wrap; box-sizing: border-box; z-index: 1000;
        }}
        .btn-action {{
            background-color: #FF8C00; color: white; border: none;
            padding: 6px 10px; font-weight: bold; border-radius: 4px;
            cursor: pointer; font-size: 12px;
        }}
        .btn-action:hover {{ background-color: #E07B00; }}
        .btn-secondary {{
            background-color: #6c757d; color: white; border: none;
            padding: 6px 10px; font-weight: bold; border-radius: 4px;
            cursor: pointer; font-size: 12px;
        }}
        .btn-secondary:hover {{ background-color: #5a6268; }}
        .btn-nav {{
            background-color: #1F3864; color: white; border: none;
            padding: 6px 12px; font-weight: bold; border-radius: 4px;
            cursor: pointer; font-size: 12px;
        }}
        .btn-nav:hover {{ background-color: #152744; }}
        
        .search-input {{
            padding: 5px 8px; border: 1px solid #ccc; border-radius: 4px;
            font-size: 12px; width: 100px;
        }}
        
        .toggle-wrapper {{
            display: flex; align-items: center; gap: 4px; font-size: 12px;
            font-weight: bold; color: #1F3864; background: #eef4fc;
            padding: 3px 8px; border-radius: 20px; border: 1px solid #cbdcf7;
        }}
        .switch {{
            position: relative; display: inline-block; width: 32px; height: 18px;
        }}
        .switch input {{ opacity: 0; width: 0; height: 0; }}
        .slider {{
            position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
            background-color: #ccc; transition: .3s; border-radius: 20px;
        }}
        .slider:before {{
            position: absolute; content: ""; height: 12px; width: 12px; left: 3px; bottom: 3px;
            background-color: white; transition: .3s; border-radius: 50%;
        }}
        input:checked + .slider {{ background-color: #FF8C00; }}
        input:checked + .slider:before {{ transform: translateX(14px); }}

        .sync-status {{
            font-size: 11px; font-weight: bold; color: #2E7D32; margin-left: auto; display: flex; align-items: center; gap: 4px;
        }}

        /* 📜 滾動區域 */
        .content-scrollable {{
            flex-grow: 1; overflow-y: auto;
            -webkit-overflow-scrolling: touch; padding: 10px; position: relative;
        }}

        .grid-container {{
            display: grid; grid-template-columns: repeat(7, 1fr); gap: 8px;
            transition: all 0.3s ease;
        }}
        .day-box {{
            border: 1px solid #d0d0d0; border-radius: 6px; background-color: #ffffff;
            min-height: 150px; display: flex; flex-direction: column;
            justify-content: space-between; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            scroll-margin-top: 15px;
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
        .amount-pos {{ color: #2E7D32; font-weight: bold; outline: none; }}
        .amount-neg {{ color: #D9534F; font-weight: bold; outline: none; }}
        .end-balance {{
            background-color: #F2F2F2; border-top: 1px solid #d0d0d0;
            padding: 3px 6px; display: flex; justify-content: space-between; font-size: 11px; font-weight: bold;
        }}
        .rec-icon {{ cursor: pointer; font-size: 10px; opacity: 0.3; }}
        .rec-icon.active {{ opacity: 1.0; color: #1F3864; font-weight: bold; }}
        .del-btn {{ color: #bbb; cursor: pointer; font-size: 10px; margin-left: 3px; }}

        /* 📱 手機版 (Compact) */
        body.mobile-view .grid-container {{
            grid-template-columns: repeat(2, 1fr) !important;
            gap: 5px !important;
        }}
        body.mobile-view .day-box {{
            min-height: 105px !important; border-radius: 4px !important;
        }}
        body.mobile-view .day-header {{ padding: 3px 5px !important; font-size: 10px !important; }}
        body.mobile-view .start-balance, body.mobile-view .end-balance {{ padding: 2px 4px !important; font-size: 9.5px !important; }}
        body.mobile-view .day-content {{ padding: 3px !important; font-size: 9.5px !important; }}
        body.mobile-view .item-row {{ margin-bottom: 2px !important; padding: 1px 2px !important; }}
        body.mobile-view .item-name {{ max-width: 45px !important; }}

        /* ----------------------------------------------------------------- */
        /* 📊 Reports 報表頁面專用 CSS                                      */
        /* ----------------------------------------------------------------- */
        #reportView {{
            display: none; height: 100%; flex-direction: column; background-color: #ffffff;
        }}
        .report-add-bar {{
            padding: 10px 15px; background: #f1f3f5; border-bottom: 1px solid #ddd;
            display: flex; gap: 8px; align-items: center;
        }}
        .report-add-bar input {{
            padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; width: 220px;
        }}
        .report-table-container {{
            flex-grow: 1; overflow: auto; position: relative;
        }}
        table.report-table {{
            border-collapse: separate; border-spacing: 0; width: max-content; font-size: 12px;
        }}
        table.report-table th, table.report-table td {{
            border-bottom: 1px solid #e0e0e0; border-right: 1px solid #e0e0e0;
            padding: 8px 12px; text-align: right; white-space: nowrap;
        }}
        table.report-table th {{
            background: #1F3864; color: white; font-weight: bold; position: sticky; top: 0; z-index: 10;
        }}
        table.report-table th.current-month-header {{
            background: #FF8C00 !important;
        }}
        
        /* 左手邊固定欄 (Freeze Column) Header */
        table.report-table td.freeze-col, table.report-table th.freeze-col {{
            position: sticky; left: 0; z-index: 20; background: #ffffff; text-align: left;
            font-weight: bold; color: #1F3864; border-right: 2px solid #ccc; width: 180px; min-width: 180px;
        }}
        table.report-table th.freeze-col {{
            background: #152744 !important; color: #ffffff !important; z-index: 30;
        }}
        .report-item-row {{ cursor: grab; }}
        .report-item-row.drag-over-row {{
            background-color: #eef4fc !important; border-top: 2px dashed #1F3864;
        }}
        .report-item-cell {{ display: flex; justify-content: space-between; align-items: center; }}
        .drag-handle {{ cursor: grab; margin-right: 6px; opacity: 0.5; font-size: 11px; }}
        .report-del-btn {{ color: #D9534F; cursor: pointer; font-weight: bold; font-size: 12px; margin-left: 8px; }}

        /* 🔥 最底 Total 加總列樣式 */
        table.report-table tfoot td {{
            position: sticky; bottom: 0; background: #f1f3f5; font-weight: bold;
            border-top: 2px solid #1F3864; border-bottom: none; z-index: 10;
        }}
        table.report-table tfoot td.freeze-col {{
            z-index: 30; background: #e9ecef !important; color: #1F3864; font-size: 13px;
        }}

        /* 🪟 Modal 彈窗樣式 */
        .modal-overlay {{
            display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(0, 0, 0, 0.65); z-index: 999999;
            justify-content: center; align-items: center; box-sizing: border-box;
        }}
        .modal-box {{
            background: #ffffff; padding: 20px; border-radius: 12px;
            width: 90%; max-width: 340px; box-shadow: 0 10px 30px rgba(0,0,0,0.4);
            font-size: 13px; box-sizing: border-box; border: 1px solid #ddd;
        }}
        .modal-title {{ font-weight: bold; font-size: 15px; margin-bottom: 10px; color: #1F3864; }}
        .modal-field {{ margin-bottom: 10px; }}
        .modal-field label {{ display: block; font-weight: bold; margin-bottom: 3px; font-size: 11px; }}
        .modal-field input {{ width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }}
        .modal-btns {{ display: flex; justify-content: flex-end; gap: 6px; margin-top: 15px; }}
        .modal-btn {{ padding: 8px 14px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 12px; }}
        .btn-confirm {{ background-color: #1F3864; color: white; }}
        .btn-cancel {{ background-color: #e0e0e0; color: #333; }}
        .btn-danger {{ background-color: #D9534F; color: white; }}
    </style>
</head>
<body>

<div id="app-wrapper">
    <div class="top-bar">
        <button class="btn-action" onclick="switchToCalendarAndToday()">📅 TODAY</button>
        <button class="btn-secondary" onclick="reloadFromCloud(true)">🔄 重新整理</button>
        <button class="btn-secondary" id="undoBtn" onclick="undoStep()" disabled>↩️ Undo (0/10)</button>
        <button class="btn-nav" onclick="switchToReportView()">📊 Reports</button>
        
        <input type="text" class="search-input" id="searchInput" placeholder="🔍 搜尋" oninput="onSearchChange(this.value)">
        
        <div class="toggle-wrapper">
            <span>💻</span>
            <label class="switch">
                <input type="checkbox" id="viewToggle" onchange="toggleViewMode(this.checked)">
                <span class="slider"></span>
            </label>
            <span>📱</span>
        </div>

        <div class="sync-status" id="syncStatus">⏳ 連線中...</div>
    </div>

    <!-- 1️⃣ 日曆檢視主區域 -->
    <div class="content-scrollable" id="calendarView">
        <div class="grid-container" id="grid"></div>
    </div>

    <!-- 2️⃣ 報表檢視主區域 (Reports View) -->
    <div id="reportView">
        <div class="report-add-bar">
            <span>新增監控項目:</span>
            <input type="text" id="newReportItemInput" placeholder="輸入項目名稱 (如: Salary, Rent)">
            <button class="btn-action" onclick="addReportItem()">➕ 新增 Item</button>
        </div>
        <div class="report-table-container" id="reportTableContainer">
            <table class="report-table" id="reportTable">
                <!-- JS 動態生成表格 -->
            </table>
        </div>
    </div>
</div>

<!-- Recursive 設定 Modal -->
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
        <p style="margin: 5px 0 12px 0; line-height: 1.4; font-size: 12px;">這是一個每月重複項目，請選擇更新範圍：</p>
        <div class="modal-btns" style="flex-direction: column; gap: 6px;">
            <button class="modal-btn btn-cancel" style="width:100%;" onclick="confirmRecAmtUpdate('single')">僅修改本次</button>
            <button class="modal-btn btn-confirm" style="width:100%;" onclick="confirmRecAmtUpdate('future')">更新日後所有 (保留過去)</button>
        </div>
    </div>
</div>

<!-- 刪除確認 Modal -->
<div class="modal-overlay" id="deleteConfirmModal">
    <div class="modal-box">
        <div class="modal-title">🗑️ 確認刪除項目</div>
        <p id="deleteConfirmMsg" style="margin: 5px 0 12px 0; font-size: 12px; line-height: 1.4;">確定要刪除此項目嗎？</p>
        <div class="modal-btns" id="deleteModalBtns"></div>
    </div>
</div>

<script>
    const BIN_ID = "{BIN_ID}";
    const MASTER_KEY = "{MASTER_KEY}";

    let store = {initial_json_str};
    if (!store || !store.items) {{
        store = {{ base_initial_balance: 109274, overrides: {{}}, items: [], report_items: ["Salary", "Rent", "Octopus"] }};
    }}
    if (!store.report_items) store.report_items = ["Salary", "Rent", "Octopus"];

    let currentView = "calendar";
    let draggedReportItemIdx = null;

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

    function switchToCalendarAndToday() {{
        document.getElementById('calendarView').style.display = 'block';
        document.getElementById('reportView').style.display = 'none';
        currentView = "calendar";
        scrollToToday();
    }}

    function switchToReportView() {{
        document.getElementById('calendarView').style.display = 'none';
        document.getElementById('reportView').style.display = 'flex';
        currentView = "report";
        renderReportTable();
    }}

    function openModal(id) {{ document.getElementById(id).style.display = 'flex'; }}
    function closeModal(id) {{ document.getElementById(id).style.display = 'none'; }}

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
            if (currentView === "calendar") renderCalendar();
            else renderReportTable();
            saveStore(false);
        }}
    }}

    function updateUndoBtn() {{
        const btn = document.getElementById('undoBtn');
        btn.disabled = historyStack.length === 0;
        btn.innerText = `↩️ Undo (${{historyStack.length}}/10)`;
    }}

    async function reloadFromCloud(showNotice = false) {{
        const statusElem = document.getElementById('syncStatus');
        if (showNotice) statusElem.innerText = "⏳ 載入最新...";

        try {{
            const res = await fetch(`https://api.jsonbin.io/v3/b/${{BIN_ID}}/latest?nocache=${{Date.now()}}`, {{
                headers: {{ "X-Master-Key": MASTER_KEY, "X-Bin-Meta": "false" }}
            }});
            const data = await res.json();
            const rec = data.record || data;
            if (rec && rec.items) {{
                store = rec;
                if (!store.report_items) store.report_items = ["Salary", "Rent", "Octopus"];
                if (currentView === "calendar") renderCalendar();
                else renderReportTable();
                statusElem.innerText = "☁️ 雲端同步完成";
                statusElem.style.color = "#2E7D32";
            }}
        }} catch(e) {{
            statusElem.innerText = "⚠️ 雲端連線失敗";
            statusElem.style.color = "#D9534F";
        }}
    }}

    async function syncToCloud() {{
        const statusElem = document.getElementById('syncStatus');
        statusElem.innerText = "⏳ 儲存中...";
        statusElem.style.color = "#FF8C00";

        try {{
            const response = await fetch(`https://api.jsonbin.io/v3/b/${{BIN_ID}}`, {{
                method: "PUT",
                headers: {{
                    "Content-Type": "application/json",
                    "X-Master-Key": MASTER_KEY
                }},
                body: JSON.stringify(store)
            }});

            if (response.ok) {{
                statusElem.innerText = "☁️ 已同步至 JSONBin";
                statusElem.style.color = "#2E7D32";
                setTimeout(() => reloadFromCloud(false), 500);
            }} else {{
                statusElem.innerText = "⚠️ 雲端同步失敗";
                statusElem.style.color = "#D9534F";
            }}
        }} catch (err) {{
            statusElem.innerText = "⚠️ 網路同步異常";
            statusElem.style.color = "#D9534F";
        }}
    }}

    function saveStore(recordHistory = true) {{
        if (recordHistory) pushHistory();
        syncToCloud();
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
        if (currentView === "calendar") renderCalendar();
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

        (store.items || []).forEach(item => {{
            const amt = parseFloat(item.amount) || 0;
            if (!item.exceptions) item.exceptions = [];

            if (!item.recursive) {{
                if (dailyChange[item.start_date] !== undefined) {{
                    dailyChange[item.start_date] += amt;
                    dailyItems[item.start_date].push(item);
                }}
            }} else {{
                const [sYear, sMonth, sDay] = item.start_date.split('-').map(Number);
                const sDObj = new Date(sYear, sMonth - 1, sDay);
                let eDObj = item.end_date ? new Date(item.end_date.split('-')[0], item.end_date.split('-')[1] - 1, item.end_date.split('-')[2]) : null;

                dates.forEach(d => {{
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

        let currBal = store.base_initial_balance || 109274;
        const weekdayMap = ["S", "M", "T", "W", "T", "F", "S"];

        dates.forEach((d, index) => {{
            const weekIndex = Math.floor(index / 7);
            const dStr = getLocalDateString(d);

            if (store.overrides && store.overrides[dStr] !== undefined) {{
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

    // -------------------------------------------------------------------------
    // 📊 Reports 報表：含 Monthly Total 統計列
    // -------------------------------------------------------------------------
    function renderReportTable() {{
        const table = document.getElementById('reportTable');
        table.innerHTML = '';

        const currDate = new Date();
        const currYear = currDate.getFullYear();
        const currMonth = currDate.getMonth();
        const currMonthKey = `${{currYear}}-${{String(currMonth + 1).padStart(2, '0')}}`;

        // 生成前12個月至後12個月清單
        const monthList = [];
        for (let i = -12; i <= 12; i++) {{
            const mDate = new Date(currYear, currMonth + i, 1);
            const mKey = `${{mDate.getFullYear()}}-${{String(mDate.getMonth() + 1).padStart(2, '0')}}`;
            const mLabel = `${{String(mDate.getMonth() + 1).padStart(2, '0')}}/${{mDate.getFullYear()}}`;
            monthList.push({{ key: mKey, label: mLabel, isCurrent: mKey === currMonthKey }});
        }}

        // 建立計算地圖
        const itemMonthlyData = {{}};
        (store.report_items || []).forEach(rItem => {{
            itemMonthlyData[rItem] = {{}};
            monthList.forEach(m => itemMonthlyData[rItem][m.key] = 0);
        }});

        (store.items || []).forEach(item => {{
            const itemName = item.name.trim();
            const matchedReportItem = (store.report_items || []).find(r => r.toLowerCase() === itemName.toLowerCase());

            if (matchedReportItem) {{
                const amt = parseFloat(item.amount) || 0;
                if (!item.recursive) {{
                    const mKey = item.start_date.substring(0, 7);
                    if (itemMonthlyData[matchedReportItem][mKey] !== undefined) {{
                        itemMonthlyData[matchedReportItem][mKey] += amt;
                    }}
                }} else {{
                    const [sYear, sMonth, sDay] = item.start_date.split('-').map(Number);
                    const sDObj = new Date(sYear, sMonth - 1, sDay);
                    let eDObj = item.end_date ? new Date(item.end_date.split('-')[0], item.end_date.split('-')[1] - 1, item.end_date.split('-')[2]) : null;

                    monthList.forEach(m => {{
                        const [y, mNum] = m.key.split('-').map(Number);
                        const daysInMonth = new Date(y, mNum, 0).getDate();
                        const targetDay = Math.min(sDay, daysInMonth);
                        const instDate = new Date(y, mNum - 1, targetDay);
                        const instDateStr = getLocalDateString(instDate);

                        if (instDate >= sDObj && (!eDObj || instDate <= eDObj)) {{
                            if (!item.exceptions || !item.exceptions.includes(instDateStr)) {{
                                itemMonthlyData[matchedReportItem][m.key] += amt;
                            }}
                        }}
                    }});
                }}
            }}
        }});

        // 生成 <thead>
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');

        const thItem = document.createElement('th');
        thItem.className = 'freeze-col';
        thItem.innerText = 'Item List';
        headerRow.appendChild(thItem);

        monthList.forEach(m => {{
            const th = document.createElement('th');
            th.innerText = m.label;
            if (m.isCurrent) {{
                th.className = 'current-month-header';
                th.innerText += ' (今月)';
                th.id = 'th-current-month';
            }}
            headerRow.appendChild(th);
        }});
        thead.appendChild(headerRow);
        table.appendChild(thead);

        // 生成 <tbody>
        const tbody = document.createElement('tbody');
        const monthlyTotal = {{}};
        monthList.forEach(m => monthlyTotal[m.key] = 0);

        (store.report_items || []).forEach((rItem, idx) => {{
            const row = document.createElement('tr');
            row.className = 'report-item-row';
            row.draggable = true;

            row.addEventListener('dragstart', (e) => {{
                draggedReportItemIdx = idx;
                e.dataTransfer.effectAllowed = 'move';
            }});

            row.addEventListener('dragover', (e) => {{
                e.preventDefault();
                row.classList.add('drag-over-row');
            }});

            row.addEventListener('dragleave', () => {{
                row.classList.remove('drag-over-row');
            }});

            row.addEventListener('drop', (e) => {{
                e.preventDefault();
                row.classList.remove('drag-over-row');
                if (draggedReportItemIdx !== null && draggedReportItemIdx !== idx) {{
                    const movedItem = store.report_items.splice(draggedReportItemIdx, 1)[0];
                    store.report_items.splice(idx, 0, movedItem);
                    draggedReportItemIdx = null;
                    renderReportTable();
                    saveStore();
                }}
            }});

            const tdItem = document.createElement('td');
            tdItem.className = 'freeze-col';
            tdItem.innerHTML = `
                <div class="report-item-cell">
                    <span><span class="drag-handle">☰</span>${{rItem}}</span>
                    <span class="report-del-btn" onclick="deleteReportItem('${{rItem}}')">✖</span>
                </div>
            `;
            row.appendChild(tdItem);

            monthList.forEach(m => {{
                const td = document.createElement('td');
                const val = itemMonthlyData[rItem][m.key] || 0;
                monthlyTotal[m.key] += val; // 累加到當月 Total

                if (val === 0) {{
                    td.innerText = '-';
                    td.style.color = '#ccc';
                }} else {{
                    td.innerText = (val > 0 ? '+' : '') + Math.round(val).toLocaleString();
                    td.style.color = val < 0 ? '#D9534F' : '#2E7D32';
                    td.style.fontWeight = 'bold';
                }}
                row.appendChild(td);
            }});
            tbody.appendChild(row);
        }});
        table.appendChild(tbody);

        // 🔥 生成 <tfoot>（表格最底 Monthly Total 列）
        const tfoot = document.createElement('tfoot');
        const footRow = document.createElement('tr');

        const tdTotalTitle = document.createElement('td');
        tdTotalTitle.className = 'freeze-col';
        tdTotalTitle.innerText = 'Total';
        footRow.appendChild(tdTotalTitle);

        monthList.forEach(m => {{
            const td = document.createElement('td');
            const totalVal = monthlyTotal[m.key] || 0;
            if (totalVal === 0) {{
                td.innerText = '-';
                td.style.color = '#888';
            }} else {{
                td.innerText = (totalVal > 0 ? '+' : '') + Math.round(totalVal).toLocaleString();
                td.style.color = totalVal < 0 ? '#D9534F' : '#2E7D32';
            }}
            footRow.appendChild(td);
        }});
        tfoot.appendChild(footRow);
        table.appendChild(tfoot);

        // 🚀 自動置中對齊至當月 (Month of Today)
        setTimeout(() => {{
            const container = document.getElementById('reportTableContainer');
            const currTh = document.getElementById('th-current-month');
            if (container && currTh) {{
                container.scrollLeft = currTh.offsetLeft - 180;
            }}
        }}, 100);
    }}

    function addReportItem() {{
        const input = document.getElementById('newReportItemInput');
        const val = input.value.trim();
        if (val) {{
            if (!store.report_items) store.report_items = [];
            if (!store.report_items.includes(val)) {{
                store.report_items.push(val);
                input.value = '';
                renderReportTable();
                saveStore();
            }}
        }}
    }}

    function deleteReportItem(rItem) {{
        if (confirm(`確定要在報表中移除 "${{rItem}}" 嗎？`)) {{
            store.report_items = store.report_items.filter(i => i !== rItem);
            renderReportTable();
            saveStore();
        }}
    }}

    // -------------------------------------------------------------------------
    // 日曆常用操作邏輯
    // -------------------------------------------------------------------------
    function moveItem(id, sourceDate, newDate) {{
        const item = store.items.find(i => i.id === id);
        if (!item) return;

        if (!item.recursive) {{
            item.start_date = newDate;
        }} else {{
            if (!item.exceptions) item.exceptions = [];
            if (!item.exceptions.includes(sourceDate)) item.exceptions.push(sourceDate);
            const newId = store.items.length ? Math.max(...store.items.map(i => i.id)) + 1 : 1;
            store.items.push({{ id: newId, name: item.name, amount: item.amount, start_date: newDate, end_date: "", recursive: false, exceptions: [] }});
        }}
        renderCalendar(); saveStore();
    }}

    let pendingAmtEdit = null;
    function handleAmtEdit(id, currentDate, rawAmt) {{
        const item = store.items.find(i => i.id === id);
        const val = parseFloat(rawAmt.replace(/,/g, '').replace(/\+/g, ''));
        if (item && !isNaN(val) && val !== item.amount) {{
            if (item.recursive) {{
                pendingAmtEdit = {{ id, currentDate, val }}; openModal('recAmtConfirmModal');
            }} else {{
                item.amount = val; renderCalendar(); saveStore();
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
                if (!target.exceptions.includes(currentDate)) target.exceptions.push(currentDate);
                const newId = store.items.length ? Math.max(...store.items.map(i => i.id)) + 1 : 1;
                store.items.push({{ id: newId, name: target.name, amount: val, start_date: currentDate, end_date: "", recursive: false, exceptions: [] }});
            }} else if (mode === 'future') {{
                const prevDateObj = new Date(currentDate);
                prevDateObj.setDate(prevDateObj.getDate() - 1);
                target.end_date = getLocalDateString(prevDateObj);
                const newId = store.items.length ? Math.max(...store.items.map(i => i.id)) + 1 : 1;
                store.items.push({{ id: newId, name: target.name, amount: val, start_date: currentDate, end_date: "", recursive: true, exceptions: [] }});
            }}
        }}
        pendingAmtEdit = null; renderCalendar(); saveStore();
    }}

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
                <button class="modal-btn btn-danger" style="width:100%; margin-top:4px;" onclick="executeDelete('single')">僅刪除本次</button>
                <button class="modal-btn btn-danger" style="width:100%; background-color:#8B0000;" onclick="executeDelete('future')">刪除本次及往後所有</button>
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
                        if (!target.exceptions) target.exceptions = [];
                        if (!target.exceptions.includes(currentDate)) target.exceptions.push(currentDate);
                    }} else if (mode === 'future') {{
                        const prevDateObj = new Date(currentDate);
                        prevDateObj.setDate(prevDateObj.getDate() - 1);
                        target.end_date = getLocalDateString(prevDateObj);
                    }}
                }}
            }}
            deletingInfo = null; renderCalendar(); saveStore();
        }}
    }}

    function updateStartBal(dateStr, rawVal) {{
        const val = parseFloat(rawVal.replace(/,/g, '').replace(/\+/g, ''));
        if (!isNaN(val)) {{
            if (!store.overrides) store.overrides = {{}};
            store.overrides[dateStr] = val;
            renderCalendar(); saveStore();
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
            closeModal('recSettingsModal'); renderCalendar(); saveStore();
        }}
    }}

    function addItem(dateStr) {{
        if (!store.items) store.items = [];
        const newId = store.items.length ? Math.max(...store.items.map(i => i.id)) + 1 : 1;
        store.items.push({{ id: newId, name: "New Item", amount: -100, start_date: dateStr, end_date: "", recursive: false, exceptions: [] }});
        renderCalendar(); saveStore();
    }}

    function updateName(id, newName) {{
        const item = store.items.find(i => i.id === id);
        if (item && newName.trim()) {{
            item.name = newName.trim(); saveStore();
        }}
    }}

    function scrollToToday() {{
        const elem = document.getElementById('day-' + todayStr);
        if (elem) elem.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
    }}

    // 🚀 初始化渲染
    renderCalendar();
    
    reloadFromCloud(false).then(() => {{
        setTimeout(scrollToToday, 200);
    }});
    setTimeout(scrollToToday, 400);
</script>
</body>
</html>
"""

st.markdown("""
    <style>
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container { padding: 0rem !important; }
        iframe { border: none; height: 100vh !important; width: 100vw !important; }
    </style>
""", unsafe_allow_html=True)

components.html(html_content, height=800, scrolling=False)
