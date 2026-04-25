-- =====================================================
-- HealthFirst Australia — Views, Stored Procedures & Window Functions
-- =====================================================


-- =====================================================
-- SECTION 1: VIEWS
-- =====================================================

-- View 1: Monthly revenue summary (used by dashboard)
CREATE OR REPLACE VIEW vw_monthly_revenue AS
SELECT
    DATE_TRUNC('month', appointment_date)                        AS month,
    billing_type,
    COUNT(CASE WHEN status = 'completed' THEN 1 END)             AS completed_appointments,
    ROUND(SUM(CASE WHEN status = 'completed' THEN billed_amount ELSE 0 END)::NUMERIC, 2) AS total_revenue_aud,
    ROUND(AVG(CASE WHEN status = 'completed' THEN billed_amount END)::NUMERIC, 2)        AS avg_billed_aud,
    ROUND(
        100.0 * COUNT(CASE WHEN status = 'no_show' THEN 1 END)
        / NULLIF(COUNT(*), 0), 2
    )                                                            AS no_show_rate_pct
FROM appointments
GROUP BY 1, 2
ORDER BY 1, 2;


-- View 2: Patient churn risk summary
CREATE OR REPLACE VIEW vw_churn_risk AS
WITH recency AS (
    SELECT
        patient_id,
        MAX(appointment_date)                                     AS last_visit,
        COUNT(*)                                                  AS total_appointments,
        ROUND(100.0 * SUM(CASE WHEN status = 'no_show' THEN 1 ELSE 0 END) / COUNT(*)::NUMERIC, 2) AS no_show_rate_pct
    FROM appointments
    GROUP BY patient_id
),
satisfaction AS (
    SELECT
        patient_id,
        ROUND(AVG(overall_score)::NUMERIC, 2) AS avg_satisfaction
    FROM satisfaction_surveys
    GROUP BY patient_id
)
SELECT
    p.patient_id,
    p.insurance_type,
    p.state,
    p.churn_flag,
    ROUND(p.total_billed::NUMERIC, 2)                                      AS lifetime_billed_aud,
    DATE_PART('day', NOW() - r.last_visit::TIMESTAMP)::INT        AS days_since_last_visit,
    r.total_appointments,
    r.no_show_rate_pct,
    COALESCE(s.avg_satisfaction, 5)                               AS avg_satisfaction,
    CASE
        WHEN DATE_PART('day', NOW() - r.last_visit::TIMESTAMP) > 180 THEN 'HIGH'
        WHEN DATE_PART('day', NOW() - r.last_visit::TIMESTAMP) > 90  THEN 'MEDIUM'
        ELSE 'LOW'
    END                                                           AS churn_risk_band
FROM patients p
LEFT JOIN recency     r ON p.patient_id = r.patient_id
LEFT JOIN satisfaction s ON p.patient_id = s.patient_id;


-- View 3: Billing leakage summary per month
CREATE OR REPLACE VIEW vw_billing_leakage AS
SELECT
    DATE_TRUNC('month', c.claim_date)                            AS month,
    c.claim_type,
    COUNT(*)                                                     AS total_claims,
    SUM(CASE WHEN c.claim_status = 'rejected' THEN 1 ELSE 0 END) AS rejected_claims,
    ROUND(SUM(CASE WHEN c.claim_status = 'rejected' THEN c.rejected_amount ELSE 0 END)::NUMERIC, 2) AS rejected_value_aud,
    ROUND(
        100.0 * SUM(CASE WHEN c.claim_status = 'rejected' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0), 2
    )                                                            AS rejection_rate_pct
FROM billing_claims c
GROUP BY 1, 2
ORDER BY 1, 2;


-- View 4: Specialty scorecard
CREATE OR REPLACE VIEW vw_specialty_scorecard AS
SELECT
    a.specialty,
    COUNT(CASE WHEN a.status = 'completed' THEN 1 END)           AS completed_appointments,
    ROUND(AVG(CASE WHEN a.status = 'completed' THEN a.billed_amount END)::NUMERIC, 2)          AS avg_billed_aud,
    ROUND(AVG(CASE WHEN a.status = 'completed' THEN a.billed_amount - a.staff_cost END)::NUMERIC, 2) AS avg_margin_aud,
    ROUND(
        100.0 * AVG(CASE WHEN a.status = 'completed' THEN a.billed_amount - a.staff_cost END)
        / NULLIF(AVG(CASE WHEN a.status = 'completed' THEN a.billed_amount END), 0), 2
    )                                                            AS margin_pct,
    ROUND(AVG(a.wait_days), 1)                                   AS avg_wait_days,
    ROUND(AVG(s.overall_score)::NUMERIC, 2)                               AS avg_satisfaction
FROM appointments a
LEFT JOIN satisfaction_surveys s ON a.appointment_id = s.appointment_id
GROUP BY a.specialty;


-- View 5: Clinic performance ranking
CREATE OR REPLACE VIEW vw_clinic_performance AS
SELECT
    st.clinic_name,
    st.state,
    st.clinic_type,
    COUNT(a.appointment_id)                                      AS total_appointments,
    COUNT(DISTINCT a.patient_id)                                 AS unique_patients,
    ROUND(SUM(CASE WHEN a.status = 'completed' THEN a.billed_amount ELSE 0 END)::NUMERIC, 2) AS total_revenue_aud,
    ROUND(
        100.0 * COUNT(CASE WHEN a.status = 'no_show' THEN 1 END)
        / NULLIF(COUNT(a.appointment_id), 0), 2
    )                                                            AS no_show_rate_pct,
    ROUND(AVG(st.avg_patient_rating)::NUMERIC, 2)                         AS avg_staff_rating
FROM staff st
LEFT JOIN appointments a ON st.staff_id = a.staff_id
GROUP BY st.clinic_name, st.state, st.clinic_type;


-- =====================================================
-- SECTION 2: STORED PROCEDURES
-- =====================================================

-- Procedure 1: Refresh all processed summary tables
CREATE OR REPLACE PROCEDURE sp_refresh_summaries()
LANGUAGE plpgsql AS $$
BEGIN
    RAISE NOTICE 'Refreshing monthly revenue summary...';
    -- In a real system this would refresh materialised views or summary tables
    -- Here we validate row counts as a health check
    PERFORM COUNT(*) FROM vw_monthly_revenue;
    PERFORM COUNT(*) FROM vw_churn_risk;
    PERFORM COUNT(*) FROM vw_billing_leakage;
    PERFORM COUNT(*) FROM vw_specialty_scorecard;
    PERFORM COUNT(*) FROM vw_clinic_performance;
    RAISE NOTICE 'All views validated successfully.';
END;
$$;

-- Run with: CALL sp_refresh_summaries();


-- Procedure 2: Flag high-risk churn patients and log count
CREATE OR REPLACE PROCEDURE sp_flag_high_churn_risk()
LANGUAGE plpgsql AS $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM vw_churn_risk
    WHERE churn_risk_band = 'HIGH'
      AND churn_flag = 0;

    RAISE NOTICE 'High churn risk patients (not yet churned): %', v_count;

    IF v_count > 100 THEN
        RAISE WARNING 'Alert: More than 100 high-risk patients detected. Retention team action required.';
    END IF;
END;
$$;

-- Run with: CALL sp_flag_high_churn_risk();


-- Procedure 3: Summarise billing leakage for a given month
CREATE OR REPLACE PROCEDURE sp_leakage_report(p_month DATE)
LANGUAGE plpgsql AS $$
DECLARE
    v_total_rejected NUMERIC;
    v_top_reason     TEXT;
BEGIN
    SELECT
        ROUND(SUM(rejected_amount)::NUMERIC, 2),
        MODE() WITHIN GROUP (ORDER BY rejection_reason)
    INTO v_total_rejected, v_top_reason
    FROM billing_claims
    WHERE DATE_TRUNC('month', claim_date) = DATE_TRUNC('month', p_month)
      AND claim_status = 'rejected';

    RAISE NOTICE 'Month: %', p_month;
    RAISE NOTICE 'Total rejected value: $%', v_total_rejected;
    RAISE NOTICE 'Top rejection reason: %', v_top_reason;
END;
$$;

-- Run with: CALL sp_leakage_report('2024-07-01');


-- =====================================================
-- SECTION 3: WINDOW FUNCTIONS
-- =====================================================

-- Window 1: Month-on-month revenue growth with running total
SELECT
    DATE_TRUNC('month', appointment_date)                        AS month,
    ROUND(SUM(CASE WHEN status = 'completed' THEN billed_amount ELSE 0 END)::NUMERIC, 2) AS monthly_revenue,

    -- Previous month revenue
    LAG(ROUND(SUM(CASE WHEN status = 'completed' THEN billed_amount ELSE 0 END)::NUMERIC, 2))
        OVER (ORDER BY DATE_TRUNC('month', appointment_date))    AS prev_month_revenue,

    -- Month-on-month growth %
    ROUND(
        100.0 * (
            SUM(CASE WHEN status = 'completed' THEN billed_amount ELSE 0 END)
            - LAG(SUM(CASE WHEN status = 'completed' THEN billed_amount ELSE 0 END))
                OVER (ORDER BY DATE_TRUNC('month', appointment_date))
        ) / NULLIF(
            LAG(SUM(CASE WHEN status = 'completed' THEN billed_amount ELSE 0 END))
                OVER (ORDER BY DATE_TRUNC('month', appointment_date))
        , 0), 2
    )                                                            AS mom_growth_pct,

    -- Running total revenue
    ROUND(SUM(SUM(CASE WHEN status = 'completed' THEN billed_amount ELSE 0 END))
        OVER (ORDER BY DATE_TRUNC('month', appointment_date) ROWS UNBOUNDED PRECEDING), 2) AS running_total_aud

FROM appointments
GROUP BY DATE_TRUNC('month', appointment_date)
ORDER BY month;


-- Window 2: Patient ranking by lifetime value within each state
SELECT
    patient_id,
    state,
    insurance_type,
    ROUND(total_billed::NUMERIC, 2)                                       AS lifetime_billed_aud,
    churn_flag,

    -- Rank patients by lifetime value within their state
    RANK() OVER (PARTITION BY state ORDER BY total_billed DESC)  AS rank_in_state,

    -- Percentile within all patients
    ROUND(
        100.0 * PERCENT_RANK() OVER (ORDER BY total_billed), 2
    )                                                            AS percentile,

    -- Cumulative revenue contribution
    ROUND(
        SUM(total_billed) OVER (ORDER BY total_billed DESC ROWS UNBOUNDED PRECEDING)
        / NULLIF(SUM(total_billed) OVER (), 0) * 100, 2
    )                                                            AS cumulative_revenue_pct

FROM patients
ORDER BY state, rank_in_state;


-- Window 3: 3-month rolling average bulk billing rate
SELECT
    DATE_TRUNC('month', appointment_date)                        AS month,
    ROUND(
        100.0 * COUNT(CASE WHEN status = 'completed' AND billing_type = 'bulk_bill' THEN 1 END)
        / NULLIF(COUNT(CASE WHEN status = 'completed' THEN 1 END), 0), 2
    )                                                            AS bulk_billing_rate_pct,

    -- 3-month rolling average
    ROUND(AVG(
        100.0 * COUNT(CASE WHEN status = 'completed' AND billing_type = 'bulk_bill' THEN 1 END)
        / NULLIF(COUNT(CASE WHEN status = 'completed' THEN 1 END), 0)
    ) OVER (ORDER BY DATE_TRUNC('month', appointment_date) ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2)
                                                                 AS rolling_3m_avg_pct

FROM appointments
GROUP BY DATE_TRUNC('month', appointment_date)
ORDER BY month;


-- Window 4: No-show rate per specialty with overall average comparison
SELECT
    specialty,
    COUNT(*)                                                     AS total_appointments,
    COUNT(CASE WHEN status = 'no_show' THEN 1 END)               AS no_shows,
    ROUND(
        100.0 * COUNT(CASE WHEN status = 'no_show' THEN 1 END)
        / NULLIF(COUNT(*), 0), 2
    )                                                            AS no_show_rate_pct,

    -- Overall average no-show rate across all specialties
    ROUND(AVG(
        100.0 * COUNT(CASE WHEN status = 'no_show' THEN 1 END)
        / NULLIF(COUNT(*), 0)
    ) OVER (), 2)                                                AS overall_avg_no_show_pct,

    -- Difference from overall average
    ROUND(
        100.0 * COUNT(CASE WHEN status = 'no_show' THEN 1 END)
        / NULLIF(COUNT(*), 0)
        - AVG(
            100.0 * COUNT(CASE WHEN status = 'no_show' THEN 1 END)
            / NULLIF(COUNT(*), 0)
        ) OVER (), 2
    )                                                            AS diff_from_avg_pct

FROM appointments
GROUP BY specialty
ORDER BY no_show_rate_pct DESC;


-- Window 5: First and most recent appointment per patient (patient journey)
SELECT
    patient_id,
    appointment_date,
    specialty,
    billing_type,
    status,
    billed_amount,

    -- First appointment date
    FIRST_VALUE(appointment_date)
        OVER (PARTITION BY patient_id ORDER BY appointment_date
              ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS first_appointment_date,

    -- Most recent appointment date
    LAST_VALUE(appointment_date)
        OVER (PARTITION BY patient_id ORDER BY appointment_date
              ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS latest_appointment_date,

    -- Appointment number for this patient
    ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY appointment_date) AS appointment_number,

    -- Running total billed per patient
    ROUND(SUM(CASE WHEN status = 'completed' THEN billed_amount ELSE 0 END)
        OVER (PARTITION BY patient_id ORDER BY appointment_date
              ROWS UNBOUNDED PRECEDING), 2)                      AS running_patient_total_aud

FROM appointments
ORDER BY patient_id, appointment_date;


-- =====================================================
-- END
-- =====================================================
