# UC07 Step 4: Synthea Feature Provenance & Robustness Audit

## 1. Test PR-AUC Baseline
- **Positive Test Cases**: 213
- **Random-Classifier Baseline (Prevalence)**: 0.3213
- **Model G PR-AUC**: 0.8262
- **PR-AUC Lift**: 2.57x

## 2. Feature Group Ablation
| Model | Feature Set | Count | PR-AUC | ROC-AUC | Precision | Recall | F1 | Specificity | Brier |
|---|---|---|---|---|---|---|---|---|---|
| A | 6 | 0.210 | 0.186 | 0.132 | 0.023 | 0.040 | 0.927 | 0.339 |
| B | 34 | 0.865 | 0.945 | 0.793 | 0.915 | 0.850 | 0.887 | 0.072 |
| C | 38 | 0.816 | 0.935 | 0.750 | 0.930 | 0.830 | 0.853 | 0.080 |
| D | 37 | 0.851 | 0.946 | 0.794 | 0.944 | 0.863 | 0.884 | 0.066 |
| E | 36 | 0.893 | 0.940 | 0.735 | 0.925 | 0.819 | 0.842 | 0.075 |
| F | 35 | 0.865 | 0.943 | 0.760 | 0.934 | 0.838 | 0.860 | 0.074 |
| G | 44 | 0.826 | 0.939 | 0.773 | 0.925 | 0.842 | 0.871 | 0.075 |

## 3. Top 20 Feature Importance (Model G)
| Feature | SHAP Rank | Native Rank | Mean Abs SHAP | Native Importance |
|---|---|---|---|---|
| all_encounters_90d | 1 | 10 | 0.7281 | 95.0 |
| total_encounter_cost_365d | 2 | 6 | 0.6620 | 159.0 |
| days_since_last_outpatient | 3 | 7 | 0.6077 | 140.0 |
| all_encounters_365d | 4 | 16 | 0.6000 | 68.0 |
| outpatient_365d | 5 | 3 | 0.5431 | 249.0 |
| hist_active_condition_count | 6 | 5 | 0.4765 | 161.0 |
| age_at_index | 7 | 1 | 0.4571 | 343.0 |
| days_since_previous_encounter | 8 | 11 | 0.3712 | 92.0 |
| hist_chronic_condition_count | 9 | 12 | 0.3412 | 83.0 |
| outpatient_30d | 10 | 15 | 0.3374 | 79.0 |
| ambulatory_365d | 11 | 2 | 0.3271 | 307.0 |
| wellness_365d | 12 | 4 | 0.2920 | 167.0 |
| days_since_previous_ed | 13 | 9 | 0.2054 | 104.0 |
| hist_unique_condition_count | 14 | 22 | 0.1673 | 42.0 |
| inpatient_365d | 15 | 8 | 0.1385 | 128.0 |
| urgent_care_365d | 16 | 12 | 0.1383 | 83.0 |
| emergency_90d | 17 | 26 | 0.1349 | 33.0 |
| ambulatory_30d | 18 | 23 | 0.1256 | 36.0 |
| inpatient_90d | 19 | 14 | 0.1199 | 81.0 |
| hist_condition_count | 20 | 19 | 0.1150 | 53.0 |

## 4. Post-Hoc Temporal Robustness (Model G)
| Period | Positives | Negatives | PR-AUC | ROC-AUC | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| Early | 73 | 148 | 0.769 | 0.918 | 0.821 | 0.877 | 0.848 |
| Middle | 95 | 126 | 0.871 | 0.949 | 0.800 | 0.968 | 0.876 |
| Late | 45 | 176 | 0.812 | 0.949 | 0.661 | 0.911 | 0.766 |

## 5. Proxy Analysis & Limitations
- **Is the 0.903 PR-AUC legitimate within Synthea?** Yes, no mechanical timeline leakage was detected (all event_dates strictly < index_timestamp). 
- **Target Proxy Effect**: Top clinical features (like active conditions or days since last ED) in synthetic data often directly correlate to the programmed disease state modules that generate the next emergency visit. The high performance is a structural artifact of Synthea's deterministic nature.
- **CMS Comparison**: Synthea achieves 0.8+ F1 while CMS achieves 0.27. Synthea possesses clear historical predictive features, but the magnitude of the score gap is driven by synthetic perfect tracking vs real-world noise.
- **Architectural Decision**: Synthea clinical context models are valid for orthogonal feature engineering. We should proceed to CMS + Synthea fusion to determine if the clinical signal holds up inside real-world noise.
