"""
wbs_extractor.py
================
Reads heymorning_task_import.csv (produced by the AI WBS extraction pipeline)
and outputs one project_data_*.json file per sub-project, ready for the
S-Curve Streamlit app.

Usage:
    python wbs_extractor.py --csv heymorning_task_import.csv --outdir projects/
    python wbs_extractor.py --csv heymorning_task_import.csv --outdir projects/ --combine-doc

Each output file is a valid project_data.json with:
    project_name, start_date, end_date, n_months, total_budget, activities[]
"""

import csv, re, json, os, argparse
from collections import OrderedDict, defaultdict

# ── Fiscal year → calendar date mapping (Thai FY: month 1 = October) ─────────
FISCAL_MONTH_MAP = {
    1:"10",2:"11",3:"12",4:"01",5:"02",6:"03",
    7:"04",8:"05",9:"06",10:"07",11:"08",12:"09",
}
MONTH_NAMES = {
    "10":"Oct","11":"Nov","12":"Dec","01":"Jan","02":"Feb","03":"Mar",
    "04":"Apr","05":"May","06":"Jun","07":"Jul","08":"Aug","09":"Sep",
}

def parse_notes(notes, key):
    m = re.search(rf'{re.escape(key)}: ([^\|]+)', notes or "")
    return m.group(1).strip() if m else ""

def parse_months_list(notes):
    raw = parse_notes(notes, "Months")
    try: return sorted(int(x) for x in raw.split(",") if x.strip())
    except: return []

def parse_weight(notes):
    try: return float(parse_notes(notes, "Weight %") or 0)
    except: return 0.0

def parse_cost(notes):
    try: return float(parse_notes(notes, "Estimated cost") or 0)
    except: return 0.0

def parse_wbs(notes):
    return parse_notes(notes, "WBS")

def doc_label(doc):
    labels = {
        "FULL": "Water Security Strategy — 4 Provinces (Full)",
        "CM":   "Water Security Strategy — Chiang Mai (CM)",
        "CR":   "Water Security Strategy — Chiang Rai (CR)",
        "LP":   "Water Security Strategy — Lamphun (LP)",
        "PY":   "Water Security Strategy — Phayao (PY)",
    }
    return labels.get(doc, doc)

def doc_label_th(doc):
    labels = {
        "FULL": "ยุทธศาสตร์น้ำมั่นคง — 4 จังหวัด (Full)",
        "CM":   "ยุทธศาสตร์น้ำมั่นคง — เชียงใหม่",
        "CR":   "ยุทธศาสตร์น้ำมั่นคง — เชียงราย",
        "LP":   "ยุทธศาสตร์น้ำมั่นคง — ลำพูน",
        "PY":   "ยุทธศาสตร์น้ำมั่นคง — พะเยา",
    }
    return labels.get(doc, doc)

def rows_to_activities(rows, normalize=True):
    acts = []
    for r in rows:
        months = parse_months_list(r.get("NOTES",""))
        if not months:
            # fallback: try START DATE / DUE DATE to derive month numbers
            continue
        wt = parse_weight(r.get("NOTES",""))
        wbs_code = parse_wbs(r.get("NOTES",""))
        acts.append({
            "no": wbs_code or str(len(acts)+1),
            "name": r.get("TASK NAME","").strip(),
            "name_th": r.get("TASK NAME","").strip(),
            "weight": wt,
            "start_month": min(months),
            "end_month": max(months),
            "status": "❌ Not Started",
            "actuals": {},
            "_cost": parse_cost(r.get("NOTES","")),
        })
    if not acts:
        return acts
    # Normalize weights to 100%
    if normalize:
        total = sum(a["weight"] for a in acts)
        if total > 0 and abs(total - 100.0) > 0.5:
            for a in acts:
                a["weight"] = round(a["weight"] / total * 100, 4)
    # Round to 2dp and remove internal keys
    for a in acts:
        a["weight"] = round(a["weight"], 2)
        a.pop("_cost", None)
    return acts

def make_project(rows, project_name, project_name_th, n_months=12,
                 start_date="2025-10-01", end_date="2026-09-30"):
    """Convert a list of CSV rows into a project_data dict."""
    acts = rows_to_activities(rows, normalize=True)
    total_cost = sum(parse_cost(r.get("NOTES","")) for r in rows)
    return {
        "project_name": project_name,
        "project_name_th": project_name_th,
        "contract_no": "",
        "project_owner": "NRCT",
        "contractor": "Faculty of Engineering, CMU",
        "start_date": start_date,
        "end_date": end_date,
        "n_months": n_months,
        "total_budget": round(total_cost, 0),
        "activities": acts,
    }

def safe_filename(s):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', s).strip('_')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="heymorning_task_import.csv")
    ap.add_argument("--outdir", default="projects")
    ap.add_argument("--combine-doc", action="store_true",
                    help="Also create one combined JSON per document code")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # Load CSV
    rows = []
    with open(args.csv, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    print(f"Loaded {len(rows)} rows from {args.csv}")

    # Group by PHASE  (e.g. "FULL / Table 19")
    phase_rows = OrderedDict()
    doc_rows   = defaultdict(list)
    for r in rows:
        ph  = r.get("PHASE","Unknown").strip()
        doc = ph.split("/")[0].strip()
        phase_rows.setdefault(ph, []).append(r)
        doc_rows[doc].append(r)

    manifest = []  # [{key, filename, project_name, n_activities, doc}]

    # ── One JSON per PHASE ────────────────────────────────────────────────────
    for ph, ph_rows in phase_rows.items():
        doc = ph.split("/")[0].strip()
        table_part = ph.split("/")[1].strip() if "/" in ph else ph
        pname    = f"{doc_label(doc)} — {table_part}"
        pname_th = f"{doc_label_th(doc)} — {table_part}"
        proj     = make_project(ph_rows, pname, pname_th)
        key      = safe_filename(ph)
        fname    = f"project_{key}.json"
        fpath    = os.path.join(args.outdir, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(proj, f, ensure_ascii=False, indent=2)
        manifest.append({"key": key, "filename": fname, "project_name": pname,
                          "doc": doc, "phase": ph,
                          "n_activities": len(proj["activities"]),
                          "total_budget": proj["total_budget"]})
        print(f"  ✅  {fname}  ({len(proj['activities'])} activities)")

    # ── One combined JSON per Document Code ───────────────────────────────────
    if args.combine_doc:
        for doc, d_rows in doc_rows.items():
            pname    = doc_label(doc)
            pname_th = doc_label_th(doc)
            proj     = make_project(d_rows, pname, pname_th)
            key      = f"combined_{safe_filename(doc)}"
            fname    = f"project_{key}.json"
            fpath    = os.path.join(args.outdir, fname)
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(proj, f, ensure_ascii=False, indent=2)
            manifest.append({"key": key, "filename": fname, "project_name": pname,
                              "doc": doc, "phase": f"{doc} (all tables combined)",
                              "n_activities": len(proj["activities"]),
                              "total_budget": proj["total_budget"]})
            print(f"  ✅  {fname}  COMBINED ({len(proj['activities'])} activities)")

    # ── Save manifest (index of all projects) ─────────────────────────────────
    mpath = os.path.join(args.outdir, "project_manifest.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\n✅  Manifest saved: {mpath}")
    print(f"✅  Total project files: {len(manifest)}")

if __name__ == "__main__":
    main()
