# Step 9: Provider / Facility Recommendation

## 1. Purpose
The Step 9 Provider Recommendation Engine securely retrieves the deterministically recommended pathway from Step 8 and queries the provider catalog for matching options. It operates strictly as a decision-support tool for human care managers.

## 2. Scope
This component only returns available provider directory options. It does **not** book appointments, redirect patients autonomously, act as an ED gatekeeper, or perform autonomous clinical triage.

## 3. Provider Source
Because the original CMS database files (`DAC_NationalDownloadableFile.csv`) are absent from this prototype repository, a small set of explicitly labeled "Demo" prototype records is used.
> [!IMPORTANT]
> The generated `provider_catalog.sqlite` is synthetic prototype/demo data only. It must never be represented as real provider data, real availability, or real network participation.

## 4. Provider Database
The data is stored in `ROOT/provider_catalog/provider_catalog.sqlite`. It contains a `providers` schema simulating the necessary subset of CMS directory fields.

## 5. Server-Side Session Authority
Step 9 requires a `pathway_session_id`. It does not accept arbitrary pathway names from the client, blocking attempts to override or manipulate the Step 8 recommendation.

## 6. Safety Gate Enforcement
By utilizing the session chain (`pathway_session_id` → `driver_session_id` → `opportunity_session_id` → `safety_session_id`), Step 9 natively verifies the Safety Gate. If `POSSIBLE_EMERGENCY` or `INSUFFICIENT_INFORMATION` is detected, provider recommendation is blocked.

## 7. Pathway & Specialty Filtering
- **Primary Care**: Matches primary care specialties (e.g., Family Practice, Internal Medicine).
- **Urgent Care**: Matches specific `URGENT CARE FACILITY` records, avoiding confusion with generic physicians.
- **Care Management**: Matches Clinical Social Workers and other care coordination roles.
- **Telehealth**: Matches providers explicitly marked with `telehealth_available='YES'`.

## 8. Location Filtering
The implementation currently allows filtering by `state`. Finer geographic filtering (zip code proximity) requires a more robust geospatial query engine not present in the SQLite prototype. No distance is fabricated.

## 9. Appointment Availability Limitation
The provider source lacks real-time appointment APIs. Therefore, Step 9 explicitly outputs `availability_status: "NOT_VERIFIED"`.

## 10. Network Limitation
No insurance network data is present. The endpoint explicitly outputs `network_status: "NOT_VERIFIED"`.

## 11. Deterministic Ranking
Providers are ranked deterministically using only attributes that actually exist in the verified catalog (e.g., sorting by MIPS score, when available, and facility affiliation count). No ranking fields are fabricated by generative AI. Missing quality data is treated neutrally.

## 12. Human-in-the-loop
All results include the flag `human_review_required: true`. The care manager must manually approve and act upon the recommendation.

## 13. Known Limitations
- Finer geographic proximity matching is unavailable.
- Real-world urgent care mappings often require cross-referencing facility NPIs with group affiliations, whereas this prototype uses a simplified schema.
