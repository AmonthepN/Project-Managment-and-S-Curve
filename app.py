"""
S-Curve Project Monitoring System — Streamlit Web App
Author: Faculty of Engineering, Chiang Mai University
Run:  streamlit run app.py
"""
import json, os, re, io, csv, sqlite3
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="S-Curve Monitor", page_icon="📈",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp{background-color:#F5F7FA;color:#1F2937}
[data-testid="stSidebar"]{background-color:#FFFFFF;border-right:1px solid #E5E7EB}
[data-testid="stSidebar"] *{color:#374151!important}
.kpi-card{background:#FFFFFF;border-radius:12px;padding:18px 16px;text-align:center;margin:4px 0;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.kpi-num{font-size:2.2rem;font-weight:700;color:#2563EB}
.kpi-label{font-size:.75rem;color:#6B7280;letter-spacing:1px;margin-top:4px}
.st-done{background:#DCFCE7;color:#15803D;padding:3px 10px;border-radius:20px;font-size:.82rem;font-weight:600}
.st-prog{background:#DBEAFE;color:#1D4ED8;padding:3px 10px;border-radius:20px;font-size:.82rem;font-weight:600}
.st-pend{background:#FEF9C3;color:#B45309;padding:3px 10px;border-radius:20px;font-size:.82rem;font-weight:600}
.st-delay{background:#FEE2E2;color:#DC2626;padding:3px 10px;border-radius:20px;font-size:.82rem;font-weight:600}
.st-none{background:#F3F4F6;color:#6B7280;padding:3px 10px;border-radius:20px;font-size:.82rem;font-weight:600}
.sec{font-size:1.05rem;font-weight:700;color:#15803D;letter-spacing:2px;border-bottom:2px solid #D1FAE5;padding-bottom:6px;margin:20px 0 12px 0}
.stButton>button{background:#2563EB;color:#FFFFFF;font-weight:700;border:none;border-radius:8px;padding:8px 24px}
.stButton>button:hover{background:#1D4ED8}
div[data-testid="stMetricValue"]{color:#2563EB!important;font-size:1.8rem!important}
div[data-testid="stMetricLabel"]{color:#6B7280!important}
[data-testid="stWidgetLabel"],label,.stTextInput label,.stSelectbox label,.stNumberInput label,
.stTextArea label,.stDateInput label,.stFileUploader label,.stCheckbox label,.stRadio label,
.stSlider label,.stMultiSelect label{color:#374151!important;font-weight:600!important}
[data-testid="stExpander"] summary,[data-testid="stExpander"] summary *{color:#1F2937!important}
[data-testid="stTabs"] [data-testid="stMarkdownContainer"] p{color:#374151}
.stDataFrame thead th{background:#F3F4F6!important;color:#1F2937!important}
input,textarea,select{color:#1F2937!important;background:#FFFFFF!important}
[data-testid="stSelectbox"] div,[data-testid="stMultiSelect"] div{color:#1F2937!important}
p,li,span:not([class]){color:#1F2937}
</style>""", unsafe_allow_html=True)

# ── Project Database (SQLite) ─────────────────────────────────────────────────
DB_FILE = "projects.db"

def db_connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def db_init():
    """Create tables and migrate from manifest JSON if needed."""
    conn = db_connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            key         TEXT    UNIQUE,
            project_name     TEXT,
            project_name_th  TEXT,
            doc         TEXT,
            phase       TEXT,
            n_activities     INTEGER DEFAULT 0,
            total_budget     REAL    DEFAULT 0,
            data_json   TEXT,
            created_at  TEXT,
            updated_at  TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS save_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            db_key       TEXT,
            project_name TEXT,
            action       TEXT,
            detail       TEXT,
            timestamp    TEXT
        )
    """)
    conn.commit()
    # Migrate from project_manifest.json + JSON files if DB is empty
    if conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 0:
        mf = "projects/project_manifest.json"
        if os.path.exists(mf):
            with open(mf, encoding="utf-8") as f:
                manifest = json.load(f)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for e in manifest:
                fpath = os.path.join("projects", e["filename"])
                d_json = ""
                if os.path.exists(fpath):
                    with open(fpath, encoding="utf-8") as pf:
                        d_json = pf.read()
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO projects
                        (key,project_name,project_name_th,doc,phase,n_activities,total_budget,data_json,created_at,updated_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?)
                    """, (e["key"], e["project_name"], e.get("project_name_th",""),
                          e["doc"], e.get("phase",""), e["n_activities"],
                          e.get("total_budget",0), d_json, now, now))
                except Exception:
                    pass
            conn.commit()
    conn.close()

def db_list(sort="updated_at", search=""):
    """Return all projects sorted by updated_at DESC."""
    conn = db_connect()
    q = "SELECT id,key,project_name,project_name_th,doc,phase,n_activities,total_budget,created_at,updated_at FROM projects"
    params = []
    if search:
        q += " WHERE project_name LIKE ? OR doc LIKE ? OR phase LIKE ?"
        params = [f"%{search}%"]*3
    q += f" ORDER BY {sort} DESC"
    rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    conn.close()
    return rows

def db_get(key):
    conn = db_connect()
    r = conn.execute("SELECT data_json FROM projects WHERE key=?", (key,)).fetchone()
    conn.close()
    return json.loads(r["data_json"]) if r and r["data_json"] else None

def db_save(key, project_name, project_name_th, doc, phase, proj_data):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    n = len(proj_data.get("activities", []))
    b = proj_data.get("total_budget", 0)
    j = json.dumps(proj_data, ensure_ascii=False)
    conn = db_connect()
    conn.execute("""
        INSERT INTO projects (key,project_name,project_name_th,doc,phase,n_activities,total_budget,data_json,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(key) DO UPDATE SET
            project_name=excluded.project_name,
            project_name_th=excluded.project_name_th,
            doc=excluded.doc, phase=excluded.phase,
            n_activities=excluded.n_activities,
            total_budget=excluded.total_budget,
            data_json=excluded.data_json,
            updated_at=excluded.updated_at
    """, (key, project_name, project_name_th, doc, phase, n, b, j, now, now))
    conn.commit()
    conn.close()

def db_touch(key, project_name=""):
    """Update updated_at timestamp (on Load)."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = db_connect()
    if not project_name:
        r = conn.execute("SELECT project_name FROM projects WHERE key=?", (key,)).fetchone()
        project_name = r["project_name"] if r else ""
    conn.execute("UPDATE projects SET updated_at=? WHERE key=?", (now, key))
    conn.commit(); conn.close()
    db_log(key, project_name, "▶ Loaded", "Project loaded into active workspace")

def db_delete(key):
    conn = db_connect()
    conn.execute("DELETE FROM projects WHERE key=?", (key,))
    conn.commit(); conn.close()

def db_log(db_key, project_name, action, detail=""):
    """Write one entry to the activity log."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = db_connect()
    conn.execute(
        "INSERT INTO save_log (db_key,project_name,action,detail,timestamp) VALUES (?,?,?,?,?)",
        (db_key or "", project_name or "", action, detail, now))
    conn.commit(); conn.close()

def db_get_log(limit=50, db_key=None):
    """Return recent log entries, optionally filtered to one project."""
    conn = db_connect()
    if db_key:
        rows = conn.execute(
            "SELECT * FROM save_log WHERE db_key=? ORDER BY timestamp DESC LIMIT ?",
            (db_key, limit)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM save_log ORDER BY timestamp DESC LIMIT ?",
            (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

db_init()   # run once on startup

# ── Data ─────────────────────────────────────────────────────────────────────
DATA_FILE = "project_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            d = json.load(f)
        # Ensure _db_key is always present after loading from disk
        if not d.get("_db_key"):
            raw = (d.get("project_name","project") + "_" + d.get("start_date","")[:7])
            d["_db_key"]   = re.sub(r'[^A-Za-z0-9_]', '_', raw)[:40]
            d["_db_doc"]   = d.get("_db_doc", "CUSTOM")
            d["_db_phase"] = d.get("_db_phase", "Custom")
            # Write key back so it persists
            with open(DATA_FILE,"w",encoding="utf-8") as f:
                json.dump(d,f,ensure_ascii=False,indent=2)
        return d
    return {"project_name":"Demo Project","project_name_th":"โครงการตัวอย่าง",
            "contract_no":"SF-NRCT-FY2569","project_owner":"NRCT",
            "contractor":"Faculty of Engineering, CMU","start_date":"2025-10-01",
            "end_date":"2026-09-30","total_budget":8166000,"n_months":12,"activities":[]}

def save_data(d):
    # ── Auto-stamp _db_key if missing so EVERY save syncs to SQLite ──────────
    if not d.get("_db_key"):
        raw = (d.get("project_name","project") + "_" + d.get("start_date","")[:7])
        d["_db_key"]   = re.sub(r'[^A-Za-z0-9_]', '_', raw)[:40]
        d["_db_doc"]   = d.get("_db_doc", "CUSTOM")
        d["_db_phase"] = d.get("_db_phase", "Custom")

    with open(DATA_FILE,"w",encoding="utf-8") as f: json.dump(d,f,ensure_ascii=False,indent=2)
    st.cache_data.clear()

    # Always sync to SQLite
    _key = d["_db_key"]
    n = len(d.get("activities",[]))
    db_save(_key, d.get("project_name",""), d.get("project_name_th",""),
            d.get("_db_doc","CUSTOM"), d.get("_db_phase","Custom"), d)
    db_log(_key, d.get("project_name",""), "💾 Saved",
           f"{n} activities | budget ฿{d.get('total_budget',0):,.0f}")

@st.cache_data
def get_labels(start_iso, n):
    base=datetime.strptime(start_iso,"%Y-%m-%d")
    return [(base+relativedelta(months=m)).strftime("%b %Y") for m in range(n)]

def cur_month(start_iso,n):
    base=datetime.strptime(start_iso,"%Y-%m-%d"); t=datetime.today()
    return max(1,min((t.year-base.year)*12+(t.month-base.month)+1,n))

def compute(data):
    n=data["n_months"]; pm=[0.0]*n; am=[0.0]*n
    for a in data["activities"]:
        s,e=int(a["start_month"]),int(a["end_month"]); dur=max(1,e-s+1); mp=a["weight"]/dur
        for m in range(s,min(e+1,n+1)):
            pm[m-1]+=mp
            v=a.get("actuals",{}).get(str(m))
            if v is not None: am[m-1]+=float(v)*a["weight"]/100/dur
    cp=ca=0.0; cump=[]; cuma=[]
    for i in range(n):
        cp+=pm[i]; cump.append(round(cp,2))
        ca+=am[i]; cuma.append(round(ca,2) if (am[i]>0 or ca>0) else None)
    return cump,cuma

def build_excel(data, cump, cuma, labels):
    """Build a formatted .xlsx workbook and return bytes."""
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
    import io as _io

    wb = openpyxl.Workbook()
    acts = data.get("activities", [])
    N    = data.get("n_months", 12)

    # ── Colour palette ────────────────────────────────────────────────────────
    HDR_BG  = PatternFill("solid", fgColor="2D3747")
    HDR_FG  = Font(color="E8ECF0", bold=True, size=10)
    LOCK_BG = PatternFill("solid", fgColor="3D4557")
    EDIT_BG = PatternFill("solid", fgColor="1A2030")
    CUR_BG  = PatternFill("solid", fgColor="5A3A00")   # orange tint = current month
    DONE_BG = PatternFill("solid", fgColor="2A5E3A")
    PROG_BG = PatternFill("solid", fgColor="2A4E2A")
    DEL_BG  = PatternFill("solid", fgColor="5A1A1A")
    THIN    = Border(
        left=Side(style="thin", color="555B6E"),
        right=Side(style="thin", color="555B6E"),
        top=Side(style="thin", color="555B6E"),
        bottom=Side(style="thin", color="555B6E"))
    WH  = Font(color="E8ECF0", size=9)
    GRY = Font(color="9BA3AF", size=9)

    def _ap(ws, r, c, v, fill=None, font=None, align=None, num_fmt=None):
        cell = ws.cell(row=r, column=c, value=v)
        if fill:    cell.fill   = fill
        if font:    cell.font   = font
        if align:   cell.alignment = align
        if num_fmt: cell.number_format = num_fmt
        cell.border = THIN
        return cell

    center = Alignment(horizontal="center", vertical="center", wrap_text=False)
    left   = Alignment(horizontal="left",   vertical="center", wrap_text=False)

    # ── Sheet 1 : Progress (editable) ────────────────────────────────────────
    ws = wb.active
    ws.title = "Progress"
    ws.freeze_panes = "F2"          # freeze cols A-E, row 1
    ws.sheet_view.showGridLines = False

    # Header row
    fixed_hdrs = ["No", "Activity", "Wt%", "Cost (฿)", "Status"]
    month_hdrs = [labels[m] if m < len(labels) else f"M{m+1}" for m in range(N)]
    all_hdrs   = fixed_hdrs + month_hdrs
    cm_idx     = cur_month(data["start_date"], N)   # 1-based

    for ci, h in enumerate(all_hdrs, 1):
        is_cm = (ci == 5 + cm_idx)
        bg = CUR_BG if is_cm else HDR_BG
        _ap(ws, 1, ci, h, fill=bg, font=HDR_FG, align=center)

    # Column widths
    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 40
    ws.column_dimensions["C"].width = 7
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 14
    for ci in range(6, 6+N):
        ws.column_dimensions[get_column_letter(ci)].width = 9

    # Status dropdown validation
    dv = DataValidation(
        type="list",
        formula1='"Not Started,In Progress,Pending,Completed,Delayed,Cancelled"',
        showDropDown=False)
    ws.add_data_validation(dv)

    sopts = ["Not Started","In Progress","Pending","Completed","Delayed","Cancelled"]

    for ri, a in enumerate(acts, 2):
        sk = next((k for k in sopts if k in a.get("status","")), sopts[0])
        # Status row colour
        if   "Completed"   in sk: row_bg = DONE_BG
        elif "In Progress" in sk: row_bg = PROG_BG
        elif "Delayed"     in sk: row_bg = DEL_BG
        else:                     row_bg = EDIT_BG

        _ap(ws, ri, 1, a.get("no",""),  fill=LOCK_BG, font=GRY,  align=center)
        _ap(ws, ri, 2, a.get("name",""),fill=LOCK_BG, font=WH,   align=left)
        _ap(ws, ri, 3, a.get("weight",0),fill=LOCK_BG,font=GRY,  align=center, num_fmt="0.0")
        _ap(ws, ri, 4, a.get("planned_cost",0), fill=LOCK_BG, font=GRY, align=center, num_fmt='#,##0')
        _ap(ws, ri, 5, sk,               fill=row_bg, font=WH,   align=center)
        dv.add(ws.cell(row=ri, column=5))

        for mi in range(1, N+1):
            ci = 5 + mi
            in_range = a["start_month"] <= mi <= a["end_month"]
            val = float(a.get("actuals",{}).get(str(mi), 0)) if in_range else None
            is_cm_col = (mi == cm_idx)
            bg = CUR_BG if is_cm_col else (EDIT_BG if in_range else LOCK_BG)
            fn = WH if in_range else GRY
            cell = _ap(ws, ri, ci, val, fill=bg, font=fn, align=center, num_fmt="0")
            if not in_range:
                cell.protection = openpyxl.styles.Protection(locked=True)

        ws.row_dimensions[ri].height = 18

    ws.row_dimensions[1].height = 22

    # ── Sheet 2 : S-Curve Data (reference) ──────────────────────────────────
    ws2 = wb.create_sheet("S-Curve Data")
    ws2.freeze_panes = "B2"
    ws2.sheet_view.showGridLines = False
    for ci, h in enumerate(["Month","Plan (%)","Actual (%)","SV","SPI"], 1):
        _ap(ws2, 1, ci, h, fill=HDR_BG, font=HDR_FG, align=center)
    ws2.column_dimensions["A"].width = 14
    for col in ["B","C","D","E"]: ws2.column_dimensions[col].width = 12
    for i, lbl in enumerate(labels):
        pv = cump[i]
        ev = cuma[i]
        sv_ = round(ev-pv,2) if ev is not None else None
        spi_= round(ev/pv,2) if (ev is not None and pv>0) else None
        row = [lbl, pv, ev, sv_, spi_]
        for ci, v in enumerate(row, 1):
            _ap(ws2, i+2, ci, v, fill=EDIT_BG, font=WH, align=center, num_fmt="0.00")

    # ── Sheet 3 : Project Info ───────────────────────────────────────────────
    ws3 = wb.create_sheet("Project Info")
    ws3.sheet_view.showGridLines = False
    ws3.column_dimensions["A"].width = 22
    ws3.column_dimensions["B"].width = 50
    fields = [
        ("Project Name (EN)", data.get("project_name","")),
        ("Project Name (TH)", data.get("project_name_th","")),
        ("Contract No.",      data.get("contract_no","")),
        ("Project Owner",     data.get("project_owner","")),
        ("Contractor",        data.get("contractor","")),
        ("Start Date",        data.get("start_date","")),
        ("End Date",          data.get("end_date","")),
        ("Months",            data.get("n_months","")),
        ("Total Budget (THB)",data.get("total_budget",0)),
        ("No. Activities",    len(acts)),
    ]
    for ri, (k, v) in enumerate(fields, 1):
        _ap(ws3, ri, 1, k, fill=HDR_BG, font=HDR_FG, align=left)
        _ap(ws3, ri, 2, v, fill=EDIT_BG, font=WH,    align=left)

    buf = _io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

SCLS={"Completed":"st-done","In Progress":"st-prog","Pending":"st-pend",
      "Delayed":"st-delay","Not Started":"st-none"}
SMAP={"Completed":"✅ Completed","In Progress":"🚧 In Progress","Pending":"⏳ Pending",
      "Delayed":"💤 Delayed","Not Started":"❌ Not Started","Cancelled":"🚫 Cancelled"}
SCOL={"Completed":"#16A34A","In Progress":"#2563EB","Pending":"#D97706",
      "Delayed":"#DC2626","Not Started":"#9CA3AF"}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 S-Curve Monitor")
    st.markdown("---")
    page=st.radio("Navigate",[
        "🏠 Dashboard",          # 1. Overview + alerts
        "📋 Process Guide",      # 2. Read how it works
        "⚙️ Project Setup",      # 3. Configure + Import WBS
        "📝 Update Progress",    # 4. Enter actuals
        "📈 S-Curve",            # 5. Plan vs Actual curve
        "📅 Gantt",              # 6. Schedule view
        "📊 EVM Indicators",     # 7. Performance metrics
    ])
    st.markdown("---")
    data=load_data()
    cm=cur_month(data["start_date"],data["n_months"])
    st.markdown(f"**📅 Current Month:** M{cm}")
    st.markdown(f"**🗓️ Today:** {date.today().strftime('%d %b %Y')}")
    st.markdown("---")
    # Active project indicator in sidebar
    _akey = data.get("_db_key","")
    _aname = data.get("project_name","—")
    st.markdown(
        f"<div style='background:#DCFCE7;border-radius:6px;padding:7px 10px;margin-bottom:4px;border:1px solid #BBF7D0'>"
        f"<div style='color:#15803D;font-size:.7rem;font-weight:700;letter-spacing:1px'>▶ ACTIVE PROJECT</div>"
        f"<div style='color:#1F2937;font-size:.8rem;margin-top:3px'>{_aname[:38]}</div>"
        f"</div>", unsafe_allow_html=True)
    st.caption("Ping River Basin • Chiang Mai University © 2026")

data=load_data()
acts=data["activities"]; N=data["n_months"]; SI=data["start_date"]
labels=get_labels(SI,N)
cump,cuma=compute(data)
cm=cur_month(SI,N)

# ── DASHBOARD ─────────────────────────────────────────────────────────────────
if page=="🏠 Dashboard":
    st.markdown(f"# 🏠 Dashboard")
    st.markdown(f"**{data['project_name']}**  \n<small>{data.get('project_name_th','')}</small>",unsafe_allow_html=True)
    st.markdown("---")

    total=len(acts)
    done=sum(1 for a in acts if "Completed" in a.get("status",""))
    prog=sum(1 for a in acts if "In Progress" in a.get("status",""))
    delay=sum(1 for a in acts if "Delayed" in a.get("status",""))
    pv=cump[cm-1] if cm<=N else cump[-1]
    ev=next((cuma[i] for i in range(cm-1,-1,-1) if cuma[i] is not None),0.0) or 0.0
    spi=round(ev/pv,2) if pv>0 else None; sv=round(ev-pv,2) if pv>0 else None

    c1,c2,c3,c4,c5,c6=st.columns(6)
    cards=[
        (c1,str(total),"TOTAL TASKS","#FFFFFF","#2563EB"),
        (c2,str(done),"✅ COMPLETED","#F0FDF4","#16A34A"),
        (c3,str(prog),"🚧 IN PROGRESS","#EFF6FF","#1D4ED8"),
        (c4,str(delay),"💤 DELAYED","#FFF1F2","#DC2626"),
        (c5,f"{spi:.2f}" if spi else "—","SPI","#FFFFFF",
         "#16A34A" if spi and spi>=1 else "#D97706" if spi and spi>=0.8 else "#DC2626"),
        (c6,f"{sv:+.1f}%" if sv is not None else "—","SCHEDULE VAR.","#FFFFFF",
         "#16A34A" if sv and sv>=0 else "#DC2626"),
    ]
    for col,val,lbl,bg,fg in cards:
        col.markdown(f'<div class="kpi-card" style="background:{bg}"><div class="kpi-num" style="color:{fg}">{val}</div><div class="kpi-label">{lbl}</div></div>',unsafe_allow_html=True)

    st.markdown("")
    cl,cr=st.columns([2,1])
    with cl:
        st.markdown('<div class="sec">S - C U R V E    O V E R V I E W</div>',unsafe_allow_html=True)
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=labels,y=cump,name="Plan",fill="tozeroy",
            fillcolor="rgba(37,99,235,.10)",line=dict(color="#2563EB",width=3),
            mode="lines+markers",marker=dict(size=7),
            hovertemplate="<b>%{x}</b><br>Plan: %{y:.1f}%<extra></extra>"))
        ax=[labels[i] for i,v in enumerate(cuma) if v is not None]
        ay=[v for v in cuma if v is not None]
        if ay:
            fig.add_trace(go.Scatter(x=ax,y=ay,name="Actual",fill="tozeroy",
                fillcolor="rgba(22,163,74,.10)",line=dict(color="#16A34A",width=3),
                mode="lines+markers",marker=dict(size=8,symbol="diamond"),
                hovertemplate="<b>%{x}</b><br>Actual: %{y:.1f}%<extra></extra>"))
        if cm<=N:
            fig.add_vline(x=labels[cm-1],line_dash="dash",line_color="#D97706")
            fig.add_annotation(x=labels[cm-1],y=105,text="TODAY",showarrow=False,
                font=dict(color="#D97706",size=11),xanchor="left")
        fig.update_layout(paper_bgcolor="#FFFFFF",plot_bgcolor="#F9FAFB",
            font_color="#1F2937",height=280,margin=dict(l=10,r=10,t=10,b=10),
            xaxis=dict(gridcolor="#E5E7EB"),yaxis=dict(gridcolor="#E5E7EB",range=[0,105]),
            legend=dict(bgcolor="#FFFFFF"),hovermode="x unified")
        st.plotly_chart(fig,use_container_width=True)

    with cr:
        st.markdown('<div class="sec">A C T I V I T I E S</div>',unsafe_allow_html=True)
        for a in acts:
            st_raw = a.get("status","Not Started")
            sk = next((k for k in SCLS if k in st_raw),"Not Started")
            is_active = a["start_month"] <= cm <= a["end_month"]
            # Highlight border for currently active activities
            border_style = "border-left:3px solid #D97706;padding-left:6px;" if is_active else "border-left:3px solid #E5E7EB;padding-left:6px;"
            active_dot = '<span style="color:#D97706;font-size:.7rem;margin-right:3px">●</span>' if is_active else ''
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:5px 0;border-bottom:1px solid #E5E7EB;{border_style}">'
                f'<span style="color:#1F2937;font-size:.82rem">{active_dot}{a["no"]}. {a["name"][:32]}…</span>'
                f'<span class="{SCLS[sk]}">{sk}</span></div>',
                unsafe_allow_html=True)

    # ── ACTIVE THIS MONTH spotlight ───────────────────────────────────────────
    active_acts = [a for a in acts if a["start_month"] <= cm <= a["end_month"]]
    if active_acts:
        st.markdown(f'<div class="sec">⏰ A C T I V E &nbsp; T H I S &nbsp; M O N T H &nbsp;— M{cm} &nbsp;({labels[cm-1] if cm<=N else ""})</div>',
                    unsafe_allow_html=True)
        cols_h = st.columns(min(len(active_acts), 3))
        for idx, a in enumerate(active_acts):
            st_raw = a.get("status","Not Started")
            sk = next((k for k in SCLS if k in st_raw),"Not Started")
            actual_cm = float(a.get("actuals",{}).get(str(cm), 0))
            # Health color
            if "Completed" in st_raw:    hcol, hlbl = "#F0FDF4", "✅ Done"
            elif "Delayed" in st_raw:    hcol, hlbl = "#FFF1F2", "⚠️ Delayed"
            elif actual_cm > 0:          hcol, hlbl = "#EFF6FF", "🚧 Active"
            else:                        hcol, hlbl = "#FFFBEB", "⏳ Needs Input"
            col = cols_h[idx % 3]
            col.markdown(f"""
<div style="background:{hcol};border:1px solid #D97706;border-radius:10px;padding:12px 14px;margin:4px 0">
  <div style="color:#B45309;font-size:.72rem;font-weight:700;letter-spacing:1px">{a['no']} &nbsp;·&nbsp; Wt {a['weight']}%</div>
  <div style="color:#1F2937;font-size:.88rem;font-weight:600;margin:4px 0">{a['name'][:50]}</div>
  <div style="display:flex;justify-content:space-between;margin-top:6px">
    <span style="color:#6B7280;font-size:.78rem">M{a['start_month']}→M{a['end_month']}</span>
    <span style="color:#15803D;font-size:.78rem;font-weight:600">{hlbl}</span>
  </div>
  <div style="background:#E5E7EB;border-radius:4px;height:6px;margin-top:6px">
    <div style="background:#D97706;height:6px;border-radius:4px;width:{min(actual_cm,100):.0f}%"></div>
  </div>
  <div style="color:#6B7280;font-size:.72rem;margin-top:2px">M{cm} actual: {actual_cm:.0f}%</div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    p1,p2,p3,p4,p5=st.columns(5)
    p1.metric("Contract",data.get("contract_no","—"))
    p2.metric("Start",data["start_date"]); p3.metric("End",data["end_date"])
    p4.metric("Budget","฿{:,.0f}".format(data["total_budget"]))
    total_planned_cost = sum(a.get("planned_cost",0) for a in acts)
    p5.metric("WBS Cost","฿{:,.0f}".format(total_planned_cost),
              delta=f"฿{total_planned_cost - data['total_budget']:+,.0f}" if total_planned_cost else None,
              delta_color="inverse")

# ── S-CURVE ───────────────────────────────────────────────────────────────────
elif page=="📈 S-Curve":
    st.markdown("# 📈 S-Curve: Plan vs Actual")
    st.markdown("---")
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=labels,y=cump,name="Planned (%)",fill="tozeroy",
        fillcolor="rgba(37,99,235,.10)",line=dict(color="#2563EB",width=3),
        mode="lines+markers",marker=dict(size=8),
        hovertemplate="<b>%{x}</b><br>Plan: %{y:.1f}%<extra></extra>"))
    ax=[labels[i] for i,v in enumerate(cuma) if v is not None]
    ay=[v for v in cuma if v is not None]
    if ay:
        fig.add_trace(go.Scatter(x=ax,y=ay,name="Actual (%)",fill="tozeroy",
            fillcolor="rgba(22,163,74,.10)",line=dict(color="#16A34A",width=3),
            mode="lines+markers",marker=dict(size=9,symbol="diamond"),
            hovertemplate="<b>%{x}</b><br>Actual: %{y:.1f}%<extra></extra>"))
    if cm<=N:
        fig.add_vline(x=labels[cm-1],line_dash="dash",line_color="#D97706")
        fig.add_annotation(x=labels[cm-1],y=105,text=f"M{cm} TODAY",showarrow=False,
            font=dict(color="#D97706",size=11),xanchor="left")
    fig.update_layout(paper_bgcolor="#FFFFFF",plot_bgcolor="#F9FAFB",
        font=dict(color="#1F2937",size=13),height=460,margin=dict(l=20,r=20,t=30,b=20),
        xaxis=dict(title="Month",gridcolor="#E5E7EB",tickangle=-30),
        yaxis=dict(title="Cumulative Progress (%)",gridcolor="#E5E7EB",range=[0,105],ticksuffix="%"),
        legend=dict(bgcolor="#FFFFFF",bordercolor="#2563EB",borderwidth=1),hovermode="x unified")
    st.plotly_chart(fig,use_container_width=True)

    rows=[]
    for i,lbl in enumerate(labels):
        pv=cump[i]; ev=cuma[i]
        sv_=round(ev-pv,2) if ev is not None else None
        spi_=round(ev/pv,2) if (ev is not None and pv>0) else None
        rows.append({"Month":lbl,"Plan (%)":f"{pv:.1f}",
            "Actual (%)":f"{ev:.1f}" if ev is not None else "—",
            "SV":f"{sv_:+.1f}" if sv_ is not None else "—",
            "SPI":f"{spi_:.2f}" if spi_ else "—",
            "Status":("✅ On Track" if spi_ and spi_>=1.05 else "⚠️ Warning" if spi_ and spi_>=0.95
                      else "💤 Delayed" if spi_ and spi_>=0.8 else "🔴 Critical" if spi_ else "—")})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

# ── GANTT ─────────────────────────────────────────────────────────────────────
elif page=="📅 Gantt":
    st.markdown("# 📅 Gantt Chart"); st.markdown("---")
    base=datetime.strptime(SI,"%Y-%m-%d"); rows=[]
    for a in acts:
        s=base+relativedelta(months=a["start_month"]-1,day=1)
        e=base+relativedelta(months=a["end_month"],day=1)-relativedelta(days=1)
        sk=next((k for k in SCOL if k in a.get("status","")),"Not Started")
        rows.append(dict(Task=f"{a['no']}. {a['name'][:45]}",Start=s.strftime("%Y-%m-%d"),
                         Finish=e.strftime("%Y-%m-%d"),Status=sk,Weight=f"{a['weight']}%"))
    if rows:
        df=pd.DataFrame(rows)
        fig=px.timeline(df,x_start="Start",x_end="Finish",y="Task",color="Status",
                        color_discrete_map=SCOL,hover_data=["Weight"])
        fig.update_yaxes(autorange="reversed")
        fig.add_vline(x=date.today().isoformat(),line_dash="dash",line_color="#D97706")
        fig.add_annotation(x=date.today().isoformat(),y=1.02,yref="paper",
            text="TODAY",showarrow=False,font=dict(color="#D97706",size=11),xanchor="left")
        fig.update_layout(paper_bgcolor="#FFFFFF",plot_bgcolor="#F9FAFB",
            font=dict(color="#1F2937",size=11),height=420,margin=dict(l=10,r=10,t=20,b=10),
            xaxis=dict(gridcolor="#E5E7EB"),yaxis=dict(gridcolor="#E5E7EB"),legend=dict(bgcolor="#FFFFFF"))
        st.plotly_chart(fig,use_container_width=True)
    else:
        st.info("No activities yet. Add them in ⚙️ Project Setup.")

# ── EVM ───────────────────────────────────────────────────────────────────────
elif page=="📊 EVM Indicators":
    st.markdown("# 📊 EVM Indicators"); st.markdown("---")

    # Cost summary from WBS
    _total_budget = data.get("total_budget", 0)
    _wbs_cost = sum(a.get("planned_cost", 0) for a in acts)
    _ev_pct = cuma[cm-1] if cm <= N and cuma[cm-1] is not None else 0
    _pv_pct = cump[cm-1] if cm <= N else 0
    # EV cost = budget × EV%/100
    _ev_cost = _total_budget * _ev_pct / 100
    _pv_cost = _total_budget * _pv_pct / 100
    _cv = _ev_cost - _pv_cost  # Cost Variance (simplified: no actual cost input)

    ec1, ec2, ec3, ec4 = st.columns(4)
    ec1.metric("Project Budget", f"฿{_total_budget:,.0f}")
    ec2.metric("WBS Planned Cost", f"฿{_wbs_cost:,.0f}",
               delta=f"฿{_wbs_cost - _total_budget:+,.0f}" if _wbs_cost else None, delta_color="inverse")
    ec3.metric(f"PV Cost (M{cm})", f"฿{_pv_cost:,.0f}")
    ec4.metric(f"EV Cost (M{cm})", f"฿{_ev_cost:,.0f}", delta=f"฿{_cv:+,.0f}", delta_color="normal")

    st.markdown("---")
    st.markdown("|Indicator|Formula|Meaning|\n|---|---|---|\n"
        "|**PV**|Cumulative Plan %|What should be done|\n"
        "|**EV**|Cumulative Actual %|What has been done|\n"
        "|**SV**|EV − PV|+ ahead / − delayed|\n"
        "|**SPI**|EV / PV|>1 ahead • <1 behind|\n"
        "|**CV**|EV cost − PV cost|Budget performance|\n"
        "|**WBS Cost**|Σ Activity planned cost|Bottom-up budget check|")
    st.markdown("---")
    rows=[]
    for i,lbl in enumerate(labels):
        pv=cump[i]; ev=cuma[i]
        if ev is None: rows.append({"Month":lbl,"PV":f"{pv:.1f}","EV":"—","SV":"—","SPI":"—","Status":"—"})
        else:
            sv_=round(ev-pv,2); spi_=round(ev/pv,2) if pv>0 else None
            rows.append({"Month":lbl,"PV":f"{pv:.1f}","EV":f"{ev:.1f}","SV":f"{sv_:+.1f}",
                "SPI":f"{spi_:.2f}" if spi_ else "—",
                "Status":("✅ On Track" if spi_ and spi_>=1.05 else "⚠️ Warning" if spi_ and spi_>=0.95
                          else "💤 Delayed" if spi_ and spi_>=0.8 else "🔴 Critical" if spi_ else "—")})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    spi_v=[round(cuma[i]/cump[i],2) if (cuma[i] is not None and cump[i]>0) else None for i in range(N)]
    xs=[labels[i] for i,v in enumerate(spi_v) if v is not None]; ys=[v for v in spi_v if v is not None]
    if ys:
        fig=go.Figure()
        fig.add_hline(y=1.0,line_color="#2563EB")
        fig.add_annotation(x=1,xref="paper",y=1.0,text="Target SPI=1.0",showarrow=False,
            font=dict(color="#2563EB",size=10),xanchor="right",yanchor="bottom")
        fig.add_hline(y=0.95,line_dash="dot",line_color="#D97706")
        fig.add_annotation(x=1,xref="paper",y=0.95,text="⚠️ Warning",showarrow=False,
            font=dict(color="#D97706",size=10),xanchor="right",yanchor="bottom")
        fig.add_hline(y=0.80,line_dash="dot",line_color="#DC2626")
        fig.add_annotation(x=1,xref="paper",y=0.80,text="🔴 Critical",showarrow=False,
            font=dict(color="#DC2626",size=10),xanchor="right",yanchor="bottom")
        fig.add_trace(go.Scatter(x=xs,y=ys,name="SPI",line=dict(color="#16A34A",width=3),
            mode="lines+markers",marker=dict(size=8,color=["#16A34A" if v>=1 else "#D97706" if v>=0.8 else "#DC2626" for v in ys])))
        fig.update_layout(paper_bgcolor="#FFFFFF",plot_bgcolor="#F9FAFB",font=dict(color="#1F2937"),
            height=260,margin=dict(l=10,r=10,t=10,b=10),showlegend=False,
            xaxis=dict(gridcolor="#E5E7EB"),yaxis=dict(gridcolor="#E5E7EB",title="SPI"))
        st.plotly_chart(fig,use_container_width=True)

# ── UPDATE PROGRESS ───────────────────────────────────────────────────────────
elif page=="📝 Update Progress":
    st.markdown("# 📝 Update Progress")
    st.markdown("---")
    if not acts: st.info("Add activities first in ⚙️ Project Setup."); st.stop()

    sopts_raw = ["Not Started","In Progress","Pending","Completed","Delayed","Cancelled"]

    st.markdown(f"Double-click any cell to edit. Current month: **M{cm} — {labels[cm-1] if cm<=N else 'N/A'}** (highlighted).")

    # Build single wide table: rows = activities, cols = Status + all months
    prows = []
    for a in acts:
        sk = next((k for k in sopts_raw if k in a.get("status","")), sopts_raw[0])
        row = {"No": a["no"], "Activity": a["name"][:45], "Wt%": a["weight"],
               "Cost(฿)": a.get("planned_cost", 0.0), "Status": sk}
        for m in range(1, N+1):
            in_range = a["start_month"] <= m <= a["end_month"]
            row[f"M{m}"] = float(a.get("actuals",{}).get(str(m), 0.0)) if in_range else None
        prows.append(row)

    pdf = pd.DataFrame(prows)

    # Month column configs — highlight current month
    m_cfg = {}
    for m in range(1, N+1):
        col_lbl = f"M{m} ★" if m == cm else f"M{m}"
        m_cfg[f"M{m}"] = st.column_config.NumberColumn(
            col_lbl, min_value=0.0, max_value=100.0,
            step=5.0, format="%.0f", width="small")

    col_cfg = {
        "No":       st.column_config.TextColumn("No",         width="small",  disabled=True),
        "Activity": st.column_config.TextColumn("Activity",   width="large",  disabled=True),
        "Wt%":      st.column_config.NumberColumn("Wt%",      width="small",  disabled=True, format="%.1f"),
        "Cost(฿)":  st.column_config.NumberColumn("Cost(฿)",  width="medium", disabled=True, format="฿%.0f"),
        "Status":   st.column_config.SelectboxColumn("Status", width="medium", options=sopts_raw),
        **m_cfg,
    }

    edited = st.data_editor(
        pdf,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config=col_cfg,
        key="progress_editor"
    )

    st.markdown("")
    cl, cr = st.columns([4, 1])
    cl.info("💡 Edit **Status** and any **M1–M12** cell. Blank cells (grey) = outside activity date range — leave as blank.")
    if cr.button("💾 Save All", use_container_width=True, type="primary"):
        for i, row in edited.iterrows():
            st_raw = str(row["Status"])
            data["activities"][i]["status"] = SMAP.get(st_raw, st_raw)
            for m in range(1, N+1):
                val = row.get(f"M{m}")
                if val is not None and not pd.isna(val):
                    data["activities"][i].setdefault("actuals",{})[str(m)] = float(val)
        save_data(data)
        st.success("✅ Progress saved!"); st.rerun()

    # ── Excel Export / Import ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📊 Excel Export / Import")
    ex_col, im_col = st.columns(2)

    with ex_col:
        st.markdown("**📥 Export to Excel**")
        fname = re.sub(r'[^A-Za-z0-9_]','_', data.get("project_name","project"))[:30]
        fname = f"{fname}_progress.xlsx"
        xl_bytes = build_excel(data, cump, cuma, labels)
        st.download_button(
            label="⬇️ Download Excel",
            data=xl_bytes,
            file_name=fname,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )
        st.caption("3 sheets: **Progress** (editable), **S-Curve Data**, **Project Info**. Edit Status & month cells, then import back below.")

    with im_col:
        st.markdown("**📤 Import from Excel**")
        xl_up = st.file_uploader("Upload edited Excel", type=["xlsx"], key="xl_import")
        if xl_up:
            try:
                import openpyxl as _xl
                _wb  = _xl.load_workbook(xl_up, data_only=True)
                _ws  = _wb["Progress"]
                _rows = list(_ws.iter_rows(min_row=2, values_only=True))
                sopts_xl = ["Not Started","In Progress","Pending","Completed","Delayed","Cancelled"]
                updated = 0
                for ri, xrow in enumerate(_rows):
                    if ri >= len(data["activities"]): break
                    # col 5 = Status (0-indexed: col 4)
                    st_xl = str(xrow[4]).strip() if xrow[4] else "Not Started"
                    st_xl = next((k for k in sopts_xl if k.lower() in st_xl.lower()), "Not Started")
                    data["activities"][ri]["status"] = SMAP.get(st_xl, st_xl)
                    # cols 6..N+5 = M1..MN (0-indexed: 5..N+4)
                    for mi in range(1, N+1):
                        val = xrow[4+mi] if (4+mi) < len(xrow) else None
                        if val is not None and str(val).strip() not in ("","None"):
                            try:
                                fval = float(val)
                                if 0 <= fval <= 100:
                                    data["activities"][ri].setdefault("actuals",{})[str(mi)] = fval
                            except (ValueError, TypeError):
                                pass
                    updated += 1
                save_data(data)
                st.success(f"✅ Imported {updated} rows from Excel and saved!")
                st.rerun()
            except Exception as _e:
                st.error(f"❌ Could not read Excel: {_e}")

# ── PROJECT SETUP (merged) ────────────────────────────────────────────────────
elif page=="⚙️ Project Setup":
    st.markdown("# ⚙️ Project Setup")
    st.markdown("---")

    MANIFEST_PATH = "projects/project_manifest.json"
    PROJECTS_DIR  = "projects"

    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Project Info", "📚 WBS Library", "📄 Import CSV/WBS", "✏️ Activities"
    ])

    # ── TAB 1: Project Info ───────────────────────────────────────────────────
    with tab1:
        st.markdown("### 📋 Project Information")
        with st.form("pf"):
            c1,c2=st.columns(2)
            pn=c1.text_input("Project Name (EN)",data["project_name"])
            pt=c2.text_input("Project Name (TH)",data.get("project_name_th",""))
            c3,c4=st.columns(2)
            po=c3.text_input("Project Owner",data.get("project_owner",""))
            pc=c4.text_input("Contractor",data.get("contractor",""))
            c5,c6,c7=st.columns(3)
            ps=c5.text_input("Start Date",data["start_date"])
            pe=c6.text_input("End Date",data["end_date"])
            nm=c7.number_input("Months",1,36,data["n_months"])
            bg=st.number_input("Budget (THB)",value=float(data["total_budget"]),step=100000.0)
            cn=st.text_input("Contract No.",data.get("contract_no",""))
            if st.form_submit_button("💾 Save Project Info"):
                data.update({"project_name":pn,"project_name_th":pt,"project_owner":po,
                    "contractor":pc,"start_date":ps,"end_date":pe,"n_months":int(nm),
                    "total_budget":bg,"contract_no":cn})
                save_data(data); st.success("✅ Saved!"); st.rerun()

        if acts:
            st.markdown("---")
            total_cost = sum(a.get("planned_cost",0) for a in acts)
            st.caption(f"**{len(acts)} activities** | WBS cost: **฿{total_cost:,.0f}** | Budget: **฿{data.get('total_budget',0):,.0f}**")
            df=pd.DataFrame([{"No":a["no"],"Name":a["name"],"Wt%":a["weight"],
                "Planned Cost (฿)":a.get("planned_cost",0),
                "Start M":a["start_month"],"End M":a["end_month"],"Status":a.get("status","—")} for a in acts])
            st.dataframe(df,use_container_width=True,hide_index=True,
                         column_config={"Planned Cost (฿)": st.column_config.NumberColumn(format="฿%.0f")})

    # ── TAB 2: WBS Library ────────────────────────────────────────────────────
    with tab2:
        st.markdown("### 📚 WBS Library")

        # ── Search + Sort controls ────────────────────────────────────────────
        hc1, hc2, hc3 = st.columns([3, 2, 1])
        search_q  = hc1.text_input("🔍 Search", placeholder="project name, doc code…", label_visibility="collapsed")
        sort_by   = hc2.selectbox("Sort by", ["updated_at","created_at","project_name","n_activities"],
                                   format_func=lambda x: {"updated_at":"Last Modified","created_at":"Date Added",
                                                           "project_name":"Name","n_activities":"No. Tasks"}[x],
                                   label_visibility="collapsed")
        doc_icons = {"FULL":"🌐","CM":"🏔️","CR":"🌾","LP":"🌿","PY":"💧"}

        entries = db_list(sort=sort_by, search=search_q)
        active_key = data.get("_db_key","")   # currently loaded project key

        if not entries:
            st.info("No projects in library yet. Use **➕ Add Current Project** below or run `wbs_extractor.py`.")
        else:
            hc3.markdown(f"<div style='text-align:right;padding-top:8px;color:#6B7280'>{len(entries)} projects</div>",
                         unsafe_allow_html=True)

            # Active project banner
            active_entry = next((e for e in entries if e["key"] == active_key), None)
            if active_entry:
                st.markdown(
                    f"<div style='background:#DCFCE7;border:1px solid #86EFAC;border-radius:8px;"
                    f"padding:8px 14px;margin-bottom:10px;display:flex;align-items:center;gap:10px'>"
                    f"<span style='color:#15803D;font-size:1rem'>▶ Active:</span>"
                    f"<span style='color:#1F2937;font-weight:600'>{active_entry['project_name']}</span>"
                    f"<span style='color:#6B7280;font-size:.8rem'>({active_entry['doc']} / {active_entry['phase']} · "
                    f"{active_entry['n_activities']} tasks)</span></div>",
                    unsafe_allow_html=True)

            st.markdown("---")

            for e in entries:
                icon     = doc_icons.get(e["doc"],"📁")
                upd      = e["updated_at"][:16] if e["updated_at"] else "—"
                cre      = e["created_at"][:16] if e["created_at"] else "—"
                is_active = e["key"] == active_key

                # Row highlight for active project
                row_bg  = "background:#F0FDF4;border:1px solid #86EFAC;border-radius:8px;padding:4px 8px;margin-bottom:2px" if is_active else ""
                active_badge = "&nbsp;<span style='background:#16A34A;color:#FFFFFF;font-size:.7rem;font-weight:700;padding:2px 7px;border-radius:10px'>● IN USE</span>" if is_active else ""

                if row_bg:
                    st.markdown(f"<div style='{row_bg}'>", unsafe_allow_html=True)

                c_info, c_acts, c_bud, c_upd, c_load, c_del = st.columns([4, 1, 2, 2, 1, 1])
                c_info.markdown(
                    f"{icon} **{e['project_name']}**{active_badge}  \n"
                    f"<small style='color:#6B7280'>{e['doc']} / {e['phase']}</small>",
                    unsafe_allow_html=True)
                c_acts.metric("Tasks", e["n_activities"])
                c_bud.metric("Budget", "฿{:,.0f}".format(e["total_budget"]) if e["total_budget"] else "—")
                c_upd.markdown(
                    f"<div style='font-size:.78rem;color:#6B7280;padding-top:6px'>"
                    f"✏️ {upd}<br>➕ {cre}</div>",
                    unsafe_allow_html=True)

                if row_bg:
                    st.markdown("</div>", unsafe_allow_html=True)

                if c_load.button("✅ Active" if is_active else "▶ Load",
                                  key=f"db_load_{e['key']}",
                                  disabled=is_active,
                                  type="primary" if is_active else "secondary"):
                    proj = db_get(e["key"])
                    if proj:
                        # Stamp DB tracking keys so every subsequent save_data() syncs back
                        proj["_db_key"]   = e["key"]
                        proj["_db_doc"]   = e["doc"]
                        proj["_db_phase"] = e["phase"]
                        save_data(proj)
                        db_touch(e["key"])
                        st.success(f"✅ Loaded **{e['project_name']}** ({e['n_activities']} tasks)")
                        st.rerun()
                    else:
                        st.error("Project data not found in database.")

                if c_del.button("🗑️", key=f"db_del_{e['key']}", help=f"Delete '{e['project_name']}'"):
                    db_log(e["key"], e["project_name"], "🗑️ Deleted", "Removed from library")
                    db_delete(e["key"])
                    st.success(f"🗑️ Deleted **{e['project_name']}**")
                    st.rerun()

                st.markdown("<hr style='margin:6px 0;border-color:#E5E7EB'>", unsafe_allow_html=True)

        # ── Bulk Import all WBS Extract Files ────────────────────────────────
        st.markdown("---")
        st.markdown("#### 📦 Import All WBS Extract Files")

        bulk_tab1, bulk_tab2 = st.tabs(["📁 From projects/ folder (JSON)", "📄 From CSV Template"])

        # ── BULK TAB 1: JSON files ────────────────────────────────────────────
        with bulk_tab1:
            st.markdown("Scan the `projects/` folder and add every JSON file into the database in one click.")
            imp_col1, imp_col2 = st.columns([3, 1])
            json_files = []
            if os.path.exists(PROJECTS_DIR):
                json_files = [f for f in os.listdir(PROJECTS_DIR)
                              if f.endswith(".json") and f != "project_manifest.json"]
            imp_col1.markdown(
                f"<div style='padding:8px 0;color:#6B7280;font-size:.88rem'>"
                f"Found <b style='color:#1F2937'>{len(json_files)}</b> JSON files in "
                f"<code>projects/</code> · "
                f"<b style='color:#1F2937'>{len(db_list())}</b> already in database</div>",
                unsafe_allow_html=True)
            if imp_col2.button("📦 Import All JSON", use_container_width=True, type="primary",
                               disabled=(len(json_files)==0), key="bulk_json"):
                imported = errors = 0
                existing_keys = {e["key"] for e in db_list()}
                manifest_map = {}
                if os.path.exists(MANIFEST_PATH):
                    with open(MANIFEST_PATH, encoding="utf-8") as _mf:
                        for m in json.load(_mf):
                            manifest_map[m.get("filename","")] = m
                for fname in json_files:
                    fpath = os.path.join(PROJECTS_DIR, fname)
                    try:
                        with open(fpath, encoding="utf-8") as _pf:
                            proj = json.load(_pf)
                        meta    = manifest_map.get(fname, {})
                        raw_key = meta.get("key") or re.sub(r'[^A-Za-z0-9_]','_', fname.replace(".json",""))[:40]
                        pname   = meta.get("project_name") or proj.get("project_name", fname)
                        pnameth = meta.get("project_name_th","") or proj.get("project_name_th","")
                        doc     = meta.get("doc") or proj.get("_db_doc","CUSTOM")
                        phase   = meta.get("phase") or proj.get("_db_phase","Custom")
                        proj["_db_key"] = raw_key; proj["_db_doc"] = doc; proj["_db_phase"] = phase
                        db_save(raw_key, pname, pnameth, doc, phase, proj)
                        db_log(raw_key, pname, "📦 Bulk Import", f"{fname}")
                        imported += 1
                    except Exception:
                        errors += 1
                st.success(f"✅ Imported **{imported}** projects | ⚠️ Errors: {errors}")
                st.rerun()

        # ── BULK TAB 2: CSV template ──────────────────────────────────────────
        with bulk_tab2:
            st.markdown("Upload `heymorning_task_import.csv` — every **PHASE** becomes a separate project in the database automatically.")

            # CSV helpers (reuse from tab2 if defined, or redefine inline)
            def _extract(notes, key):
                m = re.search(rf'{key}: ([^\|]+)', notes or "")
                return m.group(1).strip() if m else ""
            def _months(notes):
                raw = _extract(notes, "Months")
                try: return [int(x) for x in raw.split(",") if x.strip()]
                except: return []
            def _weight(notes):
                try: return float(_extract(notes, "Weight %"))
                except: return 0.0

            def csv_rows_to_project(rows, phase, proj_name, start_date, n_months, budget):
                acts = []
                for i, r in enumerate(rows):
                    mnths = _months(r.get("NOTES",""))
                    if not mnths: continue
                    wt = _weight(r.get("NOTES",""))
                    wbs = _extract(r.get("NOTES",""), "WBS")
                    try: pc = float(_extract(r.get("NOTES",""), "Estimated cost"))
                    except: pc = 0.0
                    acts.append({"no": wbs or str(i+1),
                                 "name": r.get("TASK NAME","").strip(),
                                 "name_th": r.get("TASK NAME","").strip(),
                                 "weight": wt, "planned_cost": pc,
                                 "start_month": min(mnths),
                                 "end_month": max(mnths),
                                 "status": "❌ Not Started", "actuals": {}})
                # Normalize weights
                tot = sum(a["weight"] for a in acts)
                if tot > 0 and abs(tot-100) > 1:
                    for a in acts: a["weight"] = round(a["weight"]/tot*100, 2)
                return {"project_name": proj_name, "project_name_th": "",
                        "start_date": start_date, "end_date": "",
                        "n_months": n_months, "total_budget": budget,
                        "contract_no": "", "project_owner": "NRCT",
                        "contractor": "Faculty of Engineering, CMU",
                        "activities": acts}

            bulk_csv = st.file_uploader("Upload WBS CSV", type=["csv"], key="bulk_csv_up")

            if bulk_csv:
                raw_text = bulk_csv.read().decode("utf-8-sig")
                reader = list(csv.DictReader(io.StringIO(raw_text)))

                # Group by PHASE
                from collections import OrderedDict as _OD
                phase_map = _OD()
                for r in reader:
                    phase_map.setdefault(r.get("PHASE","Unknown"), []).append(r)

                st.markdown(f"**{len(reader)} rows · {len(phase_map)} phases detected**")

                # Preview table
                prev_rows = []
                for ph, rows2 in phase_map.items():
                    wts = []
                    for r in rows2:
                        try: wts.append(_weight(r.get("NOTES","")))
                        except: pass
                    doc_code = _extract(rows2[0].get("NOTES",""),"Document") or ph.split("/")[0].strip()
                    prev_rows.append({"Phase": ph, "Doc": doc_code,
                                      "Activities": len(rows2),
                                      "Weight Sum": f"{sum(wts):.0f}%"})
                st.dataframe(pd.DataFrame(prev_rows), use_container_width=True, hide_index=True)

                # Common settings
                with st.form("bulk_csv_form"):
                    bc1, bc2, bc3 = st.columns(3)
                    b_start   = bc1.text_input("Start Date", "2025-10-01")
                    b_nmonths = bc2.number_input("Months", 1, 36, 12)
                    b_budget  = bc3.number_input("Budget per phase (THB)", value=20723000.0, step=100000.0)
                    b_overwrite = st.checkbox("Overwrite existing entries with same key", value=True)

                    if st.form_submit_button("📦 Import All Phases to Database", use_container_width=True, type="primary"):
                        imported = errors = 0
                        existing_keys = {e["key"] for e in db_list()}
                        for ph, rows2 in phase_map.items():
                            try:
                                doc_code = _extract(rows2[0].get("NOTES",""),"Document") or re.sub(r'[^A-Za-z0-9_]','_',ph.split("/")[0].strip())[:10]
                                proj_name = rows2[0].get("PROJECT", ph)
                                raw_key = re.sub(r'[^A-Za-z0-9_]','_', f"{doc_code}_{ph}")[:40]

                                if raw_key in existing_keys and not b_overwrite:
                                    continue

                                proj = csv_rows_to_project(rows2, ph, proj_name,
                                                           b_start, int(b_nmonths), float(b_budget))
                                proj["_db_key"]   = raw_key
                                proj["_db_doc"]   = doc_code
                                proj["_db_phase"] = ph

                                db_save(raw_key, proj_name, "", doc_code, ph, proj)
                                db_log(raw_key, proj_name, "📦 CSV Bulk Import",
                                       f"Phase: {ph} · {len(proj['activities'])} activities")
                                imported += 1
                            except Exception as _ex:
                                errors += 1

                        st.success(f"✅ Imported **{imported}** phases as projects | ⚠️ Errors: {errors}")
                        st.rerun()
            else:
                st.info("Upload your `heymorning_task_import.csv` file above. Each PHASE column value becomes a separate project entry in the database.")
                st.code("Expected columns: PROJECT, PHASE, TASK NAME, ..., NOTES\nNOTES must contain: WBS: | Document: | Months: | Weight %: | Estimated cost:", language="text")

        st.markdown("---")
        # ── Save current project to DB ────────────────────────────────────────
        st.markdown("#### ➕ Add Current Project to Library")
        with st.form("save_to_db"):
            c1, c2, c3 = st.columns(3)
            lib_name  = c1.text_input("Project Name", data["project_name"])
            lib_doc   = c2.text_input("Document Code", "CUSTOM")
            lib_phase = c3.text_input("Phase / Tag", "Custom")
            lib_name_th = st.text_input("Project Name (TH)", data.get("project_name_th",""))
            if st.form_submit_button("💾 Save to Library", use_container_width=True):
                safe_key = re.sub(r'[^A-Za-z0-9_]', '_', f"{lib_doc}_{lib_phase}")[:40]
                save_proj = dict(data)
                save_proj["project_name"]    = lib_name
                save_proj["project_name_th"] = lib_name_th
                # Stamp tracking keys so future edits auto-sync
                save_proj["_db_key"]   = safe_key
                save_proj["_db_doc"]   = lib_doc
                save_proj["_db_phase"] = lib_phase
                db_save(safe_key, lib_name, lib_name_th, lib_doc, lib_phase, save_proj)
                db_log(safe_key, lib_name, "➕ Added to Library",
                       f"{len(data.get('activities',[]))} activities")
                # Also write back to project_data.json so the tracking keys persist immediately
                with open(DATA_FILE, "w", encoding="utf-8") as _f:
                    json.dump(save_proj, _f, ensure_ascii=False, indent=2)
                st.cache_data.clear()
                st.success(f"✅ Saved **{lib_name}** to database — edits will now auto-sync")
                st.rerun()

        # ── Activity Log ──────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 📋 Activity Log")

        log_filter = st.selectbox("Filter by project", ["All projects"] + [e["project_name"] for e in db_list()],
                                   label_visibility="collapsed", key="log_filter")
        log_key = None
        if log_filter != "All projects":
            matched = [e for e in db_list() if e["project_name"] == log_filter]
            if matched: log_key = matched[0]["key"]

        log_entries = db_get_log(limit=60, db_key=log_key)

        if not log_entries:
            st.info("No activity recorded yet. Load or save a project to start logging.")
        else:
            action_colors = {
                "💾 Saved":           "#2563EB",
                "▶ Loaded":           "#16A34A",
                "➕ Added to Library": "#D97706",
                "🗑️ Deleted":         "#DC2626",
            }
            log_df = pd.DataFrame([{
                "Timestamp":    e["timestamp"],
                "Action":       e["action"],
                "Project":      e["project_name"][:45],
                "Detail":       e["detail"],
            } for e in log_entries])

            st.dataframe(
                log_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Timestamp": st.column_config.TextColumn("🕐 Time",    width="medium"),
                    "Action":    st.column_config.TextColumn("Action",      width="small"),
                    "Project":   st.column_config.TextColumn("Project",     width="large"),
                    "Detail":    st.column_config.TextColumn("Detail",      width="large"),
                }
            )

            lc1, lc2 = st.columns([4,1])
            lc1.caption(f"{len(log_entries)} entries shown")
            if lc2.button("🗑️ Clear Log", use_container_width=True):
                conn = db_connect()
                if log_key:
                    conn.execute("DELETE FROM save_log WHERE db_key=?", (log_key,))
                else:
                    conn.execute("DELETE FROM save_log")
                conn.commit(); conn.close()
                st.rerun()

    with tab3:
        st.markdown("### 📄 Import CSV / WBS")
        st.markdown("Upload `heymorning_task_import.csv` to parse, select a phase, and import into the active project.")

        def parse_wbs_csv(file_bytes):
            text = file_bytes.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            return list(reader)

        def extract_notes(notes, key):
            m = re.search(rf'{key}: ([^\|]+)', notes or "")
            return m.group(1).strip() if m else ""

        def parse_months(notes):
            raw = extract_notes(notes, "Months")
            try: return [int(x) for x in raw.split(",") if x.strip()]
            except: return []

        def rows_to_activities(rows, normalize=True):
            _acts = []
            for i, r in enumerate(rows):
                months = parse_months(r.get("NOTES",""))
                if not months: continue
                wt_raw = extract_notes(r.get("NOTES",""), "Weight %")
                try: wt = float(wt_raw)
                except: wt = 0.0
                wbs = extract_notes(r.get("NOTES",""), "WBS")
                cost_raw = extract_notes(r.get("NOTES",""), "Estimated cost")
                try: planned_cost = float(cost_raw)
                except: planned_cost = 0.0
                _acts.append({
                    "no": wbs or str(i+1),
                    "name": r.get("TASK NAME","").strip(),
                    "name_th": r.get("TASK NAME","").strip(),
                    "weight": wt, "planned_cost": planned_cost,
                    "start_month": min(months), "end_month": max(months),
                    "status": "❌ Not Started", "actuals": {}
                })
            if normalize and _acts:
                total = sum(a["weight"] for a in _acts)
                if total > 0 and abs(total - 100.0) > 1.0:
                    for a in _acts: a["weight"] = round(a["weight"] / total * 100, 2)
            return _acts

        uploaded = st.file_uploader("Upload WBS CSV file", type=["csv"],
                                    help="Export from AI extraction pipeline as heymorning_task_import.csv",
                                    key="csv_upload_tab3")

        if uploaded:
            raw_rows = parse_wbs_csv(uploaded.read())
            st.success(f"✅ Loaded {len(raw_rows)} activities from CSV")

            from collections import OrderedDict
            phase_map = OrderedDict()
            for r in raw_rows:
                ph = r.get("PHASE","Unknown")
                phase_map.setdefault(ph, []).append(r)

            st.markdown("---")
            st.markdown("### Step 1 — Select Sub-Project / Phase")
            st.caption(f"{len(phase_map)} phases found in CSV")

            ph_rows = []
            for ph, rows2 in phase_map.items():
                wts = []
                for r in rows2:
                    try: wts.append(float(extract_notes(r.get("NOTES",""),"Weight %")))
                    except: pass
                ph_rows.append({"Phase": ph, "Activities": len(rows2),
                                "Weight Sum %": f"{sum(wts):.0f}",
                                "Date Range": f"{rows2[0].get('START DATE','')} → {rows2[-1].get('DUE DATE','')}"})
            st.dataframe(pd.DataFrame(ph_rows), use_container_width=True, hide_index=True)

            sel_phase = st.selectbox("Select phase to import:", list(phase_map.keys()), key="sel_phase_t3")
            phase_rows = phase_map[sel_phase]
            acts_preview = rows_to_activities(phase_rows, normalize=True)

            st.markdown("---")
            st.markdown(f"### Step 2 — Preview: **{sel_phase}** ({len(acts_preview)} activities)")
            prev_df = pd.DataFrame([{
                "No": a["no"], "Task Name": a["name"][:50],
                "Weight %": f"{a['weight']:.1f}",
                "Cost(฿)": f"฿{a.get('planned_cost',0):,.0f}",
                "M Start": a["start_month"], "M End": a["end_month"]
            } for a in acts_preview])
            st.dataframe(prev_df, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("### Step 3 — Project Settings")
            with st.form("wbs_import_form"):
                c1, c2 = st.columns(2)
                proj_name   = c1.text_input("Project Name (EN)", f"Water Security — {sel_phase}")
                proj_name_th= c2.text_input("Project Name (TH)", "โครงการขับเคลื่อนยุทธศาสตร์น้ำมั่นคง")
                c3, c4, c5  = st.columns(3)
                p_start = c3.text_input("Start Date", phase_rows[0].get("START DATE","2025-10-01")[:10])
                p_end   = c4.text_input("End Date",   phase_rows[-1].get("DUE DATE","2026-09-30")[:10])
                n_mo    = c5.number_input("Months", 1, 36, 12)
                budget  = st.number_input("Total Budget (THB)", value=20723000.0, step=100000.0)
                overwrite = st.checkbox("⚠️ Replace current project data", value=True)
                submitted = st.form_submit_button("📥 Import & Save", use_container_width=True)
                if submitted:
                    new_data = {
                        "project_name": proj_name, "project_name_th": proj_name_th,
                        "start_date": p_start, "end_date": p_end,
                        "n_months": int(n_mo), "total_budget": float(budget),
                        "contract_no": "", "project_owner": "NRCT",
                        "contractor": "Faculty of Engineering, CMU",
                        "activities": acts_preview
                    }
                    if overwrite:
                        save_data(new_data)
                        st.success(f"✅ Imported {len(acts_preview)} activities from **{sel_phase}**!")
                        st.rerun()
                    else:
                        current = load_data()
                        existing_nos = {a["no"] for a in current["activities"]}
                        added = 0
                        for a in acts_preview:
                            if a["no"] not in existing_nos:
                                current["activities"].append(a); added += 1
                        save_data(current)
                        st.success(f"✅ Merged: added {added} new activities."); st.rerun()
        else:
            st.info("Upload your WBS CSV file above to begin.")
            st.code("PROJECT, PHASE, TASK NAME, DESCRIPTION, IMPORTANT, URGENT, STATUS, PRIORITY, ASSIGNED TO, START DATE, DUE DATE, KANBAN STAGE, PROGRESS, NOTES")

    with tab4:
        st.markdown("### ✏️ Manage Current Project Activities")
        st.markdown(f"**{data['project_name']}** — {len(acts)} activities loaded")
        st.markdown("Use the table below to **add new rows** (click ＋ at the bottom) or **delete rows** (select row → Delete key, or use the row checkbox). Click **💾 Save Changes** when done.")
        st.markdown("---")

        sopts_manage = ["Not Started","In Progress","Pending","Completed","Delayed","Cancelled"]

        # Build editable dataframe from current activities
        mrows = []
        for a in acts:
            sk = next((k for k in sopts_manage if k in a.get("status","")), sopts_manage[0])
            mrows.append({
                "No":             a.get("no",""),
                "Name (EN)":      a.get("name",""),
                "Name (TH)":      a.get("name_th",""),
                "Weight %":       float(a.get("weight",0)),
                "Planned Cost":   float(a.get("planned_cost",0)),
                "Start M":        int(a.get("start_month",1)),
                "End M":          int(a.get("end_month",1)),
                "Status":         sk,
            })

        mdf = pd.DataFrame(mrows) if mrows else pd.DataFrame(
            columns=["No","Name (EN)","Name (TH)","Weight %","Planned Cost","Start M","End M","Status"])

        managed = st.data_editor(
            mdf,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "No":           st.column_config.TextColumn("No", width="small"),
                "Name (EN)":    st.column_config.TextColumn("Name (EN)", width="large"),
                "Name (TH)":    st.column_config.TextColumn("Name (TH)", width="medium"),
                "Weight %":     st.column_config.NumberColumn("Weight %", min_value=0.0, max_value=100.0, step=0.5, format="%.2f", width="small"),
                "Planned Cost": st.column_config.NumberColumn("Cost (฿)", min_value=0.0, step=10000.0, format="฿%.0f", width="medium"),
                "Start M":      st.column_config.NumberColumn("Start M", min_value=1, max_value=36, step=1, width="small"),
                "End M":        st.column_config.NumberColumn("End M",   min_value=1, max_value=36, step=1, width="small"),
                "Status":       st.column_config.SelectboxColumn("Status", width="medium", options=sopts_manage),
            },
            key="manage_editor"
        )

        wt_sum = managed["Weight %"].sum() if len(managed) > 0 else 0
        cost_sum = managed["Planned Cost"].sum() if len(managed) > 0 else 0
        c_info, c_save, c_norm = st.columns([3,1,1])
        c_info.markdown(
            f"**{len(managed)} activities** | Weight: **{wt_sum:.1f}%** {'✅' if abs(wt_sum-100)<1 else '⚠️ should be 100%'}"
            f" | Total cost: **฿{cost_sum:,.0f}**")

        if c_norm.button("⚖️ Normalize Weights", use_container_width=True):
            if wt_sum > 0:
                managed["Weight %"] = (managed["Weight %"] / wt_sum * 100).round(2)
                st.info("Weights normalized to 100%. Click 💾 Save Changes to apply.")

        if c_save.button("💾 Save Changes", use_container_width=True, type="primary"):
            new_acts = []
            for _, row in managed.iterrows():
                name = str(row.get("Name (EN)","")).strip()
                if not name: continue
                st_raw = str(row.get("Status","Not Started"))
                orig = next((a for a in acts if a.get("no")==str(row.get("No",""))), {})
                new_acts.append({
                    "no":          str(row.get("No","")),
                    "name":        name,
                    "name_th":     str(row.get("Name (TH)","")).strip() or name,
                    "weight":      float(row.get("Weight %", 0) or 0),
                    "planned_cost":float(row.get("Planned Cost", 0) or 0),
                    "start_month": int(row.get("Start M", 1) or 1),
                    "end_month":   int(row.get("End M", 1) or 1),
                    "status":      SMAP.get(st_raw, st_raw),
                    "actuals":     orig.get("actuals", {}),
                })
            data["activities"] = new_acts
            save_data(data)
            st.success(f"✅ Saved {len(new_acts)} activities!"); st.rerun()


# ── PROCESS GUIDE ─────────────────────────────────────────────────────────────
elif page=="📋 Process Guide":
    st.markdown("# 📋 Process Guide")
    st.markdown("Complete pipeline — from project proposal document to live S-Curve dashboard.")
    st.markdown("---")

    # ── PIPELINE OVERVIEW ────────────────────────────────────────────────────
    st.markdown("## 🔄 Full Pipeline Overview")
    st.markdown("""
<div style="background:#F3F4F6;border:1px solid #E5E7EB;border-radius:12px;padding:20px 24px;font-family:monospace;font-size:.9rem;line-height:2.2">
<span style="color:#B45309;font-weight:700">STEP 1</span> &nbsp;📄 <span style="color:#15803D">Project Proposal Document</span> &nbsp;(.docx / .pdf)<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↓<br>
<span style="color:#B45309;font-weight:700">STEP 2</span> &nbsp;🤖 <span style="color:#15803D">AI Extraction</span> &nbsp;(Claude / ChatGPT + WBS Prompt)<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↓<br>
<span style="color:#B45309;font-weight:700">STEP 3</span> &nbsp;📊 <span style="color:#15803D">heymorning_task_import.csv</span> &nbsp;(WBS data table)<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↓<br>
<span style="color:#B45309;font-weight:700">STEP 4</span> &nbsp;⚙️ <span style="color:#15803D">wbs_extractor.py</span> &nbsp;(auto-split by sub-project)<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↓<br>
<span style="color:#B45309;font-weight:700">STEP 5</span> &nbsp;📁 <span style="color:#15803D">projects/*.json</span> &nbsp;(20 pre-built project files)<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↓<br>
<span style="color:#B45309;font-weight:700">STEP 6</span> &nbsp;📥 <span style="color:#15803D">Import WBS → Project Library</span> &nbsp;(one-click load)<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↓<br>
<span style="color:#B45309;font-weight:700">STEP 7</span> &nbsp;📈 <span style="color:#2563EB">Dashboard / S-Curve / Gantt / EVM</span> &nbsp;✅ Live
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ── STEP CARDS ───────────────────────────────────────────────────────────
    steps = [
        ("1","📄","Prepare Project Proposal",
         "Have your project proposal ready as a Word (.docx) or PDF file. The document should contain schedule tables (monthly Gantt), budget breakdown, and activity lists.",
         ["Schedule tables with month columns (fiscal months 1–12)",
          "Budget table with activity weights or costs",
          "Work package / milestone descriptions"]),
        ("2","🤖","Run AI Extraction (WBS Prompt)",
         "Open a new Claude or ChatGPT conversation. Copy the prompt from `WBS_Extraction_Prompt.md` (in your GitHub repo), paste it, and attach your proposal document.",
         ["Open: claude.ai or chatgpt.com",
          "Copy full prompt from WBS_Extraction_Prompt.md",
          "Attach proposal document",
          "Send → AI outputs WBS table + CSV"]),
        ("3","💾","Save Output as CSV",
         "The AI will output a CSV block. Copy it and save as `heymorning_task_import.csv`. Each row = one WBS activity with months, weight, cost, and WBS code in the NOTES column.",
         ["Copy the ```csv block from AI response",
          "Paste into Notepad / VS Code",
          'Save as: heymorning_task_import.csv (UTF-8 encoding)',
          "Verify: header row must match expected columns"]),
        ("4","⚙️","Auto-Split by Sub-Project (Optional)",
         "Run `wbs_extractor.py` to automatically separate the CSV into one JSON per sub-project/province. This regenerates all files in the `projects/` folder.",
         ["Open Terminal / Command Prompt",
          "Navigate to scurve_webapp/ folder",
          "Run: python wbs_extractor.py --csv heymorning_task_import.csv --outdir projects --combine-doc",
          "Push updated JSONs to GitHub"]),
        ("5","📥","Import into the App",
         "Use the Project Setup page (sidebar) to load your project data. Two options: WBS Library (pre-built) or Import CSV (manual).",
         ["Sidebar → ⚙️ Project Setup",
          "Tab 1: Project Library → click ▶ Load next to your project",
          "OR Tab 2: Upload CSV → select phase → Import & Save",
          "Dashboard updates automatically"]),
        ("6","📝","Update Monthly Progress",
         "Each month, open Update Progress to enter actual completion % per activity and update status. Then commit project_data.json to GitHub to persist the changes.",
         ["Sidebar → 📝 Update Progress",
          "Expand each activity panel",
          "Enter actual % for the current month",
          "Click 💾 Save All Activities",
          "Commit project_data.json to GitHub to save permanently"]),
    ]

    for no, icon, title, desc, bullets in steps:
        with st.expander(f"**Step {no} — {icon} {title}**", expanded=(no=="1")):
            st.markdown(f"<p style='color:#1F2937'>{desc}</p>", unsafe_allow_html=True)
            for b in bullets:
                st.markdown(f"<div style='color:#15803D;padding:2px 0 2px 16px'>✦ {b}</div>",
                            unsafe_allow_html=True)
            st.markdown("")

    st.markdown("---")

    # ── WBS PROMPT DISPLAY ────────────────────────────────────────────────────
    st.markdown("## 🤖 AI Extraction Prompt")

    PROMPT_PATH = "WBS_Extraction_Prompt.md"
    if os.path.exists(PROMPT_PATH):
        with open(PROMPT_PATH, encoding="utf-8") as _pf:
            prompt_text = _pf.read()
        if "=== PASTE PROMPT BELOW ===" in prompt_text:
            prompt_section = prompt_text.split("=== PASTE PROMPT BELOW ===")[1].split("=== END OF PROMPT ===")[0].strip()
        else:
            prompt_section = prompt_text

        # Instruction banner + action buttons
        st.markdown("""
<div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;padding:14px 20px;margin-bottom:12px">
<b style="color:#1D4ED8;font-size:1.05rem">📋 How to use this prompt</b><br>
<span style="color:#1F2937;font-size:.9rem">
1. Click <b>⬇️ Download Prompt</b> (save to your computer) <b>OR</b> select all text below and copy<br>
2. Open <b>claude.ai</b> or <b>chatgpt.com</b> → start a new conversation<br>
3. Paste the prompt, then <b>attach your project proposal (.docx / .pdf)</b><br>
4. The AI outputs a CSV block → save as <code>heymorning_task_import.csv</code><br>
5. Go to <b>⚙️ Project Setup → Import CSV/WBS</b> to load it into the app
</span>
</div>
""", unsafe_allow_html=True)

        # Action buttons row
        btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 4])

        # Download button — saves prompt as .txt file
        btn_col1.download_button(
            label="⬇️ Download Prompt (.txt)",
            data=prompt_section.encode("utf-8"),
            file_name="WBS_Extraction_Prompt.txt",
            mime="text/plain",
            use_container_width=True,
        )

        # Download as .md file
        btn_col2.download_button(
            label="📄 Download Prompt (.md)",
            data=prompt_section.encode("utf-8"),
            file_name="WBS_Extraction_Prompt.md",
            mime="text/markdown",
            use_container_width=True,
        )

        btn_col3.info("💡 Or click inside the text box below → **Ctrl+A** → **Ctrl+C** to copy all")

        # Full prompt in a tall text area — easy to select-all and copy
        st.text_area(
            label="Full AI Extraction Prompt (select all → copy)",
            value=prompt_section,
            height=520,
            key="prompt_textarea",
            help="Click inside → Ctrl+A to select all → Ctrl+C to copy"
        )

        # Also show as code block for syntax highlighting + built-in copy icon
        with st.expander("📋 View as formatted code (with copy icon ↗)", expanded=False):
            st.code(prompt_section, language="markdown")

    else:
        st.warning("WBS_Extraction_Prompt.md not found. Make sure it is in the same folder as app.py.")
        st.markdown("**Expected location:** `scurve_webapp/WBS_Extraction_Prompt.md`")

    st.markdown("---")

    # ── NOTES FIELD FORMAT ────────────────────────────────────────────────────
    st.markdown("## 📌 Required CSV Format")
    st.markdown("The NOTES column must contain this exact format for the importer to parse correctly:")
    st.code("WBS: FULL.1.01 | Document: FULL | FY(BE): 2569 | Months: 1,2,3 | Weight %: 10.0 | Estimated cost: 2072300.0 | Duration days: 92 | Source: table 19, row 2", language="text")
    st.markdown("**Full CSV header:**")
    st.code("PROJECT,PHASE,TASK NAME,DESCRIPTION,IMPORTANT,URGENT,STATUS,PRIORITY,ASSIGNED TO,START DATE,DUE DATE,KANBAN STAGE,PROGRESS,NOTES", language="text")

    st.markdown("---")

    # ── FISCAL MONTH TABLE ────────────────────────────────────────────────────
    st.markdown("## 📅 Fiscal Month Reference (FY 2569)")
    fm_data = {
        "Fiscal Month": list(range(1,13)),
        "Calendar Month": ["Oct","Nov","Dec","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep"],
        "Date (FY2569)": ["2025-10","2025-11","2025-12","2026-01","2026-02","2026-03",
                           "2026-04","2026-05","2026-06","2026-07","2026-08","2026-09"],
    }
    st.dataframe(pd.DataFrame(fm_data), use_container_width=True, hide_index=True)
