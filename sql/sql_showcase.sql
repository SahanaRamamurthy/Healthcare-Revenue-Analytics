-- =====================================================================
-- HealthFirst Australia — SQL Showcase
-- =====================================================================
-- This file demonstrates advanced PostgreSQL SQL techniques applied
-- to real healthcare business problems.
--
-- Topics covered:
--   1. CTEs (Common Table Expressions)
--   2. Window Functions (LAG, LEAD, RANK, DENSE_RANK, PERCENT_RANK,
--                        ROW_NUMBER, FIRST_VALUE, LAST_VALUE,
--                        running totals, rolling averages)
--   3. Aggregations & CASE WHEN logic
--   4. Subqueries
--   5. JOINs (INNER, LEFT, FULL OUTER)
--   6. Views
--   7. Stored Procedures
--   8. Date functions
--   9. NULLIF, COALESCE, GREATEST, MODE()
--  10. GROUP BY, HAVING, ORDER BY
--
-- Database: healthfirst (PostgreSQL 16)
-- Run: psql healthfirst -f sql/sql_showcase.sql
-- =====================================================================


-- =====================================================================
-- SECTION 1: CTEs — Common Table Expressions
-- =====================================================================
-- A CTE is a temporary named result set that you can reference within
-- a SELECT, INSERT, UPDATE, or DELETE statement.
-- Think of it as a named subquery that makes complex queries readable.
-- =====================================================================

-- CTE 1A: Monthly KPI summary with month-on-month revenue growth
-- Business question: How did revenue, bulk billing, and no-shows
-- change each month — and what was the growth rate?
WITH monthly_kpis AS (
    SELECT
        DATE_TRUNC('month', appointment_date)                          AS month,
        COUNT(CASE WHEN status = 'completed' THEN 1 END)               AS completed,
        COUNT(CASE WHEN status = 'no_show'   THEN 1 END)               AS no_shows,
        ROUND(SUM(CASE WHEN status = 'completed'
                       THEN billed_amount ELSE 0 END)::NUMERIC, 2)     AS gross_revenue,
        ROUND(AVG(CASE WHEN status = 'completed'
                       THEN billed_amount END)::NUMERIC, 2)            AS avg_billed,
        ROUND(
            100.0 * COUNT(CASE WHEN status = 'completed'
                               AND billing_type = 'bulk_bill' THEN 1 END)
            / NULLIF(COUNT(CASE WHEN status = 'completed' THEN 1 END), 0)
        , 2)                                                           AS bulk_billing_rate_pct,
        ROUND(
            100.0 * COUNT(CASE WHEN status = 'no_show' THEN 1 END)
            / NULLIF(COUNT(*), 0)
        , 2)                                                           AS no_show_rate_pct
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
    -- LAG: compare to previous month
    LAG(gross_revenue) OVER (ORDER BY month)                           AS prev_month_revenue,
    ROUND(
        100.0 * (gross_revenue - LAG(gross_revenue) OVER (ORDER BY month))
        / NULLIF(LAG(gross_revenue) OVER (ORDER BY month), 0)
    , 2)                                                               AS mom_revenue_growth_pct
FROM monthly_kpis
ORDER BY month;


-- CTE 1B: Multi-step churn feature engineering
-- Business question: Who are the highest-value patients showing
-- early signs of churn?
WITH patient_activity AS (
    -- Step 1: Summarise appointment behaviour per patient
    SELECT
        patient_id,
        MAX(appointment_date)                                          AS last_visit,
        COUNT(*)                                                       AS total_appointments,
        ROUND(100.0 * SUM(CASE WHEN status = 'no_show'
                               THEN 1 ELSE 0 END) / COUNT(*)::NUMERIC, 2) AS no_show_rate_pct,
        ROUND(AVG(wait_days)::NUMERIC, 1)                              AS avg_wait_days
    FROM appointments
    GROUP BY patient_id
),
patient_satisfaction AS (
    -- Step 2: Summarise satisfaction scores per patient
    SELECT
        patient_id,
        ROUND(AVG(overall_score)::NUMERIC, 2)                          AS avg_satisfaction,
        COUNT(CASE WHEN complaint_category != 'None' THEN 1 END)       AS complaint_count
    FROM satisfaction_surveys
    GROUP BY patient_id
),
churn_features AS (
    -- Step 3: Combine all features
    SELECT
        p.patient_id,
        p.insurance_type,
        p.state,
        p.churn_flag,
        ROUND(p.total_billed::NUMERIC, 2)                              AS lifetime_billed_aud,
        DATE_PART('day', NOW() - a.last_visit::TIMESTAMP)::INT         AS days_inactive,
        a.total_appointments,
        a.no_show_rate_pct,
        a.avg_wait_days,
        COALESCE(s.avg_satisfaction, 5)                                AS avg_satisfaction,
        COALESCE(s.complaint_count, 0)                                 AS complaint_count
    FROM patients p
    LEFT JOIN patient_activity    a ON p.patient_id = a.patient_id
    LEFT JOIN patient_satisfaction s ON p.patient_id = s.patient_id
)
-- Step 4: Filter for high-value patients showing churn signals
SELECT *
FROM churn_features
WHERE lifetime_billed_aud > 500
  AND days_inactive > 60
  AND churn_flag = 0
ORDER BY lifetime_billed_aud DESC;


-- =====================================================================
-- SECTION 2: WINDOW FUNCTIONS
-- =====================================================================
-- Window functions perform calculations across a set of rows related
-- to the current row — without collapsing rows like GROUP BY does.
-- Syntax: FUNCTION() OVER (PARTITION BY ... ORDER BY ... ROWS ...)
-- =====================================================================

-- Window 2A: LAG & LEAD — compare current month to previous and next
-- Business question: Is revenue trending up or down month by month?
SELECT
    DATE_TRUNC('month', appointment_date)                              AS month,
    ROUND(SUM(CASE WHEN status = 'completed'
                   THEN billed_amount ELSE 0 END)::NUMERIC, 2)         AS monthly_revenue,

    -- LAG: value from previous row
    LAG(ROUND(SUM(CASE WHEN status = 'completed'
                       THEN billed_amount ELSE 0 END)::NUMERIC, 2))
        OVER (ORDER BY DATE_TRUNC('month', appointment_date))          AS prev_month_revenue,

    -- LEAD: value from next row
    LEAD(ROUND(SUM(CASE WHEN status = 'completed'
                        THEN billed_amount ELSE 0 END)::NUMERIC, 2))
        OVER (ORDER BY DATE_TRUNC('month', appointment_date))          AS next_month_revenue

FROM appointments
GROUP BY DATE_TRUNC('month', appointment_date)
ORDER BY month;


-- Window 2B: RANK, DENSE_RANK, ROW_NUMBER
-- Business question: How do patients rank by lifetime value
-- within their state? What's the difference between ranking functions?
SELECT
    patient_id,
    state,
    ROUND(total_billed::NUMERIC, 2)                                    AS lifetime_billed_aud,

    -- ROW_NUMBER: unique sequential number, no ties
    ROW_NUMBER() OVER (PARTITION BY state ORDER BY total_billed DESC)  AS row_number,

    -- RANK: same rank for ties, skips numbers after ties (1,1,3)
    RANK() OVER (PARTITION BY state ORDER BY total_billed DESC)        AS rank,

    -- DENSE_RANK: same rank for ties, no gaps (1,1,2)
    DENSE_RANK() OVER (PARTITION BY state ORDER BY total_billed DESC)  AS dense_rank

FROM patients
ORDER BY state, rank;


-- Window 2C: PERCENT_RANK and cumulative revenue distribution
-- Business question: What percentage of total revenue comes from
-- the top 20% of patients? (Pareto analysis)
SELECT
    patient_id,
    ROUND(total_billed::NUMERIC, 2)                                    AS lifetime_billed_aud,

    -- PERCENT_RANK: relative rank as a percentage (0 to 1)
    ROUND(100.0 * PERCENT_RANK()
        OVER (ORDER BY total_billed)::NUMERIC, 2)                      AS percentile,

    -- Running cumulative revenue as % of total
    ROUND(
        SUM(total_billed) OVER (ORDER BY total_billed DESC
            ROWS UNBOUNDED PRECEDING)
        / NULLIF(SUM(total_billed) OVER (), 0) * 100
    , 2)                                                               AS cumulative_revenue_pct

FROM patients
ORDER BY total_billed DESC;


-- Window 2D: Running total and 3-month rolling average
-- Business question: What is the cumulative revenue to date,
-- and what is the smoothed trend in bulk billing rates?
SELECT
    DATE_TRUNC('month', appointment_date)                              AS month,

    ROUND(SUM(CASE WHEN status = 'completed'
                   THEN billed_amount ELSE 0 END)::NUMERIC, 2)         AS monthly_revenue,

    -- Running total (cumulative sum)
    ROUND(SUM(SUM(CASE WHEN status = 'completed'
                       THEN billed_amount ELSE 0 END))
        OVER (ORDER BY DATE_TRUNC('month', appointment_date)
              ROWS UNBOUNDED PRECEDING)::NUMERIC, 2)                   AS running_total_aud,

    -- 3-month rolling average bulk billing rate
    ROUND(AVG(
        100.0 * COUNT(CASE WHEN status = 'completed'
                           AND billing_type = 'bulk_bill' THEN 1 END)
        / NULLIF(COUNT(CASE WHEN status = 'completed' THEN 1 END), 0)
    ) OVER (ORDER BY DATE_TRUNC('month', appointment_date)
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)::NUMERIC, 2)    AS rolling_3m_bulk_billing_pct

FROM appointments
GROUP BY DATE_TRUNC('month', appointment_date)
ORDER BY month;


-- Window 2E: FIRST_VALUE and LAST_VALUE — patient journey
-- Business question: What was each patient's first and most recent
-- appointment, and how many visits have they had?
SELECT
    patient_id,
    appointment_date,
    specialty,
    billing_type,
    status,

    -- First appointment date for this patient
    FIRST_VALUE(appointment_date)
        OVER (PARTITION BY patient_id ORDER BY appointment_date
              ROWS BETWEEN UNBOUNDED PRECEDING
                       AND UNBOUNDED FOLLOWING)                        AS first_visit_date,

    -- Most recent appointment date for this patient
    LAST_VALUE(appointment_date)
        OVER (PARTITION BY patient_id ORDER BY appointment_date
              ROWS BETWEEN UNBOUNDED PRECEDING
                       AND UNBOUNDED FOLLOWING)                        AS latest_visit_date,

    -- Sequential visit number
    ROW_NUMBER()
        OVER (PARTITION BY patient_id ORDER BY appointment_date)       AS visit_number,

    -- Running billed total per patient
    ROUND(SUM(CASE WHEN status = 'completed' THEN billed_amount ELSE 0 END)
        OVER (PARTITION BY patient_id ORDER BY appointment_date
              ROWS UNBOUNDED PRECEDING)::NUMERIC, 2)                   AS running_patient_total_aud

FROM appointments
ORDER BY patient_id, appointment_date;


-- =====================================================================
-- SECTION 3: JOINS
-- =====================================================================
-- Joins combine rows from two or more tables based on a related column.
-- INNER JOIN  — only matching rows from both tables
-- LEFT JOIN   — all rows from left table, matching from right
-- FULL OUTER  — all rows from both tables
-- =====================================================================

-- Join 3A: INNER JOIN — completed appointments with satisfaction scores
-- Business question: For completed appointments that have a survey,
-- what is the relationship between wait time and satisfaction?
SELECT
    a.appointment_id,
    a.specialty,
    a.wait_days,
    a.billing_type,
    s.overall_score,
    s.wait_time_rating,
    s.would_recommend
FROM appointments a
INNER JOIN satisfaction_surveys s ON a.appointment_id = s.appointment_id
WHERE a.status = 'completed'
ORDER BY a.wait_days DESC;


-- Join 3B: LEFT JOIN — all patients with their appointment summary
-- Business question: Which patients have never had an appointment?
SELECT
    p.patient_id,
    p.insurance_type,
    p.state,
    p.churn_flag,
    COUNT(a.appointment_id)                                            AS total_appointments,
    -- NULL means no appointments found (patient registered but never booked)
    MAX(a.appointment_date)                                            AS last_appointment_date
FROM patients p
LEFT JOIN appointments a ON p.patient_id = a.patient_id
GROUP BY p.patient_id, p.insurance_type, p.state, p.churn_flag
HAVING COUNT(a.appointment_id) = 0
ORDER BY p.patient_id;


-- Join 3C: FULL OUTER JOIN — revenue decomposition Month 6 vs Month 7
-- Business question: Which specialties lost the most revenue
-- between Month 6 and Month 7?
WITH m6 AS (
    SELECT
        specialty,
        COUNT(CASE WHEN status = 'completed' THEN 1 END)               AS volume,
        ROUND(AVG(CASE WHEN status = 'completed'
                       THEN billed_amount END)::NUMERIC, 2)            AS avg_rate,
        ROUND(SUM(CASE WHEN status = 'completed'
                       THEN billed_amount ELSE 0 END)::NUMERIC, 2)     AS revenue
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
        COUNT(CASE WHEN status = 'completed' THEN 1 END)               AS volume,
        ROUND(AVG(CASE WHEN status = 'completed'
                       THEN billed_amount END)::NUMERIC, 2)            AS avg_rate,
        ROUND(SUM(CASE WHEN status = 'completed'
                       THEN billed_amount ELSE 0 END)::NUMERIC, 2)     AS revenue
    FROM appointments
    WHERE DATE_TRUNC('month', appointment_date) = (
        SELECT DATE_TRUNC('month', MAX(appointment_date))
        FROM appointments
    )
    GROUP BY specialty
)
SELECT
    COALESCE(m6.specialty, m7.specialty)                               AS specialty,
    COALESCE(m6.revenue, 0)                                            AS m6_revenue,
    COALESCE(m7.revenue, 0)                                            AS m7_revenue,
    ROUND((COALESCE(m7.revenue, 0) - COALESCE(m6.revenue, 0))::NUMERIC, 2) AS revenue_delta,
    -- Volume Effect = change in volume × previous average rate
    ROUND(((COALESCE(m7.volume, 0) - COALESCE(m6.volume, 0))
           * COALESCE(m6.avg_rate, 0))::NUMERIC, 2)                    AS volume_effect,
    -- Rate Effect = previous volume × change in average rate
    ROUND((COALESCE(m6.volume, 0)
           * (COALESCE(m7.avg_rate, 0) - COALESCE(m6.avg_rate, 0)))::NUMERIC, 2) AS rate_effect
FROM m6
FULL OUTER JOIN m7 ON m6.specialty = m7.specialty
ORDER BY revenue_delta ASC;


-- =====================================================================
-- SECTION 4: AGGREGATIONS, HAVING, SUBQUERIES
-- =====================================================================

-- Aggregation 4A: Specialty performance with HAVING filter
-- Business question: Which specialties have above-average no-show rates?
SELECT
    specialty,
    COUNT(*)                                                           AS total_appointments,
    ROUND(100.0 * COUNT(CASE WHEN status = 'no_show' THEN 1 END)
          / NULLIF(COUNT(*), 0)::NUMERIC, 2)                           AS no_show_rate_pct
FROM appointments
GROUP BY specialty
HAVING
    100.0 * COUNT(CASE WHEN status = 'no_show' THEN 1 END)
    / NULLIF(COUNT(*), 0) >
    (SELECT 100.0 * COUNT(CASE WHEN status = 'no_show' THEN 1 END)
                  / NULLIF(COUNT(*), 0) FROM appointments)
ORDER BY no_show_rate_pct DESC;


-- Aggregation 4B: Subquery — patients above average lifetime billing
-- Business question: Which patients bill above the network average,
-- and are they at churn risk?
SELECT
    patient_id,
    insurance_type,
    state,
    ROUND(total_billed::NUMERIC, 2)                                    AS lifetime_billed_aud,
    churn_flag
FROM patients
WHERE total_billed > (
    SELECT AVG(total_billed) FROM patients
)
ORDER BY total_billed DESC;


-- Aggregation 4C: MODE, COALESCE, NULLIF in practice
-- Business question: What is the most common rejection reason
-- per claim type, and what is the total rejected value?
SELECT
    claim_type,
    COUNT(*)                                                           AS total_claims,
    SUM(CASE WHEN claim_status = 'rejected' THEN 1 ELSE 0 END)         AS rejected_count,
    ROUND(SUM(CASE WHEN claim_status = 'rejected'
                   THEN rejected_amount ELSE 0 END)::NUMERIC, 2)       AS total_rejected_aud,
    -- NULLIF prevents division by zero
    ROUND(100.0 * SUM(CASE WHEN claim_status = 'rejected' THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0)::NUMERIC, 2)                           AS rejection_rate_pct,
    -- MODE: most frequently occurring value
    MODE() WITHIN GROUP (ORDER BY rejection_reason)                    AS top_rejection_reason
FROM billing_claims
GROUP BY claim_type
ORDER BY total_rejected_aud DESC;


-- =====================================================================
-- SECTION 5: DATE FUNCTIONS
-- =====================================================================

-- Date 5A: Extract, DATE_TRUNC, DATE_PART, AGE, INTERVAL
-- Business question: How does patient age group affect
-- appointment frequency and billing?
SELECT
    CASE
        WHEN DATE_PART('year', AGE(p.date_of_birth::DATE)) < 18 THEN 'Under 18'
        WHEN DATE_PART('year', AGE(p.date_of_birth::DATE)) < 35 THEN '18-34'
        WHEN DATE_PART('year', AGE(p.date_of_birth::DATE)) < 55 THEN '35-54'
        WHEN DATE_PART('year', AGE(p.date_of_birth::DATE)) < 70 THEN '55-69'
        ELSE '70+'
    END                                                                AS age_group,
    COUNT(DISTINCT p.patient_id)                                       AS patient_count,
    COUNT(a.appointment_id)                                            AS total_appointments,
    ROUND(AVG(a.billed_amount)::NUMERIC, 2)                            AS avg_billed_aud,
    ROUND(100.0 * COUNT(CASE WHEN a.billing_type = 'bulk_bill' THEN 1 END)
          / NULLIF(COUNT(a.appointment_id), 0)::NUMERIC, 2)            AS bulk_billing_rate_pct
FROM patients p
LEFT JOIN appointments a ON p.patient_id = a.patient_id
WHERE a.status = 'completed'
GROUP BY 1
ORDER BY 1;


-- Date 5B: Identify patients inactive for 90+ days
-- Business question: How many patients haven't visited in 3 months?
SELECT
    p.patient_id,
    p.insurance_type,
    p.state,
    MAX(a.appointment_date)                                            AS last_visit_date,
    DATE_PART('day', NOW() - MAX(a.appointment_date)::TIMESTAMP)::INT  AS days_inactive,
    p.churn_flag
FROM patients p
LEFT JOIN appointments a ON p.patient_id = a.patient_id
GROUP BY p.patient_id, p.insurance_type, p.state, p.churn_flag
HAVING DATE_PART('day', NOW() - MAX(a.appointment_date)::TIMESTAMP) > 90
ORDER BY days_inactive DESC;


-- =====================================================================
-- SECTION 6: VIEWS
-- =====================================================================
-- A view is a saved SQL query that behaves like a virtual table.
-- It does not store data — it runs the query each time it is called.
-- =====================================================================

-- View 6A: Monthly revenue by billing type (used by dashboard)
CREATE OR REPLACE VIEW vw_monthly_revenue_by_type AS
SELECT
    DATE_TRUNC('month', appointment_date)                              AS month,
    billing_type,
    COUNT(CASE WHEN status = 'completed' THEN 1 END)                   AS completed_appointments,
    ROUND(SUM(CASE WHEN status = 'completed'
                   THEN billed_amount ELSE 0 END)::NUMERIC, 2)         AS total_revenue_aud,
    ROUND(AVG(CASE WHEN status = 'completed'
                   THEN billed_amount END)::NUMERIC, 2)                AS avg_billed_aud
FROM appointments
GROUP BY 1, 2
ORDER BY 1, 2;

-- Query it: SELECT * FROM vw_monthly_revenue_by_type;


-- View 6B: High-value patients at churn risk (retention priority list)
CREATE OR REPLACE VIEW vw_retention_priority AS
WITH activity AS (
    SELECT
        patient_id,
        MAX(appointment_date)                                          AS last_visit,
        ROUND(100.0 * SUM(CASE WHEN status = 'no_show'
                               THEN 1 ELSE 0 END) / COUNT(*)::NUMERIC, 2) AS no_show_rate_pct
    FROM appointments
    GROUP BY patient_id
)
SELECT
    p.patient_id,
    p.insurance_type,
    p.state,
    ROUND(p.total_billed::NUMERIC, 2)                                  AS lifetime_billed_aud,
    DATE_PART('day', NOW() - a.last_visit::TIMESTAMP)::INT             AS days_inactive,
    a.no_show_rate_pct
FROM patients p
JOIN activity a ON p.patient_id = a.patient_id
WHERE p.total_billed > 500
  AND DATE_PART('day', NOW() - a.last_visit::TIMESTAMP) > 60
  AND p.churn_flag = 0
ORDER BY lifetime_billed_aud DESC;

-- Query it: SELECT * FROM vw_retention_priority LIMIT 20;


-- =====================================================================
-- SECTION 7: STORED PROCEDURES
-- =====================================================================
-- A stored procedure is a saved block of SQL logic that can be
-- called by name. Used for repeatable tasks like reports or alerts.
-- =====================================================================

-- Procedure 7A: Print a monthly leakage report for any given month
CREATE OR REPLACE PROCEDURE sp_leakage_report(p_month DATE)
LANGUAGE plpgsql AS $$
DECLARE
    v_total_rejected NUMERIC;
    v_top_reason     TEXT;
    v_rejection_rate NUMERIC;
BEGIN
    SELECT
        ROUND(SUM(rejected_amount)::NUMERIC, 2),
        ROUND(100.0 * SUM(CASE WHEN claim_status = 'rejected'
                               THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0)::NUMERIC, 2),
        MODE() WITHIN GROUP (ORDER BY rejection_reason)
    INTO v_total_rejected, v_rejection_rate, v_top_reason
    FROM billing_claims
    WHERE DATE_TRUNC('month', claim_date) = DATE_TRUNC('month', p_month)
      AND claim_status = 'rejected';

    RAISE NOTICE '========================================';
    RAISE NOTICE 'Billing Leakage Report — %', TO_CHAR(p_month, 'Month YYYY');
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Total rejected value : $%', v_total_rejected;
    RAISE NOTICE 'Rejection rate       : %', v_rejection_rate;
    RAISE NOTICE 'Top rejection reason : %', v_top_reason;
    RAISE NOTICE '========================================';
END;
$$;

-- Run with: CALL sp_leakage_report('2024-07-01');


-- Procedure 7B: Flag high-risk churn patients and raise alert
CREATE OR REPLACE PROCEDURE sp_churn_alert()
LANGUAGE plpgsql AS $$
DECLARE
    v_high_risk  INT;
    v_med_risk   INT;
BEGIN
    SELECT COUNT(*) INTO v_high_risk
    FROM vw_retention_priority
    WHERE days_inactive > 180;

    SELECT COUNT(*) INTO v_med_risk
    FROM vw_retention_priority
    WHERE days_inactive BETWEEN 90 AND 180;

    RAISE NOTICE '========================================';
    RAISE NOTICE 'Churn Risk Alert';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'HIGH risk patients  : %', v_high_risk;
    RAISE NOTICE 'MEDIUM risk patients: %', v_med_risk;

    IF v_high_risk > 50 THEN
        RAISE WARNING 'Action required: % high-risk patients need immediate outreach.', v_high_risk;
    END IF;
END;
$$;

-- Run with: CALL sp_churn_alert();


-- =====================================================================
-- END OF SQL SHOWCASE
-- =====================================================================
