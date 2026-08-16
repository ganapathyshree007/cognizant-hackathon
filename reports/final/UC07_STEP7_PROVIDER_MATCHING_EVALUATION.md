# UC07 Step 7: Provider Matching Engine & Sensitivity Analysis

The prototype Provider Matching Engine enforces strict clinical/safety hard constraints, then ranks eligible candidates using an explicit, explainable mathematical weighting. Specialty and Safety are NEVER scored; they are binary blocks.

### Weight Configuration: Base (35/35/20/10)
- **Status**: SUCCESS
- **Reason**: Options generated successfully.
| Rank | Name | Final Score | Breakdown (Raw 0-100) |
|---|---|---|---|
| 1 | Dr. Cardio 2 | 82.9 | Q:70|D:94|E:84|F:87 |
| 2 | Dr. Cardio 8 | 79.35 | Q:96|D:81|E:60|F:54 |
| 3 | Dr. Cardio 20 | 79.2 | Q:57|D:97|E:96|F:61 |
| 4 | Dr. Cardio 13 | 74.9 | Q:77|D:79|E:80|F:43 |
| 5 | Dr. Cardio 7 | 73.8 | Q:77|D:79|E:89|F:14 |

### Weight Configuration: Quality Heavy (40/30/20/10)
- **Status**: SUCCESS
- **Reason**: Options generated successfully.
| Rank | Name | Final Score | Breakdown (Raw 0-100) |
|---|---|---|---|
| 1 | Dr. Cardio 2 | 81.7 | Q:70|D:94|E:84|F:87 |
| 2 | Dr. Cardio 8 | 80.1 | Q:96|D:81|E:60|F:54 |
| 3 | Dr. Cardio 20 | 77.2 | Q:57|D:97|E:96|F:61 |
| 4 | Dr. Cardio 18 | 75.8 | Q:93|D:53|E:83|F:61 |
| 5 | Dr. Cardio 13 | 74.8 | Q:77|D:79|E:80|F:43 |

### Weight Configuration: Distance Heavy (30/40/20/10)
- **Status**: SUCCESS
- **Reason**: Options generated successfully.
| Rank | Name | Final Score | Breakdown (Raw 0-100) |
|---|---|---|---|
| 1 | Dr. Cardio 2 | 84.1 | Q:70|D:94|E:84|F:87 |
| 2 | Dr. Cardio 20 | 81.2 | Q:57|D:97|E:96|F:61 |
| 3 | Dr. Cardio 8 | 78.6 | Q:96|D:81|E:60|F:54 |
| 4 | Dr. Cardio 13 | 75.0 | Q:77|D:79|E:80|F:43 |
| 5 | Dr. Cardio 7 | 73.9 | Q:77|D:79|E:89|F:14 |


## Sensitivity Analysis Conclusion
The sensitivity testing demonstrates that the ranking is highly responsive to the chosen weight distribution. A 5% shift between Quality and Distance is sufficient to reorder the Top 5 candidates, particularly when competing providers have asymmetrical profiles (e.g., extremely close vs. exceptionally high MIPS scores). 

**Important Caveat**: The base `35/35/20/10` configuration acts as an explainable, transparent prototype. It is not claimed to be clinically optimal and requires future validation alongside the Care Management team.

## Architecture Rules Verified
1. **Safety Block**: RED completely blocks the matching function.
2. **Pathway Block**: YELLOW halts matching pending manual clearance.
3. **Human-In-The-Loop**: Output is strictly a "Top 5 Recommendations" array explicitly requiring Care Manager selection.
