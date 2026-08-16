# UC07 CMS Data Quality Validation

## 1. Cleaned Data Audit
| Dataset | Issue | Count | Percentage | Severity | Action |
|---|---|---:|---:|---|---|
| member_year_clean.csv | Rows | 343644 | - | Low | None |
| member_year_clean.csv | Missing BENE_ESRD_IND | 0 | 0.00% | Low | Fill False |
| claim_events_clean.csv | Rows | 846520 | - | Low | None |
| claim_events_clean.csv | Missing start_date | 278 | 0.03% | High | Drop |
| claim_events_clean.csv | Negative payment | 2612 | 0.31% | Medium | Clip to 0 |
| model_features.csv (current) | Rows | 60411 | - | Low | None |

## 2. Existing Cleaning Pipeline
- Dates are standardized to datetime objects.
- Missing start dates are dropped before feature generation.
- Negative payments are clipped to 0.
- `member_id` acts as the primary join key.
- Strict `<` temporal checks prevent future leakage.
