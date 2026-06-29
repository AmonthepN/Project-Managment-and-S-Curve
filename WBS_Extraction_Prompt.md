# WBS Extraction Prompt for S-Curve and HeyMorning Template

You are a project controls planner. Extract a clean Work Breakdown Structure (WBS) from the provided project document text, tables, budgets, and schedules.

## Goal

Create structured WBS rows that can be used for:

1. S-curve planning.
2. Project/task tracking.
3. Import into the HeyMorning Project Task Manager template.

## Source Data

Use only the information provided in the project documents. Prefer explicit schedule tables, budget tables, milestones, activity tables, and work package descriptions.

If the document does not contain an explicit WBS, infer the WBS from:

- Project/subproject structure.
- Work package labels such as `WP1`, `WP2`, `WP3`.
- Activity schedule rows.
- Milestone rows.
- Budget/task descriptions.

## Required Output

Return a table with these columns:

| Column | Description |
|---|---|
| `WBS` | Hierarchical WBS code, e.g. `1.0`, `1.1`, `CM.1.01`, `FULL.2.03` |
| `Document Code` | Source grouping, e.g. `FULL`, `CM`, `CR`, `LP`, `PY` |
| `Activity / Work Package` | Short task or work package name |
| `Description` | Brief description of scope |
| `Start Date` | Planned start date in `yyyy-mm-dd` |
| `Finish Date` | Planned finish date in `yyyy-mm-dd` |
| `Duration Days` | Inclusive duration in days |
| `Planned Hours` | Labor hours if available; blank if not stated |
| `Planned Cost` | Cost if directly stated, or estimated from budget x activity weight |
| `Weight %` | Activity percentage or calculated planning weight |
| `Weight Basis` | One of `Cost`, `Hours`, `Both`, `Manual` |
| `Status` | Default to `Not Started` unless stated otherwise |
| `Source Evidence` | File/table/section reference supporting the row |
| `Assumptions` | Any assumptions used for dates, cost, hours, or weights |

## Date Rules

If the document uses fiscal year month columns `1` to `12`, interpret them as:

| Fiscal Month | Calendar Month |
|---|---|
| 1 | October of prior calendar year |
| 2 | November of prior calendar year |
| 3 | December of prior calendar year |
| 4 | January |
| 5 | February |
| 6 | March |
| 7 | April |
| 8 | May |
| 9 | June |
| 10 | July |
| 11 | August |
| 12 | September |

For example, fiscal year `2569`, month `1` means `2025-10`, and month `12` means `2026-09`.

Use the first active month as the start month and the last active month as the finish month. Use the first day of the start month and the last day of the finish month.

## Cost Rules

Use explicit activity-level cost if available.

If only total project budget and activity percentage are available:

```text
Planned Cost = Total Project Budget x Activity Weight %
```

Mark this in `Assumptions`:

```text
Estimated from project budget x activity percentage; source table does not provide line-item activity cost.
```

## Hours Rules

Use explicit labor hours if available.

If labor hours are not stated, leave `Planned Hours` blank. Do not invent hours unless specifically asked to estimate them.

## HeyMorning Template Mapping

Also provide a second table called `HeyMorning Import` with these columns:

| HeyMorning Column | Source |
|---|---|
| `PROJECT` | Project name |
| `PHASE` | `Document Code / Table or Work Package` |
| `TASK NAME` | `Activity / Work Package` |
| `DESCRIPTION` | Source evidence or short scope |
| `IMPORTANT` | `FALSE` |
| `URGENT` | `FALSE` |
| `STATUS` | `Not Started` unless stated otherwise |
| `PRIORITY` | `High`, `Medium`, or `Low` based on weight/cost |
| `ASSIGNED TO` | `AI Planner` unless owner is stated |
| `START DATE` | `Start Date` |
| `DUE DATE` | `Finish Date` |
| `KANBAN STAGE` | `Backlog` unless status suggests otherwise |
| `PROGRESS` | `0` unless status suggests otherwise |
| `NOTES` | Include WBS, weight, cost, duration, and source evidence |

Priority rules:

- `High` if `Weight % >= 15` or `Planned Cost >= 3,000,000`.
- `Medium` if `Weight % >= 8` or `Planned Cost >= 1,000,000`.
- Otherwise `Low`.

Progress rules:

- `Completed` = `1`
- `In Progress` = `0.35`
- Otherwise `0`

## Validation Rules

Before finalizing, check:

- Every row has WBS, task name, start date, finish date, status, and source evidence.
- Start date is not after finish date.
- Dates use `yyyy-mm-dd`.
- WBS codes are unique.
- Status values are valid: `Not Started`, `In Progress`, `Completed`, `On Hold`, `Cancelled`, `Pending`.
- Priority values are valid: `High`, `Medium`, `Low`.
- Weight and cost assumptions are clearly labeled.
- Do not overwrite or populate HeyMorning formula column `N`; only prepare columns `C:M` and `O:Q`.

## Final Response Format

Return:

1. `WBS Activities` table.
2. `HeyMorning Import` table.
3. `Assumptions`.
4. `Missing Information`.
5. `Validation Summary`.

Keep the output structured and ready to export to CSV or Excel.
