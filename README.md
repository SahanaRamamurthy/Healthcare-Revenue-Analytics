# HealthFirst Australia — Revenue Intelligence System

## Overview

HealthFirst Australia is a fictional private healthcare network operating 8 clinics across Australia. In Month 7, the network reported a **sudden 15% revenue decline** — and no one knew why.

This project simulates exactly what a data analyst would do in that situation:
- Dig into the data to find the root cause
- Build a model to predict which patients are about to leave
- Identify where billing money is silently being lost
- Package everything into a dashboard that any stakeholder can understand

Everything here — data, clinics, patients, appointments — is **synthetic (fake but realistic)**. The analysis, methodology, and business thinking are real.


## The Business Problem

In Month 7, the Australian federal government changed its **Medicare bulk billing policy** — reducing incentive payments to doctors who bulk bill. As a result:

| Metric | Change |
|--------|--------|
| Total Revenue | **−15%** |
| Bulk Billing Rate | **−8 percentage points** |
| No-Show Rate | **+4 percentage points** |
| Patient Satisfaction | Declining |

Patients who previously paid nothing out-of-pocket were now asked to pay **gap fees**. Many responded by cancelling appointments, switching clinics, or avoiding care altogether.


---

## Analytical Approach

The project follows a structured, end-to-end analytical workflow:

```
1. Generate Data       → Simulate 3,000 patients, 20,000 appointments, 8 clinics
2. Clean Data          → Fix 7 real-world data quality problems
3. Analyse KPIs        → Measure 12 healthcare metrics, decompose the revenue drop
4. Predict Churn       → Machine learning model to flag at-risk patients
5. Segment Patients    → Group patients by behaviour to personalise retention
6. Find Leakage        → Identify and quantify 5 types of billing losses
7. Recommend Actions   → Prioritise fixes by dollar impact
8. Visualise           → Interactive dashboard for stakeholders
```

---

## Key Findings

**Root Cause of Revenue Drop:**
The Month 7 decline breaks down into three effects:
- **Volume Effect (−8%)** — fewer patients showing up
- **Rate Effect (−4%)** — lower revenue per appointment as bulk billing fell
- **Mix Effect (−3%)** — shift toward lower-revenue appointment types

**Churn Prediction:**
The machine learning model identified that patients most at risk of churning share these traits:
- Haven't visited in 60+ days
- Had a no-show in the last 3 months
- Rated overall satisfaction below 6/10
- Paying gap fees (not bulk billed)

**Billing Leakage:**
Across 5 leakage buckets, the analysis found recoverable revenue through:
- Fixing Medicare claim rejections
- Reducing no-show rates with SMS reminders
- Recovering self-pay defaults through payment plans
- Stabilising the bulk billing rate in high-gap-fee states

---

## Project Architecture

```
src/generate_data.py
        ↓
   data/raw/               ← 5 CSV files (patients, appointments, staff, surveys, claims)
        ↓
01_data_cleaning.ipynb     ← Fix 7 data quality issues
        ↓
   data/cleaned/
        ↓
02_kpi_analysis.ipynb      ← 12 KPIs + Month 7 root cause decomposition
03_churn_prediction.ipynb  ← Gradient Boosting churn model
04_patient_segmentation.ipynb ← RFV segmentation into 7 patient tiers
05_specialty_revenue.ipynb ← Specialty P&L and margin analysis
06_billing_leakage.ipynb   ← 5-bucket leakage + recovery scenarios
        ↓
   data/processed/
        ↓
src/recommendations.py     ← Prioritised, dollar-quantified action list
dashboard/app.py           ← Interactive Plotly dashboard
        ↓
dashboard_export.html      ← Self-contained, opens in any browser
```

---

## Tech Stack

| Tool | Why I Used It |
|------|--------------|
| **Python** | Core language for all data work |
| **Pandas** | Data cleaning, transformation, and aggregation |
| **NumPy** | Numerical computations |
| **scikit-learn** | Machine learning pipeline — churn model training and evaluation |
| **XGBoost** | Gradient Boosting classifier for churn prediction |
| **Plotly / Dash** | Interactive, professional-grade dashboard |
| **Matplotlib** | Static charts for reports and PDF export |
| **PostgreSQL + SQL** | Relational schema design and analytical query reference |
| **Jupyter Notebooks** | Structured, reproducible step-by-step analysis |
| **ReportLab** | PDF executive summary generation |

---

## Notebooks — What Each One Does

| Notebook | What I Did | Business Output |
|----------|-----------|----------------|
| `01_data_cleaning` | Found and fixed 7 data quality issues | Trustworthy, analysis-ready data |
| `02_kpi_analysis` | Calculated 12 healthcare KPIs, decomposed the Month 7 revenue drop | Clear root cause with dollar values |
| `03_churn_prediction` | Trained a Gradient Boosting model, evaluated with ROC-AUC | Churn probability score per patient |
| `04_patient_segmentation` | Applied RFV scoring, created 7 patient engagement tiers | Targeted retention strategy per segment |
| `05_specialty_revenue` | Analysed P&L and margin per specialty, tracked telehealth growth | Which specialties to invest in |
| `06_billing_leakage` | Quantified 5 leakage buckets, modelled 3 recovery scenarios | Dollar value of recoverable revenue |

---

## Machine Learning — Churn Model

**Why:** Retaining an existing patient costs far less than acquiring a new one. Knowing *who* is about to leave allows the clinic to intervene before it's too late.

**How:** A Gradient Boosting classifier is trained on patient behaviour features and outputs a churn probability score for every patient.

**Top predictors of churn:**
- Days since last visit
- No-show rate
- Average satisfaction score
- Insurance type (gap payers churn faster)
- Average wait days

**Output:** Each patient gets a `churn_probability` and a `risk_band` — Low / Medium / High — enabling the retention team to prioritise outreach.

---

## Billing Leakage — 5 Buckets

**Why:** Revenue isn't only lost when patients don't show up — it's also lost silently through billing errors, rejected claims, and unpaid fees.

| Bucket | Root Cause | Recovery Lever |
|--------|-----------|---------------|
| Medicare claim rejections | Coding errors, eligibility issues | Staff training, claim audits |
| Private insurance rejections | Missing documentation | Pre-authorisation checks |
| No-show lost revenue | Patients not cancelling | SMS reminders, cancellation policy |
| Self-pay defaults | Gap fees going unpaid | Payment plans, upfront collection |
| Bulk billing erosion | Policy-driven shift | Advocate for bulk billing incentives |

---

## 7 Data Quality Issues Fixed

Real healthcare data is messy. This project intentionally includes 7 realistic problems:

| # | Issue | Why It Matters |
|---|-------|---------------|
| 1 | NULL gap fees for bulk-billed patients | Breaks revenue calculations |
| 2 | 60 duplicate appointment rows | Inflates all appointment-based metrics |
| 3 | Inconsistent specialty names | Breaks grouping — `mental health` ≠ `MH` ≠ `Mental_Health` |
| 4 | Survey dates before appointment date | Logically impossible — signals data entry errors |
| 5 | NULL satisfaction scores (~4%) | Skews satisfaction averages downward |
| 6 | Invalid Medicare numbers (~2%) | Would fail real claim submissions |
| 7 | Non-standard date format (`DD/MM/YYYY`) | Breaks all date-based time series analysis |

---

## Australian Healthcare Context

| Term | What It Means |
|------|--------------|
| **Bulk billing** | Doctor bills Medicare directly — patient pays $0 |
| **Gap payment** | Patient pays the difference between doctor's fee and Medicare rebate |
| **Medicare** | Australia's universal public health insurance |
| **Schedule fee** | Government-set standard fee per appointment type |
| **Health fund** | Private insurer — Medibank, Bupa, HCF, NIB, etc. |
| **Churn** | A patient who stops returning to the clinic |
| **RFV** | Recency, Frequency, Value — a classic customer segmentation method |
| **NPS** | Net Promoter Score — "would you recommend us?" |

---

## How to Run

```bash
# Install dependencies
pip install -r requirements.txt

# Generate synthetic data
python src/generate_data.py

# Run notebooks in order (01 → 06)
jupyter notebook

# Open the dashboard (no server needed)
open dashboard/dashboard_export.html

# Generate recommendations report
python src/recommendations.py
```

---

## Future Improvements

- Connect to a live PostgreSQL database instead of flat CSV files
- Deploy the dashboard on AWS / Azure / GCP
- Automate the notebook pipeline with Apache Airflow
- Add real-time patient churn alerts via email or SMS
- Integrate with real Medicare Benefits Schedule (MBS) data
- Add authentication and role-based access to the dashboard

---

## Key Learnings

- How to structure an end-to-end analytics project like a real data team
- Translating business problems into analytical questions
- Handling messy, real-world data quality issues systematically
- Building, evaluating, and interpreting a machine learning churn model
- Quantifying business impact in dollar terms — not just charts
- Understanding Australian healthcare domain concepts
- Building stakeholder-ready dashboards with Plotly

---

## Author

**Sahana Ramamurthy**
Master of Data Science
 **Connect:**
- LinkedIn: https://www.linkedin.com/in/sahana-ramamurthy-9640b51a5/
- GitHub: https://github.com/SahanaRamamurthy

---

*Built with Python & Plotly · Synthetic data only · No real patient information used*
