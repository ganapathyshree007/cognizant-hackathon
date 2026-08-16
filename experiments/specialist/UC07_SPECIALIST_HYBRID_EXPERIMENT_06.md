# UC07 Specialist Hybrid / Stacked Risk Model (Experiment 06)

## 1. OBJECTIVE
This experiment tested a sophisticated heterogeneous hybrid architecture: splitting the 40 CMS features into logical specialist groups (Demographic, Utilization, Clinical), training individual base models for each group, and attempting to fuse them via Stacking meta-models and ensembles. The goal was to determine if this architecture could mathematically outperform the unified Optimized CatBoost model from Stage 4.

Additionally, we investigated whether the model could achieve a stringent **90% Accuracy** mandate while maintaining useful clinical performance.

---

## 2. SPECIALIST FEATURE ALLOCATION & BASE PERFORMANCE
The 40 features were split according to `UC07_SPECIALIST_FEATURE_GROUPS.md`:

| Specialist Model | Architecture | Features | OOF PR-AUC |
|---|---|---|---:|
| **Demographic + Chronic** | CatBoost | 18 | 0.1675 |
| **Utilization** | LightGBM | 15 | 0.1588 |
| **Clinical / Severity** | CatBoost | 7 | **0.1719** |

*Finding*: The 7 Clinical/Severity features (mostly cost and diagnosis-coded visit counts) surprisingly captured more predictive signal alone than the 15 Utilization features or 18 Demographic features. 

**Are they complementary?**
The predictions were moderately to highly correlated:
- Utilization vs Clinical: `r = 0.576`
- Demographic vs Clinical: `r = 0.371`
Because the models overlap significantly in their false negatives, there was limited orthogonal signal for the meta-model to exploit.

---

## 3. META-MODEL VALIDATION (OOF)
We evaluated both Logistic Regression and XGBoost as meta-models using the three specialist probability vectors as inputs.

| Hybrid Architecture | OOF PR-AUC |
|---|---:|
| Best Probability Ensemble (50/0/50) | 0.1822 |
| Logistic Meta-Model | 0.1821 |
| **XGBoost Meta-Model** | **0.2021** |

The XGBoost Stack appeared to find a strong non-linear combination of the specialist probabilities during cross-validation, significantly boosting the validation metric to 0.2021.

---

## 4. THE 90% ACCURACY INVESTIGATION

**Can the hybrid achieve >= 90% Accuracy while maintaining Recall >= 40%, Precision >= 15%, F1 >= 20%?**
**No. (Target Achieved: False)**

On highly imbalanced clinical data (where only ~12% of cases are positive), forcing the accuracy over 90% mathematically requires the model to almost *never* predict a positive case. 

If we push the decision threshold up to achieve ~87% accuracy, the metrics collapse:
- **Accuracy**: 87.4%
- **Recall**: 0.69% (It catches less than 1% of the high-risk patients)
- **Precision**: 45.7%
- **F1**: 1.3%

**Selected Operational Threshold:**
Because 90% accuracy destroys the model, the script fell back to finding the highest accuracy that still maintained a bare minimum of 40% Recall.
- **Operating Threshold**: `0.15`
- **Resulting Accuracy**: 67.8%

---

## 5. FINAL TEST SET COMPARISON

The XGBoost Stacked Hybrid and the current Optimized CatBoost were evaluated ONCE on the final untouched test set.

| Model | Accuracy | PR-AUC | ROC-AUC | Precision | Recall | F1 | Specificity | Brier |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Stacked Hybrid** | **81.37%** | 0.1266 | 0.6074 | **13.44%** | 20.40% | 16.20% | **87.27%** | **0.0797** |
| **Current CatBoost** | 62.27% | **0.1300** | **0.6223** | 12.18% | **52.74%** | **19.79%** | 63.19% | 0.0805 |

*Note: Accuracies differ wildly due to the threshold requirement. The Hybrid used a threshold optimizing for accuracy (0.15, giving 81% test accuracy), while CatBoost used a threshold optimizing for F1/Recall (0.13, giving 62% test accuracy).*

### Operational Burden
| Model | TP (Caught) | FN (Missed) | FP (Alert Fatigue) | Alert Rate |
|---|---:|---:|---:|---:|
| **Stacked Hybrid** | 212 | 827 | 1,365 | 13.39% |
| **Current CatBoost**| **548** | 491 | 3,949 | 38.21% |

---

## 6. FINAL DECISION

**B. CURRENT OPTIMIZED CATBOOST IS BETTER**

The XGBoost Stacked Hybrid aggressively **overfit** the validation folds (OOF PR-AUC of 0.2021 collapsed to 0.1266 on the test set). The unified Optimized Calibrated CatBoost, which learns the global feature interactions directly from all 40 features simultaneously, is mathematically superior in ranking separation (PR-AUC 0.1300 vs 0.1266) and ROC-AUC (0.6223 vs 0.6074).

Furthermore, the 90% accuracy mandate is clinically non-viable for this use case. Optimizing for high accuracy forces the model to ignore 80% to 99% of the true readmission cases. The single CatBoost architecture remains the best configuration for identifying high-risk ED repeaters. 

We will discard the hybrid and keep the **Stage 4 Optimized Calibrated CatBoost** as our final production model.
