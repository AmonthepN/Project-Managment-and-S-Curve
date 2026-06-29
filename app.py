"""
S-Curve Project Monitoring System — Streamlit Web App
Author: Faculty of Engineering, Chiang Mai University
Run:  streamlit run app.py
"""
import json, os, re, io, csv
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
.stApp{background-color:#2D3747;color:#E8ECF0}
[data-testid="stSidebar"]{background-color:#1A2030}
[data-testid="stSidebar"] *{color:#9BA3AF!important}
.kpi-card{background:#515863;border-radius:12px;padding:18px 16px;text-align:center;margin:4px 0}
.kpi-num{font-size:2.2rem;font-weight:700;color:#7BA2F1}
.kpi-label{font-size:.75rem;color:#9BA3AF;letter-spacing:1px;margin-top:4px}
.st-done{background:#2A5E3A;color:#BDE0A9;padding:3px 10px;border-radius:20px;font-size:.82rem;font-weight:600}
.st-prog{background:#2A4E2A;color:#C8E49A;padding:3px 10px;border-radius:20px;font-size:.82rem;font-weight:600}
.st-pend{background:#3A3B1A;color:#F4A25E;padding:3px 10px;border-radius:20px;font-size:.82rem;font-weight:600}
.st-delay{background:#5A3A00;color:#F07070;padding:3px 10px;border-radius:20px;font-size:.82rem;font-weight:600}
.st-none{background:#3D4557;color:#9BA3AF;padding:3px 10px;border-radius:20px;font-size:.82rem;font-weight:600}
.sec{font-size:1.05rem;font-weight:700;color:#BDE0A9;letter-spacing:2px;border-bottom:1px solid #555B6E;padding-bottom:6px;margin:20px 0 12px 0}
.stButton>button{background:#7BA2F1;color:#1A2030;font-weight:700;border:none;border-radius:8px;padding:8px 24px}
.stButton>button:hover{background:#BDE0A9}
div[data-testid="stMetricValue"]{color:#7BA2F1!important;font-size:1.8rem!important}
div[data-testid="stMetricLabel"]{color:#9BA3AF!important}
</style>""", unsafe_allow_html=True)

# ── Data ─────────────────────────────────────────────────────────────────────
DATA_FILE = "project_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"project_name":"Demo Project","project_name_th":"โครงการตัวอย่าง",
            "contract_no":"SF-NRCT-FY2569","project_owner":"NRCT",
            "contractor":"Faculty of Engineering, CMU","start_date":"2025-10-01",
            "end_date":"2026-09-30","total_budget":8166000,"n_months":12,"activities":[]}

def save_data(d):
    with open(DATA_FILE,"w",encoding="utf-8") as f: json.dump(d,f,ensure_ascii=False,indent=2)
    st.cache_data.clear()

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

SCLS={"Completed":"st-done","In Progress":"st-prog","Pending":"st-pend",
      "Delayed":"st-delay","Not Started":"st-none"}
SMAP={"Completed":"✅ Completed","In Progress":"🚧 In Progress","Pending":"⏳ Pending",
      "Delayed":"💤 Delayed","Not Started":"❌ Not Started","Cancelled":"🚫 Cancelled"}
SCOL={"Completed":"#2A5E3A","In Progress":"#7BA2F1","Pending":"#515863",
      "Delayed":"#F07070","Not Started":"#3D4557"}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 S-Curve Monitor")
    st.markdown("---")
    page=st.radio("Navigate",[
        "🏠 Dashboard","📈 S-Curve","📅 Gantt","📊 EVM Indicators",
        "📝 Update Progress","⚙️ Setup","📥 Import WBS","📋 Process Guide"])
    st.markdown("---")
    data=load_data()
    cm=cur_month(data["start_date"],data["n_months"])
    st.markdown(f"**📅 Current Month:** M{cm}")
    st.markdown(f"**🗓️ Today:** {date.today().strftime('%d %b %Y')}")
    st.markdown("---")
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
        (c1,str(total),"TOTAL TASKS","#515863","#7BA2F1"),
        (c2,str(done),"✅ COMPLETED","#2A5E3A","#BDE0A9"),
        (c3,str(prog),"🚧 IN PROGRESS","#2A4E2A","#C8E49A"),
        (c4,str(delay),"💤 DELAYED","#5A3A00","#F07070"),
        (c5,f"{spi:.2f}" if spi else "—","SPI","#515863",
         "#BDE0A9" if spi and spi>=1 else "#F4A25E" if spi and spi>=0.8 else "#F07070"),
        (c6,f"{sv:+.1f}%" if sv is not None else "—","SCHEDULE VAR.","#515863",
         "#BDE0A9" if sv and sv>=0 else "#F07070"),
    ]
    for col,val,lbl,bg,fg in cards:
        col.markdown(f'<div class="kpi-card" style="background:{bg}"><div class="kpi-num" style="color:{fg}">{val}</div><div class="kpi-label">{lbl}</div></div>',unsafe_allow_html=True)

    st.markdown("")
    cl,cr=st.columns([2,1])
    with cl:
        st.markdown('<div class="sec">S - C U R V E    O V E R V I E W</div>',unsafe_allow_html=True)
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=labels,y=cump,name="Plan",fill="tozeroy",
            fillcolor="rgba(123,162,241,.15)",line=dict(color="#7BA2F1",width=3),
            mode="lines+markers",marker=dict(size=7),
            hovertemplate="<b>%{x}</b><br>Plan: %{y:.1f}%<extra></extra>"))
        ax=[labels[i] for i,v in enumerate(cuma) if v is not None]
        ay=[v for v in cuma if v is not None]
        if ay:
            fig.add_trace(go.Scatter(x=ax,y=ay,name="Actual",fill="tozeroy",
                fillcolor="rgba(189,224,169,.15)",line=dict(color="#BDE0A9",width=3),
                mode="lines+markers",marker=dict(size=8,symbol="diamond"),
                hovertemplate="<b>%{x}</b><br>Actual: %{y:.1f}%<extra></extra>"))
        if cm<=N:
            fig.add_vline(x=labels[cm-1],line_dash="dash",line_color="#F4A25E")
            fig.add_annotation(x=labels[cm-1],y=105,text="TODAY",showarrow=False,
                font=dict(color="#F4A25E",size=11),xanchor="left")
        fig.update_layout(paper_bgcolor="#2D3747",plot_bgcolor="#1A2030",
            font_color="#E8ECF0",height=280,margin=dict(l=10,r=10,t=10,b=10),
            xaxis=dict(gridcolor="#3D4557"),yaxis=dict(gridcolor="#3D4557",range=[0,105]),
            legend=dict(bgcolor="#2D3747"),hovermode="x unified")
        st.plotly_chart(fig,use_container_width=True)

    with cr:
        st.markdown('<div class="sec">A C T I V I T I E S</div>',unsafe_allow_html=True)
        for a in acts:
            st_raw=a.get("status","Not Started")
            sk=next((k for k in SCLS if k in st_raw),"Not Started")
            st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid #3D4557">'
                f'<span style="color:#E8ECF0;font-size:.82rem">{a["no"]}. {a["name"][:35]}…</span>'
                f'<span class="{SCLS[sk]}">{sk}</span></div>',unsafe_allow_html=True)

    st.markdown("---")
    p1,p2,p3,p4=st.columns(4)
    p1.metric("Contract",data.get("contract_no","—"))
    p2.metric("Start",data["start_date"]); p3.metric("End",data["end_date"])
    p4.metric("Budget","THB {:,.0f}".format(data["total_budget"]))

# ── S-CURVE ───────────────────────────────────────────────────────────────────
elif page=="📈 S-Curve":
    st.markdown("# 📈 S-Curve: Plan vs Actual")
    st.markdown("---")
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=labels,y=cump,name="Planned (%)",fill="tozeroy",
        fillcolor="rgba(123,162,241,.15)",line=dict(color="#7BA2F1",width=3),
        mode="lines+markers",marker=dict(size=8),
        hovertemplate="<b>%{x}</b><br>Plan: %{y:.1f}%<extra></extra>"))
    ax=[labels[i] for i,v in enumerate(cuma) if v is not None]
    ay=[v for v in cuma if v is not None]
    if ay:
        fig.add_trace(go.Scatter(x=ax,y=ay,name="Actual (%)",fill="tozeroy",
            fillcolor="rgba(189,224,169,.15)",line=dict(color="#BDE0A9",width=3),
            mode="lines+markers",marker=dict(size=9,symbol="diamond"),
            hovertemplate="<b>%{x}</b><br>Actual: %{y:.1f}%<extra></extra>"))
    if cm<=N:
        fig.add_vline(x=labels[cm-1],line_dash="dash",line_color="#F4A25E")
        fig.add_annotation(x=labels[cm-1],y=105,text=f"M{cm} TODAY",showarrow=False,
            font=dict(color="#F4A25E",size=11),xanchor="left")
    fig.update_layout(paper_bgcolor="#2D3747",plot_bgcolor="#1A2030",
        font=dict(color="#E8ECF0",size=13),height=460,margin=dict(l=20,r=20,t=30,b=20),
        xaxis=dict(title="Month",gridcolor="#3D4557",tickangle=-30),
        yaxis=dict(title="Cumulative Progress (%)",gridcolor="#3D4557",range=[0,105],ticksuffix="%"),
        legend=dict(bgcolor="#515863",bordercolor="#7BA2F1",borderwidth=1),hovermode="x unified")
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
        fig.add_vline(x=date.today().isoformat(),line_dash="dash",line_color="#F4A25E")
        fig.add_annotation(x=date.today().isoformat(),y=1.02,yref="paper",
            text="TODAY",showarrow=False,font=dict(color="#F4A25E",size=11),xanchor="left")
        fig.update_layout(paper_bgcolor="#2D3747",plot_bgcolor="#1A2030",
            font=dict(color="#E8ECF0",size=11),height=420,margin=dict(l=10,r=10,t=20,b=10),
            xaxis=dict(gridcolor="#3D4557"),yaxis=dict(gridcolor="#3D4557"),legend=dict(bgcolor="#515863"))
        st.plotly_chart(fig,use_container_width=True)
    else:
        st.info("No activities yet. Add them in ⚙️ Setup.")

# ── EVM ───────────────────────────────────────────────────────────────────────
elif page=="📊 EVM Indicators":
    st.markdown("# 📊 EVM Indicators"); st.markdown("---")
    st.markdown("|Indicator|Formula|Meaning|\n|---|---|---|\n"
        "|**PV**|Cumulative Plan %|What should be done|\n"
        "|**EV**|Cumulative Actual %|What has been done|\n"
        "|**SV**|EV − PV|+ ahead / − delayed|\n"
        "|**SPI**|EV / PV|>1 ahead • <1 behind|")
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
        fig.add_hline(y=1.0,line_color="#7BA2F1")
        fig.add_annotation(x=1,xref="paper",y=1.0,text="Target SPI=1.0",showarrow=False,
            font=dict(color="#7BA2F1",size=10),xanchor="right",yanchor="bottom")
        fig.add_hline(y=0.95,line_dash="dot",line_color="#F4A25E")
        fig.add_annotation(x=1,xref="paper",y=0.95,text="⚠️ Warning",showarrow=False,
            font=dict(color="#F4A25E",size=10),xanchor="right",yanchor="bottom")
        fig.add_hline(y=0.80,line_dash="dot",line_color="#F07070")
        fig.add_annotation(x=1,xref="paper",y=0.80,text="🔴 Critical",showarrow=False,
            font=dict(color="#F07070",size=10),xanchor="right",yanchor="bottom")
        fig.add_trace(go.Scatter(x=xs,y=ys,name="SPI",line=dict(color="#BDE0A9",width=3),
            mode="lines+markers",marker=dict(size=8,color=["#BDE0A9" if v>=1 else "#F4A25E" if v>=0.8 else "#F07070" for v in ys])))
        fig.update_layout(paper_bgcolor="#2D3747",plot_bgcolor="#1A2030",font=dict(color="#E8ECF0"),
            height=260,margin=dict(l=10,r=10,t=10,b=10),showlegend=False,
            xaxis=dict(gridcolor="#3D4557"),yaxis=dict(gridcolor="#3D4557",title="SPI"))
        st.plotly_chart(fig,use_container_width=True)

# ── UPDATE PROGRESS ───────────────────────────────────────────────────────────
elif page=="📝 Update Progress":
    st.markdown("# 📝 Update Progress")
    st.markdown("---")
    if not acts: st.info("Add activities first in ⚙️ Setup."); st.stop()

    sopts_raw = ["Not Started","In Progress","Pending","Completed","Delayed","Cancelled"]

    st.markdown(f"Double-click any cell to edit. Current month: **M{cm} — {labels[cm-1] if cm<=N else 'N/A'}** (highlighted).")

    # Build single wide table: rows = activities, cols = Status + all months
    prows = []
    for a in acts:
        sk = next((k for k in sopts_raw if k in a.get("status","")), sopts_raw[0])
        row = {"No": a["no"], "Activity": a["name"][:45], "Wt%": a["weight"], "Status": sk}
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
        "No":       st.column_config.TextColumn("No",       width="small",  disabled=True),
        "Activity": st.column_config.TextColumn("Activity", width="large",  disabled=True),
        "Wt%":      st.column_config.NumberColumn("Wt%",   width="small",  disabled=True, format="%.1f"),
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

# ── SETUP ─────────────────────────────────────────────────────────────────────
elif page=="⚙️ Setup":
    st.markdown("# ⚙️ Project Setup"); st.markdown("---")
    with st.form("pf"):
        st.markdown("**Project Information**")
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
        if st.form_submit_button("💾 Save"):
            data.update({"project_name":pn,"project_name_th":pt,"project_owner":po,
                "contractor":pc,"start_date":ps,"end_date":pe,"n_months":int(nm),
                "total_budget":bg,"contract_no":cn})
            save_data(data); st.success("✅ Saved!"); st.rerun()

    st.markdown("---"); st.markdown("**Activities**")
    if acts:
        df=pd.DataFrame([{"No":a["no"],"Name":a["name"],"Wt%":a["weight"],
            "Start M":a["start_month"],"End M":a["end_month"],"Status":a.get("status","—")} for a in acts])
        st.dataframe(df,use_container_width=True,hide_index=True)

    with st.expander("➕ Add New Activity"):
        with st.form("af"):
            ca1,ca2=st.columns(2)
            nn=ca1.text_input("Name (EN)"); nt=ca2.text_input("Name (TH)")
            ca3,ca4,ca5,ca6=st.columns(4)
            ano=ca3.text_input("No.",str(len(acts)+1))
            aw=ca4.number_input("Weight %",0.0,100.0,5.0)
            as_=ca5.number_input("Start M",1,36,1); ae=ca6.number_input("End M",1,36,3)
            if st.form_submit_button("Add"):
                data["activities"].append({"no":ano,"name":nn,"name_th":nt,
                    "weight":aw,"start_month":int(as_),"end_month":int(ae),
                    "status":"❌ Not Started","actuals":{}})
                save_data(data); st.success("✅ Added!"); st.rerun()

# ── IMPORT WBS ────────────────────────────────────────────────────────────────
elif page=="📥 Import WBS":
    st.markdown("# 📥 Import WBS")
    st.markdown("---")

    MANIFEST_PATH = "projects/project_manifest.json"
    PROJECTS_DIR  = "projects"

    # ── TAB A: Project Library (pre-built JSONs) ──────────────────────────────
    tab1, tab2, tab3 = st.tabs(["📚 Project Library", "📄 Upload CSV", "✏️ Manage Activities"])

    with tab1:
        st.markdown("### Pre-built Project Library")
        st.markdown("Click **Load** to switch the active project instantly.")

        if os.path.exists(MANIFEST_PATH):
            with open(MANIFEST_PATH, encoding="utf-8") as _f:
                manifest = json.load(_f)

            # Group by doc
            from collections import OrderedDict as OD
            by_doc = OD()
            for m in manifest:
                by_doc.setdefault(m["doc"], []).append(m)

            doc_icons = {"FULL":"🌐","CM":"🏔️","CR":"🌾","LP":"🌿","PY":"💧"}
            for doc, entries in by_doc.items():
                st.markdown(f"#### {doc_icons.get(doc,'📁')} {doc} — {len(entries)} sub-projects")
                for e in entries:
                    col_name, col_acts, col_bud, col_btn = st.columns([4,1,2,1])
                    col_name.markdown(f"**{e['project_name']}**  \n<small>{e['phase']}</small>",
                                      unsafe_allow_html=True)
                    col_acts.metric("Tasks", e["n_activities"])
                    col_bud.metric("Budget", "THB {:,.0f}".format(e["total_budget"]) if e["total_budget"] else "—")
                    fpath = os.path.join(PROJECTS_DIR, e["filename"])
                    if col_btn.button("▶ Load", key=f"lib_{e['key']}"):
                        if os.path.exists(fpath):
                            with open(fpath, encoding="utf-8") as _pf:
                                new_proj = json.load(_pf)
                            save_data(new_proj)
                            st.success(f"✅ Loaded: **{e['project_name']}** ({e['n_activities']} activities)")
                            st.rerun()
                        else:
                            st.error(f"File not found: {fpath}")
                st.markdown("---")
        else:
            st.warning("No project library found. Run `wbs_extractor.py` to generate pre-built project files, or use the **Upload CSV** tab.")
            st.code("python wbs_extractor.py --csv heymorning_task_import.csv --outdir projects --combine-doc")

    with tab2:
        st.markdown("### Upload WBS CSV")
        st.markdown("Upload `heymorning_task_import.csv` to parse, select a phase, and import.")

    with tab3:
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
                "No":          a.get("no",""),
                "Name (EN)":   a.get("name",""),
                "Name (TH)":   a.get("name_th",""),
                "Weight %":    float(a.get("weight",0)),
                "Start M":     int(a.get("start_month",1)),
                "End M":       int(a.get("end_month",1)),
                "Status":      sk,
            })

        mdf = pd.DataFrame(mrows) if mrows else pd.DataFrame(columns=["No","Name (EN)","Name (TH)","Weight %","Start M","End M","Status"])

        managed = st.data_editor(
            mdf,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",          # ← enables add row (+) and delete (trash)
            column_config={
                "No":        st.column_config.TextColumn("No", width="small"),
                "Name (EN)": st.column_config.TextColumn("Name (EN)", width="large"),
                "Name (TH)": st.column_config.TextColumn("Name (TH)", width="large"),
                "Weight %":  st.column_config.NumberColumn("Weight %", min_value=0.0, max_value=100.0, step=0.5, format="%.2f", width="small"),
                "Start M":   st.column_config.NumberColumn("Start M",  min_value=1, max_value=36, step=1, width="small"),
                "End M":     st.column_config.NumberColumn("End M",    min_value=1, max_value=36, step=1, width="small"),
                "Status":    st.column_config.SelectboxColumn("Status", width="medium", options=sopts_manage),
            },
            key="manage_editor"
        )

        wt_sum = managed["Weight %"].sum() if len(managed) > 0 else 0
        c_info, c_save, c_norm = st.columns([3,1,1])
        c_info.markdown(f"**{len(managed)} activities** | Weight sum: **{wt_sum:.1f}%** {'✅' if abs(wt_sum-100)<1 else '⚠️ should be 100%'}")

        if c_norm.button("⚖️ Normalize Weights", use_container_width=True):
            if wt_sum > 0:
                managed["Weight %"] = (managed["Weight %"] / wt_sum * 100).round(2)
                st.info("Weights normalized to 100%. Click 💾 Save Changes to apply.")

        if c_save.button("💾 Save Changes", use_container_width=True, type="primary"):
            new_acts = []
            for _, row in managed.iterrows():
                name = str(row.get("Name (EN)","")).strip()
                if not name: continue  # skip blank rows
                st_raw = str(row.get("Status","Not Started"))
                new_acts.append({
                    "no":          str(row.get("No","")),
                    "name":        name,
                    "name_th":     str(row.get("Name (TH)","")).strip() or name,
                    "weight":      float(row.get("Weight %", 0) or 0),
                    "start_month": int(row.get("Start M", 1) or 1),
                    "end_month":   int(row.get("End M", 1) or 1),
                    "status":      SMAP.get(st_raw, st_raw),
                    "actuals":     next((a.get("actuals",{}) for a in acts if a.get("no")==str(row.get("No",""))), {}),
                })
            data["activities"] = new_acts
            save_data(data)
            st.success(f"✅ Saved {len(new_acts)} activities!"); st.rerun()

    # ── WBS CSV parser ────────────────────────────────────────────────────────
    def parse_wbs_csv(file_bytes):
        """Parse HeyMorning WBS CSV → list of raw row dicts."""
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
        """Convert filtered CSV rows to activity list for project_data.json."""
        acts = []
        for i, r in enumerate(rows):
            months = parse_months(r.get("NOTES",""))
            if not months: continue
            wt_raw = extract_notes(r.get("NOTES",""), "Weight %")
            try: wt = float(wt_raw)
            except: wt = 0.0
            wbs = extract_notes(r.get("NOTES",""), "WBS")
            acts.append({
                "no": wbs or str(i+1),
                "name": r.get("TASK NAME","").strip(),
                "name_th": r.get("TASK NAME","").strip(),
                "weight": wt,
                "start_month": min(months),
                "end_month": max(months),
                "status": "❌ Not Started",
                "actuals": {}
            })
        # Normalize weights to sum to 100%
        if normalize and acts:
            total = sum(a["weight"] for a in acts)
            if total > 0 and abs(total - 100.0) > 1.0:
                for a in acts:
                    a["weight"] = round(a["weight"] / total * 100, 2)
        return acts

    # ── Upload UI ─────────────────────────────────────────────────────────────
    uploaded = st.file_uploader("Upload WBS CSV file", type=["csv"],
                                help="Export from AI extraction pipeline as heymorning_task_import.csv")

    if uploaded:
        raw_rows = parse_wbs_csv(uploaded.read())
        st.success(f"✅ Loaded {len(raw_rows)} activities from CSV")

        # Group by PHASE
        from collections import OrderedDict
        phase_map = OrderedDict()
        for r in raw_rows:
            ph = r.get("PHASE","Unknown")
            phase_map.setdefault(ph, []).append(r)

        st.markdown("---")
        st.markdown("### Step 1 — Select Sub-Project / Phase")
        st.caption(f"{len(phase_map)} phases found in CSV")

        # Phase summary table
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

        sel_phase = st.selectbox("Select phase to import:", list(phase_map.keys()))
        phase_rows = phase_map[sel_phase]
        acts_preview = rows_to_activities(phase_rows, normalize=True)

        st.markdown("---")
        st.markdown(f"### Step 2 — Preview: **{sel_phase}** ({len(acts_preview)} activities)")
        prev_df = pd.DataFrame([{
            "No": a["no"], "Task Name": a["name"][:50],
            "Weight %": f"{a['weight']:.1f}",
            "M Start": a["start_month"], "M End": a["end_month"]
        } for a in acts_preview])
        st.dataframe(prev_df, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### Step 3 — Project Settings")
        with st.form("wbs_import_form"):
            c1, c2 = st.columns(2)
            proj_name = c1.text_input("Project Name (EN)",
                f"Water Security — {sel_phase}")
            proj_name_th = c2.text_input("Project Name (TH)",
                "โครงการขับเคลื่อนยุทธศาสตร์น้ำมั่นคง")
            c3, c4, c5 = st.columns(3)
            p_start = c3.text_input("Start Date", phase_rows[0].get("START DATE","2025-10-01")[:10])
            p_end   = c4.text_input("End Date",   phase_rows[-1].get("DUE DATE","2026-09-30")[:10])
            n_mo    = c5.number_input("Months", 1, 36, 12)
            budget  = st.number_input("Total Budget (THB)", value=20723000.0, step=100000.0)

            overwrite = st.checkbox("⚠️ Replace current project data", value=True)

            submitted = st.form_submit_button("📥 Import & Save", use_container_width=True)
            if submitted:
                new_data = {
                    "project_name": proj_name,
                    "project_name_th": proj_name_th,
                    "start_date": p_start,
                    "end_date": p_end,
                    "n_months": int(n_mo),
                    "total_budget": float(budget),
                    "contract_no": "",
                    "project_owner": "NRCT",
                    "contractor": "Faculty of Engineering, CMU",
                    "activities": acts_preview
                }
                if overwrite:
                    save_data(new_data)
                    st.success(f"✅ Imported {len(acts_preview)} activities from **{sel_phase}**! Navigate to Dashboard to view.")
                    st.rerun()
                else:
                    # Merge — append activities with new WBS nos
                    current = load_data()
                    existing_nos = {a["no"] for a in current["activities"]}
                    added = 0
                    for a in acts_preview:
                        if a["no"] not in existing_nos:
                            current["activities"].append(a); added += 1
                    save_data(current)
                    st.success(f"✅ Merged: added {added} new activities.")
                    st.rerun()
    else:
        st.info("Upload your WBS CSV file above to begin. The expected format is the `heymorning_task_import.csv` generated by the AI extraction pipeline.")
        st.markdown("**Expected CSV columns:**")
        st.code("PROJECT, PHASE, TASK NAME, DESCRIPTION, IMPORTANT, URGENT, STATUS, PRIORITY, ASSIGNED TO, START DATE, DUE DATE, KANBAN STAGE, PROGRESS, NOTES")

# ── PROCESS GUIDE ─────────────────────────────────────────────────────────────
elif page=="📋 Process Guide":
    st.markdown("# 📋 Process Guide")
    st.markdown("Complete pipeline — from project proposal document to live S-Curve dashboard.")
    st.markdown("---")

    # ── PIPELINE OVERVIEW ────────────────────────────────────────────────────
    st.markdown("## 🔄 Full Pipeline Overview")
    st.markdown("""
<div style="background:#1A2030;border-radius:12px;padding:20px 24px;font-family:monospace;font-size:.9rem;line-height:2.2">
<span style="color:#F4A25E;font-weight:700">STEP 1</span> &nbsp;📄 <span style="color:#BDE0A9">Project Proposal Document</span> &nbsp;(.docx / .pdf)<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↓<br>
<span style="color:#F4A25E;font-weight:700">STEP 2</span> &nbsp;🤖 <span style="color:#BDE0A9">AI Extraction</span> &nbsp;(Claude / ChatGPT + WBS Prompt)<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↓<br>
<span style="color:#F4A25E;font-weight:700">STEP 3</span> &nbsp;📊 <span style="color:#BDE0A9">heymorning_task_import.csv</span> &nbsp;(WBS data table)<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↓<br>
<span style="color:#F4A25E;font-weight:700">STEP 4</span> &nbsp;⚙️ <span style="color:#BDE0A9">wbs_extractor.py</span> &nbsp;(auto-split by sub-project)<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↓<br>
<span style="color:#F4A25E;font-weight:700">STEP 5</span> &nbsp;📁 <span style="color:#BDE0A9">projects/*.json</span> &nbsp;(20 pre-built project files)<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↓<br>
<span style="color:#F4A25E;font-weight:700">STEP 6</span> &nbsp;📥 <span style="color:#BDE0A9">Import WBS → Project Library</span> &nbsp;(one-click load)<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↓<br>
<span style="color:#F4A25E;font-weight:700">STEP 7</span> &nbsp;📈 <span style="color:#7BA2F1">Dashboard / S-Curve / Gantt / EVM</span> &nbsp;✅ Live
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
         "Use the Import WBS page (sidebar) to load your project data. Two options: Project Library (pre-built) or Upload CSV (manual).",
         ["Sidebar → 📥 Import WBS",
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
            st.markdown(f"<p style='color:#E8ECF0'>{desc}</p>", unsafe_allow_html=True)
            for b in bullets:
                st.markdown(f"<div style='color:#BDE0A9;padding:2px 0 2px 16px'>✦ {b}</div>",
                            unsafe_allow_html=True)
            st.markdown("")

    st.markdown("---")

    # ── WBS PROMPT DISPLAY ────────────────────────────────────────────────────
    st.markdown("## 🤖 AI Extraction Prompt")
    st.markdown("Copy this prompt and use it with Claude or ChatGPT + your proposal document.")

    PROMPT_PATH = "WBS_Extraction_Prompt.md"
    if os.path.exists(PROMPT_PATH):
        with open(PROMPT_PATH, encoding="utf-8") as _pf:
            prompt_text = _pf.read()
        # Show only the extractable prompt section
        if "=== PASTE PROMPT BELOW ===" in prompt_text:
            prompt_section = prompt_text.split("=== PASTE PROMPT BELOW ===")[1].split("=== END OF PROMPT ===")[0].strip()
        else:
            prompt_section = prompt_text
        with st.expander("📋 View / Copy Full Prompt", expanded=False):
            st.code(prompt_section, language="markdown")
        st.info("💡 Tip: Click the copy icon (top-right of the code block above) to copy the full prompt, then paste into Claude or ChatGPT with your document attached.")
    else:
        st.warning("WBS_Extraction_Prompt.md not found. Make sure it is in the same folder as app.py.")

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
