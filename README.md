# HealthFirst Australia - Revenue Intelligence System

> An end-to-end data analytics project that diagnoses a healthcare network's revenue decline, predicts patient churn, quantifies billing leakage, and delivers prioritised recommendations - built entirely in Python, SQL, and Plotly.

---

## The Business Scenario

**HealthFirst Australia** is a fictional private healthcare network running 20 clinics across all Australian states and territories. In Month 7, the network's revenue dropped 15% with no clear explanation.

The culprit turned out to be a federal government change to the **Medicare bulk billing policy** - reducing incentive payments to doctors who bulk bill. Patients who previously paid nothing were suddenly being asked to pay gap fees. Many cancelled appointments. Others stopped coming altogether.

This project answers three questions leadership needed answered:

1. **Why did revenue drop?** - Root cause decomposition
2. **Which patients are about to leave?** - Machine learning churn prediction
3. **Where is billing money being silently lost?** - Leakage quantification

---

## What I Built - At a Glance

| Component | What It Does |
|---|---|
| Synthetic data generator | Creates 3,000 patients, 20,000 appointments, 80 staff, and billing claims with realistic Australian healthcare patterns |
| 6 Jupyter notebooks | End-to-end pipeline from raw data → cleaned data → KPIs → ML model → segments → leakage |
| ML churn model | Gradient Boosting classifier that scores every patient with a churn probability |
| Recommendations engine | Auto-generates dollar-quantified action items from processed data |
| Interactive dashboard | Plotly/Dash dashboard exported as a self-contained HTML file |
| SQL reference layer | PostgreSQL schema + 12 KPI queries + cleaning queries + analysis queries |
| PDF executive summary | ReportLab-generated PDF guide for stakeholder presentation |

---

## Phase 1 - Problem Framing & Schema Design

**What I did first:** Before writing a single line of Python, I defined the business problem clearly and designed the database schema.

I wrote `01_business_problem.md` to document:
- The exact business scenario (Medicare policy change → bulk billing rate drop → revenue decline)
- Four testable hypotheses covering volume, rate, churn, and leakage
- Success metrics with current vs target values for bulk billing rate, no-show rate, patient churn, wait times, and Medicare claim rejections

I then designed a **5-table PostgreSQL schema** (`sql/schema.sql`) to model the healthcare domain:

```
patients           → demographics, insurance type, churn flag, lifetime value
staff              → specialty, clinic, location, patient rating
appointments       → billing type, wait days, Medicare rebate, patient gap, status
satisfaction_surveys → NPS, overall score, complaint category
billing_claims     → claim type, status, rejection reason, rejected amount
```

Key Australian healthcare fields I had to model explicitly:
- `billing_type` - bulk_bill / gap_payment / private / self_pay
- `patient_gap` - the out-of-pocket amount a patient pays above Medicare rebate
- `medicare_rebate` - government reimbursement (~85% of schedule fee for GP)
- `scheduled_fee` - fee set by the Medicare Benefits Schedule (MBS)

---

## Phase 2 - Synthetic Data Generation

**Why synthetic data?** No public dataset has all five dimensions (patients + appointments + billing + satisfaction surveys + staff) with engineered business scenarios for Australian healthcare. I built it from scratch.

**Script:** `src/generate_data.py`

**What it generates:**

| File | Rows | Key Design Decisions |
|---|---|---|
| `patients.csv` | 3,000 | State weights match ABS population data (NSW 32%, VIC 26%, QLD 20%…) |
| `staff.csv` | 80 | 8 specialties, metro/regional split, realistic rating distributions |
| `appointments.csv` | 20,060 | Includes 60 injected duplicate rows as a data quality issue |
| `satisfaction_surveys.csv` | 3,894 | ~19% survey response rate, realistic NPS distribution |
| `billing_claims.csv` | 11,094 | ~12% rejection rate with real rejection reason categories |

**Australian realism baked in:**
- Health fund market share: Medibank 27%, Bupa 25%, HCF 13%, NIB 9%, HBF 9%, ahm 8%
- Specialty billing rates reflect real MBS schedule fees (GP: $42.85, Mental Health: $131.65, Cardiology: $185.00)
- Month 7 scenario: bulk billing rate × 0.88 and no-show rate +4 percentage points to simulate the policy change

**7 intentional data quality issues injected:**

| # | Issue | Why I Included It |
|---|---|---|
| 1 | NULL `patient_gap` for bulk-billed patients | Bulk bill means no gap - but the field was left blank, not zero |
| 2 | 60 duplicate appointment rows | Simulates a common ETL/export bug |
| 3 | Inconsistent specialty names (`mental health` / `MH` / `Mental_Health`) | Tests string normalisation skill |
| 4 | Survey dates before appointment date | Logically impossible - tests date validation |
| 5 | NULL satisfaction scores (~4% of surveys) | Tests imputation strategy decisions |
| 6 | Invalid Medicare number format (~2% of patients) | Tests format validation without data loss |
| 7 | Non-ISO date strings (`DD/MM/YYYY`) | Tests date parsing robustness |

---

## Phase 3 - Data Cleaning

**Notebook:** `01_data_cleaning.ipynb`  
**Output:** `data/cleaned/` (5 cleaned CSV files)

I audited every table before touching anything, printed null counts, duplicate counts, and value distributions. Then applied fixes in a deliberate order:

- **Fix 1** - `patient_gap` NULLs → filled with 0 (business rule: bulk bill = $0 out-of-pocket)
- **Fix 2** - Dropped 60 exact duplicate appointment rows, kept first occurrence
- **Fix 3** - Standardised specialty names using a lookup map (`SPECIALTY_MAP`) so Mental Health, MH, and Mental_Health all resolve to one canonical value
- **Fix 4** - Imputed NULL `overall_score` with the column median (not mean - bounded 1–10 scale is median-appropriate)
- **Fix 5** - Corrected survey dates that preceded appointment dates → set to `appointment_date + 1 day`
- **Fix 6** - Flagged invalid Medicare numbers with an `invalid_medicare_flag` column instead of dropping records (preserves the audit trail)
- **Fix 7** - Parsed `appointment_date` from `object` → `datetime64` for time-series operations

Produced a before/after quality report chart saved to `reports/data_quality_report.png`.

---

## Phase 4 - KPI Analysis & Root Cause Decomposition

**Notebook:** `02_kpi_analysis.ipynb`  
**SQL reference:** `sql/kpi_queries.sql`

Calculated 12 healthcare KPIs across the 12-month period:

| KPI | Insight |
|---|---|
| Gross Revenue by Billing Type | Bulk bill revenue fell sharply in Month 7 |
| Bulk Billing Rate | Dropped 8 percentage points - the central policy impact |
| Avg Wait Days by Specialty | Mental Health at 18 days, breaching the 14-day SLA |
| No-Show Rate by Specialty | Network average ~17%, target is ≤10% |
| Patient Satisfaction Trend | NPS proxy declined after Month 7 |
| Revenue per Appointment by Specialty | Cardiology and Oncology highest margin |
| Patient Churn by State | WA and QLD showing highest churn rates |
| Medicare Claim Rejection Rate | ~12% rejection rate, target ≤6% |
| Telehealth Adoption | Growing, but underdeveloped in Cardiology |
| Patient Out-of-Pocket Costs | Gap payments increased significantly post Month 7 |
| Staff Utilisation by Clinic | Revenue and rating performance across 20 clinics |
| Referral Source Quality | GP referrals producing highest lifetime value |

**Month 7 Root Cause Decomposition (Bridge/Waterfall Analysis):**

The 15% revenue drop broke down into three effects:
- **Volume Effect (−8%)** - fewer completed appointments due to no-shows and cancellations
- **Rate Effect (−4%)** - lower average billed amount as bulk-billed visits replaced private consultations
- **Mix Effect (−3%)** - shift toward lower-revenue specialties relative to prior months

---

## Phase 5 - Churn Prediction (Machine Learning)

**Notebook:** `03_churn_prediction.ipynb`  
**Module:** `src/churn_model.py`  
**Output:** `data/processed/patients_churn_scored.csv`, `data/processed/retention_priority_list.csv`

**Why I built this:** Retaining an existing patient costs far less than acquiring a new one. The network needed to know *who* was about to leave - not just that churn was high.

**Feature engineering (`build_features`):**

I engineered features from three tables (patients + appointments + surveys):

| Feature | Source | Why It Matters |
|---|---|---|
| `days_since_visit` | appointments | Primary recency signal |
| `appointment_count` | appointments | Frequency |
| `total_billed` | appointments | Value |
| `avg_wait_days` | appointments | Access frustration driver |
| `no_show_rate` | appointments | Disengagement signal |
| `telehealth_rate` | appointments | Preference indicator |
| `avg_overall_score` | surveys | Satisfaction |
| `avg_wait_rating` | surveys | Wait time perception |
| `complaint_count` | surveys | Explicit dissatisfaction |
| `insurance_type` | patients | Gap payers churn faster |
| `state` | patients | Geographic access differences |
| `chronic_conditions` | patients | Care dependency anchor |

**Model choice:** I trained and compared two models:
- **Logistic Regression** via `sklearn.Pipeline` with `StandardScaler` - interpretable baseline
- **Gradient Boosting Classifier** (`n_estimators=150, max_depth=4, learning_rate=0.05`) - primary model

Evaluated with ROC-AUC, Precision-Recall curves, and 5-fold cross-validation.

**Output:** Every patient receives a `churn_probability` (0–1) and a `risk_band`:
- **High** (>0.60) - priority outreach within 7 days
- **Medium** (0.30–0.60) - scheduled follow-up
- **Low** (<0.30) - standard engagement

---

## Phase 6 - Patient Segmentation

**Notebook:** `04_patient_segmentation.ipynb`  
**Output:** `data/processed/patient_segments.csv`

I applied an **RFV framework** (Recency, Frequency, Value) - adapted from retail RFM for healthcare - to group patients into 7 engagement tiers:

| Segment | Profile | Strategy |
|---|---|---|
| Active & Engaged | Recent, frequent, high value | Loyalty rewards, preventive care |
| Chronic Care Patient | Recent, high frequency, medium value | Disease management programs |
| New Patient | Recent, low frequency | Onboarding, follow-up booking |
| Preventive Only | Recent, annual visits, low value | Annual check-up reminders |
| At Risk of Lapsing | 60–90 days inactive, medium value | Personalised phone outreach |
| Disengaged | 90+ days inactive, low value | Re-engagement campaign |
| High Value Occasional | Infrequent but high spend | VIP retention, priority booking |

Each patient is scored 1–4 on R, F, and V independently, then mapped to a segment using business-rule thresholds.

---

## Phase 7 - Specialty Revenue & Profitability

**Notebook:** `05_specialty_revenue.ipynb`  
**Output:** `data/processed/specialty_profitability.csv`, `data/processed/clinic_performance.csv`

Analysed each specialty's P&L:
- Average billed, average staff cost, average margin, and margin percentage
- Bulk billing rate per specialty (some specialties show much greater policy impact than others)
- Wait time vs satisfaction scatter - identifies specialties with long waits *and* low satisfaction (highest churn risk)
- Telehealth adoption trend - Mental Health and GP growing fastest
- Clinic performance ranking across all 20 locations

---

## Phase 8 - Billing Leakage Quantification

**Notebook:** `06_billing_leakage.ipynb`  
**Output:** `data/processed/leakage_summary.csv`, `data/processed/recovery_scenarios.csv`

Identified and quantified revenue leakage across 5 buckets:

| Bucket | Root Cause | Recovery Lever |
|---|---|---|
| Medicare claim rejections | Coding errors, eligibility issues | Claim audits, staff training |
| Private insurance rejections | Missing documentation | Pre-authorisation workflow |
| No-show lost revenue | Patients not cancelling in advance | SMS reminders, cancellation policy |
| Self-pay defaults | Gap fees going unpaid | Payment plans, upfront collection |
| Bulk billing erosion | Policy-driven shift from bulk bill | Advocacy, billing type review |

Modelled three recovery scenarios (20% / 50% / 75% fix rate) to give management a realistic range of recoverable value.

---

## Phase 9 - Automated Recommendations

**Script:** `src/recommendations.py`  
**Output:** `reports/recommendations.csv`, `reports/recommendations.json`

Reads from all processed CSVs and auto-generates prioritised recommendations across 5 categories:

1. **Churn Prevention** - flags high-risk patients (churn score >0.60), estimates AUD retained at 30% save rate
2. **Bulk Billing Optimisation** - detects specialties where rate dropped >5% from prior 3-month average
3. **Wait Time SLA Breaches** - checks against SLAs (GP ≤7 days, Mental Health ≤14 days, Cardiology ≤21 days)
4. **No-Show Reduction** - estimates annual revenue recovery from reducing no-show rate to 10% benchmark
5. **Medicare Claim Recovery** - flags leakage buckets >$10,000 and calculates 50% recovery scenarios

Each recommendation includes a priority (High / Medium / Low) and an estimated AUD impact.

---

## Phase 10 - Interactive Dashboard

**Script:** `dashboard/app.py`  
**Output:** `dashboard/dashboard_export.html`

Built with **Plotly and Dash**, exported as a fully self-contained HTML file that opens in any browser with no server required.

**8 dashboard sections:**
1. **KPI Cards** - Total Revenue, Completed Appointments, Bulk Billing Rate, Avg Wait Days, Patient Churn Rate, No-Show Rate
2. **Revenue Trend & Bulk Billing Rate** - Stacked area chart by billing type + line chart overlay
3. **Wait Times by Specialty** - Horizontal bar chart colour-coded against SLA benchmarks
4. **Patient Satisfaction Trend** - Overall score + recommend rate over time
5. **Specialty Profitability** - Margin bar chart + total revenue bar chart
6. **Churn by State** - Geographic churn rate breakdown across Australian states
7. **Patient Segments** - Treemap showing segment size and revenue share
8. **Claim Rejection Analysis** - Monthly rejection rate trend by claim type

---

## Tech Stack

| Tool | Purpose |
|---|---|
| **Python 3.12** | Core language |
| **Pandas** | Data cleaning, transformation, aggregation |
| **NumPy** | Numerical operations |
| **scikit-learn** | ML pipeline - Gradient Boosting, Logistic Regression, cross-validation, ROC-AUC |
| **Plotly / Dash** | Interactive dashboard + static HTML export |
| **Matplotlib / Seaborn** | Static charts in notebooks and PDF |
| **ReportLab** | PDF executive summary generation |
| **PostgreSQL / SQL** | Schema design, KPI queries, cleaning queries, analysis queries |
| **Jupyter Notebooks** | Reproducible step-by-step analysis pipeline |

---

## How to Run It

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate raw data
python src/generate_data.py

# 3. Run notebooks in order
jupyter nbconvert --to notebook --execute --inplace notebooks/01_data_cleaning.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/02_kpi_analysis.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/03_churn_prediction.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/04_patient_segmentation.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/05_specialty_revenue.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/06_billing_leakage.ipynb

# 4. Generate recommendations
python src/recommendations.py

# 5. Open dashboard (no server needed)
open dashboard/dashboard_export.html
```

---

## Project Structure

```
revenue-intelligence/
│
├── src/
│   ├── generate_data.py          # Synthetic data generator
│   ├── churn_model.py            # Reusable ML module (build, train, score, explain)
│   └── recommendations.py        # Auto-generates dollar-quantified action items
│
├── notebooks/
│   ├── 01_data_cleaning.ipynb    # Fix 7 data quality issues
│   ├── 02_kpi_analysis.ipynb     # 12 KPIs + Month 7 root cause waterfall
│   ├── 03_churn_prediction.ipynb # Gradient Boosting churn model
│   ├── 04_patient_segmentation.ipynb  # RFV segmentation - 7 patient tiers
│   ├── 05_specialty_revenue.ipynb     # Specialty P&L and clinic performance
│   └── 06_billing_leakage.ipynb       # 5-bucket leakage + recovery scenarios
│
├── dashboard/
│   ├── app.py                    # Plotly/Dash app
│   └── dashboard_export.html     # Self-contained dashboard (open in browser)
│
├── sql/
│   ├── schema.sql                # 5-table PostgreSQL schema
│   ├── cleaning_queries.sql      # Audit + fix queries for all 7 data issues
│   ├── kpi_queries.sql           # 12 KPI queries
│   └── analysis_queries.sql      # Root cause, churn features, leakage analysis
│
├── data/
│   ├── raw/                      # 5 generated CSV files
│   ├── cleaned/                  # After notebook 01
│   └── processed/                # After notebooks 03–06
│
├── reports/
│   ├── recommendations.csv       # Auto-generated action items
│   ├── recommendations.json
│   ├── executive_summary.md
│   └── HealthFirst_Revenue_Intelligence_Guide.pdf
│
├── 01_business_problem.md        # Problem framing and hypotheses
├── 02_metrics_dictionary.md      # Definitions for all 16 KPIs
└── README.md
```

---

## Australian Healthcare Context

| Term | What It Means |
|---|---|
| **Bulk billing** | Doctor bills Medicare directly - patient pays nothing out-of-pocket |
| **Gap payment** | Patient pays the difference between billed amount and Medicare rebate |
| **Medicare rebate** | Federal government reimbursement (~85% of MBS schedule fee for GP) |
| **MBS** | Medicare Benefits Schedule - the federal fee schedule for all medical services |
| **Health fund** | Private health insurer (Medibank, Bupa, HCF, NIB, HBF, ahm, etc.) |
| **Bulk billing rate** | % of consultations bulk billed - the primary access equity and policy metric |
| **Churn flag** | Patient inactive for 90+ days, assumed to have switched providers |
