# UC07 Specialist Feature Groups (Experiment 06)

This document defines the strict categorization of the 40 validated CMS historical features into three mutually exclusive specialist models.

## A. DEMOGRAPHIC + CHRONIC (18 Features)
**Concept**: Intrinsic patient risk factors, coverage characteristics, and long-term established disease burden.
**Model**: CatBoost

| Feature | Reason | Source | Time Window |
|---|---|---|---|
| `age_at_year_end` | Demographic core | Beneficiary File | Index Year |
| `BENE_HI_CVRAGE_TOT_MONS` | Coverage/Demographic | Beneficiary File | Index Year |
| `BENE_SMI_CVRAGE_TOT_MONS` | Coverage/Demographic | Beneficiary File | Index Year |
| `BENE_HMO_CVRAGE_TOT_MONS` | Coverage/Demographic | Beneficiary File | Index Year |
| `PLAN_CVRG_MOS_NUM` | Coverage/Demographic | Beneficiary File | Index Year |
| `BENE_ESRD_IND` | Chronic physiological condition | Beneficiary File | Index Year |
| `chronic_alzhdmta` | Chronic condition flag | Beneficiary File | Historical |
| `chronic_chf` | Chronic condition flag | Beneficiary File | Historical |
| `chronic_chrnkidn` | Chronic condition flag | Beneficiary File | Historical |
| `chronic_cncr` | Chronic condition flag | Beneficiary File | Historical |
| `chronic_copd` | Chronic condition flag | Beneficiary File | Historical |
| `chronic_depressn` | Chronic condition flag | Beneficiary File | Historical |
| `chronic_diabetes` | Chronic condition flag | Beneficiary File | Historical |
| `chronic_ischmcht` | Chronic condition flag | Beneficiary File | Historical |
| `chronic_osteoprs` | Chronic condition flag | Beneficiary File | Historical |
| `chronic_ra_oa` | Chronic condition flag | Beneficiary File | Historical |
| `chronic_strketia` | Chronic condition flag | Beneficiary File | Historical |
| `chronic_condition_burden` | Meta-chronic severity | Engineered | Historical |

## B. UTILIZATION (15 Features)
**Concept**: Volumetric tracking of how frequently the patient interacts with the healthcare system, independent of cost.
**Model**: LightGBM

| Feature | Reason | Source | Time Window |
|---|---|---|---|
| `days_since_previous_event` | Temporal utilization spacing | Claims | Rolling |
| `days_since_previous_ed` | Temporal utilization spacing | Claims | Rolling |
| `all_visits_30d` | Encounter volume | Claims | 30 Days |
| `ed_visits_30d` | Encounter volume | Claims | 30 Days |
| `outpatient_visits_30d` | Encounter volume | Claims | 30 Days |
| `inpatient_visits_30d` | Encounter volume | Claims | 30 Days |
| `all_visits_90d` | Encounter volume | Claims | 90 Days |
| `ed_visits_90d` | Encounter volume | Claims | 90 Days |
| `outpatient_visits_90d` | Encounter volume | Claims | 90 Days |
| `inpatient_visits_90d` | Encounter volume | Claims | 90 Days |
| `all_visits_365d` | Encounter volume | Claims | 365 Days |
| `ed_visits_365d` | Encounter volume | Claims | 365 Days |
| `outpatient_visits_365d` | Encounter volume | Claims | 365 Days |
| `inpatient_visits_365d` | Encounter volume | Claims | 365 Days |
| `distinct_provider_count_365d` | Utilization fragmentation | Claims | 365 Days |

## C. CLINICAL / SEVERITY (7 Features)
**Concept**: Financial and diagnostic intensity markers serving as proxies for acuity and encounter complexity.
**Model**: CatBoost

| Feature | Reason | Source | Time Window |
|---|---|---|---|
| `total_paid_30d` | Cost/Acuity proxy | Claims | 30 Days |
| `diagnosis_coded_visits_30d` | Clinical documentation intensity | Claims | 30 Days |
| `total_paid_90d` | Cost/Acuity proxy | Claims | 90 Days |
| `diagnosis_coded_visits_90d` | Clinical documentation intensity | Claims | 90 Days |
| `total_paid_365d` | Cost/Acuity proxy | Claims | 365 Days |
| `diagnosis_coded_visits_365d` | Clinical documentation intensity | Claims | 365 Days |
| `acute_cost_velocity_90d` | Acuity trend/escalation | Engineered | 90 vs 365 Days |
