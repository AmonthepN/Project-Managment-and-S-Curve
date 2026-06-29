# WBS Extraction Prompt — S-Curve Project Manager
## Version 1.1 | Faculty of Engineering, Chiang Mai University

---

## HOW TO USE THIS PROMPT

1. Copy everything below the line `=== PASTE PROMPT BELOW ===`
2. Open a new Claude / ChatGPT conversation
3. Paste the prompt, then **attach your project proposal document** (Word / PDF)
4. The AI will output a CSV table
5. Save the CSV as `heymorning_task_import.csv`
6. Upload to the S-Curve web app → **📥 Import WBS → Upload CSV** tab

---

## EXPECTED OUTPUT FORMAT

The AI must output a CSV with these exact columns:

```
PROJECT, PHASE, TASK NAME, DESCRIPTION, IMPORTANT, URGENT, STATUS, PRIORITY,
ASSIGNED TO, START DATE, DUE DATE, KANBAN STAGE, PROGRESS, NOTES
```

The `NOTES` column must contain pipe-separated metadata:

```
WBS: FULL.1.01 | Document: FULL | FY(BE): 2569 | Months: 1,2,3 |
Weight %: 10.0 | Estimated cost: 2072300.0 | Duration days: 92 | Source: table 19, row 2
```

---

=== PASTE PROMPT BELOW ===

# ROLE

You are a senior project controls engineer and WBS specialist.
Your task is to read the attached project proposal document and extract a
complete Work Breakdown Structure (WBS) that is ready for import into
an S-Curve Project Management system.

---

# OBJECTIVE

Extract ALL activities, tasks, and work packages from the document.
Output TWO things:

1. **WBS Summary Table** — full structured breakdown
2. **Import CSV** — ready to copy-paste or save as `heymorning_task_import.csv`

---

# STEP 1 — IDENTIFY PROJECT STRUCTURE

Before extracting, identify:

- **Project name** (EN and TH if available)
- **Document code(s)**: e.g. `FULL`, `CM`, `CR`, `LP`, `PY`
  - If the document covers multiple provinces or sub-projects, assign each a code
- **Fiscal year** (BE): e.g. 2569 (= 2026 CE)
- **Total budget** (THB)
- **Project duration** in months (usually 12)
- **Start month**: fiscal month 1 = October of prior calendar year

### Fiscal Month → Calendar Date Table

| Fiscal Month | Calendar Month | Example (FY2569) |
|---|---|---|
| 1  | October   | 2025-10 |
| 2  | November  | 2025-11 |
| 3  | December  | 2025-12 |
| 4  | January   | 2026-01 |
| 5  | February  | 2026-02 |
| 6  | March     | 2026-03 |
| 7  | April     | 2026-04 |
| 8  | May       | 2026-05 |
| 9  | June      | 2026-06 |
| 10 | July      | 2026-07 |
| 11 | August    | 2026-08 |
| 12 | September | 2026-09 |

---

# STEP 2 — EXTRACT WBS ACTIVITIES

Scan the document for:

- **Schedule tables** (rows = activities, columns = months with ✓ or shading)
- **Budget breakdown tables** (rows = activities with cost or % columns)
- **Work package lists** (WP1, WP2, milestone rows)
- **Gantt chart** descriptions

For each activity extract:

| Field | Rule |
|---|---|
| **WBS Code** | Format: `[DOC].[TABLE].[SEQ]` e.g. `FULL.1.01`, `CM.2.03` |
| **Document Code** | `FULL`, `CM`, `CR`, `LP`, `PY`, or custom |
| **Phase / Table** | `[DOC] / Table [N]` or `[DOC] / WP[N]` |
| **Activity Name** | Exact Thai or English name from document |
| **Active Months** | List of fiscal month numbers where the activity is active, e.g. `1,2,3` |
| **Start Date** | First day of first active month (`yyyy-mm-dd`) |
| **Finish Date** | Last day of last active month (`yyyy-mm-dd`) |
| **Duration Days** | Calendar days from start to finish inclusive |
| **Weight %** | Percentage weight of activity within its phase/table (sum = 100% per table) |
| **Estimated Cost** | `Total Budget × Weight %`. If explicit cost given, use that |
| **Source Evidence** | File name + table number + row number |

---

# STEP 3 — APPLY THESE RULES

### Weight Rules
- If the document has explicit % weights per activity → use them directly
- If no weights: estimate as `1 / total_activities × 100`
- Weights within each source table must sum to **100%**

### Cost Rules
- If explicit line-item cost → use it
- Else: `Estimated Cost = Total Budget × (Weight % / 100)`
- Always add to Assumptions: *"Estimated from project budget × activity weight %"*

### Priority Rules
| Condition | Priority |
|---|---|
| Weight ≥ 15% OR Cost ≥ 3,000,000 THB | `High` |
| Weight ≥ 8% OR Cost ≥ 1,000,000 THB | `Medium` |
| Otherwise | `Low` |

### Status Rules
- Default: `Not Started`
- Override if document explicitly states otherwise

### Validation Checklist
Before outputting, verify:
- [ ] Every row has WBS, task name, start date, finish date, weight %, source
- [ ] Start date ≤ finish date
- [ ] All dates use `yyyy-mm-dd` format
- [ ] WBS codes are unique across the entire document
- [ ] Weights per table sum to 100%
- [ ] No formula column N is referenced (skip it)

---

# STEP 4 — OUTPUT FORMAT

## Part A: WBS Summary Table

Output a markdown table with columns:
`WBS | Document | Phase | Activity Name | Start Date | Finish Date | Duration Days | Weight % | Estimated Cost | Priority | Source`

## Part B: Import CSV

Output a code block labeled ```csv with this EXACT header row and one data row per activity:

```
PROJECT,PHASE,TASK NAME,DESCRIPTION,IMPORTANT,URGENT,STATUS,PRIORITY,ASSIGNED TO,START DATE,DUE DATE,KANBAN STAGE,PROGRESS,NOTES
```

Rules for each column:
- `PROJECT`: Use project name (EN). Same value for all rows in the same document
- `PHASE`: Format exactly as `[DOC] / Table [N]` e.g. `FULL / Table 19`
- `TASK NAME`: Activity name (Thai or EN from document)
- `DESCRIPTION`: `[source_file] | table [N], row [R]`
- `IMPORTANT`: `false`
- `URGENT`: `false`
- `STATUS`: `Not Started`
- `PRIORITY`: `High`, `Medium`, or `Low` (see rules above)
- `ASSIGNED TO`: `AI Planner`
- `START DATE`: `yyyy-mm-dd`
- `DUE DATE`: `yyyy-mm-dd`
- `KANBAN STAGE`: `Backlog`
- `PROGRESS`: `0`
- `NOTES`: Exactly this format (pipe-separated, no line breaks):

```
WBS: [code] | Document: [DOC] | FY(BE): [year] | Months: [1,2,3] | Weight %: [n.n] | Estimated cost: [nnnn.n] | Duration days: [n] | Source: [file | table N, row R] | [assumption text if any]
```

## Part C: Assumptions

List all assumptions made during extraction.

## Part D: Missing Information

List any fields that could not be determined from the document.

## Part E: Validation Summary

Confirm: total rows extracted, date range, weight sum per table.

---

# IMPORTANT NOTES

- Do NOT invent activities not in the document
- Do NOT skip any activity row in a schedule or budget table
- If multiple sub-projects or provinces exist in ONE document, give each its own Document Code and separate rows
- The NOTES column is critical — the import script reads `Months:`, `Weight %:`, `WBS:`, and `Estimated cost:` from it
- Keep commas out of activity names (use semicolons if needed in Thai text)
- Wrap fields containing commas in double quotes in the CSV

Now read the attached document and extract the complete WBS.

=== END OF PROMPT ===
