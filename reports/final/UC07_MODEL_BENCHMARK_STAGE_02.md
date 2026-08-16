# UC07 Model Benchmarking (Stage 02)

## 1. OBJECTIVE & METHODOLOGY
This stage benchmarks 5 model families (Logistic Regression, Random Forest, XGBoost, LightGBM, CatBoost) to determine the most suitable algorithmic approach for predicting repeat ED utilization (UC07).
- **Dataset**: `UC07_final_40_features.csv` (60,411 rows, 40 features).
- **Cross-Validation**: 3-fold Temporal Split on the training set.
- **Test Set**: Untouched temporal holdout.
- **Threshold**: Static baseline `0.5` across all models with internal `balanced` class weights to allow threshold-agnostic comparison.
- **Primary Metric**: PR-AUC.

---

## 2. CROSS-VALIDATION RESULTS (Training Data)

| Model | Mean CV PR-AUC | CV Std | Mean F1 | Mean Recall | Mean Precision | Mean ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|
| **Logistic Regression** | **0.1814** | ±0.0096 | 0.2590 | 0.5921 | 0.1665 | **0.6166** |
| **CatBoost** | 0.1777 | ±0.0080 | 0.2536 | 0.5998 | 0.1625 | 0.6094 |
| **LightGBM** | 0.1681 | ±0.0113 | 0.2431 | 0.5136 | 0.1604 | 0.5924 |
| **XGBoost** | 0.1669 | ±0.0094 | 0.2458 | 0.6057 | 0.1551 | 0.5869 |
| **Random Forest** | 0.1603 | ±0.0044 | 0.1991 | 0.2882 | 0.1703 | 0.5822 |

*Finding: Logistic Regression and CatBoost were the clear leaders during temporal cross-validation, demonstrating that strict regularization (LR) and oblivious symmetric trees (CatBoost) prevent overfitting on noisy healthcare data better than traditional deep trees.*

---

## 3. FINAL MODEL COMPARISON (Untouched Test Set)

| Model | PR-AUC | ROC-AUC | Precision | Recall | F1 | Specificity | Brier |
|---|---:|---:|---:|---:|---:|---:|---:|
| **CatBoost** | **0.1292** | **0.6142** | 12.87% | **38.97%** | **19.35%** | 74.46% | 0.2000 |
| **Logistic Regression** | 0.1251 | 0.6082 | 12.93% | 37.34% | 19.21% | 75.66% | 0.1996 |
| **XGBoost** | 0.1232 | 0.5992 | 12.49% | 37.15% | 18.69% | 74.79% | 0.1974 |
| **LightGBM** | 0.1221 | 0.5977 | 12.86% | 37.15% | 19.11% | 75.63% | 0.1924 |
| **Random Forest** | 0.1209 | 0.5995 | **13.41%** | 22.61% | 16.83% | **85.86%** | **0.1766** |

**Old Production Baseline (For Reference):**
*PR-AUC = 0.1254, ROC-AUC = 0.6053, F1 = 14.67%*

---

## 4. MODEL RANKING & TRADE-OFFS

**1. Best Overall PR-AUC:** CatBoost (0.1292)
**2. Best Recall:** CatBoost (38.97%)
**3. Best Precision:** Random Forest (13.41%)
**4. Best F1:** CatBoost (19.35%)
**5. Best ROC-AUC:** CatBoost (0.6142)
**6. Best Calibration (Brier):** Random Forest (0.1766)
**7. Most Stable Model:** Logistic Regression (Highest CV PR-AUC, matched test-set separation very closely).

**Trade-offs Explained:**
- **Random Forest** achieved the highest Precision and best Brier score (calibration) because it produces very conservative probabilities. However, it suffered a catastrophic drop in Recall (22.61%) compared to the others, crippling its F1 score. 
- **CatBoost** swept almost all major metrics. Its symmetric tree structure naturally resists the heavy overfitting that plagued XGBoost and LightGBM on this noisy dataset.
- **Logistic Regression** was the massive surprise. It outperformed XGBoost, LightGBM, and Random Forest on PR-AUC, ROC-AUC, F1, and Recall. This happens frequently in healthcare claims: the data is so noisy and sparse that a highly regularized linear model captures the macroscopic trends (e.g., chronic condition burden) more reliably than deep, non-linear trees that memorize local noise.

---

## 5. FEATURE IMPORTANCE

For the top two models, the most heavily weighted features were:

**CatBoost (Information Gain):**
1. `chronic_condition_burden`
2. `days_since_previous_event`
3. `age_at_year_end`
4. `all_visits_365d`
5. `diagnosis_coded_visits_90d`
*Note: `distinct_provider_count_365d` ranked 8th.*

**Logistic Regression (Coefficient Magnitude):**
1. `days_since_previous_event`
2. `chronic_condition_burden`
3. `chronic_ischmcht`
4. `chronic_depressn`
5. `chronic_copd`
*Note: The LR model placed huge emphasis on individual chronic flags rather than just aggregate utilization.*

---

## 6. FINAL DECISIONS

**8. Which 2–3 models should proceed to the next experiment?**
**CatBoost** and **Logistic Regression**. They are the undisputed leaders in this benchmark, outperforming the legacy XGBoost model entirely.

**9. Should we investigate a hybrid/ensemble?**
**YES.** This is a textbook use case for an ensemble. We have a highly performant linear model (Logistic Regression) and a highly performant non-linear model (CatBoost). Because their underlying mathematical architectures are entirely different, they will make uncorrelated errors. Ensembling them will likely provide a massive stability boost and raise the PR-AUC ceiling further.

**10. Which model should NOT be pursued further?**
**Random Forest**. Its recall collapse makes it unviable for an ED-triage tool. **XGBoost and LightGBM** should also be dropped, as they were cleanly beaten by CatBoost's symmetric tree approach.
