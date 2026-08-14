# Deployment checklist

1. Store API credentials in a secrets manager; do not commit them.
2. Add authentication and role-based access before exposing the API.
3. Encrypt data in transit and at rest; record immutable access/audit events.
4. Validate model performance, threshold, fairness, and drift on approved real data.
5. Obtain clinical, privacy, security, and governance approval.
6. Configure monitoring for API errors, data quality, feature drift, calibration, and outcome rates.
7. Keep a human care manager in the approval workflow.
