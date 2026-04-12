-- =====================================================
-- HealthFirst Australia — Analysis Queries
-- Purpose: Root cause analysis, churn prediction
--          features, and revenue recovery insights
-- =====================================================

-- =====================================================
-- SECTION 1: ROOT CAUSE ANALYSIS — MONTH 7 BULK BILLING DROP
-- =====================================================

-- 1A. Monthly KPI summary with month-on-month growth
WITH monthly_kpis AS (
    SELECT
        DATE_TRUNC('month', appointment_date)                   AS month,
        COUNT(CASE WHEN status = 'completed' THEN 1 END)        AS completed,
        COUNT(CASE WHEN status = 'no_show'   THEN 1 END)        AS no_shows,
        ROUND(SUM(CASE WHEN status = 'completed' THEN billed_amount ELSE 0 END), 2) AS gross_revenue,
        ROUND(AVG(CASE WHEN status = 'completed' THEN billed_amount END), 2)        AS avg_billed,
        ROUND(
            100.0 * COUNT(CASE WHEN status = 'completed' AND billing_type = 'bulk_bill' THEN 1 END)
            / NULLIF(COUNT(CASE WHEN status = 'completed' THEN 1 END), 0), 2
        )                                                       AS bulk_billing_rate_pct,
        ROUND(
            100.0 * COUNT(CASE WHEN status = 'no_show' THEN 1 END)
            / NULLIF(COUNT(*), 0), 2
        )                                                       AS no_show_rate_pct
    FROM appointments
    GROUP BY 1
)
SELECT
    month,
    completed,
    no_shows,
    gross_revenue,
    avg_billed,
    bulk_billing_rate_pct,
    no_show_rate_pct,
    LAG(gross_revenue) OVER (ORDER BY month)           AS prev_month_revenue,
    ROUND(
        100.0 * (gross_revenue - LAG(gross_revenue) OVER (ORDER BY month))
        / NULLIF(LAG(gross_revenue) OVER (ORDER BY month), 0), 2
    )                                                  AS mom_revenue_growth_pct
FROM monthly_kpis
ORDER BY month;

-- 1B. Decompose Month 7 drop: Volume Effect + Rate Effect + Mix Effect
WITH m6 AS (
    SELECT
        specialty,
        COUNT(CASE WHEN status = 'completed' THEN 1 END)          AS volume,
        ROUND(AVG(CASE WHEN status = 'completed' THEN billed_amount END), 2) AS avg_rate,
        ROUND(SUM(CASE WHEN status = 'completed' THEN billed_amount ELSE 0 END), 2) AS revenue
    FROM appointments
    WHERE DATE_TRUNC('month', appointment_date) = (
        SELECT DATE_TRUNC('month', MAX(appointment_date)) - INTERVAL '1 month'
        FROM appointments
    )
    GROUP BY specialty
),
m7 AS (
    SELECT
        specialty,
        COUNT(CASE WHEN status = 'completed' THEN 1 END)          AS volume,
        ROUND(AVG(CASE WHEN status = 'completed' THEN billed_amount END), 2) AS avg_rate,
        ROUND(SUM(CASE WHEN status = 'completed' THEN billed_amount ELSE 0 END), 2) AS revenue
    FROM appointments
    WHERE DATE_TRUNC('month', appointment_date) = (
        SELECT DATE_TRUNC('month', MAX(appointment_date))
        FROM appointments
    )
    GROUP BY specialty
)
SELECT
    COALESCE(m6.specialty, m7.specialty)           AS specialty,
    COALESCE(m6.volume, 0)                         AS m6_volume,
    COALESCE(m7.volume, 0)                         AS m7_volume,
    ROUND(COALESCE(m6.avg_rate, 0), 2)             AS m6_avg_rate,
    ROUND(COALESCE(m7.avg_rate, 0), 2)             AS m7_avg_rate,
    ROUND(COALESCE(m6.revenue, 0), 2)              AS m6_revenue,
    ROUND(COALESCE(m7.revenue, 0), 2)              AS m7_revenue,
    ROUND(COALESCE(m7.revenue, 0) - COALESCE(m6.revenue, 0), 2) AS revenue_delta,
    -- Volume Effect = (m7_volume - m6_volume) × m6_avg_rate
    ROUND((COALESCE(m7.volume, 0) - COALESCE(m6.volume, 0)) * COALESCE(m6.avg_rate, 0), 2) AS volume_effect,
    -- Rate Effect = m6_volume × (m7_avg_rate - m6_avg_rate)
    ROUND(COALESCE(m6.volume, 0) * (COALESCE(m7.avg_rate, 0) - COALESCE(m6.avg_rate, 0)), 2) AS rate_effect
FROM m6
FULL OUTER JOIN m7 ON m6.specialty = m7.specialty
ORDER BY revenue_delta ASC;

-- =====================================================
-- SECTION 2: PATIENT CHURN FEATURES
-- =====================================================

-- 2A. Build churn feature table per patient
WITH patient_recency AS (
    SELECT
        patient_id,
        MAX(appointment_date)                               AS last_visit,
        COUNT(DISTINCT appointment_id)                      AS appointment_count,
        ROUND(SUM(CASE WHEN status = 'completed' THEN billed_amount ELSE 0 END), 2) AS total_billed,
        ROUND(AVG(CASE WHEN status = 'completed' THEN billed_amount END), 2)        AS avg_billed,
        ROUND(AVG(wait_days), 1)                            AS avg_wait_days,
        ROUND(100.0 * SUM(CASE WHEN appointment_type = 'telehealth' THEN 1 ELSE 0 END) / COUNT(*), 2) AS telehealth_pct,
        ROUND(100.0 * SUM(CASE WHEN status = 'no_show' THEN 1 ELSE 0 END) / COUNT(*), 2) AS no_show_rate_pct
    FROM appointments
    GROUP BY patient_id
),
patient_satisfaction AS (
    SELECT
        patient_id,
        ROUND(AVG(overall_score), 2)    AS avg_overall_score,
        ROUND(AVG(wait_time_rating), 2) AS avg_wait_rating,
        COUNT(CASE WHEN complaint_category != 'None' THEN 1 END) AS complaint_count
    FROM satisfaction_surveys
    GROUP BY patient_id
)
SELECT
    p.patient_id,
    p.insurance_type,
    p.state,
    p.chronic_conditions,
    p.churn_flag,                                           -- TARGET VARIABLE
    DATE_PART('day', NOW() - r.last_visit::TIMESTAMP)::INT AS days_since_visit,
    r.appointment_count,
    r.total_billed,
    r.avg_billed,
    r.avg_wait_days,
    r.telehealth_pct,
    r.no_show_rate_pct,
    COALESCE(s.avg_overall_score, 5)                        AS avg_overall_score,
    COALESCE(s.avg_wait_rating, 3)                          AS avg_wait_rating,
    COALESCE(s.complaint_count, 0)                          AS complaint_count
FROM patients p
LEFT JOIN patient_recency    r ON p.patient_id = r.patient_id
LEFT JOIN patient_satisfaction s ON p.patient_id = s.patient_id
ORDER BY days_since_visit DESC NULLS LAST;

-- 2B. Rule-based churn risk score (before ML)
WITH features AS (
    SELECT
        p.patient_id,
        p.churn_flag,
        p.insurance_type,
        p.total_billed,
        DATE_PART('day', NOW() - MAX(a.appointment_date)::TIMESTAMP)::INT AS days_inactive,
        COUNT(a.appointment_id)                             AS appt_count,
        COALESCE(AVG(s.overall_score), 5)                   AS avg_score
    FROM patients p
    LEFT JOIN appointments a         ON p.patient_id = a.patient_id
    LEFT JOIN satisfaction_surveys s ON p.patient_id = s.patient_id
    GROUP BY p.patient_id, p.churn_flag, p.insurance_type, p.total_billed
)
SELECT
    patient_id,
    churn_flag,
    insurance_type,
    ROUND(total_billed, 2)  AS lifetime_billed,
    days_inactive,
    appt_count,
    ROUND(avg_score, 2)     AS avg_satisfaction,
    -- Churn risk scoring (0–5)
    (
      CASE WHEN days_inactive > 180 THEN 2 WHEN days_inactive > 90 THEN 1 ELSE 0 END
    + CASE WHEN appt_count = 1      THEN 1 ELSE 0 END
    + CASE WHEN avg_score < 4       THEN 2 WHEN avg_score < 6    THEN 1 ELSE 0 END
    )                       AS churn_risk_score,
    CASE
        WHEN (CASE WHEN days_inactive > 180 THEN 2 WHEN days_inactive > 90 THEN 1 ELSE 0 END
            + CASE WHEN appt_count = 1      THEN 1 ELSE 0 END
            + CASE WHEN avg_score < 4       THEN 2 WHEN avg_score < 6    THEN 1 ELSE 0 END) >= 4 THEN 'HIGH'
        WHEN (CASE WHEN days_inactive > 180 THEN 2 WHEN days_inactive > 90 THEN 1 ELSE 0 END
            + CASE WHEN appt_count = 1      THEN 1 ELSE 0 END
            + CASE WHEN avg_score < 4       THEN 2 WHEN avg_score < 6    THEN 1 ELSE 0 END) >= 2 THEN 'MEDIUM'
        ELSE 'LOW'
    END                     AS churn_risk_band
FROM features
ORDER BY churn_risk_score DESC;

-- 2C. High-value patients at churn risk (priority retention list)
WITH features AS (
    SELECT
        p.patient_id,
        p.insurance_type,
        p.state,
        p.total_billed,
        p.churn_flag,
        DATE_PART('day', NOW() - MAX(a.appointment_date)::TIMESTAMP)::INT AS days_inactive,
        COALESCE(AVG(s.overall_score), 5) AS avg_score
    FROM patients p
    LEFT JOIN appointments a         ON p.patient_id = a.patient_id
    LEFT JOIN satisfaction_surveys s ON p.patient_id = s.patient_id
    GROUP BY p.patient_id, p.insurance_type, p.state, p.total_billed, p.churn_flag
)
SELECT
    patient_id,
    insurance_type,
    state,
    ROUND(total_billed, 2)  AS lifetime_billed_aud,
    days_inactive,
    ROUND(avg_score, 2)     AS avg_satisfaction,
    churn_flag
FROM features
WHERE total_billed > 500        -- high value
  AND days_inactive > 90        -- showing inactivity
  AND churn_flag = 0            -- not yet churned
ORDER BY lifetime_billed_aud DESC
LIMIT 50;

-- =====================================================
-- SECTION 3: BILLING LEAKAGE & RECOVERY ANALYSIS
-- =====================================================

-- 3A. Medicare rejection trend — monthly
SELECT
    DATE_TRUNC('month', claim_date)    AS month,
    COUNT(*)                           AS total_claims,
    SUM(CASE WHEN claim_status = 'rejected' THEN 1 ELSE 0 END) AS rejected,
    ROUND(100.0 * SUM(CASE WHEN claim_status = 'rejected' THEN 1 ELSE 0 END) / COUNT(*), 2) AS rejection_rate_pct,
    ROUND(SUM(CASE WHEN claim_status = 'rejected' THEN rejected_amount ELSE 0 END), 2)      AS rejected_value_aud,
    -- Most common rejection reason
    MODE() WITHIN GROUP (ORDER BY rejection_reason) AS top_rejection_reason
FROM billing_claims
WHERE claim_type = 'Medicare'
GROUP BY 1
ORDER BY 1;

-- 3B. No-show revenue loss by specialty — monthly
SELECT
    DATE_TRUNC('month', appointment_date) AS month,
    specialty,
    SUM(CASE WHEN status = 'no_show' THEN 1 ELSE 0 END)                 AS no_shows,
    ROUND(SUM(CASE WHEN status = 'no_show' THEN scheduled_fee ELSE 0 END), 2) AS lost_revenue_aud,
    -- Recovery at 70% fill rate
    ROUND(SUM(CASE WHEN status = 'no_show' THEN scheduled_fee ELSE 0 END) * 0.70, 2) AS recoverable_at_70pct
FROM appointments
GROUP BY 1, 2
ORDER BY 1, lost_revenue_aud DESC;

-- 3C. Bulk billing erosion — revenue impact of rate drop
WITH monthly_bb AS (
    SELECT
        DATE_TRUNC('month', appointment_date) AS month,
        COUNT(CASE WHEN status = 'completed' THEN 1 END)     AS completed,
        COUNT(CASE WHEN status = 'completed' AND billing_type = 'bulk_bill' THEN 1 END) AS bulk_billed,
        ROUND(AVG(CASE WHEN status = 'completed' THEN billed_amount END), 2) AS avg_fee
    FROM appointments
    GROUP BY 1
),
baseline AS (
    SELECT AVG(bulk_billed::DECIMAL / NULLIF(completed, 0)) AS baseline_rate
    FROM monthly_bb
    WHERE month < (SELECT MAX(month) - INTERVAL '3 months' FROM monthly_bb)
)
SELECT
    m.month,
    m.completed,
    m.bulk_billed,
    ROUND(100.0 * m.bulk_billed / NULLIF(m.completed, 0), 2)  AS actual_bb_rate_pct,
    ROUND(b.baseline_rate * 100, 2)                            AS baseline_bb_rate_pct,
    ROUND(
        -- Lost revenue = appointments that SHOULD have been bulk-billed but weren't × avg fee
        GREATEST(0, (b.baseline_rate - m.bulk_billed::DECIMAL / NULLIF(m.completed, 0)))
        * m.completed * m.avg_fee, 2
    )                                                          AS erosion_cost_aud
FROM monthly_bb m
CROSS JOIN baseline b
ORDER BY m.month;

-- =====================================================
-- SECTION 4: SPECIALTY BENCHMARKING
-- =====================================================

-- 4A. Specialty scorecard: revenue, margin, wait, satisfaction, bulk-billing rate
SELECT
    a.specialty,
    COUNT(CASE WHEN a.status = 'completed' THEN 1 END)              AS completed_appointments,
    ROUND(AVG(CASE WHEN a.status = 'completed' THEN a.billed_amount END), 2)          AS avg_billed_aud,
    ROUND(AVG(CASE WHEN a.status = 'completed' THEN a.staff_cost END), 2)             AS avg_cost_aud,
    ROUND(AVG(CASE WHEN a.status = 'completed' THEN a.billed_amount - a.staff_cost END), 2) AS avg_margin_aud,
    ROUND(
        100.0 * AVG(CASE WHEN a.status = 'completed' THEN a.billed_amount - a.staff_cost END)
        / NULLIF(AVG(CASE WHEN a.status = 'completed' THEN a.billed_amount END), 0), 2
    )                                                                AS margin_pct,
    ROUND(AVG(CASE WHEN a.status = 'completed' THEN a.wait_days END), 1)              AS avg_wait_days,
    ROUND(
        100.0 * COUNT(CASE WHEN a.status = 'completed' AND a.billing_type = 'bulk_bill' THEN 1 END)
        / NULLIF(COUNT(CASE WHEN a.status = 'completed' THEN 1 END), 0), 2
    )                                                                AS bulk_billing_rate_pct,
    ROUND(AVG(s.overall_score), 2)                                   AS avg_satisfaction
FROM appointments a
LEFT JOIN satisfaction_surveys s ON a.appointment_id = s.appointment_id
GROUP BY a.specialty
ORDER BY avg_margin_aud DESC;

-- 4B. Clinic performance ranking
SELECT
    st.clinic_name,
    st.state,
    st.clinic_type,
    COUNT(a.appointment_id)                             AS appointments,
    COUNT(DISTINCT a.patient_id)                        AS unique_patients,
    ROUND(SUM(CASE WHEN a.status = 'completed' THEN a.billed_amount ELSE 0 END), 2) AS total_revenue_aud,
    ROUND(AVG(CASE WHEN a.status = 'completed' THEN a.billed_amount END), 2)        AS avg_billed_aud,
    ROUND(
        100.0 * COUNT(CASE WHEN a.status = 'no_show' THEN 1 END)
        / NULLIF(COUNT(a.appointment_id), 0), 2
    )                                                   AS no_show_rate_pct,
    ROUND(AVG(st.avg_patient_rating), 2)                AS avg_staff_rating
FROM staff st
LEFT JOIN appointments a ON st.staff_id = a.staff_id
GROUP BY st.clinic_name, st.state, st.clinic_type
ORDER BY total_revenue_aud DESC;

-- =====================================================
-- SECTION 5: TELEHEALTH ANALYSIS
-- =====================================================

-- 5A. Telehealth vs in-person: volume, revenue, and satisfaction comparison
SELECT
    DATE_TRUNC('month', a.appointment_date)             AS month,
    a.appointment_type,
    COUNT(CASE WHEN a.status = 'completed' THEN 1 END)  AS completed,
    ROUND(AVG(CASE WHEN a.status = 'completed' THEN a.billed_amount END), 2) AS avg_billed_aud,
    ROUND(SUM(CASE WHEN a.status = 'completed' THEN a.billed_amount ELSE 0 END), 2) AS total_revenue_aud,
    ROUND(AVG(s.overall_score), 2)                       AS avg_satisfaction,
    ROUND(AVG(a.wait_days), 1)                           AS avg_wait_days
FROM appointments a
LEFT JOIN satisfaction_surveys s ON a.appointment_id = s.appointment_id
WHERE a.status = 'completed'
GROUP BY 1, 2
ORDER BY 1, 2;

-- =====================================================
-- END ANALYSIS QUERIES
-- =====================================================
