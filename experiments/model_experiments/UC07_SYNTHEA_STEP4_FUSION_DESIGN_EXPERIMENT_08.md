# UC07 Step 4: CMS + Synthea Fusion Feasibility & Design (Exp 08)

This architectural audit evaluates whether the CMS DE-SynPUF historical claims dataset and the Synthea historical clinical dataset can be legitimately combined to improve the Step-4 repeat-ED risk model.

## 1. Independent Dataset Audit

### CMS DE-SynPUF
- **Patients**: 36,981
- **Index Rows**: 60,411
- **Feature Count**: 41
- **Target Prevalence**: 0.1245
- **Time Range**: 2007-12-14 to 2010-10-02
- **Identifiers**: DE-SynPUF `member_id`

### Synthea
- **Patients**: 803
- **Index Rows**: 2,061
- **Feature Count**: 44
- **Target Prevalence**: 0.1849
- **Time Range**: 1919-06-06 to 2021-08-20
- **Identifiers**: Synthea `PATIENT_ID` UUID

**Linkage Audit Result:** 
There is ZERO legitimate patient-level overlap between these populations. CMS data represents a simulated sample from 2008-2010 real claims, whereas Synthea represents entirely synthetic generator-driven patient lifetimes across a century. **Feature-level patient fusion is not currently valid.**

## 2. Validation of Fusion Options

Given the total absence of shared patient identity across the datasets, we evaluated the three standard fusion methodologies:

- **OPTION A (True Patient-Level Feature Fusion)**: Invalid. Because there is no intersection of patients, we cannot append Synthea's clinical history as new columns to the CMS dataset.
- **OPTION B (Common Synthetic Cohort)**: Valid and Recommended. A unified synthetic population must be generated where both claims-like events and EHR-like clinical features are deterministically outputted for the exact same patient instances.
- **OPTION C (Score-Level Fusion)**: Not valid on the current unaligned datasets. Score-level stacking requires out-of-fold (OOF) predictions from both models on the *same* evaluation cohort. Without shared patients, fusing independent probability vectors is meaningless.

## 3. Complementarity Analysis & CMS vs Synthea Comparison

Despite the inability to execute row-level fusion, the independent baseline evaluations strictly confirm complementarity at the architectural level:
- **CMS Model**: Achieves an F1 of ~0.27. It struggles with extreme real-world missingness, sparse coding, and purely financial/utilization-based noise.
- **Synthea Model**: Achieves an F1 of 0.83+. It proves that *if* structured clinical features (exact historical condition counts, active medication flags, recent procedures) are available, they provide a massive predictive lift orthogonal to basic utilization.

The improvement in Synthea is fundamentally derived from its **richer clinical information space** coupled with a perfectly structured, zero-noise synthetic generation logic.

## 4. Final Architectural Recommendation

1. **"CMS + Synthea fusion improves real-world patient prediction" cannot be claimed at this stage.** 
2. We must **NOT** fabricate random mappings between Synthea UUIDs and CMS member IDs.
3. The only technically legitimate mechanism to evaluate a true fusion model is to establish a **Common Synthetic Cohort (Option B)**. This requires extending the data-generation pipeline so that both claims-based models and clinical-history models can evaluate the exact same simulated individuals.
