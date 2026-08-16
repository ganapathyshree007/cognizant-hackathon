# UC07 Step 4: Synthea Historical Risk Model Benchmark

## 1. Evaluation Strategy
**Grouped Chronological Holdout**
Patients were grouped by their last index timestamp. The earliest 60% of patients form the Train set, the next 20% the Validation set, and the most recent 20% the Test set. All historical records for a patient follow them into their assigned cohort, preventing patient leakage.
*Limitation*: The test set contains older historical examples because entire patient histories are assigned to the test cohort if their final event is recent.

## 2. Models Evaluated
Logistic Regression, XGBoost, LightGBM, CatBoost. 
*Note*: FT-Transformer was excluded due to the small sample size (N=2061).

## 3. Validation & Calibration
- **Best Model**: LightGBM
- **Optimal Validation Threshold**: 0.094
- **Calibration Method**: isotonic (Fitted on Validation/OOF without touching final test set).

## 4. Final Test Performance (Untouched Holdout)
| Metric | Synthea Model (LightGBM) | CMS Existing Model (Ref) |
|---|---|---|
| PR-AUC | 0.903 | N/A (Not in threshold export) |
| ROC-AUC | 0.938 | N/A |
| F1 | 0.839 | 0.269 |
| Precision | 0.758 | 0.167 |
| Recall | 0.939 | 0.684 |
| Specificity | 0.858 | 0.521 |
| Brier Score | 0.173 | N/A |

### Confusion Matrix
TP: 200
TN: 386
FP: 64
FN: 13

## 5. Comparison
- **Against Friend's Model**: Our methodology is statistically far more reliable. Grouped chronologic holds prevent patient leakage.
- **Against CMS Model**: Synthea clean clinical features provide strong historical prediction capabilities. 
