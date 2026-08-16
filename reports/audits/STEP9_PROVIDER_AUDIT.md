# Step 9: Provider / Facility Recommendation Audit

## 1. Executive Summary
The Step 9 Provider Recommendation API is currently **critically broken and disconnected from the authoritative session chain**. While `backend/main.py` defines a `/v1/providers/search` endpoint, it attempts to query a non-existent SQLite database (`provider_catalog.sqlite`), completely ignores the Step 8 `pathway_session_id`, lacks proper geographic location filtering, and does not enforce the Safety Gate.

## 2. Existing Provider Architecture
The repository contains scripts (`build_provider_catalog.py`, `rank_providers.py`) intended to build a CSV file from raw CMS directory files. However, the `backend/main.py` expects an SQLite database containing a `providers` table, which is completely missing from the project.

## 3. Existing API
The endpoint `GET /v1/providers/search` accepts `pathway` (as an arbitrary string), `state`, `require_telehealth`, and `limit`. It executes a raw SQL query but fails due to the missing database file.

## 4. Provider Data Source
The intended source is `ROOT/'provider_catalog'/'provider_catalog.sqlite'`, which is missing. There are no provider records in the repository to evaluate.

## 5. Provider Data Quality
Cannot be evaluated due to the missing database.

## 6. Pathway-to-Provider Mapping
The backend maps pathways to specialties deterministically:
- `PRIMARY_CARE`: General Practice, Family Practice, Internal Medicine, Geriatric Medicine
- `URGENT_CARE`: Emergency Medicine, Family Practice, General Practice, Internal Medicine (Note: This incorrectly maps urgent care to general doctors rather than specific urgent care facilities)
- `CARE_MANAGEMENT`: Clinical Social Worker, Nurse Practitioner, General/Internal Medicine
- `TELEHEALTH`: General/Family/Internal Medicine

## 7. Location Filtering
**Partially Implemented**. The API only supports filtering by `state` (exact match). It has no concept of geographic distance, zip code proximity, or city-level filtering.

## 8. Telehealth
**Implemented**. The system filters providers where `telehealth_available='YES'`, derived from the CMS indicator.

## 9. Appointment Availability
**Missing**. The provider data has no real-time appointment slots or scheduling APIs.

## 10. Network/Insurance
**Missing**. There is no insurance, payer, or network affiliation data in the database design.

## 11. Provider Ranking
**Implemented**. Providers are deterministically ranked using a hardcoded SQL `ORDER BY` clause: prioritizing non-null MIPS quality scores, then raw MIPS score, then affiliated facility count.

## 12. Server-Side Authority
**Critically Failed**. The endpoint accepts `pathway="PRIMARY_CARE"` directly from the client. It does not require a `pathway_session_id`. A client can completely bypass Step 8 and request providers for any pathway.

## 13. Safety Gate Integration
**Critically Failed**. Because the endpoint does not trace back to a `safety_session_id`, a client can query providers for a patient flagged as `POSSIBLE_EMERGENCY`.

## 14. Human Review
**Implemented**. The API serves as a read-only directory and includes a disclaimer that human review is required. No auto-booking or patient redirection exists.

## 15. LLM/RAG Audit
**Passed**. Provider recommendation relies entirely on deterministic SQL queries (no LLM hallucination of providers).

## 16. End-to-End Scenario Results
- **Scenario A (Primary Care)**: Fails (DB missing). If fixed, returns primary care doctors.
- **Scenario B (Urgent Care)**: Incorrectly returns general practitioners instead of urgent care facilities.
- **Scenario C (Telehealth)**: Returns telehealth-marked doctors.
- **Scenario E (Possible Emergency)**: Fails to block the request.

## 17. Missing Components
- The actual SQLite provider database.
- Linkage to `pathway_session_id` (Server-side authority).
- Safety Gate enforcement.
- Proper location/distance filtering.
- Network/Appointment availability.

## 18. Incorrect Components
- `URGENT_CARE` mapping is flawed (maps to doctors, not urgent care centers).
- Endpoint accepts arbitrary client strings instead of session IDs.

## 19. Recommended Changes
1. **Enforce Session Chain**: Update `/v1/providers/search` to require `pathway_session_id` instead of raw strings. This implicitly enforces the Safety Gate.
2. **Database Generation**: Create a script to actually build the `provider_catalog.sqlite` database required by the backend.
3. **Location Search**: Upgrade the search to support zip-code level proximity or city filtering, not just state.
4. **Urgent Care Fix**: Adjust the urgent care mapping to target specific facility types rather than broad medical specialties.

## 20. Priority Order
1. Server-side authority & Safety Gate enforcement.
2. Provider SQLite database generation.
3. Location/Distance filtering.
4. Pathway mapping corrections.
