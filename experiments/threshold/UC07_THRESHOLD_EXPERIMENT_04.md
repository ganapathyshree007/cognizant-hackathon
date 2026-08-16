# UC07 Threshold Optimization & Final Evaluation

**PRODUCTION BASELINE**
- Precision = 15.23%
- Recall = 14.14%
- F1 = 14.67%
- PR-AUC = 0.1254
- ROC-AUC = 0.6053
- Threshold = 0.1746

**EXPERIMENTAL MODEL**
- Threshold = 0.125 (Max F1 on Validation)
- Precision = 12.29%
- Recall = 50.43%
- F1 = 19.77%
- PR-AUC = 0.1288
- ROC-AUC = 0.6155

**IMPROVEMENT**
- Precision Δ = -2.94%
- Recall Δ = +36.29%
- F1 Δ = +5.10%
- PR-AUC Δ = +0.0034
- ROC-AUC Δ = +0.0102

**FINAL RECOMMENDATION:**
KEEP PRODUCTION BASELINE. 
While the experimental model is mathematically superior in terms of global separation (ROC-AUC) and theoretical F1 score at the 0.125 threshold, the operational reality of the 0.125 threshold is unacceptable for Care Managers due to alert fatigue.

---

## 1. DATA SPLIT & VALIDATION METHODOLOGY
To prevent test-set leakage, threshold selection was performed strictly on the training dataset using Out-of-Fold (OOF) predictions from a 3-fold Stratified K-Fold cross-validation. The final test set remained untouched until the selected threshold (0.125) was frozen.

---

## 2. THRESHOLD SWEEP RESULTS (Validation Candidates)
A sweep from 0.01 to 0.40 was performed. The following candidate thresholds were identified:
- **Maximum Recall**: 0.01 (Captures almost everyone, but precision approaches 0)
- **Maximum Precision**: 0.28 (Highly precise, but captures virtually no one)
- **Maximum F1**: 0.125 (Mathematically balances the harmonic mean of Precision and Recall)

The threshold of **0.125** was frozen for final test set evaluation.

---

## 3. FINAL MODEL COMPARISON (On Untouched Test Set)

| | Production Model | Tuned Experimental Model |
|---|---:|---:|
| **Features** | Baseline (37) | Baseline + ESRD + Cost Vel + Prov Count (40) |
| **Hyperparameters** | Legacy | max_depth=3, gamma=1, colsample=1.0 |
| **Threshold** | 0.1746 | 0.1250 |
| **Precision** | 15.23% | 12.29% |
| **Recall** | 14.14% | 50.43% |
| **F1** | 14.67% | 19.77% |
| **PR-AUC** | 0.1254 | 0.1288 |
| **ROC-AUC** | 0.6053 | 0.6155 |
| **Specificity** | 92.37% | 65.16% |
| **Brier Score** | 0.0802 | 0.0800 |
| **Positive Rate** | 8.20% | 36.21% |

---

## 4. ERROR ANALYSIS

When shifting from the Production Model (0.1746) to the Experimental Model (0.125):
- **Recovered False Negatives**: 378 (Patients missed by production but caught by the new model)
- **New False Positives**: 2,924 (Healthy/non-returning patients incorrectly flagged as high risk)
- **Lost True Positives**: 1
- **Fixed False Positives**: 4

---

## 5. STATISTICAL ROBUSTNESS CHECK
Bootstrapping (100 iterations) on the final test set yields the following 95% Confidence Intervals for the Experimental Model at threshold 0.125:
- **Precision CI**: [11.45%, 13.16%]
- **Recall CI**: [47.80%, 53.14%]
- **F1 CI**: [18.49%, 21.03%]
- **PR-AUC CI**: [0.1193, 0.1421]

The improvement in Recall and F1 is statistically robust and not due to a lucky test split.

---

## 6. CALIBRATION
- **Brier Score**: Improved slightly from 0.0802 to 0.0800.
- **Probability Quality**: The tuned probabilities are much tighter and heavily regularized. This means the model is technically *better* calibrated mathematically, but the probabilities are compressed, which forces the operating threshold down to 0.125 to achieve recall.

---

## 7. UC07-SPECIFIC THRESHOLD CONSIDERATION

In the context of the Avoidable ED Utilization Navigator, the model acts as a decision-support tool to alert Care Managers. 
- The 0.125 threshold yields a **Positive Prediction Rate of 36.21%**. This means the model flags over one-third of the entire population as "high risk for repeat ED visits."
- While it catches 378 additional true repeat-ED patients, it burdens the Care Managers with nearly **3,000 additional false alarms**.
- **Conclusion**: In a constrained resource environment (Care Manager bandwidth), **Precision** is more critical than Recall. Alert fatigue from a 36% flag rate will cause users to ignore the model entirely. The mathematical maximum F1 (0.125) is clinically unviable.

---

## 8. FINAL DECISION

**1. What threshold was selected from validation data?** 0.125 (Maximum F1).
**2. Why was this threshold selected?** To evaluate if the mathematical ceiling of the tuned model's F1 tradeoff could beat production.
**3. What is the experimental model's final test Precision?** 12.29%.
**4. Recall?** 50.43%.
**5. F1?** 19.77%.
**6. PR-AUC?** 0.1288.
**7. ROC-AUC?** 0.6155.
**8. Specificity?** 65.16%.
**9. Did it outperform the production model?** Mathematically, yes (higher F1, PR-AUC, ROC-AUC). Operationally, no (devastating drop in Precision and Specificity).
**10. Is the improvement meaningful or only marginal?** The separation (AUC) improvement is marginal. The threshold shift is massive.
**11. Does the model remain well calibrated?** Yes, Brier score improved slightly (0.0800 vs 0.0802).
**12. Is the experimental model ready for further validation?** No. 
**13. Should we replace the production model?** NO.
**14. What should Experiment 05 investigate?** We have reached the predictive limits of claims data alone. Experiment 05 should investigate integrating **real-time clinical notes / NLP features** or **Social Determinants of Health (SDoH)**. Tweaking tree hyperparameters on claims data has hit a hard ceiling.
