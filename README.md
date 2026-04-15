# 🏥 HealthFirst Australia — Revenue Intelligence System

<div align="center">

**An end-to-end healthcare data analytics portfolio project**

*Diagnosing a 15% revenue decline · Predicting patient churn · Quantifying billing leakage · Delivering actionable recommendations*

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-orange?style=flat-square&logo=jupyter)
![Plotly](https://img.shields.io/badge/Plotly-Dashboard-3D4DB7?style=flat-square&logo=plotly)
![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-F7931E?style=flat-square&logo=scikit-learn)

</div>

---

## 📖 The Story

> *It's Month 7. The CFO of HealthFirst Australia walks in with a report showing a **−15% revenue drop**. No one knows why. Appointments are down. Patients aren't coming back. Bulk billing has collapsed.*
>
> *This project is the data team's response.*

We built a full analytics system from scratch — generating realistic patient data, cleaning it, analysing it, predicting which patients are at risk of leaving, finding where money is being lost, and presenting everything in a live interactive dashboard.

---

## 🎯 Business Questions Answered

| # | Question | How We Answer It |
|---|----------|-----------------|
| 1 | Why did revenue drop in Month 7? | KPI decomposition + waterfall chart |
| 2 | Which patients are about to leave? | Gradient Boosting churn model |
| 3 | Which patient groups matter most? | RFV segmentation (7 tiers) |
| 4 | Which specialties are most profitable? | Specialty P&L analysis |
| 5 | Where is billing money being lost? | 5-bucket leakage analysis |
| 6 | What should we do about it? | Dollar-quantified recommendations |

---

## 🗂️ Project Structure

```
revenue-intelligence/
│
├── 📁 data/
│   ├── raw/              ← Original synthetic data (never modified)
│   ├── cleaned/          ← Data after fixing 7 quality issues
│   └── processed/        ← Scored, segmented, analysis-ready data
│
├── 📓 notebooks/         ← Run in order: 01 → 06
│   ├── 01_data_cleaning.ipynb
│   ├── 02_kpi_analysis.ipynb
│   ├── 03_churn_prediction.ipynb
│   ├── 04_patient_segmentation.ipynb
│   ├── 05_specialty_revenue.ipynb
│   └── 06_billing_leakage.ipynb
│
├── 🐍 src/
│   ├── generate_data.py
│   ├── churn_model.py
│   └── recommendations.py
│
├── 📊 dashboard/
│   ├── app.py
│   └── dashboard_export.html
│
├── 📄 reports/
└── 🗄️ sql/
```

---

## 🔄 Data Flow

```
src/generate_data.py
        ↓
   data/raw/
        ↓
01_data_cleaning.ipynb
        ↓
   data/cleaned/
        ↓
02 → 06 notebooks
        ↓
   data/processed/
        ↓
dashboard/app.py  +  src/recommendations.py
        ↓
   dashboard_export.html  +  reports/recommendations.csv
```

---

## 🚀 How to Run

**Step 1 — Install dependencies**
```bash
pip install -r requirements.txt
```

**Step 2 — Generate synthetic data**
```bash
python src/generate_data.py
```

**Step 3 — Run notebooks in order**
```bash
jupyter notebook
```
Open and run each notebook from `01_data_cleaning` through to `06_billing_leakage`.

**Step 4 — View the dashboard**
```bash
open dashboard/dashboard_export.html
```

**Step 5 — Generate recommendations**
```bash
python src/recommendations.py
```

---

## 🧠 Machine Learning — Churn Model

The churn model in `src/churn_model.py` uses a **Gradient Boosting classifier** to predict the probability that each patient will stop visiting.

**Top predictors:**
- Days since last visit
- No-show rate
- Average satisfaction score
- Insurance type
- Average wait days

**Output:** Each patient gets a `churn_probability` score and a `risk_band` (Low / Medium / High).

---

## 💸 Billing Leakage — 5 Buckets

| Bucket | What It Means |
|--------|--------------|
| Medicare rejections | Claims rejected by Medicare due to errors or eligibility issues |
| Private insurance rejections | Claims rejected by private health funds |
| No-show lost revenue | Appointments missed with no cancellation notice |
| Self-pay defaults | Patients who owe gap fees but haven't paid |
| Bulk billing rate erosion | Revenue lost from shifting away from bulk billing |

---

## 🏥 Australian Healthcare — Key Terms

| Term | Simple Explanation |
|------|--------------------|
| **Bulk billing** | Doctor bills Medicare directly — patient pays $0 out of pocket |
| **Gap payment** | Patient pays the difference between the doctor's fee and Medicare rebate |
| **Medicare** | Australia's universal government health insurance scheme |
| **Schedule fee** | The standard government-set fee for each type of appointment |
| **Health fund** | Private health insurer (Medibank, Bupa, HCF, NIB, etc.) |
| **Churn** | A patient who stops returning to the clinic |
| **RFV** | Recency (last visit), Frequency (how often), Value (how much spent) |
| **NPS** | Net Promoter Score — likelihood of recommending the clinic to others |

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| Python | Core language |
| Pandas | Data cleaning & analysis |
| scikit-learn | Machine learning pipeline |
| XGBoost | Gradient boosting classifier |
| Plotly / Dash | Interactive dashboard |
| Matplotlib | Static chart generation |
| PostgreSQL | Schema design & query reference |
| Jupyter | Step-by-step analysis notebooks |

---

## 📋 Data Summary

| Table | Rows | Key Fields |
|-------|------|-----------|
| patients | 3,000 | state, insurance_type, churn_flag, total_billed |
| staff | 80 | specialty, clinic_name, state, clinic_type |
| appointments | ~20,000 | billing_type, status, wait_days, billed_amount |
| satisfaction_surveys | ~3,900 | overall_score, nps_score, would_recommend |
| billing_claims | ~11,000 | claim_type, claim_status, rejected_amount |

---

## 🔍 7 Intentional Data Quality Issues

| # | Issue | Impact |
|---|-------|--------|
| 1 | NULL `patient_gap` for bulk-billed patients | Breaks revenue calculations |
| 2 | 60 duplicate appointment rows | Inflates appointment counts |
| 3 | Inconsistent specialty names | Breaks grouping & aggregation |
| 4 | Survey dates before appointment date | Logically impossible timestamps |
| 5 | NULL satisfaction scores (~4%) | Skews average scores |
| 6 | Invalid Medicare number format (~2%) | Fails claim validation |
| 7 | Non-standard date format (`DD/MM/YYYY`) | Breaks date parsing |

---

## 📁 SQL Reference

| File | Contents |
|------|---------|
| `schema.sql` | 5-table database schema with indexes |
| `cleaning_queries.sql` | Audit + fix queries for all 7 data issues |
| `kpi_queries.sql` | 12 KPI calculation queries |
| `analysis_queries.sql` | Root cause, churn features, leakage analysis |

---

<div align="center">

*Built with Python & Plotly · Synthetic data only · No real patient information used*

**[View Repository](https://github.com/SahanaRamamurthy/Healthcare-Revenue-Analytics)**

</div>
