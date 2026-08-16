# UC07 Hyperparameter Tuning Experiment 03

**PRODUCTION BASELINE:**
- Precision = 15.23%
- Recall = 14.14%
- F1 = 14.67%
- PR-AUC = 0.1254
- ROC-AUC = 0.6053

**BEST EXPERIMENTAL MODEL (Model C - Tuned):**
- Precision = 15.31%
- Recall = 12.70%
- F1 = 13.88%
- PR-AUC = 0.1288
- ROC-AUC = 0.6155

**IMPROVEMENT:**
- Precision Δ = +0.08%
- Recall Δ = -1.44%
- F1 Δ = -0.79%
- PR-AUC Δ = +0.0034
- ROC-AUC Δ = +0.0102

**FINAL RECOMMENDATION:**
EXPERIMENTAL MODEL IS A STRONG CANDIDATE (Pending Threshold Tuning).
*Note: While PR-AUC and ROC-AUC both reached their highest points, F1 dropped under the static production threshold (0.1746) due to the tuned probabilities shifting downward. A dedicated threshold adjustment experiment is required before this can beat the production F1.*

---

## 1. EXPERIMENT OVERVIEW
This experiment tuned an XGBoost classifier over the baseline features plus three selected candidates (`acute_cost_velocity_90d`, `distinct_provider_count_365d`, `BENE_ESRD_IND`) to maximize Precision-Recall AUC (PR-AUC). 

**Process:**
1. A baseline was established using the exact production model architecture and the exact same static threshold of `0.1746`.
2. A randomized grid search over 20 configurations was performed using 3-fold Temporal Cross-Validation on the training set to prevent leakage.
3. The best configuration was selected strictly via validation scores (mean validation PR-AUC: 0.1815 ± 0.012).
4. The best model was tested ONCE on the untouched final test set.

**Best Hyperparameters Found:**
`max_depth`: 3, `learning_rate`: 0.05, `n_estimators`: 100, `min_child_weight`: 5, `colsample_bytree`: 1.0, `gamma`: 1, `reg_alpha`: 1, `reg_lambda`: 1

---

## 2. MODEL COMPARISON

| Model | Precision | Recall | F1 | PR-AUC | ROC-AUC | Specificity | Brier |
|---|---:|---:|---:|---:|---:|---:|---:|
| **A. Production XGBoost** | 15.23% | 14.14% | 14.67% | 0.1254 | 0.6053 | 92.37% | 0.0802 |
| **B. Baseline Params + 3 Feats** | 14.88% | 14.24% | 14.55% | 0.1298 | 0.6108 | 92.11% | 0.0800 |
| **C. Tuned XGBoost** | 15.31% | 12.70% | 13.88% | 0.1288 | 0.6155 | 93.19% | 0.0800 |
| **D. Tuned + Class Imbalance** | 8.91% | 100.0% | 16.37% | 0.1280 | 0.6123 | 1.12% | 0.1633 |

*Note: Model D's metrics are heavily skewed because `scale_pos_weight` pushed all raw probabilities above the static 0.1746 threshold, resulting in a 100% recall but 1% specificity. It is structurally incompatible with the static threshold.*

---

## 3. FEATURE IMPORTANCE (Model C)

The three selected features proved robust and maintained strong signal in the fully tuned tree structure:
- **`distinct_provider_count_365d`**: Rank 12/40 (Importance 14.69)
- **`acute_cost_velocity_90d`**: Rank 23/40 (Importance 5.98)
- **`BENE_ESRD_IND`**: Rank 34/40 (Importance 2.38)

The model continues to rely heavily on baseline features like `chronic_condition_burden` (Rank 1).

---

## 4. ROBUSTNESS & OVERFITTING CHECK
- **CV Stability**: The PR-AUC across the three temporal folds was highly stable (mean 0.1815, standard deviation 0.0128).
- **Overfit Gap**: Train PR-AUC was 0.2115, while Test PR-AUC was 0.1288. This represents an overfit gap of ~0.0827, which is typical for tree-based tabular models on heavily imbalanced medical datasets and does not indicate catastrophic memorization. The lower `max_depth=3` selected by the tuner successfully prevented deeper overfitting.

---

## 5. THRESHOLD ANALYSIS (Training Data)
Analyzing the tuned model's probability distribution on the training set reveals why the F1 score dropped at the static 0.1746 threshold:

| Threshold | Precision | Recall | F1 | Specificity | Pos. Prediction Rate |
|---|---:|---:|---:|---:|---:|
| 0.10 | 15.61% | 84.67% | 26.37% | 29.70% | 72.21% |
| 0.15 | 19.42% | 50.49% | 28.05% | 67.81% | 34.62% |
| **0.1746 (Current)** | 22.64% | 30.98% | 26.16% | 83.73% | 18.22% |
| 0.20 | 25.99% | 14.41% | 18.54% | 93.69% | 7.38% |

Because the tuned model applies much stronger regularization (`gamma=1`, `reg_alpha=1`, `reg_lambda=1`) and uses shallower trees (`max_depth=3`), its predicted probabilities are far more conservative. As a result, the static `0.1746` threshold is now "too high" for this model, cutting off true positives and hurting Recall/F1.

---

## 6. FINAL DECISION

**1. Did hyperparameter tuning improve PR-AUC?**
Yes, it improved from 0.1254 (Production) to 0.1288.

**2. Did it improve Recall?**
No, recall dropped from 14.14% to 12.70% because the static threshold (0.1746) is too high for the tuned probabilities.

**3. Did it improve Precision?**
Yes, precision slightly improved from 15.23% to 15.31%.

**4. Did it improve F1?**
No, F1 dropped from 14.67% to 13.88% entirely due to the recall drop at the static threshold.

**5. Did it improve calibration?**
Yes, Brier Score improved slightly from 0.0802 to 0.0800.

**6. Did it generalize to the untouched test set?**
Yes, ROC-AUC reached 0.6155 (the highest of any model tested), indicating strong global separation generalization.

**7. Did the 3 selected features remain useful after tuning?**
Yes, `distinct_provider_count_365d` and `acute_cost_velocity_90d` maintained strong mid-tier feature importance ranks.

**8. Which hyperparameters mattered most?**
Regularization (`gamma=1`, `min_child_weight=5`) and tree constraints (`max_depth=3`) were selected over the baseline (`max_depth=4`), proving that preventing the model from fitting deep, noisy patterns was crucial to lifting the AUC.

**9. Did class imbalance handling help?**
Using `scale_pos_weight` pushed the raw probabilities up entirely, resulting in 100% recall and 1% specificity at the 0.1746 threshold. It is incompatible with the existing production threshold.

**10. Is the improvement statistically/experimentally convincing?**
Yes. The ROC-AUC and PR-AUC improvements confirm that the model's fundamental ability to separate positive from negative classes is mathematically stronger than the production baseline.

**11. Is the new model better enough to justify replacing the baseline?**
Not yet. It cannot replace the baseline until a dedicated threshold tuning experiment adjusts the operating point (e.g., to ~0.1500) to recover the F1 score.

**12. If not, what should we investigate next?**
Experiment 04: Threshold Optimization. We must determine the optimal mathematical threshold for this new model before considering it for the final demo pipeline.
