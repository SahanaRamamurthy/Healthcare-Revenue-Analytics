"""
dashboard/app.py — HealthFirst Australia
=========================================
Interactive Plotly Dash dashboard with filters for specialty, clinic,
appointment type, and date range.

Run live server:  python dashboard/app.py
Export static HTML: python dashboard/app.py --export
"""
import sys, os, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio
from sqlalchemy import create_engine

# ── Database connection (optional) ──────────────────────────────────────────
DB_URL = "postgresql://localhost/healthfirst"
engine = create_engine(DB_URL)

PROC    = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed')
CLEANED = os.path.join(os.path.dirname(__file__), '..', 'data', 'cleaned')
RAW     = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')

def load_csv(fname, base=PROC, **kw):
    p = os.path.join(base, fname)
    return pd.read_csv(p, **kw) if os.path.exists(p) else pd.DataFrame()

def load_db_or_csv(query, csv_name, csv_base=CLEANED, **kw):
    try:
        return pd.read_sql(query, engine, **kw)
    except Exception as e:
        print(f"DB error: {e}")
        return load_csv(csv_name, base=csv_base, **kw)

# ── Load data ────────────────────────────────────────────────────────────────
appointments = load_db_or_csv("SELECT * FROM appointments", "appointments.csv",
                               parse_dates=['appointment_date'])
patients     = load_db_or_csv("SELECT * FROM patients",     "patients.csv")
surveys      = load_db_or_csv("SELECT * FROM satisfaction_surveys", "satisfaction_surveys.csv",
                               parse_dates=['survey_date'])
claims       = load_db_or_csv("SELECT * FROM billing_claims", "billing_claims.csv",
                               parse_dates=['claim_date'])
churn_scored = load_csv('patients_churn_scored.csv')
segments     = load_csv('patient_segments.csv')

appointments['appointment_date'] = pd.to_datetime(appointments['appointment_date'])
appointments['month'] = appointments['appointment_date'].dt.to_period('M').astype(str)

# ── Filter options ───────────────────────────────────────────────────────────
ALL_SPECIALTIES = sorted(appointments['specialty'].dropna().unique()) if not appointments.empty else []
ALL_CLINICS     = sorted(appointments['clinic_id'].dropna().unique()) if not appointments.empty else []
ALL_TYPES       = sorted(appointments['appointment_type'].dropna().unique()) if not appointments.empty else []
DATE_MIN        = appointments['appointment_date'].min() if not appointments.empty else pd.Timestamp('2024-01-01')
DATE_MAX        = appointments['appointment_date'].max() if not appointments.empty else pd.Timestamp('2025-12-31')

# ── Colours ──────────────────────────────────────────────────────────────────
BLUE   = '#2980b9'
GREEN  = '#27ae60'
RED    = '#c0392b'
ORANGE = '#e67e22'
PURPLE = '#8e44ad'
TEAL   = '#16a085'
GRAY   = '#7f8c8d'

BILLING_COLORS = {
    'bulk_bill':   GREEN,
    'gap_payment': ORANGE,
    'private':     BLUE,
    'self_pay':    RED,
}


# ════════════════════════════════════════════════════════════════════════════
# CHART FUNCTIONS — all accept a filtered `df` slice
# ════════════════════════════════════════════════════════════════════════════

def fig_kpi_cards(df, pat):
    if df.empty:
        return go.Figure()
    completed = df[df['status'] == 'completed']
    total_rev    = completed['billed_amount'].sum()
    total_appts  = completed['appointment_id'].nunique()
    bulk_rate    = (completed['billing_type'] == 'bulk_bill').mean() * 100
    avg_wait     = completed['wait_days'].mean()
    churn_rate   = pat['churn_flag'].mean() * 100 if not pat.empty else 0
    no_show_rate = (df['status'] == 'no_show').mean() * 100

    kpis = [
        ('Total Revenue',          total_rev,    f'${total_rev/1e6:.2f}M',  BLUE),
        ('Completed Appointments', total_appts,  f'{total_appts:,}',         GREEN),
        ('Bulk Billing Rate',      bulk_rate,    f'{bulk_rate:.1f}%',        TEAL),
        ('Avg Wait Days',          avg_wait,     f'{avg_wait:.0f} days',     ORANGE),
        ('Patient Churn Rate',     churn_rate,   f'{churn_rate:.1f}%',       RED),
        ('No-Show Rate',           no_show_rate, f'{no_show_rate:.1f}%',     PURPLE),
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


def fig_revenue_trend(df):
    completed = df[df['status'] == 'completed']
    if completed.empty:
        return go.Figure()
    monthly = completed.groupby(['month', 'billing_type'])['billed_amount'].sum().reset_index()
    pivot   = monthly.pivot(index='month', columns='billing_type', values='billed_amount').fillna(0).reset_index()

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        subplot_titles=['Monthly Revenue by Billing Type ($)',
                                        'Bulk Billing Rate (%)'],
                        row_heights=[0.65, 0.35])
    for btype, color in BILLING_COLORS.items():
        if btype in pivot.columns:
            fig.add_trace(go.Bar(x=pivot['month'], y=pivot[btype],
                                 name=btype.replace('_', ' ').title(),
                                 marker_color=color), row=1, col=1)

    bb_rate = completed.groupby('month').apply(
        lambda d: (d['billing_type'] == 'bulk_bill').mean() * 100
    ).reset_index()
    bb_rate.columns = ['month', 'rate']
    fig.add_trace(go.Scatter(x=bb_rate['month'], y=bb_rate['rate'],
                             mode='lines+markers', name='Bulk Bill %',
                             line=dict(color=GREEN, width=2.5)), row=2, col=1)
    fig.add_hline(y=bb_rate['rate'].mean(), line_dash='dash', line_color=GRAY,
                  annotation_text=f"Avg {bb_rate['rate'].mean():.1f}%", row=2, col=1)

    fig.update_layout(height=500, barmode='stack',
                      title='Revenue & Bulk Billing Trend',
                      legend=dict(orientation='h', y=1.02))
    fig.update_yaxes(tickprefix='$', tickformat=',.0f', row=1, col=1)
    fig.update_yaxes(ticksuffix='%', row=2, col=1)
    return fig


def fig_wait_times(df):
    completed = df[df['status'] == 'completed']
    if completed.empty:
        return go.Figure()
    wt = completed.groupby('specialty').agg(
        avg_wait=('wait_days', 'mean'),
        appts=('appointment_id', 'count')
    ).reset_index().sort_values('avg_wait', ascending=True)

    colors = [RED if w > 30 else ORANGE if w > 14 else GREEN for w in wt['avg_wait']]
    fig = go.Figure(go.Bar(
        x=wt['avg_wait'], y=wt['specialty'], orientation='h',
        marker_color=colors,
        text=[f'{v:.0f} days' for v in wt['avg_wait']],
        textposition='outside',
    ))
    fig.add_vline(x=14, line_dash='dash', line_color=GRAY, annotation_text='14-day SLA')
    fig.update_layout(height=360, title='Average Wait Time by Specialty', xaxis_title='Wait Days')
    return fig


def fig_satisfaction(surv):
    if surv.empty or 'survey_date' not in surv.columns:
        return go.Figure()
    surv = surv.copy()
    surv['survey_date'] = pd.to_datetime(surv['survey_date'], errors='coerce')
    surv['month'] = surv['survey_date'].dt.to_period('M').astype(str)
    monthly = surv.groupby('month').agg(
        avg_overall=('overall_score', 'mean'),
        recommend_rate=('would_recommend', 'mean'),
    ).reset_index()

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=['Avg Overall Score by Month (1–10)',
                                        'Would Recommend Rate (%)'])
    fig.add_trace(go.Scatter(x=monthly['month'], y=monthly['avg_overall'],
                             mode='lines+markers', name='Overall Score',
                             line=dict(color=BLUE, width=2)), row=1, col=1)
    fig.add_hline(y=7, line_dash='dash', line_color=GRAY, annotation_text='Target 7/10', row=1, col=1)
    fig.add_trace(go.Bar(x=monthly['month'], y=monthly['recommend_rate'] * 100,
                         name='Recommend %',
                         marker_color=[GREEN if v > 0.70 else ORANGE if v > 0.55 else RED
                                       for v in monthly['recommend_rate']]), row=1, col=2)
    fig.update_layout(height=380, title='Patient Satisfaction Trends', showlegend=False)
    fig.update_yaxes(range=[0, 10], row=1, col=1)
    fig.update_yaxes(ticksuffix='%', row=1, col=2)
    fig.update_xaxes(tickangle=45)
    return fig


def fig_specialty_margin(df):
    completed = df[df['status'] == 'completed']
    if completed.empty:
        return go.Figure()
    sp = completed.groupby('specialty').apply(lambda d: pd.Series({
        'avg_margin':    (d['billed_amount'] - d['staff_cost']).mean(),
        'total_revenue': d['billed_amount'].sum(),
        'margin_pct':    ((d['billed_amount'] - d['staff_cost']) / d['billed_amount']).mean() * 100,
    }), include_groups=False).reset_index().sort_values('avg_margin', ascending=True)

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=['Avg Margin per Appointment ($)',
                                        'Total Revenue by Specialty ($000s)'])
    bar_colors = [GREEN if m > 50 else ORANGE if m > 25 else RED for m in sp['margin_pct']]
    fig.add_trace(go.Bar(x=sp['avg_margin'], y=sp['specialty'], orientation='h',
                         marker_color=bar_colors,
                         text=[f'${v:.0f}' for v in sp['avg_margin']],
                         textposition='outside'), row=1, col=1)
    sp2 = sp.sort_values('total_revenue', ascending=True)
    fig.add_trace(go.Bar(x=sp2['total_revenue'] / 1000, y=sp2['specialty'], orientation='h',
                         marker_color=BLUE,
                         text=[f'${v:.0f}k' for v in sp2['total_revenue'] / 1000],
                         textposition='outside'), row=1, col=2)
    fig.update_layout(height=380, title='Specialty Profitability', showlegend=False)
    return fig


def fig_churn_state(pat):
    if pat.empty:
        return go.Figure()
    ch = pat.groupby('state').agg(
        total=('patient_id', 'count'),
        churned=('churn_flag', 'sum'),
        avg_billed=('total_billed', 'mean'),
    ).assign(churn_rate=lambda d: d['churned'] / d['total'] * 100).reset_index()
    ch = ch.sort_values('churn_rate', ascending=True)

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=['Churn Rate by State (%)',
                                        'Avg Lifetime Billing by State ($)'])
    fig.add_trace(go.Bar(x=ch['churn_rate'], y=ch['state'], orientation='h',
                         marker_color=[RED if r > 25 else ORANGE if r > 18 else GREEN
                                       for r in ch['churn_rate']]), row=1, col=1)
    fig.add_trace(go.Bar(x=ch['avg_billed'], y=ch['state'], orientation='h',
                         marker_color=BLUE), row=1, col=2)
    fig.update_layout(height=360, title='Patient Engagement by State', showlegend=False)
    fig.update_xaxes(ticksuffix='%', row=1, col=1)
    fig.update_xaxes(tickprefix='$', row=1, col=2)
    return fig


def fig_segments(seg):
    if seg.empty:
        return go.Figure().update_layout(title='Patient Segments (run Notebook 04 first)')
    seg_col = 'segment' if 'segment' in seg.columns else seg.columns[-1]
    val_col = next((c for c in ['V', 'monetary', 'total_billed'] if c in seg.columns), None)
    agg = seg.groupby(seg_col).agg(
        patients=(seg_col, 'count'),
        total_value=(val_col, 'sum') if val_col else (seg_col, 'count'),
    ).reset_index()
    fig = px.treemap(agg, path=[seg_col], values='patients', color='total_value',
                     color_continuous_scale='RdYlGn',
                     title='Patient Engagement Segments (sized by patient count)')
    fig.update_layout(height=400)
    return fig


def fig_claims(clm):
    if clm.empty:
        return go.Figure()
    clm = clm.copy()
    clm['claim_date'] = pd.to_datetime(clm['claim_date'], errors='coerce')
    clm['month'] = clm['claim_date'].dt.to_period('M').astype(str)
    rej = clm.groupby(['month', 'claim_type']).apply(lambda d: pd.Series({
        'rejection_rate': (d['claim_status'] == 'rejected').mean() * 100,
        'rejected_value': d.loc[d['claim_status'] == 'rejected', 'rejected_amount'].sum(),
    }), include_groups=False).reset_index()

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=['Claim Rejection Rate by Type (%)',
                                        'Total Rejected Value by Month ($)'])
    for ctype, color in [('Medicare', BLUE), ('Private_Insurance', ORANGE), ('Self_Pay', RED)]:
        sub = rej[rej['claim_type'] == ctype]
        if not sub.empty:
            fig.add_trace(go.Scatter(x=sub['month'], y=sub['rejection_rate'],
                                     mode='lines+markers', name=ctype,
                                     line=dict(color=color, width=2)), row=1, col=1)
    monthly_rej = clm[clm['claim_status'] == 'rejected'].groupby('month')['rejected_amount'].sum().reset_index()
    fig.add_trace(go.Bar(x=monthly_rej['month'], y=monthly_rej['rejected_amount'],
                         marker_color=RED, name='Rejected Value', showlegend=False), row=1, col=2)
    fig.update_layout(height=380, title='Billing Claim Rejections', legend=dict(orientation='h'))
    fig.update_yaxes(ticksuffix='%', row=1, col=1)
    fig.update_yaxes(tickprefix='$', tickformat=',.0f', row=1, col=2)
    fig.update_xaxes(tickangle=45)
    return fig


# ════════════════════════════════════════════════════════════════════════════
# DASH APP — live interactive server with filters
# ════════════════════════════════════════════════════════════════════════════

def build_dash_app():
    from dash import Dash, dcc, html, Input, Output

    app = Dash(__name__, title='HealthFirst Australia — Revenue Intelligence')

    filter_style = {'width': '22%', 'display': 'inline-block', 'verticalAlign': 'top',
                    'margin': '0 1% 12px 0'}
    label_style  = {'fontWeight': '600', 'fontSize': '12px', 'color': '#1a5276',
                    'marginBottom': '4px', 'display': 'block'}

    app.layout = html.Div(style={'fontFamily': "'Segoe UI', sans-serif",
                                  'background': '#f0f2f5', 'minHeight': '100vh'}, children=[

        # ── Header ──────────────────────────────────────────────────────────
        html.Div(style={'background': 'linear-gradient(135deg,#1a5276,#2980b9)',
                        'color': 'white', 'padding': '18px 30px'}, children=[
            html.H1('HealthFirst Australia — Revenue Intelligence Dashboard',
                    style={'margin': 0, 'fontSize': '22px'}),
            html.P('Synthetic data · 8 clinics · 3,000 patients · 20,000 appointments',
                   style={'margin': '4px 0 0', 'opacity': 0.85, 'fontSize': '13px'}),
        ]),

        # ── Filter bar ───────────────────────────────────────────────────────
        html.Div(style={'background': 'white', 'padding': '16px 22px',
                        'borderBottom': '1px solid #e0e6ed',
                        'boxShadow': '0 2px 6px rgba(0,0,0,.06)'}, children=[

            html.Div(style=filter_style, children=[
                html.Label('Specialty', style=label_style),
                dcc.Dropdown(
                    id='filter-specialty',
                    options=[{'label': 'All Specialties', 'value': 'ALL'}] +
                            [{'label': s, 'value': s} for s in ALL_SPECIALTIES],
                    value='ALL', clearable=False,
                ),
            ]),

            html.Div(style=filter_style, children=[
                html.Label('Clinic', style=label_style),
                dcc.Dropdown(
                    id='filter-clinic',
                    options=[{'label': 'All Clinics', 'value': 'ALL'}] +
                            [{'label': f'Clinic {c}', 'value': c} for c in ALL_CLINICS],
                    value='ALL', clearable=False,
                ),
            ]),

            html.Div(style=filter_style, children=[
                html.Label('Appointment Type', style=label_style),
                dcc.Dropdown(
                    id='filter-type',
                    options=[{'label': 'All Types', 'value': 'ALL'}] +
                            [{'label': t.replace('_', ' ').title(), 'value': t} for t in ALL_TYPES],
                    value='ALL', clearable=False,
                ),
            ]),

            html.Div(style=filter_style, children=[
                html.Label('Date Range', style=label_style),
                dcc.DatePickerRange(
                    id='filter-dates',
                    min_date_allowed=DATE_MIN,
                    max_date_allowed=DATE_MAX,
                    start_date=DATE_MIN,
                    end_date=DATE_MAX,
                    display_format='MMM YYYY',
                    style={'fontSize': '12px'},
                ),
            ]),
        ]),

        # ── Charts ───────────────────────────────────────────────────────────
        html.Div(id='kpi-section',    style={'background': 'white', 'margin': '14px 22px',
                                             'borderRadius': '10px', 'padding': '10px 18px',
                                             'boxShadow': '0 2px 10px rgba(0,0,0,.08)'}),

        *[html.Div([
            html.H2(title, style={'background': '#f7f9fc', 'margin': 0, 'padding': '10px 18px',
                                  'fontSize': '13px', 'color': '#1a5276',
                                  'borderBottom': '1px solid #e0e6ed'}),
            dcc.Graph(id=graph_id),
        ], style={'background': 'white', 'margin': '14px 22px', 'borderRadius': '10px',
                  'boxShadow': '0 2px 10px rgba(0,0,0,.08)', 'overflow': 'hidden'})
         for title, graph_id in [
            ('Revenue Trend & Bulk Billing Rate',       'graph-revenue'),
            ('Patient Wait Times by Specialty',          'graph-wait'),
            ('Patient Satisfaction & Recommendation',    'graph-satisfaction'),
            ('Specialty Revenue & Profitability',        'graph-specialty'),
            ('Patient Churn by State',                   'graph-churn'),
            ('Patient Engagement Segments',              'graph-segments'),
            ('Billing Claim Rejections',                 'graph-claims'),
        ]],

        html.Footer('HealthFirst Australia · Revenue Intelligence · Built with Python & Plotly',
                    style={'textAlign': 'center', 'padding': '18px',
                           'color': '#7f8c8d', 'fontSize': '11px'}),
    ])

    # ── Callback — all charts update when any filter changes ─────────────────
    @app.callback(
        Output('kpi-section', 'children'),
        Output('graph-revenue',      'figure'),
        Output('graph-wait',         'figure'),
        Output('graph-satisfaction', 'figure'),
        Output('graph-specialty',    'figure'),
        Output('graph-churn',        'figure'),
        Output('graph-segments',     'figure'),
        Output('graph-claims',       'figure'),
        Input('filter-specialty', 'value'),
        Input('filter-clinic',    'value'),
        Input('filter-type',      'value'),
        Input('filter-dates',     'start_date'),
        Input('filter-dates',     'end_date'),
    )
    def update_all(specialty, clinic, appt_type, start_date, end_date):
        df = appointments.copy()

        if specialty != 'ALL':
            df = df[df['specialty'] == specialty]
        if clinic != 'ALL':
            df = df[df['clinic_id'] == clinic]
        if appt_type != 'ALL':
            df = df[df['appointment_type'] == appt_type]
        if start_date:
            df = df[df['appointment_date'] >= pd.Timestamp(start_date)]
        if end_date:
            df = df[df['appointment_date'] <= pd.Timestamp(end_date)]

        kpi_fig = fig_kpi_cards(df, patients)
        kpi_component = dcc.Graph(figure=kpi_fig)

        return (
            kpi_component,
            fig_revenue_trend(df),
            fig_wait_times(df),
            fig_satisfaction(surveys),
            fig_specialty_margin(df),
            fig_churn_state(patients),
            fig_segments(segments),
            fig_claims(claims),
        )

    return app


# ════════════════════════════════════════════════════════════════════════════
# STATIC HTML EXPORT
# ════════════════════════════════════════════════════════════════════════════

def build_static_html():
    figs = {
        'kpi':        fig_kpi_cards(appointments, patients),
        'revenue':    fig_revenue_trend(appointments),
        'wait':       fig_wait_times(appointments),
        'sat':        fig_satisfaction(surveys),
        'specialty':  fig_specialty_margin(appointments),
        'churn':      fig_churn_state(patients),
        'segments':   fig_segments(segments),
        'claims':     fig_claims(claims),
    }
    sections = [
        ('KPI Summary',                          'kpi'),
        ('Revenue Trend & Bulk Billing Rate',     'revenue'),
        ('Patient Wait Times by Specialty',       'wait'),
        ('Patient Satisfaction & Recommendation', 'sat'),
        ('Specialty Revenue & Profitability',     'specialty'),
        ('Patient Churn by State',                'churn'),
        ('Patient Engagement Segments',           'segments'),
        ('Billing Claim Rejections',              'claims'),
    ]

    parts = ["""<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'>
  <title>HealthFirst Australia — Revenue Intelligence Dashboard</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; }
    header { background: linear-gradient(135deg,#1a5276,#2980b9); color:white; padding:18px 30px; }
    header h1 { margin:0; font-size:22px; }
    header p  { margin:4px 0 0; font-size:13px; opacity:.85; }
    .section  { background:white; margin:14px 22px; border-radius:10px;
                box-shadow:0 2px 10px rgba(0,0,0,.08); overflow:hidden; }
    .section h2 { background:#f7f9fc; margin:0; padding:10px 18px;
                  font-size:13px; color:#1a5276; border-bottom:1px solid #e0e6ed; }
    footer { text-align:center; padding:18px; color:#7f8c8d; font-size:11px; }
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
        chart_html = pio.to_html(figs[key], full_html=False, include_plotlyjs=first)
        parts.append(f'<div class="section"><h2>{title}</h2>{chart_html}</div>\n')
        first = False

    parts.append('<footer>HealthFirst Australia · Revenue Intelligence · Built with Python &amp; Plotly</footer></body></html>')

    out = os.path.join(os.path.dirname(__file__), 'dashboard_export.html')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(parts))
    print(f'Dashboard saved: {os.path.abspath(out)}')


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--export', action='store_true', help='Export static HTML instead of running server')
    args = parser.parse_args()

    if args.export:
        build_static_html()
    else:
        app = build_dash_app()
        print('Starting dashboard at http://localhost:8050')
        app.run(debug=False, port=8050)
