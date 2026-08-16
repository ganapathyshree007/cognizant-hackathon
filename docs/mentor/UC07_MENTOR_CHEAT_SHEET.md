# UC07 MENTOR CHEAT SHEET

**1. What is the problem?**
Some ER visits could have been a cheaper same-day clinic or telehealth call instead. The system identifies potentially avoidable ED use and recommends a lower-acuity next step without blocking true emergencies.

**2. Who uses the system?**
Human Care Managers operating within a payer or population health organization.

**3. Why is it payer-side?**
It focuses on proactive population health management, reducing total cost of care by coordinating appropriate lower-acuity pathways, rather than operating at the high-stakes point-of-injury at a hospital.

**4. Why not hospital ED?**
Hospital EDs must stabilize patients under EMTALA. A hospital triage system cannot divert patients away from the ED for legal and safety reasons.

**5. What data did we use?**
CMS SynPUF historical claims (Outpatient, Inpatient, Beneficiary).

**6. Why CMS claims?**
Claims provide a standardized, longitudinal view of a member's healthcare utilization history, ideal for identifying repeated patterns over time.

**7. What does XGBoost predict?**
It predicts repeat ED utilization risk/candidate utilization within the defined 90-day prediction window based on historical features.

**8. What does the Safety Gate predict?**
It does not predict. It deterministically evaluates current clinical context (vitals, triage notes) against hardcoded safety rules to determine if navigation is safe to proceed.

**9. Does the system decide ED vs non-ED?**
No. It identifies *opportunities* for lower-acuity navigation but leaves clinical triage to professionals and the final decision to Care Managers.

**10. Does it ever block an emergency?**
No. If the Safety Gate detects an emergency indicator or lacks sufficient information, it explicitly halts automated lower-acuity navigation.

**11. What is Navigation Opportunity?**
An evidence-based evaluation of whether a member's history demonstrates a pattern suitable for alternative care pathways, independent of pure statistical risk.

**12. How is opportunity different from risk?**
Risk is a statistical probability of repeat utilization. Opportunity evaluates whether specific historical patterns (e.g., high ED use but zero outpatient use) make the member a good candidate for proactive navigation.

**13. What are the drivers?**
Specific, evidence-based data points (e.g., `HIGH_ED_FREQUENCY` due to 4 past visits) that justify the navigation opportunity and support pathway selection.

**14. How is the pathway selected?**
By evaluating the safety status, navigation opportunity, and supporting drivers through a deterministic rule engine to map to the most appropriate lower-acuity setting.

**15. How are providers selected?**
By querying a provider database for matches on the recommended pathway's specialties, geographic location, and telehealth availability, ranked deterministically.

**16. Who makes the final decision?**
The Human Care Manager.

**17. Why is human review necessary?**
To ensure clinical appropriateness, evaluate nuanced context not captured by the AI, and maintain accountability over care-coordination interventions.

**18. What happens after intervention?**
The intervention is logged and tied to an observation window to track subsequent healthcare utilization.

**19. What is the outcome?**
An observational record comparing repeat ED visits and outpatient follow-ups during a 90-day post-intervention window against an historical index encounter.

**20. Does outcome prove success?**
No. Claims absence is not definitive proof that the intervention successfully prevented an ED visit. It is purely observational.

**21. Does the model retrain automatically?**
No. Automated retraining is a future production improvement.

**22. How is temporal leakage prevented?**
Features are engineered strictly as point-in-time snapshots using only data available on or before the prediction date.

**23. What are the current prototype limitations?**
Synthetic provider catalog, prototype reviewer authentication, missing real-time appointment/network status, no automated model retraining, and a future-ready (but not actively queried) member history feedback loop.

**24. What would be needed for production?**
Live HIE/EHR integrations for the Safety Gate, active provider directory integrations with FHIR APIs, SSO/JWT authentication, and active feedback loops for model retraining.
