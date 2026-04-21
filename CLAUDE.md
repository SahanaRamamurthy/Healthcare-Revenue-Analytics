# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **HealthFirst Australia — Revenue Intelligence** — an end-to-end data analytics, for a fictional Australian private healthcare network. It diagnoses a revenue decline driven by a Medicare bulk billing policy change, predicts patient churn, quantifies billing leakage, and delivers actionable clinical and operational recommendations.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Generate/regenerate synthetic raw data (3k patients, ~20k appointments)
python src/generate_data.py

# Run notebooks in order (each notebook chains its output into the next)
jupyter notebook

# Regenerate recommendations report → reports/recommendations.csv + .json
python src/recommendations.py

# Open the pre-built interactive dashboard (no server needed)
open dashboard/dashboard_export.html

# Run the live Dash server (optional)
python dashboard/app.py
```

## Architecture

### Data Flow

Raw data (`data/raw/`) → cleaned data (`data/cleaned/`) → processed/scored data (`data/processed/`) → reports + dashboard.

The notebooks run in sequence and each one writes its outputs to `data/processed/` or `reports/` for use by subsequent notebooks:

1. `01_data_cleaning.ipynb` — fixes 7 data quality issues, writes `data/cleaned/`
2. `02_kpi_analysis.ipynb` — calculates 12 healthcare KPIs, decomposes Month 7 revenue drop
3. `03_churn_prediction.ipynb` — uses `src/churn_model.py`, writes `data/processed/patients_churn_scored.csv` and `data/processed/retention_priority_list.csv`
4. `04_patient_segmentation.ipynb` — RFV segmentation, writes `data/processed/patient_segments.csv`
5. `05_specialty_revenue.ipynb` — specialty P&L, writes `data/processed/specialty_profitability.csv` and `data/processed/clinic_performance.csv`
6. `06_billing_leakage.ipynb` — 5-bucket leakage analysis, writes `data/processed/leakage_summary.csv` and `data/processed/recovery_scenarios.csv`

### `src/churn_model.py` — Reusable ML Module

Four public functions:
- `build_features(patients, appointments, surveys)` — engineers RFV + satisfaction features, one-hot encodes insurance_type, state, chronic_conditions
- `train_model(features, model_type='xgboost')` — trains Gradient Boosting (default) or Logistic Regression via sklearn Pipeline; returns dict with `model`, `X_test`, `y_test`, `feature_names`, `metrics`
- `score_customers(features, model)` — returns scored DataFrame with `churn_probability` and `risk_band` (Low/Medium/High)
- `get_feature_importance(result, top_n=15)` — extracts feature importances from the returned model dict

### `src/recommendations.py`

Reads from `data/processed/` and `data/cleaned/` CSVs. Generates 5 categories of recommendations (churn prevention, bulk billing optimisation, wait time SLA breaches, no-show reduction, Medicare claim recovery). Saves to `reports/recommendations.csv` and `reports/recommendations.json`.

### `dashboard/app.py`

Plotly/Dash app. Reads from `data/processed/` CSVs. Can be run as a live Dash server or exported to `dashboard/dashboard_export.html` (self-contained, opens in any browser without a server).

### SQL

`sql/` contains standalone SQL files (not executed by any Python script — intended for reference/portfolio):
- `schema.sql` — 5-table PostgreSQL schema with indexes
- `cleaning_queries.sql` — audit + fix queries for all 7 data quality issues
- `kpi_queries.sql` — 12 KPI queries
- `analysis_queries.sql` — root cause analysis, churn features, leakage analysis

## Key Domain Concepts

- **Bulk billing**: Medicare direct billing — patient pays nothing out-of-pocket; ~80% national GP average
- **Gap payment**: Patient pays difference between scheduled fee and Medicare rebate
- **RFV Segmentation**: Recency / Frequency / Value — 7 patient tiers (Active & Engaged, Chronic Care, New Patient, Preventive Only, At Risk of Lapsing, Disengaged, High Value Occasional)
- **Churn flag**: binary target in `patients_cleaned.csv`; churn model uses days_since_visit, no_show_rate, avg_overall_score, insurance_type, and wait_days as top predictors
- **Billing leakage buckets**: Medicare rejections, private insurance rejections, no-show lost revenue, self-pay defaults, bulk billing rate erosion
- **Month 7 drop decomposition**: Volume Effect (−8%) + Rate Effect (−4%) + Mix Effect (−3%)
- **State population weights**: NSW 32%, VIC 26%, QLD 20%, WA 10%, SA 7%, TAS 2%, ACT 2%, NT 1%
