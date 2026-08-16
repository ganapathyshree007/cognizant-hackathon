# Patient History Feedback & Idempotency

## 1. Duplicate Protection (Idempotency)
The system now enforces deterministic duplicate protection for both Interventions and Outcomes. This prevents the accidental creation of duplicate records if the client resubmits the same request (e.g., due to network timeouts).

### Intervention Idempotency
- **Endpoint**: `POST /v1/interventions`
- **Rule**: A single `review_id` can only generate one intervention. 
- **Behavior**: If the endpoint is called again with the same `review_id`, the system intercepts the insertion, retrieves the existing `intervention_id`, and returns it seamlessly to the client with a 200 OK status. No error is thrown and no duplicate row is created.

### Outcome Idempotency
- **Endpoint**: `POST /v1/interventions/{intervention_id}/outcomes`
- **Rule**: A specific intervention can only have one outcome generated for a specific `anchor_type` (`INDEX_ENCOUNTER` or `POST_INTERVENTION`).
- **Behavior**: If called repeatedly for the same intervention, the endpoint will safely return the existing `outcome_id`s instead of computing and inserting new identical outcome records.

## 2. Patient History Feedback Loop
We implemented a secure patient history feedback loop that segregates operational care management data from raw CMS claims.

### The `member_history` Table
A new `member_history` table was added to `backend_state.sqlite`. This table records point-in-time operational events without fabricating artificial CMS claims.
- **`event_id`**: Unique identifier for the history event.
- **`member_id`**: The member the event belongs to.
- **`event_type`**: Either `INTERVENTION` or `OUTCOME`.
- **`event_date`**: The date the event occurred or was anchored to.
- **`source`**: The lineage of the event (e.g., `intervention_id:1234` or `outcome_id:5678`).
- **`details`**: JSON payload detailing the event (the decision made or the utilization observed).

### Event Triggers
- When an intervention is successfully created, an `INTERVENTION` event is appended to the member's history.
- When an outcome is successfully computed, an `OUTCOME` event is appended to the member's history.

## 3. Future Scoring Integration
This patient history table serves as the foundation for future Machine Learning cycles.

1. **Static XGBoost Model**: We explicitly DO NOT retrain the existing XGBoost repeat-ED risk model automatically. The model operates correctly as a point-in-time prediction engine.
2. **Feature Generation Access**: During a future prediction cycle, the feature-generation pipeline can read from `member_history` to compute features (e.g., "Days since last care management intervention" or "Previous intervention outcome success").
3. **Temporal Leakage Control**: The system guarantees temporal validity. By checking that the `event_date` is strictly less than or equal to the `prediction_date`, the pipeline mathematically prevents future interventions or outcomes from leaking into an earlier prediction cycle.
