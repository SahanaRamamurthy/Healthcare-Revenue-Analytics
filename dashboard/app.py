"""
dashboard/app.py — HealthFirst Australia
=========================================
Interactive Plotly dashboard for the HealthFirst Australia Revenue Intelligence project.

Run:  python dashboard/app.py
Open: dashboard/dashboard_export.html  (static, no server needed)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio

CLEAN = os.path.join(os.path.dirname(__file__), '..', 'data', 'cleaned')
PROC  = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed')

def load(fname, directory=CLEAN, **kw):
    p = os.path.join(directory, fname)
    return pd.read_csv(p, **kw) if os.path.exists(p) else pd.DataFrame()

appointments = load('appointments.csv', parse_dates=['appointment_date'])
patients     = load('patients.csv')
staff        = load('staff.csv')
surveys      = load('satisfaction_surveys.csv')
claims       = load('billing_claims.csv')
churn_scored = load('patients_churn_scored.csv', directory=PROC)
segments     = load('patient_segments.csv', directory=PROC)

if not appointments.empty:
    appointments['month'] = appointments['appointment_date'].dt.to_period('M').astype(str)
    completed = appointments[appointments['status'] == 'completed'].copy()
else:
    completed = pd.DataFrame()

# ── Colours ────────────────────────────────────────────────────────────────
BLUE   = '#2980b9'
GREEN  = '#27ae60'
RED    = '#c0392b'
ORANGE = '#e67e22'
PURPLE = '#8e44ad'
TEAL   = '#16a085'
GRAY   = '#7f8c8d'
LIGHT  = '#ecf0f1'

SPECIALTY_COLORS = {
    'GP':            BLUE,
    'Cardiology':    RED,
    'Mental Health': PURPLE,
    'Oncology':      ORANGE,
    'Orthopaedics':  TEAL,
    'Paediatrics':   GREEN,
    'Emergency':     '#e74c3c',
    'Dermatology':   '#f39c12',
}

BILLING_COLORS = {
    'bulk_bill':   GREEN,
    'gap_payment': ORANGE,
    'private':     BLUE,
    'self_pay':    RED,
}

SEGMENT_COLORS = {
    'Active & Engaged':       GREEN,
    'Chronic Care Patient':   BLUE,
    'New Patient':            TEAL,
    'Preventive Only':        '#5dade2',
    'At Risk of Lapsing':     ORANGE,
    'Disengaged':             GRAY,
    'High Value Occasional':  PURPLE,
}

# ════════════════════════════════════════════════════════════════════════════
# KPI CARDS
# ════════════════════════════════════════════════════════════════════════════
def fig_kpi_cards():
    if completed.empty:
        return go.Figure()

    total_rev     = completed['billed_amount'].sum()
    total_appts   = completed['appointment_id'].nunique()
    bulk_rate     = (completed['billing_type']=='bulk_bill').mean() * 100
    avg_wait      = completed['wait_days'].mean()
    churn_rate    = patients['churn_flag'].mean() * 100 if not patients.empty else 0
    no_show_rate  = (appointments['status']=='no_show').mean() * 100 if not appointments.empty else 0

    kpis = [
        ('Total Revenue',          total_rev,    f'${total_rev/1e6:.2f}M',  BLUE),
        ('Completed Appointments', total_appts,  f'{total_appts:,}',         GREEN),
        ('Bulk Billing Rate',      bulk_rate,    f'{bulk_rate:.1f}%',         TEAL),
        ('Avg Wait Days',          avg_wait,     f'{avg_wait:.0f} days',      ORANGE),
        ('Patient Churn Rate',     churn_rate,   f'{churn_rate:.1f}%',        RED),
        ('No-Show Rate',           no_show_rate, f'{no_show_rate:.1f}%',      PURPLE),
    ]
    fig = go.Figure()
    for i, (label, val, disp, color) in enumerate(kpis):
        fig.add_trace(go.Indicator(
            mode='number',
            value=val,
            title={'text': label, 'font': {'size': 12}},
            number={'valueformat': '', 'font': {'size': 26, 'color': color}},
            domain={'row': 0, 'column': i},
        ))
    fig.update_layout(
        grid={'rows': 1, 'columns': len(kpis)},
        height=140,
        margin=dict(t=30, b=0, l=10, r=10),
        paper_bgcolor='#f8f9fa',
    )
    return fig

# ════════════════════════════════════════════════════════════════════════════
# REVENUE TREND
# ════════════════════════════════════════════════════════════════════════════
def fig_revenue_trend():
    if completed.empty:
        return go.Figure()

    monthly = completed.groupby(['month','billing_type'])['billed_amount'].sum().reset_index()
    pivot   = monthly.pivot(index='month', columns='billing_type', values='billed_amount').fillna(0).reset_index()

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        subplot_titles=['Monthly Revenue by Billing Type ($)',
                                        'Bulk Billing Rate (%) — Month 7 Policy Change'],
                        row_heights=[0.65, 0.35])

    for btype, color in BILLING_COLORS.items():
        if btype in pivot.columns:
            fig.add_trace(go.Bar(x=pivot['month'], y=pivot[btype],
                                 name=btype.replace('_',' ').title(),
                                 marker_color=color), row=1, col=1)

    # Bulk billing rate line
    bb_rate = completed.groupby('month').apply(
        lambda df: (df['billing_type']=='bulk_bill').mean()*100
    ).reset_index()
    bb_rate.columns = ['month','rate']
    fig.add_trace(go.Scatter(x=bb_rate['month'], y=bb_rate['rate'],
                             mode='lines+markers', name='Bulk Bill Rate %',
                             line=dict(color=GREEN, width=2.5)),
                  row=2, col=1)
    fig.add_hline(y=bb_rate['rate'].mean(), line_dash='dash', line_color=GRAY,
                  annotation_text=f"Avg {bb_rate['rate'].mean():.1f}%", row=2, col=1)

    fig.update_layout(height=500, title='HealthFirst Australia — Revenue Dashboard',
                      barmode='stack', legend=dict(orientation='h', y=1.02))
    fig.update_yaxes(tickprefix='$', tickformat=',.0f', row=1, col=1)
    fig.update_yaxes(ticksuffix='%', row=2, col=1)
    return fig

# ════════════════════════════════════════════════════════════════════════════
# WAIT TIMES
# ════════════════════════════════════════════════════════════════════════════
def fig_wait_times():
    if completed.empty:
        return go.Figure()

    wt = completed.groupby('specialty').agg(
        avg_wait=('wait_days','mean'),
        appts=('appointment_id','count')
    ).reset_index().sort_values('avg_wait', ascending=True)

    colors = [RED if w > 30 else ORANGE if w > 14 else GREEN for w in wt['avg_wait']]
    fig = go.Figure(go.Bar(
        x=wt['avg_wait'], y=wt['specialty'],
        orientation='h', marker_color=colors,
        text=[f'{v:.0f} days' for v in wt['avg_wait']],
        textposition='outside',
    ))
    fig.add_vline(x=14, line_dash='dash', line_color=GRAY,
                  annotation_text='14-day benchmark')
    fig.update_layout(height=360, title='Average Wait Time by Specialty (days)',
                      xaxis_title='Wait Days')
    return fig

# ════════════════════════════════════════════════════════════════════════════
# SATISFACTION TREND
# ════════════════════════════════════════════════════════════════════════════
def fig_satisfaction():
    if surveys.empty:
        return go.Figure()

    if 'survey_date' not in surveys.columns:
        return go.Figure()

    surveys2 = surveys.copy()
    surveys2['survey_date'] = pd.to_datetime(surveys2['survey_date'], errors='coerce')
    surveys2['month'] = surveys2['survey_date'].dt.to_period('M').astype(str)

    monthly = surveys2.groupby('month').agg(
        avg_overall=('overall_score','mean'),
        avg_wait_rating=('wait_time_rating','mean'),
        recommend_rate=('would_recommend','mean'),
        complaints=('complaint_category', lambda x: (x!='None').sum()),
    ).reset_index()

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=['Avg Overall Score by Month (1–10)',
                                        'Would Recommend Rate (%)'])

    fig.add_trace(go.Scatter(x=monthly['month'], y=monthly['avg_overall'],
                             mode='lines+markers', name='Overall Score',
                             line=dict(color=BLUE, width=2)),
                  row=1, col=1)
    fig.add_hline(y=7, line_dash='dash', line_color=GRAY,
                  annotation_text='Target 7/10', row=1, col=1)

    fig.add_trace(go.Bar(x=monthly['month'],
                         y=monthly['recommend_rate']*100,
                         name='Recommend %',
                         marker_color=[GREEN if v>0.70 else ORANGE if v>0.55 else RED
                                       for v in monthly['recommend_rate']]),
                  row=1, col=2)

    fig.update_layout(height=380, title='Patient Satisfaction Trends', showlegend=False)
    fig.update_yaxes(range=[0,10], row=1, col=1)
    fig.update_yaxes(ticksuffix='%', row=1, col=2)
    fig.update_xaxes(tickangle=45)
    return fig

# ════════════════════════════════════════════════════════════════════════════
# SPECIALTY PROFITABILITY
# ════════════════════════════════════════════════════════════════════════════
def fig_specialty_margin():
    if completed.empty:
        return go.Figure()

    sp = completed.groupby('specialty').apply(lambda df: pd.Series({
        'avg_billed': df['billed_amount'].mean(),
        'avg_cost':   df['staff_cost'].mean(),
        'avg_margin': (df['billed_amount'] - df['staff_cost']).mean(),
        'total_revenue': df['billed_amount'].sum(),
        'appointments': len(df),
    }), include_groups=False).reset_index()
    sp['margin_pct'] = sp['avg_margin'] / sp['avg_billed'] * 100
    sp = sp.sort_values('avg_margin', ascending=True)

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=['Avg Margin per Appointment by Specialty ($)',
                                        'Total Revenue by Specialty ($000s)'])

    bar_colors = [GREEN if m > 50 else ORANGE if m > 25 else RED for m in sp['margin_pct']]
    fig.add_trace(go.Bar(x=sp['avg_margin'], y=sp['specialty'],
                         orientation='h', marker_color=bar_colors,
                         text=[f'${v:.0f}' for v in sp['avg_margin']],
                         textposition='outside'), row=1, col=1)

    sp2 = sp.sort_values('total_revenue', ascending=True)
    fig.add_trace(go.Bar(x=sp2['total_revenue']/1000, y=sp2['specialty'],
                         orientation='h', marker_color=BLUE,
                         text=[f'${v:.0f}k' for v in sp2['total_revenue']/1000],
                         textposition='outside'), row=1, col=2)

    fig.update_layout(height=380, title='Specialty Profitability', showlegend=False)
    fig.update_xaxes(tickprefix='$', row=1, col=1)
    fig.update_xaxes(tickprefix='$', ticksuffix='k', row=1, col=2)
    return fig

# ════════════════════════════════════════════════════════════════════════════
# CHURN BY STATE
# ════════════════════════════════════════════════════════════════════════════
def fig_churn_state():
    if patients.empty:
        return go.Figure()

    ch = patients.groupby('state').agg(
        total=('patient_id','count'),
        churned=('churn_flag','sum'),
        avg_billed=('total_billed','mean'),
    ).assign(churn_rate=lambda df: df['churned']/df['total']*100).reset_index()
    ch = ch.sort_values('churn_rate', ascending=True)

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=['Patient Churn Rate by State (%)',
                                        'Avg Lifetime Billing by State ($)'])

    fig.add_trace(go.Bar(x=ch['churn_rate'], y=ch['state'],
                         orientation='h',
                         marker_color=[RED if r>25 else ORANGE if r>18 else GREEN for r in ch['churn_rate']]),
                  row=1, col=1)
    fig.add_trace(go.Bar(x=ch['avg_billed'], y=ch['state'],
                         orientation='h', marker_color=BLUE),
                  row=1, col=2)

    fig.update_layout(height=360, title='Patient Engagement by State', showlegend=False)
    fig.update_xaxes(ticksuffix='%', row=1, col=1)
    fig.update_xaxes(tickprefix='$', row=1, col=2)
    return fig

# ════════════════════════════════════════════════════════════════════════════
# PATIENT SEGMENTS TREEMAP
# ════════════════════════════════════════════════════════════════════════════
def fig_segments():
    if segments.empty:
        return go.Figure().update_layout(title='Patient Segments (run Notebook 04 first)')

    seg_col = 'segment' if 'segment' in segments.columns else segments.columns[-1]
    val_col = 'V' if 'V' in segments.columns else ('monetary' if 'monetary' in segments.columns else None)

    if val_col:
        agg = segments.groupby(seg_col).agg(
            patients=(seg_col,'count'),
            total_value=(val_col,'sum'),
        ).reset_index()
    else:
        agg = segments.groupby(seg_col).size().reset_index(name='patients')
        agg['total_value'] = agg['patients'] * 100

    fig = px.treemap(agg, path=[seg_col], values='patients',
                     color='total_value',
                     color_continuous_scale='RdYlGn',
                     title='Patient Engagement Segments (sized by patient count)')
    fig.update_layout(height=400)
    return fig

# ════════════════════════════════════════════════════════════════════════════
# CLAIM REJECTION RATES
# ════════════════════════════════════════════════════════════════════════════
def fig_claims():
    if claims.empty:
        return go.Figure()

    claims2 = claims.copy()
    claims2['claim_date'] = pd.to_datetime(claims2['claim_date'], errors='coerce')
    claims2['month'] = claims2['claim_date'].dt.to_period('M').astype(str)

    rej = claims2.groupby(['month','claim_type']).apply(lambda df: pd.Series({
        'rejection_rate': (df['claim_status']=='rejected').mean()*100,
        'rejected_value': df.loc[df['claim_status']=='rejected','rejected_amount'].sum(),
    }), include_groups=False).reset_index()

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=['Claim Rejection Rate by Type (%)',
                                        'Total Rejected Value by Month ($)'])

    for ctype, color in [('Medicare', BLUE), ('Private_Insurance', ORANGE), ('Self_Pay', RED)]:
        sub = rej[rej['claim_type']==ctype]
        if not sub.empty:
            fig.add_trace(go.Scatter(x=sub['month'], y=sub['rejection_rate'],
                                     mode='lines+markers', name=ctype,
                                     line=dict(color=color, width=2)), row=1, col=1)

    monthly_rej = claims2[claims2['claim_status']=='rejected'].groupby('month')['rejected_amount'].sum().reset_index()
    fig.add_trace(go.Bar(x=monthly_rej['month'], y=monthly_rej['rejected_amount'],
                         marker_color=RED, name='Rejected Value', showlegend=False),
                  row=1, col=2)

    fig.update_layout(height=380, title='Billing Claims — Rejection Analysis',
                      legend=dict(orientation='h'))
    fig.update_yaxes(ticksuffix='%', row=1, col=1)
    fig.update_yaxes(tickprefix='$', tickformat=',.0f', row=1, col=2)
    fig.update_xaxes(tickangle=45)
    return fig

# ════════════════════════════════════════════════════════════════════════════
# BUILD & EXPORT STATIC HTML
# ════════════════════════════════════════════════════════════════════════════
def build_static_html():
    figs = {
        'kpi_cards':    fig_kpi_cards(),
        'revenue':      fig_revenue_trend(),
        'wait_times':   fig_wait_times(),
        'satisfaction': fig_satisfaction(),
        'specialty':    fig_specialty_margin(),
        'churn_state':  fig_churn_state(),
        'segments':     fig_segments(),
        'claims':       fig_claims(),
    }

    sections = [
        ('KPI Summary',                             'kpi_cards'),
        ('Revenue Trend & Bulk Billing Rate',        'revenue'),
        ('Patient Wait Times by Specialty',          'wait_times'),
        ('Patient Satisfaction & Recommendation',    'satisfaction'),
        ('Specialty Revenue & Profitability',        'specialty'),
        ('Patient Churn by State',                   'churn_state'),
        ('Patient Engagement Segments',              'segments'),
        ('Billing Claim Rejections',                 'claims'),
    ]

    parts = ["""<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'>
  <title>HealthFirst Australia — Revenue Intelligence Dashboard</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; padding: 0; }
    header { background: linear-gradient(135deg, #1a5276, #2980b9);
             color: white; padding: 18px 30px; }
    header h1 { margin: 0; font-size: 22px; }
    header p  { margin: 4px 0 0; font-size: 13px; opacity: 0.85; }
    .section  { background: white; margin: 14px 22px; border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,.08); overflow: hidden; }
    .section h2 { background: #f7f9fc; margin: 0; padding: 10px 18px;
                  font-size: 13px; color: #1a5276; border-bottom: 1px solid #e0e6ed; }
    footer { text-align: center; padding: 18px; color: #7f8c8d; font-size: 11px; }
  </style>
</head>
<body>
<header>
  <h1>HealthFirst Australia — Revenue Intelligence Dashboard</h1>
  <p>Synthetic data · 8 clinics across Australia · 3,000 patients · 20,000 appointments</p>
</header>
"""]

    first = True
    for title, key in sections:
        incl = True if first else False
        chart_html = pio.to_html(figs[key], full_html=False, include_plotlyjs=incl)
        parts.append(f'<div class="section"><h2>{title}</h2>{chart_html}</div>\n')
        first = False

    parts.append('<footer>HealthFirst Australia · Revenue Intelligence System · Built with Python &amp; Plotly</footer></body></html>')

    out = os.path.join(os.path.dirname(__file__), 'dashboard_export.html')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(parts))
    print(f'Dashboard saved: {os.path.abspath(out)}')
    return out


if __name__ == '__main__':
    build_static_html()
