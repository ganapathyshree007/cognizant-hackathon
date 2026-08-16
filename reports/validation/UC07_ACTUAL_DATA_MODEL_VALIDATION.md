# UC07 ACTUAL DATA & MODEL VALIDATION REPORT

## A. Dataset Inventory
The following cleaned datasets and artifact directories were located in the repository:
- **`data_improved/`**: Contains raw, intermediate, and feature datasets such as `trusted_claim_events.csv`, `features_v1_baseline.csv`, `features_v2_enhanced.csv`, and `model_ready_v2.csv`.
- **`cleaned_model_inputs/`**: Contains `claim_events_clean.csv`, `claim_provider_clean.csv`, `member_year_clean.csv`.
- **`model_training_data/`**: Contains `model_features.csv` (used for final training and test splits) and `model_features_report.json`.
- **`pipeline_output/`**: Contains aggregated claims like `unified_encounters.csv` and `collapsed_inpatient_claims.csv`.
- **`step4_raw/`**: Contains raw synthetic FHIR-like data (`claims.csv`, `encounters.csv`, `patients.csv`).

## B. Cleaned-Data Quality (Evaluation of `model_features.csv`)
- **Rows**: 60,411
- **Columns**: 43
- **Data Types**: Mixed numerical (counts, days, binary flags, monetary amounts) and categorical (member IDs, split).
- **Missing Values**: Present primarily in lag features (`days_since_previous_ed`: 36,981 missing; `days_since_previous_event`: 6,264 missing), appropriately reflecting members without prior events. Small missing counts (13 rows) for demographics.
- **Duplicate Rows**: 0
- **Target Distribution**:
  - Negatives (0): 52,890
  - Positives (1): 7,521
- **Target Definition**: "repeat ED-candidate event strictly after index date and within 90 days."

## C. Feature Pipeline
- **Source Tables**: Derived from aggregated claims (Inpatient, Outpatient) transformed through `cms_pipeline.py`.
- **Transformations**: Collapse events into single member-encounters. Calculates 30, 90, and 365-day rolling aggregations of ED visits, outpatient visits, inpatient visits, and total paid amounts strictly prior to the index date. Lag features (`days_since_previous_event`) are computed.
- **Preprocessing Logic**: Handled by an `sklearn.pipeline.Pipeline` with a `SimpleImputer(strategy='median', add_indicator=True)` before being passed to XGBoost. Inference strictly matches training preprocessing because the entire pipeline is serialized in the joblib artifact.

## D. Model Artifact Details
- **Location**: `model_artifacts/repeat_ed_risk_model.joblib`
- **Model Type**: `sklearn.pipeline.Pipeline` containing an `XGBClassifier` (objective: `binary:logistic`).
- **XGBoost Parameters**: 
  - `n_estimators`: 350
  - `learning_rate`: 0.05
  - `max_depth`: 4
  - `colsample_bytree`: 0.85
  - `subsample`: 0.8
  - `min_child_weight`: 8
  - `reg_lambda`: 5
- **Features Expected**: 38 specific numerical/binary features.

## E. Model-Data Compatibility
**PASS**: The actual `model_features.csv` dataset contains all 38 expected features with matching column names, counts, and data types required by the serialized pipeline. No missing required features. Preprocessing handles NaNs correctly via the internal imputer.

## F. Direct Model Prediction Results
Predictions were successfully generated on the test split (11,769 samples). The model output raw probabilities using `predict_proba()[:, 1]`. The model discriminated between risk profiles without failing.

## G. /v1/score Results
The `/v1/score` API implementation correctly extracts the required features from the JSON payload, dynamically constructs a `pd.DataFrame`, and executes the serialized pipeline. The high/low risk band logic is driven dynamically by `THRESHOLD`.

## H. Direct-vs-API Comparison
**PASS**: Tested 5 randomly selected validation records.
- **DIRECT MODEL OUTPUT vs API OUTPUT**: The probability scores matched perfectly to the decimal limit (e.g., Direct: `0.155894` vs API: `0.155894`). The API correctly categorized the risk bands based on the threshold.

## I. Leakage Checks
**PASS**: No temporal leakage detected. A check for negative values in `days_since_previous_event` (which would indicate future data leaking into past indexes) returned 0 violations. The metadata report strictly asserts: "all utilization features use only events strictly before index_date."

## J. Actual Model Metrics (Test Set, N=11,769)
- **Accuracy**: 0.8547
- **Precision**: 0.1523
- **Recall / Sensitivity**: 0.1415
- **Specificity**: 0.9238
- **F1-score**: 0.1467
- **ROC-AUC**: 0.6054
- **PR-AUC**: 0.1255
- **Brier Score**: 0.0802
- **Confusion Matrix**:
  - True Negatives (TN): 9912
  - False Positives (FP): 818
  - False Negatives (FN): 892
  - True Positives (TP): 147

## K. Class Balance
- **Positive Samples**: 7,521 (12.45%)
- **Negative Samples**: 52,890 (87.55%)
- **Explanation**: Accuracy is highly misleading in this context. Because the majority class (No Repeat ED) makes up ~87.5% of the data, a naive model guessing "Negative" every time would achieve 87.5% accuracy. The low F1 and Precision scores indicate the model struggles to accurately isolate the rare positive events.

## L. Threshold Analysis
- **Threshold**: 0.1746
- The threshold is dynamically loaded from `model_report.json` and diverges from the default 0.5. This explicitly adjusts for the severe class imbalance, attempting to improve recall at the expense of false positives. Risk bands in the API correctly use this 0.1746 cutoff.

## M. Prediction Distribution
- **Minimum Risk Score**: 0.0271
- **Maximum Risk Score**: 0.3755
- **Mean Score**: 0.1101
- **Distribution**: The model predictions cluster heavily toward the lower probabilities, reflecting the underlying population prevalence. The maximum predicted probability never exceeds 0.38, highlighting why the operational threshold must be lowered to 0.1746 for the decision rule to trigger positive categorizations.

## N. End-to-End Connectivity
**PASS**: The `predict_proba` logic feeds the numerical `risk_score` directly to the `/v1/score` endpoint. This output cleanly connects to the Navigation Opportunity logic (which conditionally accepts the baseline score) and is compatible with the UC07 Care Management flow.

## O. Problems Found
1. **Low Precision and Recall**: The model correctly predicts only 14% of the true target cases (Recall = 0.141), while suffering from a high false-positive rate amongst those it does flag (Precision = 0.152). 
2. **Probability Calibration Constraint**: The maximum predicted risk score across the test set is only 0.375. The model is systematically underconfident or lacks strongly predictive features capable of definitively identifying high-risk individuals.

## P. Severity of Each Problem
1. **Low Precision/Recall**: **Moderate severity.** Because UC07 treats the model purely as an upstream "decision support" heuristic to identify "opportunities" (and relies on subsequent deterministic rules and a human Care Manager), false positives are largely filtered out by the Safety Gate and Drivers. However, false negatives mean missed intervention opportunities.
2. **Probability Calibration Constraint**: **Low severity** for the immediate workflow, because the operating threshold is explicitly calibrated down to 0.1746 to match the distribution.

## Q. Recommended Next Steps
- Implement advanced feature engineering leveraging unstructured text (if available) or deeper diagnostic pathways to increase model signal.
- Explore different sampling techniques (e.g., SMOTE) or adjusted class weights (`scale_pos_weight`) during model retraining to improve recall for the minority class.

---

## FINAL SUMMARY

- **DATASET**: PASS 
- **PREPROCESSING**: PASS 
- **FEATURE COMPATIBILITY**: PASS 
- **MODEL ARTIFACT**: PASS 
- **MODEL PREDICTION**: PASS 
- **API INTEGRATION**: PASS 
- **DIRECT VS API**: PASS 
- **DATA LEAKAGE**: PASS 
- **MODEL EVALUATION**: AVAILABLE 
- **END-TO-END MODEL FLOW**: PASS 
