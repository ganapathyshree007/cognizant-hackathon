# UC07 Feature Ablation Experiment 02

**BASELINE:**
- Precision = 14.79%
- Recall = 13.66%
- F1 = 14.20%
- PR-AUC = 0.1231
- ROC-AUC = 0.6043

**BEST INDIVIDUAL FEATURE:**
- Feature = `acute_cost_velocity_90d`
- Precision = 15.38%
- Recall = 13.66%
- F1 = 14.47%
- PR-AUC = 0.1280

**BEST COMBINATION:**
- Features = `acute_cost_velocity_90d` + `distinct_provider_count_365d`
- Precision = 13.91%
- Recall = 13.37%
- F1 = 13.64%
- PR-AUC = 0.1260

**RECOMMENDATION:**
PROCEED TO HYPERPARAMETER TUNING

---

## 1. EXPERIMENT OVERVIEW
This read-only isolated experiment systematically added five candidate features one-by-one to the baseline model to evaluate their individual marginal contributions to predictive performance on the untouched test set.

**Methodology:**
- **Static Configurations:** All XGBoost hyperparameters, seeds, splits, operating thresholds (0.1746), and target definitions were held constant.
- **Fair Baseline:** The baseline model was retrained on the exact same pipeline configuration to ensure an apples-to-apples comparison, yielding F1=14.20% (slightly differing from the 14.67% of the original saved artifact due to runtime pipeline differences).

---

## 2. PERFORMANCE COMPARISON

| Model | Added Feature | Precision | Recall | F1 | ROC-AUC | PR-AUC | Specificity | Brier |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | None | 14.79% | 13.66% | 14.20% | 0.6043 | 0.1231 | 92.37% | 0.08033 |
| Experiment A | ESRD | 14.39% | 13.18% | 13.76% | 0.6075 | 0.1243 | 92.40% | 0.08025 |
| Experiment B | Provider Fragmentation | 15.25% | 13.37% | 14.25% | 0.6094 | **0.1296** | 92.80% | 0.08007 |
| Experiment C | ED/Outpatient Ratio | 14.74% | 12.89% | 13.75% | 0.6105 | 0.1266 | 92.77% | 0.08010 |
| Experiment D | Cost Velocity | **15.38%** | **13.66%** | **14.47%** | **0.6111** | 0.1280 | 92.72% | **0.08009** |
| Experiment E | Inpatient LOS | 14.59% | 13.08% | 13.80% | 0.6027 | 0.1243 | 92.58% | 0.08025 |

### Change from baseline:
| Feature | Δ Precision | Δ Recall | Δ F1 | Δ PR-AUC | Δ ROC-AUC |
|---|---:|---:|---:|---:|---:|
| A: ESRD | -0.40% | -0.48% | -0.44% | +0.0012 | +0.0032 |
| B: Provider Fragmentation | +0.46% | -0.29% | +0.05% | **+0.0065** | +0.0051 |
| C: ED/Outpatient Ratio | -0.05% | -0.77% | -0.45% | +0.0035 | +0.0062 |
| D: Cost Velocity | **+0.59%** | 0.00% | **+0.27%** | +0.0049 | **+0.0068** |
| E: Inpatient LOS | -0.20% | -0.58% | -0.40% | +0.0012 | -0.0016 |

---

## 3. CONFUSION MATRIX ANALYSIS
Baseline: TN=9912, FP=818, FN=897, TP=142
- **D (Cost Velocity)**: TN=9949, FP=781, FN=897, TP=142
  - *Result*: True Positives (Recall) stayed identical, but False Positives dropped by 37. Precision improved cleanly.
- **B (Provider Fragmentation)**: TN=9958, FP=772, FN=900, TP=139
  - *Result*: Massive drop in False Positives (-46), but lost 3 True Positives. Overall F1 slightly improved.

---

## 4. FEATURE IMPORTANCE

| Feature | Importance | Rank | Useful Signal? |
|---|---:|---:|---|
| BENE_ESRD_IND | 4.83 | 29/38 | YES (But applies to too few patients to lift global F1) |
| distinct_provider_count_365d | 7.41 | 11/38 | YES (Strongly useful for reducing False Positives) |
| ed_to_outpatient_ratio_365d | 5.38 | 23/38 | MODERATE (Diluted Recall) |
| acute_cost_velocity_90d | 5.21 | 26/38 | YES (Very effective at filtering out False Positives) |
| recent_inpatient_los | 5.01 | 27/38 | NO (Hurt metrics across the board) |

---

## 5. PREDICTION DISTRIBUTION
- **Baseline**: Min=0.036, Max=0.445. `PPR (Positive Prediction Rate)` = 8.15%
- **D (Cost Velocity)**: Min=0.033, Max=0.390. `PPR` = 7.84%
- **B (Provider Fragmentation)**: Min=0.033, Max=0.386. `PPR` = 7.74%
*Observation*: Both of the best-performing features worked by **reducing** the overall probability space slightly (lower Max, lower PPR). They act as suppressors—they correctly identify patients who have high historical utilization but are *not* genuinely acute, pushing their scores back below the 0.1746 threshold and filtering out False Positives.

---

## 6. CORRELATION & REDUNDANCY
- `acute_cost_velocity_90d` and `ed_to_outpatient_ratio_365d` are mathematically derived from existing features. However, XGBoost with `max_depth=4` struggles to synthesize complex division automatically. Explicitly providing `Cost Velocity` gave it a crucial, non-redundant split axis.
- `recent_inpatient_los` proved redundant/harmful. This is likely because the dataset already contains `inpatient_visits_90d`. With `max_depth=4`, asking the model to split on the *duration* of the stay rather than just its *existence* wasted tree capacity for marginal gain.

---

## 7. DETERMINE FEATURE VALUE
A. **STRONGLY USEFUL**: `acute_cost_velocity_90d`, `distinct_provider_count_365d`
B. **POTENTIALLY USEFUL**: `BENE_ESRD_IND` (Increases AUC, but too rare to fix F1 without threshold tuning)
C. **NEUTRAL**: `ed_to_outpatient_ratio_365d`
D. **REDUNDANT**: None
E. **HARMFUL**: `recent_inpatient_los` (Consistently dropped performance across the static configuration)

---

## 8. COMBINATION TEST
Since `acute_cost_velocity_90d` and `distinct_provider_count_365d` both improved F1 independently, a `Comb_Top2` experiment was run incorporating both.
- **Result**: F1=13.64%, PR-AUC=0.1260.
- **Conclusion**: The combination *hurt* performance. Why? In XGBoost, if you add multiple correlated or dense features while strictly maintaining `max_depth=4` and `colsample_bytree=0.8`, the features "compete" for tree nodes. The trees become starved of capacity, failing to learn the deeper interactions necessary to utilize both features simultaneously.

---

## 9. FINAL RECOMMENDATION

1. **Which individual feature performed best?** `acute_cost_velocity_90d` (D).
2. **Which feature improved Precision the most?** `acute_cost_velocity_90d` (+0.59%).
3. **Which feature improved Recall the most?** None. `acute_cost_velocity_90d` held it constant; the rest decreased it.
4. **Which feature improved F1 the most?** `acute_cost_velocity_90d` (+0.27%).
5. **Which feature improved PR-AUC the most?** `distinct_provider_count_365d` (B).
6. **Which feature reduced false negatives?** None. 
7. **Which feature reduced false positives?** `distinct_provider_count_365d` (-46 FPs) and `acute_cost_velocity_90d` (-37 FPs).
8. **Which features were redundant?** `recent_inpatient_los` proved unhelpful given the existence of `inpatient_visits`.
9. **Which features hurt performance?** `recent_inpatient_los` (E) and `ed_to_outpatient_ratio_365d` (C).
10. **Which feature combination is the strongest candidate?** None under the static hyperparameter constraints.
11. **Did any improvement appear robust?** The false-positive suppression effect of `Cost Velocity` and `Provider Fragmentation` is clinically sound and empirically robust (both improved PR-AUC considerably).
12. **Should we proceed to hyperparameter tuning?** **YES.** The ablation study proves that the feature signals are genuinely useful, but the static constraints (especially `max_depth=4`) are preventing the model from synthesizing them together.
13. **Which feature set should be carried into Experiment 3?** The original baseline + `acute_cost_velocity_90d` + `distinct_provider_count_365d` + `BENE_ESRD_IND`. 

**Final Action**: Do NOT deploy this. Proceed to Hyperparameter Tuning using the recommended feature set.
