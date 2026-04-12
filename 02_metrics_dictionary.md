# Metrics Dictionary
## HealthFirst Australia — Revenue Intelligence

This document defines every KPI used in this project: what it measures, why it matters,
how it is calculated, and where to find it in the data.

---

## Revenue & Billing KPIs

### 1. Gross Revenue
- **Definition**: Total billed_amount for all completed appointments in a period.
- **Why it matters**: Top-line measure of the network's financial output.
- **Formula**: `SUM(billed_amount) WHERE status = 'completed'`
- **Source**: `appointments` table

### 2. Bulk Billing Rate
- **Definition**: Percentage of completed appointments billed under Medicare bulk billing (no patient gap payment).
- **Why it matters**: Key Australian healthcare policy metric. Higher bulk billing = greater patient access but lower per-appointment revenue. Government incentives tie to this rate.
- **Formula**: `COUNT(billing_type='bulk_bill') / COUNT(completed) × 100`
- **Benchmark**: National average ~80% for GP; target ≥78% for HealthFirst
- **Source**: `appointments` table

### 3. Average Billed Amount
- **Definition**: Mean billed_amount per completed appointment.
- **Why it matters**: Signals pricing mix and billing type shifts independent of volume.
- **Formula**: `AVG(billed_amount) WHERE status = 'completed'`
- **Source**: `appointments` table

### 4. Revenue per Specialty
- **Definition**: Total and average revenue broken down by clinical specialty.
- **Why it matters**: Identifies highest-margin and lowest-margin service lines for resource allocation.
- **Source**: `appointments` JOIN `staff` tables

### 5. Patient Out-of-Pocket (Gap Payment)
- **Definition**: Amount the patient pays after Medicare rebate and private insurance cover.
- **Formula**: `patient_gap = billed_amount - medicare_rebate - insurance_paid`
- **Why it matters**: Higher gap payments correlate with lower bulk billing rate and higher churn risk.
- **Source**: `appointments` table

---

## Access & Quality KPIs

### 6. Average Wait Days
- **Definition**: Mean number of days from booking to appointment, by specialty.
- **Why it matters**: Patient access indicator. Long wait times drive disengagement and churn.
- **SLAs**: GP ≤7 days | Mental Health ≤14 days | Cardiology ≤21 days | All others ≤14 days
- **Formula**: `AVG(wait_days) WHERE status = 'completed'`
- **Source**: `appointments` table

### 7. No-Show Rate
- **Definition**: Percentage of scheduled appointments where patient did not attend.
- **Why it matters**: Direct revenue loss (slot wasted) and indirect signal of patient disengagement.
- **Formula**: `COUNT(status='no_show') / COUNT(*) × 100`
- **Benchmark**: Industry target ≤10%; HealthFirst current ~17%
- **Source**: `appointments` table

### 8. Telehealth Adoption Rate
- **Definition**: Percentage of completed appointments delivered via telehealth.
- **Why it matters**: Telehealth expands reach to regional patients and reduces no-shows; impacts billing rates differently.
- **Formula**: `COUNT(appointment_type='telehealth') / COUNT(completed) × 100`
- **Source**: `appointments` table

---

## Patient Satisfaction KPIs

### 9. Overall Satisfaction Score
- **Definition**: Patient-rated overall experience, scale 1–10.
- **Why it matters**: Predictor of patient retention and referral behaviour.
- **Source**: `satisfaction_surveys` table

### 10. Net Promoter Score (NPS) Proxy
- **Definition**: Estimated NPS derived from `nps_score` column (−100 to +100 scale).
- **Why it matters**: Widely used healthcare experience benchmark; target ≥55.
- **Source**: `satisfaction_surveys` table

### 11. Would Recommend Rate
- **Definition**: Percentage of survey respondents who said they would recommend the clinic.
- **Formula**: `SUM(would_recommend) / COUNT(*) × 100`
- **Source**: `satisfaction_surveys` table

---

## Churn & Retention KPIs

### 12. Patient Churn Rate
- **Definition**: Percentage of patients who have not attended an appointment in 90+ days and are flagged as likely to have switched providers.
- **Formula**: `SUM(churn_flag) / COUNT(patients) × 100`
- **Target**: ≤15%
- **Source**: `patients` table

### 13. Churn Probability Score
- **Definition**: ML model output (0–1) representing the probability a patient will churn in the next 90 days.
- **Model**: Gradient Boosting Classifier trained on RFV features + satisfaction + wait time
- **Risk bands**: Low (<0.30) | Medium (0.30–0.60) | High (>0.60)
- **Source**: `data/processed/patients_churn_scored.csv`

### 14. Patient Lifetime Value (LTV)
- **Definition**: Total historical billed amount for a patient across all completed appointments.
- **Formula**: `SUM(billed_amount) WHERE status = 'completed'` per patient
- **Why it matters**: Weights churn risk — a high-LTV patient churning is far more costly.
- **Source**: `patients.total_billed`

---

## Billing Claims KPIs

### 15. Medicare Claim Rejection Rate
- **Definition**: Percentage of Medicare claims that are rejected by the payer.
- **Formula**: `COUNT(claim_status='rejected') / COUNT(*) × 100`
- **Target**: ≤6%
- **Source**: `billing_claims` table

### 16. Rejected Claim Value
- **Definition**: Total dollar value of rejected Medicare and insurance claims.
- **Formula**: `SUM(rejected_amount) WHERE claim_status = 'rejected'`
- **Why it matters**: Recoverable revenue — fixing documentation errors and resubmitting can recover 50%+ of rejections.
- **Source**: `billing_claims` table

---

## Patient Segment Definitions (RFV Framework)

| Segment | Recency | Frequency | Value | Strategy |
|---|---|---|---|---|
| Active & Engaged | Recent | High | High | Loyalty rewards, preventive care prompts |
| Chronic Care Patient | Recent | High | Medium | Chronic disease management programs |
| New Patient | Recent | Low | Low–Med | Onboarding, follow-up booking |
| Preventive Only | Recent | Low | Low | Annual check-up reminders |
| At Risk of Lapsing | 60–90 days | Medium | Medium | Personalised outreach call |
| Disengaged | 90+ days | Low | Low | Re-engagement campaign |
| High Value Occasional | 30–90 days | Low | High | VIP retention, priority booking |
