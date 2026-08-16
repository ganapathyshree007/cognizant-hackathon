# UC07 Feature Experiment 01 Results

## 1. EXPERIMENT OVERVIEW
An isolated ML experiment was conducted to evaluate the predictive value of 5 proposed point-in-time features on the CMS/DE-SynPUF dataset. 

**Experimental Features Added:**
1. `BENE_ESRD_IND` (ESRD indicator)
2. `distinct_provider_count_365d` (Care fragmentation)
3. `ed_to_outpatient_ratio_365d` (ED dependence)
4. `acute_cost_velocity_90d` (Sudden acuity spike)
5. `recent_inpatient_los` (Hospitalization severity)

**Methodology Constraints:**
- The experimental dataset (`experimental_model_features.csv`) exactly mirrors the baseline row count and splits.
- `recent_inpatient_los` was derived securely by ensuring `discharge_date < index_date`, completely eliminating temporal leakage.
- The XGBoost hyperparameters, test set, positive/negative label distribution, and operating threshold (`0.1746`) were kept identical to the production baseline.

---

## 2. DATASET STATISTICS
- **Number of training samples**: 48,629
- **Number of test samples**: 11,769
- **Positive labels (Test)**: 1,039 (8.8%)
- **Negative labels (Test)**: 10,730 (91.2%)
- **Number of Base Features**: 37
- **Number of Experimental Features**: 42

---

## 3. PERFORMANCE COMPARISON

| Metric | Baseline | Experimental | Change |
|---|---:|---:|---:|
| **Precision** | 15.23% | 15.02% | ▼ -0.21% |
| **Recall** | 14.14% | 13.76% | ▼ -0.38% |
| **F1 Score** | 14.67% | 14.36% | ▼ -0.31% |
| **ROC-AUC** | 0.6053 | 0.6039 | ▼ -0.0014 |
| **PR-AUC** | 0.1254 | 0.1238 | ▼ -0.0016 |
| **Specificity** | 92.37% | 92.46% | ▲ +0.09% |
| **Brier Score** | 0.0802 | 0.0803 | ▼ -0.0001 (worse) |

*Note: Evaluated at the static production threshold of 0.1746.*

---

## 4. EXPERIMENT CONCLUSIONS & ANSWERS

**1. Did the new features improve Precision?**
No, precision decreased slightly from 15.23% to 15.02%.

**2. Did they improve Recall?**
No, recall decreased from 14.14% to 13.76%.

**3. Did they improve F1?**
No, F1 decreased from 14.67% to 14.36%.

**4. Did PR-AUC improve?**
No, the Area Under the Precision-Recall Curve dropped marginally from 0.1254 to 0.1238.

**5. Did ROC-AUC improve?**
No, ROC-AUC dropped marginally from 0.6053 to 0.6039.

**6. Did calibration improve?**
No, the Brier score (measuring probability calibration) worsened slightly (0.0802 to 0.0803).

**7. Which new features actually contributed useful signal?**
While the new features were successfully ingested, they failed to improve the global metrics. Feature Importance (Gain) analysis showed that `recent_inpatient_los` and `ed_to_outpatient_ratio` appeared in the top 15 features, meaning the model *did* split on them when available, but the splits did not generalize to better test-set predictions.

**8. Which features appear redundant or useless?**
`acute_cost_velocity_90d` and `ed_to_outpatient_ratio_365d`. Because tree-based models like XGBoost are already highly capable of discovering interactions between raw columns (e.g., `ed_visits` and `outpatient_visits`), manually computing arithmetic ratios over those same columns often provides highly correlated, redundant splits that dilute the learning capacity of the trees (especially when constrained to `max_depth=4`).

**9. Is the experimental model genuinely better than the baseline?**
**No.** The experimental model is marginally worse across almost every metric. The addition of these specific features without concurrent hyperparameter tuning (such as adjusting `colsample_bytree` or `max_depth` to handle the wider, correlated feature space) caused slight overfitting and signal dilution.

**10. Should we proceed with these features?**
**No, do not deploy this experimental model to production.** 
The baseline model remains superior. To effectively utilize these new features, a full hyperparameter search (grid search/random search) and feature-selection ablation study would be required. In their current state with the static pipeline parameters, they dilute rather than enhance the predictive signal.
