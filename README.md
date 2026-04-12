# HealthFirst Australia — Revenue Intelligence System

> **End-to-end data analytics portfolio project** — diagnosing a healthcare network's revenue decline, predicting patient churn, quantifying billing leakage, and delivering actionable clinical and operational recommendations.

---

## Project Overview

HealthFirst Australia operates 20 clinics across all Australian states and territories. In Month 7 of this analysis, the network experienced a −15% revenue drop, an −8 percentage point fall in bulk billing rate, and a +4 percentage point rise in no-shows — driven by a Medicare policy change and growing patient out-of-pocket costs.

This project:
1. Generates realistic synthetic healthcare data (patients, appointments, billing claims, satisfaction surveys)
2. Cleans and audits 7 intentional data quality issues
3. Calculates 12 Australian healthcare KPIs
4. Predicts patient churn using machine learning
5. Segments patients by engagement using RFV scoring
6. Quantifies billing leakage across 5 buckets
7. Delivers dollar-quantified recovery recommendations
8. Presents everything in an interactive Plotly dashboard

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Generate synthetic healthcare data
python src/generate_data.py

# Run all notebooks in order
jupyter nbconvert --to notebook --execute notebooks/01_data_cleaning.ipynb --output notebooks/01_data_cleaning.ipynb
jupyter nbconvert --to notebook --execute notebooks/02_kpi_analysis.ipynb --output notebooks/02_kpi_analysis.ipynb
jupyter nbconvert --to notebook --execute notebooks/03_churn_prediction.ipynb --output notebooks/03_churn_prediction.ipynb
jupyter nbconvert --to notebook --execute notebooks/04_patient_segmentation.ipynb --output notebooks/04_patient_segmentation.ipynb
jupyter nbconvert --to notebook --execute notebooks/05_specialty_revenue.ipynb --output notebooks/05_specialty_revenue.ipynb
jupyter nbconvert --to notebook --execute notebooks/06_billing_leakage.ipynb --output notebooks/06_billing_leakage.ipynb

# Generate recommendations report
python src/recommendations.py

# Open dashboard (no server needed)
open dashboard/dashboard_export.html

# OR run live Dash server
python dashboard/app.py
```

---

## Architecture

### Data Flow

```
data/raw/          →  data/cleaned/      →  data/processed/    →  reports/ + dashboard/
(5 CSV files)          (cleaned CSVs)        (scored, segmented)
```

### Notebooks (run in order)

| Notebook | Purpose | Key Outputs |
|---|---|---|
| `01_data_cleaning.ipynb` | Fix 7 data quality issues | `data/cleaned/*.csv`, `reports/data_quality_report.png` |
| `02_kpi_analysis.ipynb` | 12 healthcare KPIs + Month 7 RCA | `reports/revenue_trend.png`, `rca_waterfall.png` |
| `03_churn_prediction.ipynb` | ML churn model (Gradient Boosting) | `data/processed/patients_churn_scored.csv` |
| `04_patient_segmentation.ipynb` | RFV segmentation (7 segments) | `data/processed/patient_segments.csv` |
| `05_specialty_revenue.ipynb` | Specialty P&L + telehealth trend | `data/processed/specialty_profitability.csv` |
| `06_billing_leakage.ipynb` | 5-bucket leakage + recovery scenarios | `data/processed/leakage_summary.csv` |

### Key Source Files

| File | Purpose |
|---|---|
| `src/generate_data.py` | Generates all 5 synthetic raw CSV files |
| `src/churn_model.py` | Reusable ML module: build_features, train_model, score_customers |
| `src/recommendations.py` | Reads processed data → outputs recommendations.csv + .json |
| `dashboard/app.py` | Plotly/Dash dashboard with static HTML export |
| `sql/schema.sql` | 5-table PostgreSQL schema |
| `sql/cleaning_queries.sql` | Audit + fix queries for all 7 data issues |
| `sql/kpi_queries.sql` | 12 KPI queries |
| `sql/analysis_queries.sql` | Root cause, churn features, leakage analysis |

---

## Australian Healthcare Context

| Term | Meaning |
|---|---|
| **Bulk billing** | Doctor bills Medicare directly; patient pays nothing out-of-pocket |
| **Gap payment** | Patient pays the difference between scheduled fee and Medicare rebate |
| **Schedule fee** | Medicare Benefits Schedule (MBS) fee set by the federal government |
| **Medicare rebate** | Government reimbursement (typically 85% of schedule fee for GP) |
| **Health fund** | Private health insurer (Medibank, Bupa, HCF, NIB, HBF, ahm, etc.) |
| **Bulk billing rate** | % of consultations billed under bulk billing — key policy metric |

---

## Data Summary

| Table | Rows | Key Fields |
|---|---|---|
| patients | 3,000 | state, insurance_type, churn_flag, total_billed |
| staff | 80 | specialty, clinic_name, state, clinic_type |
| appointments | ~20,000 | billing_type, status, wait_days, billed_amount, patient_gap |
| satisfaction_surveys | ~3,900 | overall_score, nps_score, would_recommend |
| billing_claims | ~11,000 | claim_type, claim_status, rejected_amount |

---

## 7 Intentional Data Quality Issues

1. NULL `patient_gap` values (bulk-billed patients)
2. 60 duplicate appointment rows
3. Inconsistent specialty names (`mental health` / `MH` / `Mental_Health`)
4. Survey dates before appointment date (impossible)
5. NULL satisfaction scores (~4% of surveys)
6. Invalid Medicare number format (~2% of patients)
7. Non-ISO appointment date strings (`DD/MM/YYYY` format)
