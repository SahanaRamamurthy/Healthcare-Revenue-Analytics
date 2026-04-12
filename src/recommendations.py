"""
recommendations.py
==================
Recommendations engine for HealthFirst Australia.

Reads processed and cleaned datasets and generates five categories of
prioritised, dollar-quantified clinical and operational recommendations.

Output:
  - Formatted table printed to console
  - reports/recommendations.csv
  - reports/recommendations.json
"""

import json
import os

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Directory paths
# ---------------------------------------------------------------------------
BASE_DIR  = os.path.join(os.path.dirname(__file__), '..')
PROC_DIR  = os.path.join(BASE_DIR, 'data', 'processed')
CLEAN_DIR = os.path.join(BASE_DIR, 'data', 'cleaned')
RPT_DIR   = os.path.join(BASE_DIR, 'reports')

# ---------------------------------------------------------------------------
# SLA thresholds (days) by specialty
# ---------------------------------------------------------------------------
WAIT_TIME_SLAS = {
    'GP':             7,
    'Mental Health': 14,
    'Cardiology':    21,
}
DEFAULT_WAIT_SLA = 14  # all other specialties

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data() -> dict:
    """Load all datasets required for the recommendations engine."""
    files = {
        # processed
        'churn_scored':          (PROC_DIR,  'patients_churn_scored.csv'),
        'patient_segments':      (PROC_DIR,  'patient_segments.csv'),
        'specialty_profitability': (PROC_DIR, 'specialty_profitability.csv'),
        'leakage':               (PROC_DIR,  'leakage_summary.csv'),
        # cleaned
        'appointments':          (CLEAN_DIR, 'appointments_cleaned.csv'),
        'patients':              (CLEAN_DIR, 'patients_cleaned.csv'),
        'billing':               (CLEAN_DIR, 'billing_claims_cleaned.csv'),
    }
    data = {}
    for key, (directory, fname) in files.items():
        path = os.path.join(directory, fname)
        if os.path.exists(path):
            data[key] = pd.read_csv(path)
        else:
            data[key] = pd.DataFrame()
    return data


# ---------------------------------------------------------------------------
# Category 1: Churn Prevention
# ---------------------------------------------------------------------------

def _churn_prevention(churn_df: pd.DataFrame) -> list[dict]:
    recs = []
    if churn_df.empty:
        return recs

    # Normalise column names to lowercase
    churn_df = churn_df.copy()
    churn_df.columns = [c.lower().strip() for c in churn_df.columns]

    risk_col = next(
        (c for c in churn_df.columns if 'churn_risk' in c or 'churn_prob' in c or 'churn_score' in c),
        None,
    )
    ltv_col = next(
        (c for c in churn_df.columns if 'lifetime_value' in c or 'ltv' in c or 'avg_lifetime' in c),
        None,
    )

    if risk_col is None:
        return recs

    high_risk = churn_df[churn_df[risk_col] > 0.6].copy()
    if high_risk.empty:
        return recs

    # Sort by LTV descending when available
    if ltv_col and ltv_col in high_risk.columns:
        high_risk = high_risk.sort_values(ltv_col, ascending=False)
        avg_ltv = high_risk[ltv_col].mean()
        total_ltv_at_risk = high_risk[ltv_col].sum()
        ltv_str = f"${avg_ltv:,.0f}"
        impact = f"${total_ltv_at_risk * 0.30:,.0f} AUD retained (est. 30% save rate)"
        current_val = f"{len(high_risk)} high-risk patients, avg LTV {ltv_str}"
        estimated_impact = total_ltv_at_risk * 0.30
    else:
        current_val = f"{len(high_risk)} high-risk patients (churn score > 0.60)"
        impact = "Revenue retention subject to LTV data availability"
        estimated_impact = 0.0

    avg_score = high_risk[risk_col].mean()

    recs.append({
        'category':            'Churn Prevention',
        'priority':            'High',
        'metric':              'High-Risk Patient Count (churn score > 0.60)',
        'current_value':       current_val,
        'target_value':        'Churn score < 0.40 after intervention',
        'action':              f'Schedule outreach call within 7 days for {len(high_risk):,} high-risk patients — prioritise by lifetime value',
        'estimated_impact_aud': round(estimated_impact, 2),
    })

    return recs


# ---------------------------------------------------------------------------
# Category 2: Bulk Billing Optimisation
# ---------------------------------------------------------------------------

def _bulk_billing_optimisation(billing_df: pd.DataFrame,
                                appointments_df: pd.DataFrame) -> list[dict]:
    recs = []

    # Try to derive bulk billing rate from billing claims
    if not billing_df.empty:
        billing_df = billing_df.copy()
        billing_df.columns = [c.lower().strip() for c in billing_df.columns]

        specialty_col = next(
            (c for c in billing_df.columns if 'specialty' in c or 'department' in c), None
        )
        bulk_col = next(
            (c for c in billing_df.columns if 'bulk_bill' in c or 'billing_type' in c or 'bulk' in c), None
        )
        date_col = next(
            (c for c in billing_df.columns if 'date' in c or 'claim_date' in c or 'service_date' in c), None
        )

        if specialty_col and bulk_col:
            if date_col:
                billing_df[date_col] = pd.to_datetime(billing_df[date_col], errors='coerce')
                billing_df = billing_df.dropna(subset=[date_col])
                max_date = billing_df[date_col].max()
                cutoff_recent = max_date - pd.DateOffset(months=1)
                cutoff_prior  = max_date - pd.DateOffset(months=4)

                recent = billing_df[billing_df[date_col] >= cutoff_recent]
                prior  = billing_df[
                    (billing_df[date_col] >= cutoff_prior) &
                    (billing_df[date_col] < cutoff_recent)
                ]

                def bulk_rate(df):
                    if df.empty:
                        return pd.Series(dtype=float)
                    col = df[bulk_col]
                    if col.dtype == object:
                        is_bulk = col.str.lower().str.contains('bulk', na=False)
                    else:
                        is_bulk = col.astype(bool)
                    return is_bulk.groupby(df[specialty_col]).mean() * 100

                recent_rates = bulk_rate(recent)
                prior_rates  = bulk_rate(prior)

                for specialty in recent_rates.index:
                    if specialty not in prior_rates.index:
                        continue
                    current_rate = recent_rates[specialty]
                    prior_rate   = prior_rates[specialty]
                    drop = prior_rate - current_rate
                    if drop > 5:
                        recs.append({
                            'category':            'Bulk Billing Optimisation',
                            'priority':            'High' if drop > 10 else 'Medium',
                            'metric':              f'Bulk Billing Rate — {specialty}',
                            'current_value':       f'{current_rate:.1f}%',
                            'target_value':        f'{prior_rate:.1f}% (prior 3-month avg)',
                            'action':              (
                                f'Review billing type policy for {specialty} — '
                                f'bulk billing rate dropped {drop:.1f}% from prior 3-month average'
                            ),
                            'estimated_impact_aud': 0.0,
                        })
            else:
                # No date column — compute overall rate per specialty
                col = billing_df[bulk_col]
                if col.dtype == object:
                    is_bulk = col.str.lower().str.contains('bulk', na=False)
                else:
                    is_bulk = col.astype(bool)
                rates = is_bulk.groupby(billing_df[specialty_col]).mean() * 100
                low_rate = rates[rates < 70]
                for specialty, rate in low_rate.items():
                    recs.append({
                        'category':            'Bulk Billing Optimisation',
                        'priority':            'Medium',
                        'metric':              f'Bulk Billing Rate — {specialty}',
                        'current_value':       f'{rate:.1f}%',
                        'target_value':        '70%+ (national benchmark)',
                        'action':              (
                            f'Review billing type policy for {specialty} — '
                            f'bulk billing rate of {rate:.1f}% is below benchmark'
                        ),
                        'estimated_impact_aud': 0.0,
                    })

    if not recs:
        # Fallback: flag if specialty_profitability has billing info
        recs.append({
            'category':            'Bulk Billing Optimisation',
            'priority':            'Medium',
            'metric':              'Bulk Billing Rate (all specialties)',
            'current_value':       'Insufficient historical data to compute 3-month trend',
            'target_value':        'No decline > 5% from prior 3-month average',
            'action':              'Ensure billing_claims_cleaned.csv includes specialty, billing_type, and service_date columns for trend analysis',
            'estimated_impact_aud': 0.0,
        })

    return recs


# ---------------------------------------------------------------------------
# Category 3: Wait Time SLA Breaches
# ---------------------------------------------------------------------------

def _wait_time_sla(appointments_df: pd.DataFrame) -> list[dict]:
    recs = []
    if appointments_df.empty:
        return recs

    appts = appointments_df.copy()
    appts.columns = [c.lower().strip() for c in appts.columns]

    specialty_col = next(
        (c for c in appts.columns if 'specialty' in c or 'department' in c or 'service_type' in c), None
    )
    wait_col = next(
        (c for c in appts.columns if 'wait' in c and ('day' in c or 'time' in c)), None
    )

    if specialty_col is None or wait_col is None:
        return recs

    appts[wait_col] = pd.to_numeric(appts[wait_col], errors='coerce')
    avg_wait = appts.groupby(specialty_col)[wait_col].mean().dropna()

    for specialty, avg_days in avg_wait.items():
        sla = WAIT_TIME_SLAS.get(specialty, DEFAULT_WAIT_SLA)
        if avg_days > sla:
            excess = avg_days - sla
            recs.append({
                'category':            'Wait Time SLA Breaches',
                'priority':            'High' if excess > sla * 0.5 else 'Medium',
                'metric':              f'Avg Wait Days — {specialty}',
                'current_value':       f'{avg_days:.1f} days',
                'target_value':        f'{sla} days (SLA)',
                'action':              (
                    f'Increase appointment slots for {specialty} — '
                    f'avg wait {avg_days:.1f} days exceeds SLA of {sla} days'
                ),
                'estimated_impact_aud': 0.0,
            })

    return recs


# ---------------------------------------------------------------------------
# Category 4: No-Show Reduction
# ---------------------------------------------------------------------------

def _no_show_reduction(appointments_df: pd.DataFrame,
                        billing_df: pd.DataFrame) -> list[dict]:
    recs = []
    if appointments_df.empty:
        return recs

    appts = appointments_df.copy()
    appts.columns = [c.lower().strip() for c in appts.columns]

    specialty_col = next(
        (c for c in appts.columns if 'specialty' in c or 'department' in c or 'service_type' in c), None
    )
    noshow_col = next(
        (c for c in appts.columns if 'no_show' in c or 'noshow' in c or 'did_not_attend' in c or 'dna' in c),
        None,
    )
    fee_col = next(
        (c for c in appts.columns if 'fee' in c or 'revenue' in c or 'charge' in c or 'amount' in c),
        None,
    )

    if specialty_col is None or noshow_col is None:
        return recs

    appts[noshow_col] = pd.to_numeric(appts[noshow_col], errors='coerce').fillna(0)

    # Calculate no-show rate per specialty
    def no_show_rate(grp):
        total = len(grp)
        no_shows = grp[noshow_col].sum() if grp[noshow_col].max() <= 1 else (grp[noshow_col] > 0).sum()
        return (no_shows / total * 100) if total else 0.0

    rates = appts.groupby(specialty_col).apply(no_show_rate)
    counts = appts.groupby(specialty_col).size()

    # Average fee per appointment — use billing data if available
    avg_fee_global = None
    if not billing_df.empty:
        billing_df_c = billing_df.copy()
        billing_df_c.columns = [c.lower().strip() for c in billing_df_c.columns]
        amt_col = next(
            (c for c in billing_df_c.columns if 'amount' in c or 'fee' in c or 'charge' in c or 'revenue' in c),
            None,
        )
        if amt_col:
            avg_fee_global = pd.to_numeric(billing_df_c[amt_col], errors='coerce').mean()

    if avg_fee_global is None or np.isnan(avg_fee_global):
        avg_fee_global = 80.0  # conservative AU bulk-billing estimate

    for specialty, rate in rates.items():
        if rate > 15:
            n_appts = counts[specialty]
            current_no_show_frac = rate / 100
            target_no_show_frac  = 0.10
            improvement_frac     = current_no_show_frac - target_no_show_frac
            annual_slots          = n_appts * 12  # rough annual extrapolation
            recoverable_appts     = annual_slots * improvement_frac
            revenue_recovery      = recoverable_appts * avg_fee_global

            recs.append({
                'category':            'No-Show Reduction',
                'priority':            'High' if rate > 25 else 'Medium',
                'metric':              f'No-Show Rate — {specialty}',
                'current_value':       f'{rate:.1f}%',
                'target_value':        '10% (industry benchmark)',
                'action':              (
                    f'Implement SMS reminder system for {specialty} — '
                    f'potential ${revenue_recovery:,.0f} AUD annual recovery '
                    f'(reducing no-show rate from {rate:.1f}% to 10%)'
                ),
                'estimated_impact_aud': round(revenue_recovery, 2),
            })

    return recs


# ---------------------------------------------------------------------------
# Category 5: Medicare Claim Recovery
# ---------------------------------------------------------------------------

def _medicare_claim_recovery(leakage_df: pd.DataFrame) -> list[dict]:
    recs = []
    if leakage_df.empty:
        return recs

    leakage_df = leakage_df.copy()
    leakage_df.columns = [c.lower().strip() for c in leakage_df.columns]

    bucket_col = next(
        (c for c in leakage_df.columns if 'bucket' in c or 'category' in c or 'leakage_type' in c or 'type' in c),
        None,
    )
    value_col = next(
        (c for c in leakage_df.columns if 'value' in c or 'amount' in c or 'total' in c or 'leakage' in c),
        None,
    )

    if bucket_col is None or value_col is None:
        return recs

    leakage_df[value_col] = pd.to_numeric(leakage_df[value_col], errors='coerce').fillna(0)

    significant = leakage_df[leakage_df[value_col] > 10_000]

    for _, row in significant.iterrows():
        bucket  = row[bucket_col]
        amount  = row[value_col]
        recovery = amount * 0.50

        recs.append({
            'category':            'Medicare Claim Recovery',
            'priority':            'High' if amount > 50_000 else 'Medium',
            'metric':              f'Claim Leakage — {bucket}',
            'current_value':       f'${amount:,.0f} AUD leakage identified',
            'target_value':        f'${recovery:,.0f} AUD recovered (50% fix rate)',
            'action':              (
                f'Prioritise {bucket} claims — '
                f'${recovery:,.0f} AUD recoverable at 50% fix rate'
            ),
            'estimated_impact_aud': round(recovery, 2),
        })

    return recs


# ---------------------------------------------------------------------------
# Master recommendation builder
# ---------------------------------------------------------------------------

def generate_recommendations(data: dict) -> list[dict]:
    """Run all five recommendation categories and return a combined list."""
    all_recs = []

    all_recs.extend(_churn_prevention(data.get('churn_scored', pd.DataFrame())))
    all_recs.extend(_bulk_billing_optimisation(
        data.get('billing', pd.DataFrame()),
        data.get('appointments', pd.DataFrame()),
    ))
    all_recs.extend(_wait_time_sla(data.get('appointments', pd.DataFrame())))
    all_recs.extend(_no_show_reduction(
        data.get('appointments', pd.DataFrame()),
        data.get('billing', pd.DataFrame()),
    ))
    all_recs.extend(_medicare_claim_recovery(data.get('leakage', pd.DataFrame())))

    # Assign sequential IDs
    priority_rank = {'High': 0, 'Medium': 1, 'Low': 2}
    all_recs.sort(key=lambda r: priority_rank.get(r['priority'], 9))
    for i, rec in enumerate(all_recs, start=1):
        rec['rec_id'] = f'REC-{i:02d}'

    return all_recs


# ---------------------------------------------------------------------------
# Output: console table
# ---------------------------------------------------------------------------

def print_recommendations(recs: list[dict]) -> None:
    """Print a formatted console table of all recommendations."""
    if not recs:
        print('No recommendations generated.')
        return

    col_widths = {
        'rec_id':   6,
        'category': 30,
        'priority': 8,
        'metric':   40,
        'action':   70,
        'estimated_impact_aud': 22,
    }

    header = (
        f"{'ID':<{col_widths['rec_id']}} "
        f"{'Category':<{col_widths['category']}} "
        f"{'Priority':<{col_widths['priority']}} "
        f"{'Metric':<{col_widths['metric']}} "
        f"{'Estimated Impact (AUD)':<{col_widths['estimated_impact_aud']}} "
        f"Action"
    )
    separator = '-' * min(len(header) + 20, 200)

    print()
    print('HealthFirst Australia — Recommendations Report')
    print('=' * 60)
    print(f'Total recommendations: {len(recs)}')
    print(separator)
    print(header)
    print(separator)

    for rec in recs:
        impact = rec.get('estimated_impact_aud', 0.0)
        impact_str = f"${impact:,.0f}" if impact else 'N/A'
        rec_id   = str(rec.get('rec_id', ''))[:col_widths['rec_id']]
        category = str(rec.get('category', ''))[:col_widths['category']]
        priority = str(rec.get('priority', ''))[:col_widths['priority']]
        metric   = str(rec.get('metric', ''))[:col_widths['metric']]
        action   = str(rec.get('action', ''))

        print(
            f"{rec_id:<{col_widths['rec_id']}} "
            f"{category:<{col_widths['category']}} "
            f"{priority:<{col_widths['priority']}} "
            f"{metric:<{col_widths['metric']}} "
            f"{impact_str:<{col_widths['estimated_impact_aud']}} "
            f"{action}"
        )

    print(separator)
    total_impact = sum(r.get('estimated_impact_aud', 0.0) for r in recs)
    print(f"Total estimated recoverable value: ${total_impact:,.0f} AUD")
    print()


# ---------------------------------------------------------------------------
# Output: CSV + JSON
# ---------------------------------------------------------------------------

REPORT_COLUMNS = [
    'rec_id',
    'category',
    'priority',
    'metric',
    'current_value',
    'target_value',
    'action',
    'estimated_impact_aud',
]


def save_recommendations(recs: list[dict]) -> None:
    """Save recommendations to reports/recommendations.csv and .json."""
    os.makedirs(RPT_DIR, exist_ok=True)

    # CSV
    csv_path = os.path.join(RPT_DIR, 'recommendations.csv')
    df = pd.DataFrame(recs, columns=REPORT_COLUMNS)
    df.to_csv(csv_path, index=False)
    print(f'CSV saved  : {os.path.abspath(csv_path)}')

    # JSON
    json_path = os.path.join(RPT_DIR, 'recommendations.json')
    with open(json_path, 'w') as f:
        json.dump(recs, f, indent=2, default=str)
    print(f'JSON saved : {os.path.abspath(json_path)}')


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print('Loading data...')
    data = load_data()

    loaded = [k for k, v in data.items() if not v.empty]
    missing = [k for k, v in data.items() if v.empty]
    print(f'Loaded datasets : {loaded}')
    if missing:
        print(f'Missing/empty   : {missing} (recommendations may be limited)')

    recs = generate_recommendations(data)
    print_recommendations(recs)
    save_recommendations(recs)
    print(f'\nGenerated {len(recs)} recommendations.')
