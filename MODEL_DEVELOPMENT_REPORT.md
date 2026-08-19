# Repeat Emergency Department Utilization: Model Development Report

## Decision-support scope

This model estimates the risk of a **subsequent emergency encounter within 90 days** after an emergency encounter. It supports Care Manager prioritisation only. It does not determine whether an encounter is avoidable, diagnose a patient, provide triage, or override the Safety Gate or human review.

## Dataset and feature preparation

The source is the synthetic Synthea data in `step4_raw`.

| Source table | Role in the model |
|---|---|
| `encounters.csv` | Index emergency encounters, historical encounter classes, dates, and total claim cost |
| `patients.csv` | Birthdate and demographic fields |

The other Synthea tables (`conditions`, `medications`, `procedures`, and `observations`) are **not included** in this model version.

After type standardisation, key-field checks, duplicate checks, and referential-integrity checks, there were 61,459 encounters and 1,163 patients. There were 2,168 raw emergency encounters. The final feature table contains 2,055 rows:

* 41 emergency encounters in the final 90 observed days were excluded because their outcome cannot be observed completely.
* 72 rows were excluded because a recorded death occurred within the 90-day outcome window; these are not valid “no repeat ED” labels.

Each row represents one patient emergency encounter (`index_date`). The target is 1 if another emergency encounter occurs strictly after the index encounter and within the next 90 days; otherwise 0.

### Leakage controls

All utilization and cost features end strictly before `index_date`. The target-window encounters, the index encounter itself, patient ID, encounter ID, and current Care Manager/Safety Gate context are excluded from the model inputs. Patient ID is used only to assemble the historical timeline.

The primary split is chronological:

| Split | Index dates | Rows | Patients | Positive labels |
|---|---|---:|---:|---:|
| Train | 1919-06-06 to 2019-12-30 | 1,833 | 746 | 335 (18.28%) |
| Validation | 2020-01-08 to 2020-12-31 | 135 | 109 | 25 (18.52%) |
| Test | 2021-01-01 to 2021-08-20 | 87 | 71 | 16 (18.39%) |

The class rate is stable across the three periods. Patients may recur in later time splits (72 train-validation, 49 train-test, and 10 validation-test overlaps). This is appropriate for assessing future scoring of known patients, provided all features remain point-in-time. It is **not** a patient-disjoint estimate of performance on entirely unseen patients.

### Features: 32 model inputs

1. Days since previous encounter and days since previous ED encounter.
2. Counts in 30, 90, and 365-day lookback windows for all encounters and each class: emergency, inpatient, outpatient, ambulatory, urgent care, and wellness.
3. Total claim cost in each 30, 90, and 365-day lookback window.
4. Age at index date, gender, race, ethnicity, marital status, and state.

## Why these models are appropriate for this Synthea tabular dataset

### XGBoost

XGBoost is a gradient-boosted decision-tree model. It is a strong baseline for structured healthcare-utilization data because it models non-linear effects and interactions, for example “recent ED use + low outpatient engagement,” without requiring manually specified interaction terms. It is efficient with modest datasets and can rank high-risk cases well.

Configuration: up to 500 trees, depth 4, learning rate 0.03, row and feature subsampling of 0.85, class-weight ratio, and early stopping after 50 non-improving validation rounds. Numeric variables are median-imputed; categorical variables are mode-imputed and one-hot encoded.

### CatBoost

CatBoost is another gradient-boosted tree method, designed to handle categorical variables directly. It is well suited here because demographic fields are categorical and the dataset is modest in size. Its ordered boosting approach often produces stable performance with fewer preprocessing assumptions than one-hot encoding.

Configuration: up to 500 iterations, depth 6, learning rate 0.04, balanced class weights, and 50-round validation early stopping. Missing categorical values use a dedicated missing category.

### FT-Transformer

FT-Transformer uses feature-token embeddings and self-attention. It can learn interactions across numeric utilization signals and categorical demographics in a single model. It is included as a neural tabular comparator, not assumed to be superior: transformers often need more data than tree methods.

Configuration: 32-dimensional feature embeddings, two Transformer encoder layers, four attention heads, 64-unit feed-forward layers, dropout 0.1, AdamW learning rate 0.001, class-weighted binary loss, and validation early stopping (patience 12, maximum 80 epochs). Numeric features are median-imputed and standardized; categorical features are embedded with an unknown/missing bucket.

## Primary chronological performance (threshold = 0.50)

| Model | Split | ROC-AUC | PR-AUC | Precision | Recall | F1 | Brier | Accuracy |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| CatBoost | Train | 0.9676 | 0.9266 | 0.8194 | 0.8806 | 0.8489 | 0.0725 | 0.9427 |
| CatBoost | Validation | 0.9786 | 0.9483 | 0.7667 | 0.9200 | 0.8364 | 0.0761 | 0.9333 |
| CatBoost | Test | 0.9771 | 0.9552 | 0.8824 | 0.9375 | 0.9091 | 0.0733 | 0.9655 |
| XGBoost | Train | 0.9992 | 0.9961 | 0.9516 | 0.9970 | 0.9738 | 0.0125 | 0.9902 |
| XGBoost | Validation | 0.9662 | 0.9233 | 0.7667 | 0.9200 | 0.8364 | 0.0500 | 0.9333 |
| XGBoost | Test | 0.9833 | 0.9630 | 0.8824 | 0.9375 | 0.9091 | 0.0325 | 0.9655 |
| FT-Transformer | Train | 0.9397 | 0.8981 | 0.8056 | 0.8657 | 0.8345 | 0.0597 | 0.9373 |
| FT-Transformer | Validation | 0.9295 | 0.9214 | 0.7419 | 0.9200 | 0.8214 | 0.0606 | 0.9259 |
| FT-Transformer | Test | 0.9604 | 0.9539 | 0.8333 | 0.9375 | 0.8824 | 0.0523 | 0.9540 |

On the 87-row test period, XGBoost and CatBoost both have TP=15, TN=69, FP=2, FN=1, specificity=97.18%. FT-Transformer has TP=15, TN=68, FP=3, FN=1, specificity=95.77%.

## Is the model overfitting or underfitting?

### CatBoost: no material evidence of overfitting

CatBoost has comparable train, validation, and test ranking quality (ROC-AUC 0.9676, 0.9786, 0.9771). Its F1 is 0.8489, 0.8364, and 0.9091. There is no train-to-validation deterioration suggesting material overfitting. It is also stable in rolling temporal validation. This is not evidence of underfitting because its PR-AUC and recall are high.

### XGBoost: moderate overfitting risk; not underfitting

XGBoost is nearly perfect on train data (ROC-AUC 0.9992, PR-AUC 0.9961, F1 0.9738) but drops on validation (0.9662, 0.9233, 0.8364). That train-validation gap is a warning of moderate overfitting. Its 2021 test performance is excellent, but the test set has only 87 rows and therefore does not remove that concern. It is not underfitting: both validation and test performance remain strong.

### FT-Transformer: low generalization gap; possible capacity/data mismatch

FT-Transformer has a smaller train-validation gap (ROC-AUC 0.9397 to 0.9295; F1 0.8345 to 0.8214), so there is no clear overfitting signal. However, it is generally below the tree models on validation and test ranking metrics. With only 1,833 training rows, a transformer may not have enough data to demonstrate its full advantage. This is best described as a possible capacity/data mismatch rather than proven underfitting.

## Repeated rolling temporal validation

The models were retrained using only earlier years and evaluated on 2019, 2020, and 2021. Average metrics across these three holdout periods:

| Model | ROC-AUC | PR-AUC | F1 | Recall | Brier |
|---|---:|---:|---:|---:|---:|
| CatBoost | 0.9787 | 0.9437 | 0.8510 | 0.9374 | 0.0718 |
| XGBoost | 0.9719 | 0.9246 | 0.8298 | 0.8501 | 0.0437 |
| FT-Transformer | 0.9517 | 0.9330 | 0.8536 | 0.9374 | 0.0563 |

This reinforces the caution on XGBoost: it is best on the latest test period and probability calibration, but CatBoost and FT-Transformer show stronger average recall/F1 across the repeated temporal periods.

## Threshold, calibration, explainability, and fairness

* Thresholds from 0.10 to 0.80 were evaluated on the test set. At threshold 0.30, XGBoost already produces the same TP=15, FP=2, FN=1 as at 0.50. Threshold selection must be finalized on validation data using Care Manager capacity and the accepted false-negative risk, never based solely on accuracy.
* XGBoost has the best test Brier score (0.0325), followed by FT-Transformer (0.0523) and CatBoost (0.0733). Calibration curves are available, but the 87-case test set is too small for a definitive calibration claim.
* Leading feature signals: XGBoost emphasizes urgent-care use in 365/90 days and total 90-day utilization; CatBoost emphasizes urgent-care 90/365 days, outpatient 365-day use, emergency 365-day use, and all encounters in 90 days. These are utilization-pattern signals, not clinical diagnoses.
* Subgroup metrics are descriptive only. The test set has only one positive case in the female subgroup, so it cannot support a fairness conclusion. Larger, representative real-world validation data is required.

## Recommendation

Do not finalize a production model from this synthetic, small test dataset. For the current prototype, retain **XGBoost and CatBoost** as the leading candidates: XGBoost has the strongest latest-period discrimination and Brier score; CatBoost shows less apparent overfitting and stronger rolling temporal stability. FT-Transformer remains a valid comparator but is not currently the performance leader. Select the operating threshold only after Care Manager review capacity and acceptable missed-risk criteria are defined.

## Evidence files

* `step4_ml_output/evaluation/full_metrics_by_split.csv`
* `step4_ml_output/evaluation/rolling_temporal_validation.csv`
* `step4_ml_output/evaluation/threshold_analysis_test.csv`
* `step4_ml_output/evaluation/calibration_test.csv`
* `step4_ml_output/evaluation/*_feature_importance.csv`
* `step4_ml_output/evaluation/subgroup_fairness_test.csv`
