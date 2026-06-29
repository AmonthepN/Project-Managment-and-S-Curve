"""
S-Curve Project Monitoring System — Streamlit Web App
Author: Faculty of Engineering, Chiang Mai University
Run:  streamlit run app.py
"""
import json, os
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
        "📝 Update Progress","⚙️ Setup"])
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
    st.markdown("# 📝 Update Monthly Progress")
    st.markdown("Select an activity, enter actual % per month, and save.")
    st.markdown("---")
    if not acts: st.info("Add activities first in ⚙️ Setup."); st.stop()
    sel=st.selectbox("Select Activity",[f"{a['no']}. {a['name']}" for a in acts])
    idx=next(i for i,a in enumerate(acts) if f"{a['no']}. {a['name']}"==sel)
    a=acts[idx]
    st.markdown(f"**Weight:** {a['weight']}%  |  **Months:** M{a['start_month']} → M{a['end_month']}")
    sopts=["Not Started","In Progress","Pending","Completed","Delayed","Cancelled"]
    sk=next((k for k in sopts if k in a.get("status","")),sopts[0])
    new_st=st.selectbox("Status",sopts,index=sopts.index(sk))
    st.markdown("**Monthly Actual Progress (%)** — for this activity only:")
    actuals=a.get("actuals",{}); new_actuals={}
    months_act=list(range(a["start_month"],a["end_month"]+1))
    for i in range(0,len(months_act),4):
        chunk=months_act[i:i+4]; cols=st.columns(len(chunk))
        for col,m in zip(cols,chunk):
            lbl=(datetime.strptime(SI,"%Y-%m-%d")+relativedelta(months=m-1)).strftime("%b %Y")
            new_actuals[str(m)]=col.number_input(f"M{m} ({lbl})",0.0,100.0,
                float(actuals.get(str(m),0)),5.0,key=f"a{idx}m{m}")
    st.markdown("")
    if st.button("💾 Save Progress"):
        data["activities"][idx]["actuals"]=new_actuals
        data["activities"][idx]["status"]=SMAP.get(new_st,new_st)
        save_data(data)
        st.success(f"✅ Saved for Activity {a['no']}!"); st.rerun()

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
