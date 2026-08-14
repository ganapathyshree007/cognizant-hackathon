# UC07 — Power BI Dashboard Build Guide

## Purpose and guardrail

This dashboard is a care-manager decision-support experience. It surfaces a modelled **repeat-ED utilisation opportunity**, but never determines emergency safety. Keep the two populations separate:

- `Fact_CMS_Cases`: CMS-derived, de-identified proxy-risk cases used for the XGBoost model and 90-day repeat-ED outcome.
- `Fact_Synthea_Safety`: separate synthetic clinical encounters used to exercise the safety rules.

Do **not** create a relationship between these tables using `member_id`.

## Import and model

1. In Power BI Desktop choose **Get data → Text/CSV** and import every CSV in `powerbi_dashboard/data`.
2. Set `Fact_CMS_Cases[index_date]` and `Dim_Date[Date]` to Date. Set `Fact_Synthea_Safety[index_datetime]` to Date/Time.
3. Create one relationship: `Dim_Date[Date]` (1) → `Fact_CMS_Cases[index_date]` (*), single direction.
4. Keep `Fact_Synthea_Safety`, interventions, outcomes, providers, and evidence tables disconnected unless a clearly documented key is added later.
5. Apply the supplied `UC07_PowerBI_Theme.json` via **View → Themes → Browse for themes**.

## Measures (Modeling → New measure)

```DAX
Cases = DISTINCTCOUNT(Fact_CMS_Cases[case_id])

High Risk Cases = CALCULATE([Cases], Fact_CMS_Cases[risk_band] = "HIGH")

High Risk Rate = DIVIDE([High Risk Cases], [Cases])

Average Risk Score = AVERAGE(Fact_CMS_Cases[risk_score_pct])

Observed Repeat ED 90d = AVERAGE(Fact_CMS_Cases[repeat_ed_90d_flag])

Safety Cases = COUNTROWS(Fact_Synthea_Safety)

Possible Emergency = CALCULATE([Safety Cases], Fact_Synthea_Safety[safety_status] = "POSSIBLE_EMERGENCY")

Interventions Logged = COUNTROWS(Fact_Interventions)
```

Format `High Risk Rate` and `Observed Repeat ED 90d` as percentages.

## Page 1 — Navigator Command Center

Header: `UC07 | Avoidable ED Utilization Navigator` with subtitle `Human-in-the-loop care navigation • modelled opportunity, never emergency triage`.

Top row: Cards for **Cases**, **High Risk Cases**, **Average Risk Score**, **Observed Repeat ED 90d**.

Middle row:

- Clustered column: `Year Month` vs `Cases`.
- Donut: `risk_band` vs `Cases`.
- Bar chart: `suggested_pathway` vs `Cases`.

Bottom row: care-manager queue table with `case_id`, `index_date`, `risk_score_pct`, `risk_band`, `ed_visits_90d`, `chronic_condition_burden`, `safety_status`, `suggested_pathway`, `reason`. Add conditional background: high risk amber, review-required red-tint.

Slicers (top-right): `Year`, `risk_band`, `suggested_pathway`.

## Page 2 — Safety First

Place a red safety banner: `Safety rules override model opportunity scoring. Synthetic validation population shown separately.`

- Cards: **Safety Cases**, **Possible Emergency**.
- Donut: `safety_status`.
- Bar: `DESCRIPTION` by count, Top 10.
- Detail table: `index_datetime`, `DESCRIPTION`, `reason_red_flag`, `abnormal_vital_count`, `safety_status`, `safety_drivers`.

## Page 3 — Care Manager Workbench

Use the CMS case queue. Add a drill-through page filtered by `case_id` with risk score, utilisation history, pathway reason, and evidence links. Use a prominent instruction: `Care manager must review before contacting or referring a member.`

## Page 4 — Provider Navigator

Use `Dim_Provider_Demo` only for the live demo. The full provider catalogue is searched through the protected API, not loaded into Power BI.

- Table: provider name, specialty, telehealth, city, state, quality score, ranking score.
- Slicers: `pathway`, `telehealth_available`.
- Callout: `Live search route: GET /v1/providers/search`.

## Page 5 — Intervention & Outcomes

Use `Fact_Interventions` and `Fact_Outcomes`. Add an information note that current local rows may be test/demo records. Outcome records contain both `INDEX_ENCOUNTER` and `POST_INTERVENTION` anchors; do not blend the two in one rate.

## Design system

- Canvas: 16:9. Use a pale blue-grey page background (#F6F8FB) and white visual cards.
- Primary navy #0B1F3A; teal #0F766E; cyan #38BDF8; amber #F59E0B; escalation red #DC2626.
- Use `Segoe UI` with titles 14–16pt and KPI values 26–32pt.
- Keep page headers aligned; use rounded cards, generous spacing, and no more than six visuals per page.
- Never use green as a signal that a patient is clinically safe; use `REVIEW REQUIRED` and the safety status text.
