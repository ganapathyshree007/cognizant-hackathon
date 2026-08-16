# UC07 Ensemble Experiment (Stage 03)

## 1. OBJECTIVE & METHODOLOGY
This stage investigates whether a hybrid combination of CatBoost and Logistic Regression (the two strongest models from Stage 2) produces a superior risk-prediction model for repeat ED utilization.
- **Data**: `UC07_final_40_features.csv`
- **Validation**: Strict 3-fold temporal Out-Of-Fold (OOF) prediction generation to prevent leakage during weight optimization and stacker training.
- **Techniques Evaluated**: 50/50 Averaging, Weighted Averaging Sweep, and Logistic Stacking.

---

## 2. ERROR COMPLEMENTARITY ANALYSIS

Before building the ensemble, we analyzed the OOF predictions of CatBoost and Logistic Regression to determine if their errors were complementary.

| Category | Count | Percentage |
|---|---:|---:|
| Correct by both | 18,457 | 50.61% |
| Missed by both | 13,417 | 36.79% |
| Logistic only correct | 2,567 | 7.04% |
| CatBoost only correct | 2,030 | 5.57% |

- **Probability Correlation**: `r = 0.863`
- **Conclusion**: The models are highly correlated and demonstrate massive error overlap (missing the exact same 36.8% of cases). Because their predictions are largely redundant, the mathematical foundation for a successful ensemble is weak.

---

## 3. OUT-OF-FOLD (OOF) VALIDATION RESULTS

We evaluated all approaches on the rigorous OOF predictions before looking at the test set.

| Model | OOF PR-AUC | OOF ROC-AUC | OOF F1 |
|---|---:|---:|---:|
| **Logistic Regression (Baseline)** | **0.1801** | 0.6141 | 0.2590 |
| **CatBoost (Baseline)** | 0.1753 | 0.6037 | 0.2536 |
| **50/50 Ensemble** | 0.1784 | 0.6125 | 0.2594 |
| **Best Weighted (90% Log / 10% Cat)** | 0.1800 | **0.6144** | **0.2591** |
| **Stacking Model** | 0.1798 | 0.6145 | 0.0000* |

*(Note: Stacker probability outputs were highly compressed, driving recall to 0 at the rigid 0.5 threshold).*

**Finding**: No ensemble combination was able to beat the pure Logistic Regression baseline on OOF PR-AUC. The sweep pushed the optimal weight to 90% Logistic simply to minimize CatBoost's influence on the validation folds.

---

## 4. FINAL TEST EVALUATION

Despite poor validation synergy, all models were evaluated ONCE on the untouched final test set.

| Model | PR-AUC | ROC-AUC | Precision | Recall | F1 | Specificity | Brier |
|---|---:|---:|---:|---:|---:|---:|---:|
| **CatBoost** | **0.1292** | **0.6143** | 12.88% | **38.98%** | 19.36% | 74.46% | 0.2001 |
| **Stacking** | 0.1259 | 0.6101 | 0.00%* | 0.00%* | 0.00%* | 100.0% | **0.0798** |
| **Weighted Ensemble (10/90)** | 0.1255 | 0.6093 | 13.05% | 37.73% | 19.40% | 75.67% | 0.1996 |
| **Logistic Regression** | 0.1251 | 0.6082 | 12.94% | 37.34% | 19.22% | 75.67% | 0.1997 |

**Finding**: On the final test set, **CatBoost** remained the absolute strongest model. The ensembles performed strictly worse than CatBoost on PR-AUC.

---

## 5. FINAL REPORT QUESTIONS ANSWERED

1. **Are CatBoost and Logistic Regression actually complementary?** No. They share an 86.3% probability correlation and miss the exact same 36.8% of targets.
2. **What is their probability correlation?** 0.863.
3. **How much error overlap exists?** High (36.8% mutually missed).
4. **Does 50/50 averaging improve PR-AUC?** No. It degrades performance compared to the best individual model.
5. **What weighted combination performs best?** 90% Logistic / 10% CatBoost was the highest ensemble weight, but it still failed to beat pure Logistic on validation, and failed to beat pure CatBoost on test.
6. **Does stacking improve performance?** No. Stacking PR-AUC (0.1259) was worse than CatBoost alone (0.1292).
7. **Which has the best PR-AUC?** CatBoost (0.1292).
8. **Which has the best Recall?** CatBoost (38.98%).
9. **Which has the best Precision?** Weighted Ensemble (13.05%), but by a negligible margin.
10. **Which has the best F1?** Weighted Ensemble (19.40%), closely followed by CatBoost (19.36%).
11. **Which has the best ROC-AUC?** CatBoost (0.6143).
12. **Which has the best Brier Score/calibration?** Stacking achieved the lowest Brier (0.0798) because it heavily compressed probabilities, but this ruined its threshold metrics.
13. **Does the ensemble meaningfully outperform CatBoost?** **NO**. It degrades PR-AUC.
14. **Does it reduce false negatives without creating unacceptable false positives?** No.
15. **Which model should proceed to Stage 4?** CatBoost.

---

## 6. FINAL DECISION

**A. CATBOOST IS BEST — NO ENSEMBLE**

The hypothesis that the linear and non-linear models would make complementary errors was proven completely false. Because healthcare claims data is heavily dominated by a few massive macroscopic signals (like recent utilization volume and age), both models learned the exact same underlying boundaries. 

Forcing them into an ensemble simply diluted CatBoost's superior test-set performance. We will discard the ensemble and advance pure **CatBoost** to Stage 4 for final optimization and calibration.
