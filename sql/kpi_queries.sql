-- =====================================================
-- HealthFirst Australia — KPI Queries
-- =====================================================

-- KPI 1: Monthly Revenue by Billing Type
SELECT
    DATE_TRUNC('month', appointment_date)       AS month,
    COUNT(CASE WHEN status='completed' THEN 1 END) AS completed_appointments,
    COUNT(CASE WHEN status='no_show'   THEN 1 END) AS no_shows,
    ROUND(SUM(CASE WHEN status='completed' THEN billed_amount ELSE 0 END), 2) AS gross_revenue,
    ROUND(SUM(CASE WHEN status='completed' AND billing_type='bulk_bill'   THEN billed_amount ELSE 0 END), 2) AS bulk_bill_revenue,
    ROUND(SUM(CASE WHEN status='completed' AND billing_type='gap_payment' THEN billed_amount ELSE 0 END), 2) AS gap_payment_revenue,
    ROUND(SUM(CASE WHEN status='completed' AND billing_type='private'     THEN billed_amount ELSE 0 END), 2) AS private_revenue,
    ROUND(SUM(CASE WHEN status='completed' AND billing_type='self_pay'    THEN billed_amount ELSE 0 END), 2) AS self_pay_revenue
FROM appointments
GROUP BY 1 ORDER BY 1;

-- KPI 2: Bulk Billing Rate by Month (key metric for Australian healthcare)
SELECT
    DATE_TRUNC('month', appointment_date) AS month,
    COUNT(CASE WHEN status='completed' THEN 1 END) AS total_completed,
    COUNT(CASE WHEN status='completed' AND billing_type='bulk_bill' THEN 1 END) AS bulk_billed,
    ROUND(
        100.0 * COUNT(CASE WHEN status='completed' AND billing_type='bulk_bill' THEN 1 END)
        / NULLIF(COUNT(CASE WHEN status='completed' THEN 1 END), 0), 2
    ) AS bulk_billing_rate_pct
FROM appointments
GROUP BY 1 ORDER BY 1;

-- KPI 3: Average Wait Time by Specialty (patient access metric)
SELECT
    specialty,
    COUNT(*)                            AS appointments,
    ROUND(AVG(wait_days), 1)           AS avg_wait_days,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY wait_days), 1) AS median_wait_days,
    MAX(wait_days)                      AS max_wait_days,
    SUM(CASE WHEN wait_days > 30 THEN 1 ELSE 0 END) AS long_wait_count,
    ROUND(100.0 * SUM(CASE WHEN wait_days > 30 THEN 1 ELSE 0 END) / COUNT(*), 2) AS long_wait_pct
FROM appointments
WHERE status = 'completed'
GROUP BY specialty ORDER BY avg_wait_days DESC;

-- KPI 4: No-Show Rate by Specialty and Month
SELECT
    DATE_TRUNC('month', appointment_date) AS month,
    specialty,
    COUNT(*) AS total_appointments,
    SUM(CASE WHEN status='no_show' THEN 1 ELSE 0 END) AS no_shows,
    ROUND(100.0 * SUM(CASE WHEN status='no_show' THEN 1 ELSE 0 END) / COUNT(*), 2) AS no_show_rate_pct,
    ROUND(SUM(CASE WHEN status='no_show' THEN scheduled_fee ELSE 0 END), 2) AS lost_revenue
FROM appointments
GROUP BY 1, 2 ORDER BY 1, no_show_rate_pct DESC;

-- KPI 5: Patient Satisfaction Trend
SELECT
    DATE_TRUNC('month', survey_date) AS month,
    COUNT(*)                         AS surveys,
    ROUND(AVG(overall_score), 2)    AS avg_overall,
    ROUND(AVG(wait_time_rating), 2) AS avg_wait_rating,
    ROUND(AVG(doctor_rating), 2)    AS avg_doctor_rating,
    ROUND(100.0 * SUM(would_recommend) / COUNT(*), 2) AS recommend_rate_pct,
    ROUND(AVG(nps_score), 2)        AS avg_nps,
    SUM(CASE WHEN complaint_category != 'None' THEN 1 ELSE 0 END) AS complaints
FROM satisfaction_surveys
GROUP BY 1 ORDER BY 1;

-- KPI 6: Revenue per Appointment by Specialty (profitability signal)
SELECT
    specialty,
    COUNT(CASE WHEN status='completed' THEN 1 END)  AS completed,
    ROUND(AVG(CASE WHEN status='completed' THEN billed_amount END), 2)  AS avg_billed,
    ROUND(AVG(CASE WHEN status='completed' THEN staff_cost END), 2)     AS avg_cost,
    ROUND(AVG(CASE WHEN status='completed' THEN billed_amount - staff_cost END), 2) AS avg_margin,
    ROUND(100.0 * AVG(CASE WHEN status='completed' THEN billed_amount - staff_cost END)
          / NULLIF(AVG(CASE WHEN status='completed' THEN billed_amount END), 0), 2) AS margin_pct
FROM appointments
GROUP BY specialty ORDER BY avg_margin DESC;

-- KPI 7: Patient Churn by State and Insurance Type
SELECT
    state,
    insurance_type,
    COUNT(*) AS patients,
    SUM(churn_flag) AS churned,
    ROUND(100.0 * SUM(churn_flag) / COUNT(*), 2) AS churn_rate_pct,
    ROUND(AVG(total_billed), 2) AS avg_lifetime_billed
FROM patients
GROUP BY state, insurance_type
ORDER BY churn_rate_pct DESC;

-- KPI 8: Medicare Claim Rejection Rate
SELECT
    DATE_TRUNC('month', claim_date) AS month,
    claim_type,
    COUNT(*) AS total_claims,
    SUM(CASE WHEN claim_status='rejected' THEN 1 ELSE 0 END) AS rejected,
    ROUND(100.0 * SUM(CASE WHEN claim_status='rejected' THEN 1 ELSE 0 END) / COUNT(*), 2) AS rejection_rate_pct,
    ROUND(SUM(rejected_amount), 2) AS rejected_value
FROM billing_claims
GROUP BY 1, 2 ORDER BY 1, claim_type;

-- KPI 9: Telehealth Adoption Trend
SELECT
    DATE_TRUNC('month', appointment_date) AS month,
    COUNT(*) AS total_appointments,
    SUM(CASE WHEN appointment_type='telehealth' THEN 1 ELSE 0 END) AS telehealth_count,
    ROUND(100.0 * SUM(CASE WHEN appointment_type='telehealth' THEN 1 ELSE 0 END) / COUNT(*), 2) AS telehealth_pct,
    ROUND(SUM(CASE WHEN appointment_type='telehealth' THEN billed_amount ELSE 0 END), 2) AS telehealth_revenue
FROM appointments
WHERE status='completed'
GROUP BY 1 ORDER BY 1;

-- KPI 10: Patient Out-of-Pocket Costs (affordability pressure)
SELECT
    DATE_TRUNC('month', appointment_date) AS month,
    ROUND(AVG(CASE WHEN patient_gap > 0 THEN patient_gap END), 2) AS avg_gap_payment,
    ROUND(SUM(patient_gap), 2)    AS total_gap_collected,
    ROUND(SUM(billed_amount - medicare_rebate - insurance_paid - COALESCE(patient_gap,0)), 2) AS uncollected
FROM appointments
WHERE status='completed'
GROUP BY 1 ORDER BY 1;

-- KPI 11: Staff Utilisation by Clinic
SELECT
    s.clinic_name,
    s.state,
    s.clinic_type,
    COUNT(a.appointment_id)  AS total_appointments,
    COUNT(DISTINCT a.patient_id) AS unique_patients,
    ROUND(AVG(a.billed_amount), 2) AS avg_billed_per_appt,
    ROUND(SUM(a.billed_amount), 2) AS total_revenue,
    ROUND(AVG(s.avg_patient_rating), 2) AS avg_staff_rating
FROM staff s
LEFT JOIN appointments a ON s.staff_id = a.staff_id AND a.status='completed'
GROUP BY s.clinic_name, s.state, s.clinic_type
ORDER BY total_revenue DESC;

-- KPI 12: Referral Source Quality
SELECT
    p.referral_source,
    COUNT(DISTINCT p.patient_id)          AS patients,
    ROUND(AVG(p.total_appointments), 2)   AS avg_appointments,
    ROUND(AVG(p.total_billed), 2)         AS avg_lifetime_value,
    SUM(p.churn_flag)                     AS churned,
    ROUND(100.0 * SUM(p.churn_flag) / COUNT(*), 2) AS churn_rate_pct
FROM patients p
GROUP BY p.referral_source
ORDER BY avg_lifetime_value DESC;
