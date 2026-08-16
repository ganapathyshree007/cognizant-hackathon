| Component | Method | Accuracy/Agreement | Precision | Recall | F1 | AUC | Main Metric | Status |
|-----------|--------|-------------------|-----------|--------|----|-----|-------------|--------|
| XGBoost | ML | NOT MEASURABLE | N/A | N/A | N/A | N/A | PR-AUC | WEAK |
| Safety Gate | Rules | 100% | 100% | 100% | N/A | N/A | Emergency FN rate (0%) | STRONG |
| Opportunity | Rules | 100% | N/A | N/A | N/A | N/A | Rule agreement (100%) | STRONG |
| Drivers | Rules | 100% | 100% | N/A | N/A | N/A | Evidence coverage (100%) | STRONG |
| Pathway | Rules | 100% | N/A | N/A | N/A | N/A | Rule agreement (100%) | STRONG |
| Provider | SQL/ranking | 100% | 100% | 100% | N/A | N/A | Filtering precision (100%)| MODERATE |
| Care Manager | HITL | 100% | N/A | N/A | N/A | N/A | Workflow correctness (100%) | STRONG |
| Intervention | Rules/API | 100% | N/A | N/A | N/A | N/A | Authorization accuracy (100%) | STRONG |
| Outcome | Claims logic | NOT MEASURABLE | N/A | N/A | N/A | N/A | Event detection | WEAK |
| History | Persistence | 100% | N/A | N/A | N/A | N/A | Recording accuracy (100%) | STRONG |
