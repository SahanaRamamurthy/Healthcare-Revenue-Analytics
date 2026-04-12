-- =====================================================
-- HealthFirst Australia — Data Cleaning Queries
-- Purpose: Identify and fix data quality issues
--          across all five healthcare tables
-- =====================================================

-- =====================================================
-- SECTION 1: DATA QUALITY AUDIT
-- Run these first to understand the scope of issues
-- =====================================================

-- 1A. NULL audit — appointments table
SELECT
    COUNT(*)                                                         AS total_appointments,
    SUM(CASE WHEN patient_gap      IS NULL THEN 1 ELSE 0 END)       AS null_patient_gap,
    SUM(CASE WHEN billed_amount    IS NULL THEN 1 ELSE 0 END)       AS null_billed_amount,
    SUM(CASE WHEN medicare_rebate  IS NULL THEN 1 ELSE 0 END)       AS null_medicare_rebate,
    SUM(CASE WHEN appointment_date IS NULL THEN 1 ELSE 0 END)       AS null_appointment_date,
    SUM(CASE WHEN wait_days        IS NULL THEN 1 ELSE 0 END)       AS null_wait_days,
    SUM(CASE WHEN status           IS NULL THEN 1 ELSE 0 END)       AS null_status
FROM appointments;

-- 1B. Duplicate appointment rows (same appointment_id appearing > once)
SELECT
    appointment_id,
    COUNT(*) AS occurrences
FROM appointments
GROUP BY appointment_id
HAVING COUNT(*) > 1
ORDER BY occurrences DESC;

-- 1C. Inconsistent specialty name variants
SELECT
    specialty,
    COUNT(*) AS row_count
FROM appointments
GROUP BY specialty
ORDER BY specialty;

-- 1D. Impossible survey dates (survey recorded before appointment)
SELECT
    s.survey_id,
    s.appointment_id,
    a.appointment_date,
    s.survey_date
FROM satisfaction_surveys s
JOIN appointments a ON s.appointment_id = a.appointment_id
WHERE s.survey_date < a.appointment_date;

-- 1E. NULL satisfaction scores in surveys
SELECT
    COUNT(*)                                                                  AS total_surveys,
    SUM(CASE WHEN overall_score    IS NULL THEN 1 ELSE 0 END)                AS null_overall,
    SUM(CASE WHEN wait_time_rating IS NULL THEN 1 ELSE 0 END)                AS null_wait_rating,
    SUM(CASE WHEN doctor_rating    IS NULL THEN 1 ELSE 0 END)                AS null_doctor_rating,
    ROUND(
        100.0 * SUM(CASE WHEN overall_score IS NULL THEN 1 ELSE 0 END) / COUNT(*),
        2
    )                                                                         AS null_overall_pct
FROM satisfaction_surveys;

-- 1F. Invalid Medicare number format (should be 10 digits)
SELECT
    patient_id,
    medicare_number
FROM patients
WHERE medicare_number !~ '^\d{10}$'
ORDER BY patient_id;

-- 1G. Appointments with impossible financial values
SELECT
    appointment_id,
    billed_amount,
    medicare_rebate,
    patient_gap,
    insurance_paid
FROM appointments
WHERE billed_amount < 0
   OR medicare_rebate < 0
   OR patient_gap < 0
   OR insurance_paid < 0;

-- =====================================================
-- SECTION 2: FIX — APPOINTMENTS TABLE
-- =====================================================

-- 2A. Fix NULL patient_gap → set to 0 (bulk-billed patients pay nothing out-of-pocket)
UPDATE appointments
SET patient_gap = 0
WHERE patient_gap IS NULL;

-- Verify fix
SELECT COUNT(*) AS remaining_null_patient_gap
FROM appointments
WHERE patient_gap IS NULL;

-- 2B. Remove duplicate appointment rows — keep first occurrence
DELETE FROM appointments
WHERE ctid NOT IN (
    SELECT MIN(ctid)
    FROM appointments
    GROUP BY appointment_id
);

-- Verify: should be 0 duplicates
SELECT appointment_id, COUNT(*) AS cnt
FROM appointments
GROUP BY appointment_id
HAVING COUNT(*) > 1;

-- 2C. Standardise specialty name variants
UPDATE appointments SET specialty = 'Mental Health'
WHERE LOWER(TRIM(specialty)) IN ('mental health', 'mh', 'mental_health', 'mentalhealth');

UPDATE appointments SET specialty = 'General Practice'
WHERE LOWER(TRIM(specialty)) IN ('general practice', 'gp', 'general_practice');

UPDATE appointments SET specialty = 'Cardiology'
WHERE LOWER(TRIM(specialty)) IN ('cardiology', 'cardio');

UPDATE appointments SET specialty = 'Physiotherapy'
WHERE LOWER(TRIM(specialty)) IN ('physiotherapy', 'physio', 'physical therapy');

UPDATE appointments SET specialty = 'Paediatrics'
WHERE LOWER(TRIM(specialty)) IN ('paediatrics', 'pediatrics', 'paeds', 'peds');

-- Verify: distinct specialty names after standardisation
SELECT specialty, COUNT(*) AS row_count
FROM appointments
GROUP BY specialty
ORDER BY specialty;

-- 2D. Standardise appointment_date strings to ISO format (YYYY-MM-DD)
UPDATE appointments
SET appointment_date = TO_CHAR(TO_DATE(appointment_date::TEXT, 'DD/MM/YYYY'), 'YYYY-MM-DD')
WHERE appointment_date::TEXT LIKE '__/__/____';

-- =====================================================
-- SECTION 3: FIX — SATISFACTION SURVEYS
-- =====================================================

-- 3A. Fix impossible survey dates → set to appointment date + 3 days
UPDATE satisfaction_surveys s
SET survey_date = a.appointment_date + INTERVAL '3 days'
FROM appointments a
WHERE s.appointment_id = a.appointment_id
  AND s.survey_date < a.appointment_date;

-- 3B. Fill NULL satisfaction scores with column median
UPDATE satisfaction_surveys
SET overall_score = (
    SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY overall_score)
    FROM satisfaction_surveys WHERE overall_score IS NOT NULL
)
WHERE overall_score IS NULL;

UPDATE satisfaction_surveys
SET wait_time_rating = (
    SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY wait_time_rating)
    FROM satisfaction_surveys WHERE wait_time_rating IS NOT NULL
)
WHERE wait_time_rating IS NULL;

UPDATE satisfaction_surveys
SET doctor_rating = (
    SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY doctor_rating)
    FROM satisfaction_surveys WHERE doctor_rating IS NOT NULL
)
WHERE doctor_rating IS NULL;

-- =====================================================
-- SECTION 4: FIX — PATIENTS TABLE
-- =====================================================

-- 4A. Flag invalid Medicare numbers (do not delete — audit trail)
ALTER TABLE patients ADD COLUMN IF NOT EXISTS medicare_number_valid BOOLEAN DEFAULT TRUE;

UPDATE patients
SET medicare_number_valid = FALSE
WHERE medicare_number !~ '^\d{10}$';

-- 4B. Confirm no patients have negative age
SELECT COUNT(*) AS impossible_ages
FROM patients
WHERE age < 0 OR age > 120;

-- =====================================================
-- SECTION 5: VALIDATION SCORECARD (run after all fixes)
-- =====================================================

SELECT 'appointments'        AS table_name,
       COUNT(*)              AS total_rows,
       SUM(CASE WHEN patient_gap IS NULL THEN 1 ELSE 0 END) AS null_issues,
       SUM(CASE WHEN billed_amount < 0   THEN 1 ELSE 0 END) AS negative_values,
       0                     AS impossible_dates
FROM appointments
UNION ALL
SELECT 'satisfaction_surveys',
       COUNT(*),
       SUM(CASE WHEN overall_score IS NULL THEN 1 ELSE 0 END),
       0,
       SUM(CASE WHEN survey_date < (
           SELECT appointment_date FROM appointments a
           WHERE a.appointment_id = satisfaction_surveys.appointment_id
       ) THEN 1 ELSE 0 END)
FROM satisfaction_surveys
UNION ALL
SELECT 'patients',
       COUNT(*),
       SUM(CASE WHEN medicare_number_valid = FALSE THEN 1 ELSE 0 END),
       0,
       SUM(CASE WHEN age < 0 OR age > 120 THEN 1 ELSE 0 END)
FROM patients;

-- =====================================================
-- SECTION 6: LOAD RAW DATA (PostgreSQL COPY commands)
-- =====================================================
/*
\COPY patients              FROM 'data/raw/patients.csv'              CSV HEADER;
\COPY staff                 FROM 'data/raw/staff.csv'                 CSV HEADER;
\COPY appointments          FROM 'data/raw/appointments.csv'          CSV HEADER;
\COPY satisfaction_surveys  FROM 'data/raw/satisfaction_surveys.csv'  CSV HEADER;
\COPY billing_claims        FROM 'data/raw/billing_claims.csv'        CSV HEADER;

-- After cleaning, export to cleaned/:
\COPY patients              TO 'data/cleaned/patients_cleaned.csv'             CSV HEADER;
\COPY staff                 TO 'data/cleaned/staff_cleaned.csv'                CSV HEADER;
\COPY appointments          TO 'data/cleaned/appointments_cleaned.csv'         CSV HEADER;
\COPY satisfaction_surveys  TO 'data/cleaned/satisfaction_surveys_cleaned.csv' CSV HEADER;
\COPY billing_claims        TO 'data/cleaned/billing_claims_cleaned.csv'       CSV HEADER;
*/

-- =====================================================
-- END CLEANING QUERIES
-- =====================================================
