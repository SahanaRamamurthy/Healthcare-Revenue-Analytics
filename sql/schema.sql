-- =====================================================
-- HealthFirst Australia — Database Schema
-- =====================================================

CREATE TABLE patients (
    patient_id          INT PRIMARY KEY,
    full_name           VARCHAR(200),
    gender              VARCHAR(20),
    age                 INT,
    age_group           VARCHAR(10),
    date_of_birth       DATE,
    state               VARCHAR(10),
    city                VARCHAR(100),
    postcode            VARCHAR(10),
    medicare_number     VARCHAR(20),
    insurance_type      VARCHAR(20),   -- bulk_bill | private_fund | self_pay
    health_fund         VARCHAR(50),
    chronic_conditions  VARCHAR(100),
    referral_source     VARCHAR(100),
    registration_date   DATE,
    last_visit_date     DATE,
    churn_flag          INT DEFAULT 0, -- 1 = switched to another provider (90+ days inactive)
    total_appointments  INT DEFAULT 0,
    total_billed        DECIMAL(10,2) DEFAULT 0
);

CREATE TABLE staff (
    staff_id            INT PRIMARY KEY,
    full_name           VARCHAR(200),
    role                VARCHAR(50),   -- GP | Specialist | Nurse | Allied_Health
    specialty           VARCHAR(100),
    clinic_id           INT,
    clinic_name         VARCHAR(200),
    city                VARCHAR(100),
    state               VARCHAR(10),
    clinic_type         VARCHAR(20),   -- metro | regional
    years_experience    INT,
    avg_patient_rating  DECIMAL(3,1)
);

CREATE TABLE appointments (
    appointment_id      INT PRIMARY KEY,
    patient_id          INT,
    staff_id            INT,
    clinic_id           INT,
    appointment_date    DATE,
    specialty           VARCHAR(100),
    appointment_type    VARCHAR(20),   -- in_person | telehealth | emergency
    wait_days           INT,           -- days from booking to appointment
    status              VARCHAR(20),   -- completed | no_show | cancelled | rescheduled
    billing_type        VARCHAR(20),   -- bulk_bill | gap_payment | private | self_pay
    scheduled_fee       DECIMAL(10,2), -- Medicare schedule fee
    billed_amount       DECIMAL(10,2),
    medicare_rebate     DECIMAL(10,2),
    patient_gap         DECIMAL(10,2), -- amount patient pays out-of-pocket
    insurance_paid      DECIMAL(10,2),
    staff_cost          DECIMAL(10,2),
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (staff_id)   REFERENCES staff(staff_id)
);

CREATE TABLE satisfaction_surveys (
    survey_id           INT PRIMARY KEY,
    patient_id          INT,
    appointment_id      INT,
    survey_date         DATE,
    specialty           VARCHAR(100),
    overall_score       INT,           -- 1-10
    wait_time_rating    INT,           -- 1-5
    doctor_rating       INT,           -- 1-5
    facility_rating     INT,           -- 1-5
    would_recommend     INT,           -- 1=yes 0=no
    nps_score           INT,           -- Net Promoter Score proxy
    complaint_category  VARCHAR(100),
    FOREIGN KEY (patient_id)      REFERENCES patients(patient_id),
    FOREIGN KEY (appointment_id)  REFERENCES appointments(appointment_id)
);

CREATE TABLE billing_claims (
    claim_id            INT PRIMARY KEY,
    appointment_id      INT,
    patient_id          INT,
    claim_date          DATE,
    claim_type          VARCHAR(30),   -- Medicare | Private_Insurance | Self_Pay
    claimed_amount      DECIMAL(10,2),
    approved_amount     DECIMAL(10,2),
    rejected_amount     DECIMAL(10,2),
    claim_status        VARCHAR(20),   -- approved | rejected | partial | unpaid | paid
    rejection_reason    VARCHAR(100),
    FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id),
    FOREIGN KEY (patient_id)     REFERENCES patients(patient_id)
);

-- Indexes
CREATE INDEX idx_appt_patient_date ON appointments(patient_id, appointment_date);
CREATE INDEX idx_appt_specialty    ON appointments(specialty);
CREATE INDEX idx_appt_status       ON appointments(status);
CREATE INDEX idx_appt_billing      ON appointments(billing_type);
CREATE INDEX idx_survey_patient    ON satisfaction_surveys(patient_id, survey_date);
CREATE INDEX idx_claim_status      ON billing_claims(claim_status);
CREATE INDEX idx_patient_state     ON patients(state);
CREATE INDEX idx_patient_churn     ON patients(churn_flag);
