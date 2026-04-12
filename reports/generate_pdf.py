"""
generate_pdf.py
===============
Generates a comprehensive PDF guide for the HealthFirst Australia Revenue Intelligence project.
Run with: python3 reports/generate_pdf.py
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
import os

OUT = os.path.join(os.path.dirname(__file__), 'HealthFirst_Revenue_Intelligence_Guide.pdf')

# ── Colour palette ──────────────────────────────────────────────────────────
DARK    = colors.HexColor('#2c3e50')
BLUE    = colors.HexColor('#3498db')
GREEN   = colors.HexColor('#2ecc71')
RED     = colors.HexColor('#e74c3c')
ORANGE  = colors.HexColor('#e67e22')
PURPLE  = colors.HexColor('#8e44ad')
LIGHT   = colors.HexColor('#ecf0f1')
MID     = colors.HexColor('#bdc3c7')
WHITE   = colors.white

# ── Custom styles ───────────────────────────────────────────────────────────
base = getSampleStyleSheet()

def style(name, parent='Normal', **kw):
    s = ParagraphStyle(name, parent=base[parent], **kw)
    return s

S = {
    'cover_title': style('cover_title', 'Title',
        fontSize=28, textColor=WHITE, alignment=TA_CENTER, leading=34, spaceAfter=8),
    'cover_sub':   style('cover_sub', 'Normal',
        fontSize=13, textColor=colors.HexColor('#ecf0f1'), alignment=TA_CENTER, leading=18),
    'h1':  style('h1',  fontSize=16, textColor=WHITE,  spaceAfter=4,  spaceBefore=2,  leading=20, fontName='Helvetica-Bold'),
    'h2':  style('h2',  fontSize=13, textColor=DARK,   spaceAfter=4,  spaceBefore=10, leading=16, fontName='Helvetica-Bold'),
    'h3':  style('h3',  fontSize=11, textColor=BLUE,   spaceAfter=3,  spaceBefore=6,  leading=14, fontName='Helvetica-Bold'),
    'body':style('body',fontSize=9.5,textColor=colors.HexColor('#2c3e50'), spaceAfter=4, leading=14, alignment=TA_JUSTIFY),
    'bullet': style('bullet', fontSize=9.5, textColor=DARK, spaceAfter=3, leading=13, leftIndent=16),
    'code': style('code', fontName='Courier', fontSize=8.5, textColor=colors.HexColor('#1a252f'),
                  backColor=colors.HexColor('#f4f6f8'), spaceAfter=2, leading=12, leftIndent=10),
    'caption': style('caption', fontSize=8, textColor=MID, alignment=TA_CENTER, spaceAfter=6),
    'small':   style('small', fontSize=8.5, textColor=colors.HexColor('#555'), leading=12),
    'tag_high':  style('tag_high',  fontSize=8, textColor=WHITE, backColor=RED,    fontName='Helvetica-Bold'),
    'tag_med':   style('tag_med',   fontSize=8, textColor=WHITE, backColor=ORANGE, fontName='Helvetica-Bold'),
    'tag_green': style('tag_green', fontSize=8, textColor=WHITE, backColor=GREEN,  fontName='Helvetica-Bold'),
}

# ── Helpers ─────────────────────────────────────────────────────────────────
def hr(color=MID, thickness=0.5):
    return HRFlowable(width='100%', thickness=thickness, color=color, spaceAfter=6, spaceBefore=4)

def section_header(text, color=DARK):
    data = [[Paragraph(text, S['h1'])]]
    t = Table(data, colWidths=[17*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), color),
        ('ROUNDEDCORNERS', [4]),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING',   (0,0), (-1,-1), 12),
    ]))
    return t

def info_box(text, bg=colors.HexColor('#eaf4fb'), border=BLUE):
    data = [[Paragraph(text, style('ib', fontSize=9.5, textColor=DARK, leading=13, alignment=TA_LEFT))]]
    t = Table(data, colWidths=[17*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (-1,-1), bg),
        ('LEFTPADDING',  (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING',   (0,0), (-1,-1), 8),
        ('BOTTOMPADDING',(0,0), (-1,-1), 8),
        ('LINECOLOR',    (0,0), (-1,-1), border),
        ('BOX',          (0,0), (-1,-1), 1.5, border),
        ('ROUNDEDCORNERS', [3]),
    ]))
    return t

def make_table(header, rows, col_widths=None, header_bg=DARK):
    data = [header] + rows
    if col_widths is None:
        col_widths = [17*cm / len(header)] * len(header)
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ('BACKGROUND',   (0,0), (-1,0),  header_bg),
        ('TEXTCOLOR',    (0,0), (-1,0),  WHITE),
        ('FONTNAME',     (0,0), (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',     (0,0), (-1,-1), 8.5),
        ('ROWBACKGROUNDS',(0,1),(-1,-1), [WHITE, colors.HexColor('#f7f9fc')]),
        ('GRID',         (0,0), (-1,-1), 0.4, MID),
        ('TOPPADDING',   (0,0), (-1,-1), 5),
        ('BOTTOMPADDING',(0,0), (-1,-1), 5),
        ('LEFTPADDING',  (0,0), (-1,-1), 7),
        ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
    ]
    t.setStyle(TableStyle(style_cmds))
    return t

def B(text): return f'<b>{text}</b>'
def C(text, color='#3498db'): return f'<font color="{color}">{text}</font>'
def bullet(text): return Paragraph(f'• {text}', S['bullet'])
def body(text):   return Paragraph(text, S['body'])
def h2(text):     return Paragraph(text, S['h2'])
def h3(text):     return Paragraph(text, S['h3'])
def sp(h=6):      return Spacer(1, h)

# ════════════════════════════════════════════════════════════════════════════
# CONTENT
# ════════════════════════════════════════════════════════════════════════════
story = []

# ── COVER PAGE ───────────────────────────────────────────────────────────────
cover_bg = Table(
    [[Paragraph('HealthFirst Australia — Revenue Intelligence', S['cover_title'])],
     [Paragraph('Complete Project Guide — End to End', S['cover_sub'])],
     [sp(8)],
     [Paragraph('What we built · Where to find it · How it works · Why every choice was made', S['cover_sub'])],
    ],
    colWidths=[17*cm]
)
cover_bg.setStyle(TableStyle([
    ('BACKGROUND',    (0,0), (-1,-1), DARK),
    ('TOPPADDING',    (0,0), (-1,-1), 14),
    ('BOTTOMPADDING', (0,0), (-1,-1), 14),
    ('LEFTPADDING',   (0,0), (-1,-1), 20),
    ('RIGHTPADDING',  (0,0), (-1,-1), 20),
    ('ROUNDEDCORNERS',[6]),
]))
story += [sp(40), cover_bg, sp(30)]

meta = make_table(
    ['Field', 'Detail'],
    [['Project Name',     'HealthFirst Australia — Revenue Intelligence'],
     ['Type',             'End-to-end data analytics portfolio project'],
     ['Data',             'Synthetic — 50,000 orders, 5,000 customers, 50 products'],
     ['Tech Stack',       'Python, pandas, scikit-learn, Plotly, SQL, Jupyter'],
     ['Notebooks',        '6 (fully executed with outputs)'],
     ['Charts Generated', '22 PNG files'],
     ['SQL Files',        '4'],
     ['Python Modules',   '3 reusable src/ files'],
     ['Key Output',       'Churn model, RFM segments, $6M leakage quantified, 6 recommendations'],
    ],
    col_widths=[5*cm, 12*cm]
)
story += [meta, PageBreak()]

# ── SECTION 1: BIG PICTURE ───────────────────────────────────────────────────
story += [section_header('1.  The Big Picture — What Is This Project?', DARK), sp(8)]
story += [body(
    'This project builds a <b>Revenue Intelligence System</b> for a fictional Australian private '
    'healthcare network called <b>HealthFirst Australia</b>. The network is experiencing three problems:'
), sp(4)]
for item in [
    'Revenue dropped 15% in one month — driven by a Medicare bulk billing policy change',
    'Bulk billing rate fell 8 percentage points, increasing patient out-of-pocket costs',
    'Patient no-show rate increased 4 percentage points, wasting clinical capacity',
]:
    story.append(bullet(item))
story += [sp(6), body(
    'The goal is to <b>diagnose the root causes</b>, <b>predict which patients will churn next</b>, '
    '<b>quantify every dollar of billing leakage</b>, and deliver <b>specific, numbered recommendations</b> '
    'with estimated AUD impacts — exactly as a healthcare data analyst would.'
), sp(8), hr()]

story += [h2('Skills this project demonstrates'), sp(4)]
story.append(make_table(
    ['Skill Area', 'Evidence in This Project'],
    [['SQL',                    'Schema design, KPI queries, cleaning queries, RCA analysis (4 SQL files)'],
     ['Python / pandas',        'Data generation, cleaning, feature engineering across 6 notebooks'],
     ['Machine Learning',       'Logistic Regression + Gradient Boosting churn model with ROC-AUC evaluation'],
     ['Data Visualisation',     '22 charts auto-generated across 6 notebooks'],
     ['Business Thinking',      'Root cause analysis, revenue decomposition, segment action playbook'],
     ['Dashboarding',           'Interactive Plotly dashboard exported as self-contained HTML'],
     ['Documentation',          'Metrics dictionary (27 KPIs), executive summary, this README'],
    ],
    col_widths=[4.5*cm, 12.5*cm]
))
story += [PageBreak()]

# ── SECTION 2: WHERE THE DATA CAME FROM ─────────────────────────────────────
story += [section_header('2.  Where Did the Data Come From?', BLUE), sp(8)]
story += [info_box(
    '⚠  We did NOT download data from Kaggle or the internet. '
    'We wrote a Python script that <b>generates fake-but-realistic data</b>. '
    'Here is exactly why — and what it creates.'
), sp(8)]
story += [body(
    'No single public dataset has all five dimensions at once: revenue data with discounts, '
    'customer churn status, support satisfaction scores, refund details, AND 24 months of history '
    'with a specific engineered revenue drop. Generating it ourselves gives complete control '
    'over every business scenario.'
), sp(6)]

story += [h2('The data generator: src/generate_data.py'), sp(4)]
story.append(make_table(
    ['File Created', 'Rows', 'What it Contains'],
    [['data/raw/customers.csv',        '5,000',  'Customer profiles: name, region, signup date, acquisition channel, churn status, lifetime value'],
     ['data/raw/products.csv',         '50',     'Product catalog: name, category, unit price, unit cost, supplier, margin %'],
     ['data/raw/orders.csv',           '50,050', '50,000 real orders + 50 injected duplicates. Each row: who bought what, when, how much, discount, refund status'],
     ['data/raw/support_tickets.csv',  '3,000',  'Customer support interactions: ticket type, resolution time, satisfaction score (1–5)'],
     ['data/raw/engagement.csv',       '7,680',  'Monthly snapshots of customer activity: logins, purchases, email opens, days since last buy'],
    ],
    col_widths=[4.5*cm, 1.8*cm, 10.7*cm]
))
story += [sp(8), h2('Business scenarios engineered into the data'), sp(4)]
for item in [
    '<b>Months 1–6:</b> Normal growth — order volume increasing slightly each month (~$50k revenue/month)',
    '<b>Month 7:</b> A deliberate 15% revenue drop — fewer orders, heavier discounts, more refunds',
    '<b>Months 8–24:</b> Slow recovery with lingering margin pressure',
    '<b>Affiliate/Social channels:</b> Engineered to have 30–35% churn rate vs Organic at 10%',
    '<b>Months 7–12:</b> Support quality deliberately degraded — longer resolution times, lower satisfaction',
]:
    story.append(bullet(item))
story += [sp(8), h2('Data quality problems intentionally introduced'), sp(4)]
story.append(make_table(
    ['Problem', 'In Which File', 'What Was Wrong'],
    [['NULL discount_amount',      'orders.csv',           'Some rows had blank instead of 0'],
     ['~50 duplicate order rows',  'orders.csv',           'Same transaction recorded twice'],
     ['Negative net_revenue',      'orders.csv',           'A few rows had −$200 revenue (impossible)'],
     ['Negative fulfillment_days', 'orders.csv',           '"Delivered 3 days before ordered" (impossible)'],
     ['Category typos',            'products.csv',         '"Electronisc", "SW", "accessores"'],
     ['Mixed date formats',        'support_tickets.csv',  'Some dates in MM/DD/YYYY instead of YYYY-MM-DD'],
     ['NULL satisfaction scores',  'support_tickets.csv',  '3% of rows had no score'],
    ],
    col_widths=[4.5*cm, 4.5*cm, 8*cm]
))
story += [sp(4), body(
    'This mimics exactly what real-world messy data looks like — and fixing it shows you know '
    'what professional data cleaning involves.'
), PageBreak()]

# ── SECTION 3: FOLDER STRUCTURE ─────────────────────────────────────────────
story += [section_header('3.  Project Folder Structure — What Lives Where', DARK), sp(8)]
story += [body(
    'The folder layout follows a professional data pipeline pattern used in industry. '
    'There are three data folders on purpose — each serving a different stage.'
), sp(6)]
story.append(make_table(
    ['Folder / File', 'Purpose'],
    [['data/raw/',                    'Original files exactly as generated. Never overwritten. If cleaning breaks, restart from here.'],
     ['data/cleaned/',                'Fixed versions. Same columns, corrected values. Output of Notebook 01.'],
     ['data/processed/',              'New files created BY analysis. ML scores, RFM segments, leakage summaries. Output of Notebooks 03–06.'],
     ['notebooks/',                   '6 Jupyter notebooks — the step-by-step analysis. Must run in order (each feeds the next).'],
     ['sql/',                         '4 SQL files — same logic as notebooks but written for a database. Proves SQL skills.'],
     ['src/',                         '3 reusable Python modules. Code extracted from notebooks so it can be called again on new data.'],
     ['dashboard/',                   'Plotly dashboard. app.py generates dashboard_export.html — open in any browser.'],
     ['reports/',                     '22 PNG charts auto-generated by notebooks + executive_summary.md'],
     ['01_business_problem.md',       'Written before any code. Defines the problem, stakeholders, and success criteria.'],
     ['02_metrics_dictionary.md',     '27 KPIs defined: formula, source table, business meaning.'],
     ['README.md',                    'First thing a recruiter sees on GitHub. Explains the whole project.'],
    ],
    col_widths=[5*cm, 12*cm]
))
story += [PageBreak()]

# ── SECTION 4: NOTEBOOKS ─────────────────────────────────────────────────────
story += [section_header('4.  The Six Notebooks — Step by Step', BLUE), sp(6)]
story += [info_box(
    'Notebooks must be run in order: 01 → 02 → 03 → 04 → 05 → 06. '
    'Each notebook reads cleaned/processed files from the previous one. '
    'All 6 have already been executed and their outputs are saved.'
), sp(8)]

# NB01
story += [h2('Notebook 01 — Data Cleaning'), sp(4)]
story += [
    body('<b>File:</b> notebooks/01_data_cleaning.ipynb'),
    body('<b>Reads from:</b> data/raw/ (5 messy CSV files)'),
    body('<b>Saves to:</b> data/cleaned/ (5 clean CSV files)'),
    sp(4),
    body('Loads the raw data, audits every column for problems, and fixes all 7 issues listed in Section 2. '
         'Produces a before/after quality summary table and a bar chart showing null count reductions. '
         'This is the foundation — no downstream analysis is trustworthy without clean data.'),
    sp(4),
]
story.append(make_table(
    ['Fix Applied', 'Code Logic'],
    [['NULL discount → 0',               'orders["discount_amount"].fillna(0)'],
     ['Remove duplicates',               'drop_duplicates(subset="order_id", keep="first")'],
     ['Negative net_revenue → recalculate','net = gross − discount where net < 0'],
     ['Negative fulfillment_days → NaN', 'orders.loc[mask, "fulfillment_days"] = np.nan'],
     ['Category typos → standard names', 'Apply CATEGORY_MAP dictionary'],
     ['Mixed date formats → ISO',        'pd.to_datetime(infer_datetime_format=True)'],
     ['NULL satisfaction → median (3)',  'fillna(tickets["satisfaction_score"].median())'],
    ],
    col_widths=[5.5*cm, 11.5*cm]
))
story += [sp(4), body('Chart saved: reports/data_quality_report.png'), sp(8), hr()]

# NB02
story += [h2('Notebook 02 — KPI Analysis & Root Cause'), sp(4)]
story += [
    body('<b>File:</b> notebooks/02_kpi_analysis.ipynb'),
    body('<b>Reads from:</b> data/cleaned/'),
    body('<b>Saves charts to:</b> reports/'),
    sp(4),
    body('Calculates 15+ business KPIs grouped into: revenue, profitability, customer, leakage, and channel metrics. '
         'The most important analysis is the <b>Root Cause Decomposition</b> of the Month 7 revenue drop.'),
    sp(4),
]
story.append(info_box(
    '<b>Root Cause Decomposition (Bridge Analysis):</b><br/>'
    'Revenue drop = Volume Effect + Price Effect + Mix/Quality Effect<br/><br/>'
    'Volume Effect: Month 7 had fewer orders than Month 6. The dollar impact = (M7 orders − M6 orders) × M6 avg price.<br/>'
    'Price Effect: Average order value fell (more discounting). Impact = (M7 AOV − M6 AOV) × M7 order count.<br/>'
    'Mix/Quality: Remaining gap = cheaper products being bought + more refunds.'
))
story += [sp(4), body('Charts saved: revenue_trend.png, rca_waterfall.png, discount_refund_trend.png, churn_by_channel.png, revenue_leakage.png'), sp(8), hr()]

# NB03
story += [h2('Notebook 03 — Churn Prediction (Machine Learning)'), sp(4)]
story += [
    body('<b>File:</b> notebooks/03_churn_prediction.ipynb'),
    body('<b>Reads from:</b> data/cleaned/ + src/churn_model.py'),
    body('<b>Saves to:</b> data/processed/customers_churn_scored.csv, data/processed/retention_priority_list.csv'),
    sp(4),
    body('Builds a machine learning model that reads customer behaviour signals and predicts '
         'which customers are about to leave (churn). Two models are compared.'),
    sp(4),
]
story.append(make_table(
    ['Feature (Input)', 'What It Captures'],
    [['days_since_purchase',    'How recently they bought — the strongest churn signal'],
     ['order_count',            'Total orders — frequent buyers are less likely to churn'],
     ['avg_order_value',        'How much they spend per order'],
     ['avg_discount',           'Do they only buy when discounted? Signals price sensitivity'],
     ['refund_rate',            'Do they return products often? Could signal dissatisfaction'],
     ['ticket_count',           'How many support issues have they had?'],
     ['avg_satisfaction',       'How happy were they with support resolution?'],
     ['acquisition_channel',    'One-hot encoded: paid_search, organic, social, affiliate, email'],
     ['customer_segment',       'One-hot encoded: premium, standard, budget'],
     ['region',                 'One-hot encoded: US-East, US-West, EU, APAC, LATAM'],
    ],
    col_widths=[5*cm, 12*cm]
))
story += [sp(4)]
story.append(make_table(
    ['Model', 'Why Used', 'Evaluated By'],
    [['Logistic Regression', 'Simple baseline — like a scorecard. Easy to explain to business.', 'ROC-AUC, precision-recall, CV score'],
     ['Gradient Boosting',   'Advanced — combines hundreds of decision trees. More accurate.', 'ROC-AUC, confusion matrix, feature importance'],
    ],
    col_widths=[4*cm, 8*cm, 5*cm]
))
story += [sp(4),
    body('Every customer gets a <b>churn_probability</b> (0.0–1.0) and a <b>risk band</b>: Low / Medium / High. '
         'The top 20 highest-value at-risk customers are exported as a retention priority list for the sales team.'),
    sp(4),
    body('Charts saved: churn_feature_correlation.png, churn_model_evaluation.png, churn_confusion_matrix.png, churn_feature_importance.png, churn_risk_distribution.png'),
    sp(8), hr()]

# NB04
story += [h2('Notebook 04 — RFM Customer Segmentation'), sp(4)]
story += [
    body('<b>File:</b> notebooks/04_rfm_segmentation.ipynb'),
    body('<b>Reads from:</b> data/cleaned/ + data/processed/customers_churn_scored.csv'),
    body('<b>Saves to:</b> data/processed/customers_rfm_segments.csv'),
    sp(4),
    body('<b>RFM = Recency · Frequency · Monetary.</b> Every customer is scored 1–4 on each dimension (4 = best), '
         'then those three scores are combined to assign them to one of 8 named segments.'),
    sp(4),
]
story.append(make_table(
    ['Segment', 'Who They Are', 'Recommended Action'],
    [['Champions',           'Bought recently, buy often, big spenders',   'Reward, referral program, early access'],
     ['Loyal Customers',     'Buy regularly, good spend',                   'Upsell, cross-sell, loyalty tier upgrade'],
     ['Potential Loyalists', 'Recent but not yet frequent',                 'Follow-up, subscription offer'],
     ['New Customers',       'Just placed first order',                     'Onboarding emails, day-30 prompt'],
     ['Promising',           'Recent, low spend',                           'Product education, targeted campaigns'],
     ['At Risk',             'Used to buy often, now going quiet',          'Re-engagement email with offer'],
     ['Cannot Lose Them',    'High past spend, becoming inactive — URGENT', 'Personal phone call or email from account manager'],
     ['Hibernating',         'Long inactive, low spend',                    'Low-cost win-back or accept loss'],
    ],
    col_widths=[3.5*cm, 6.5*cm, 7*cm]
))
story += [sp(4), body('Charts saved: rfm_segments.png, rfm_revenue_share.png, rfm_churn_by_segment.png'), sp(8), hr()]

# NB05
story += [h2('Notebook 05 — Profitability Analysis'), sp(4)]
story += [
    body('<b>File:</b> notebooks/05_profitability_analysis.ipynb'),
    body('<b>Reads from:</b> data/cleaned/'),
    body('<b>Saves to:</b> data/processed/product_profitability.csv, data/processed/category_profitability.csv'),
    sp(4),
    body('Revenue ≠ Profit. This notebook finds which products are actually making money after '
         'subtracting the cost to produce/buy them (COGS = Cost of Goods Sold).'),
    sp(4),
    body('<b>Gross Profit = Net Revenue (after discount) − COGS (quantity × unit_cost)</b>'),
    sp(4),
]
for item in [
    'Category-level P&L — which product families have best/worst margins',
    'Product-level P&L — top 10 by profit vs top 10 by revenue (often very different lists)',
    '"Loss leaders" — products ranked high by sales but near the bottom on actual profit',
    'Revenue rank vs Profit rank scatter — visually shows misleading bestsellers',
    'Margin trend over 24 months — confirms erosion during months 7–12',
    'Channel profitability — web vs mobile vs affiliate order economics',
]:
    story.append(bullet(item))
story += [sp(4), body('Charts saved: profitability_category.png, profitability_products.png, margin_trend.png'), sp(8), hr()]

# NB06
story += [h2('Notebook 06 — Revenue Leakage Deep Dive'), sp(4)]
story += [
    body('<b>File:</b> notebooks/06_revenue_leakage.ipynb'),
    body('<b>Reads from:</b> data/cleaned/'),
    body('<b>Saves to:</b> data/processed/leakage_summary.csv, data/processed/recovery_scenarios.csv'),
    sp(4),
    body('Quantifies every dollar that could have been revenue but was not. Four leakage buckets:'),
    sp(4),
]
story.append(make_table(
    ['Source', 'Amount', '% of Gross Revenue'],
    [['Discount Waste',        '$1,961,083',  '6.7%'],
     ['Refunds & Returns',     '$1,631,659',  '5.6%'],
     ['Cancellations',         '$1,371,402',  '4.7%'],
     ['Churned LTV (est.)',    '$1,209,645',  '4.1%'],
     [B('TOTAL LEAKAGE'),      B('$6,173,789'), B('21.1%')],
    ],
    col_widths=[5.5*cm, 5*cm, 6.5*cm]
))
story += [sp(6),
    body('Three recovery scenarios are modelled (Conservative 25% / Moderate 50% / Aggressive 75% fix) '
         'to show how much revenue could be recovered with different levels of operational change — '
         'giving the business team a dollar figure to justify the effort.'),
    sp(4),
    body('Charts saved: leakage_waterfall.png, leakage_trend.png, leakage_recovery_scenarios.png'),
    PageBreak()]

# ── SECTION 5: SQL FILES ─────────────────────────────────────────────────────
story += [section_header('5.  The SQL Files', DARK), sp(8)]
story += [body(
    'The SQL files in sql/ do the same analysis as the notebooks, but written for a PostgreSQL database. '
    'They exist for two reasons: (1) real company data lives in databases, not CSV files, and '
    '(2) demonstrating SQL skills separately from Python.'
), sp(6)]
story.append(make_table(
    ['File', 'What It Does'],
    [['sql/schema.sql',           '7-table database design: CREATE TABLE statements, foreign keys, indexes for performance, and 2 pre-built analytical views'],
     ['sql/cleaning_queries.sql', 'SQL version of Notebook 01 — audit queries to find problems, UPDATE/DELETE queries to fix them, validation queries after fixing'],
     ['sql/kpi_queries.sql',      '15 KPI calculations written as SELECT queries — monthly revenue, MoM growth, gross margin, churn rates, leakage, AOV, regional performance'],
     ['sql/analysis_queries.sql', 'Advanced analysis: Month 7 root cause in SQL, churn risk scoring (rule-based), high-value at-risk customer list, recovery recommendations'],
    ],
    col_widths=[5*cm, 12*cm]
))
story += [PageBreak()]

# ── SECTION 6: PYTHON MODULES ────────────────────────────────────────────────
story += [section_header('6.  The Python Modules (src/)', BLUE), sp(8)]

story += [h2('src/generate_data.py'), sp(3),
    body('The data factory. Run once, creates all 5 raw CSV files. Uses random.seed(42) — a fixed seed '
         'means every run produces identical data. This is called <b>reproducibility</b> and is '
         'a best practice in data science and engineering.'), sp(8)]

story += [h2('src/churn_model.py'), sp(3),
    body('A reusable ML engine with 4 functions you can call from any notebook or script:'), sp(4)]
story.append(make_table(
    ['Function', 'What It Does'],
    [['build_features(customers, orders, tickets)', 'Joins three tables, engineers all features, one-hot encodes categoricals → returns feature matrix'],
     ['train_model(features, model_type)',           'Trains Logistic Regression or Gradient Boosting, runs 5-fold cross-validation, returns model + metrics'],
     ['score_customers(features, model)',            'Applies trained model to all customers → returns churn_probability + risk_band per customer'],
     ['get_feature_importance(result)',              'Extracts and ranks which features matter most for the trained model'],
    ],
    col_widths=[7*cm, 10*cm]
))
story += [sp(6),
    body('Why separate from the notebook? If you get new customer data next month, you call '
         'score_customers(new_data, model) — no rewriting, no re-running the entire notebook.'),
    sp(8)]

story += [h2('src/recommendations.py'), sp(3),
    body('An automated recommendations engine. Reads all processed outputs and generates 6 '
         'prioritised business recommendations. Run this file and it writes '
         'reports/executive_summary.md automatically. Each recommendation includes:'), sp(4)]
for item in [
    'Finding (what the data shows)',
    'Estimated dollar impact',
    'Specific action steps',
    'KPIs to track',
    'Implementation timeline',
]:
    story.append(bullet(item))
story += [PageBreak()]

# ── SECTION 7: DASHBOARD ─────────────────────────────────────────────────────
story += [section_header('7.  The Dashboard', DARK), sp(8)]
story += [
    body('<b>File:</b> dashboard/app.py'),
    body('<b>Output:</b> dashboard/dashboard_export.html — open this in any browser'),
    sp(6),
    body('Built with <b>Plotly</b> (Python charting library). Reads all clean and processed data '
         'and renders 7 interactive chart sections into a single self-contained HTML file. '
         'No server, no Python, no license needed — just open the HTML file in Chrome.'),
    sp(6),
]
story.append(make_table(
    ['Dashboard Section', 'What It Shows'],
    [['KPI Cards',                   '6 headline numbers: Total revenue, orders, churn rate, margin %, AOV, discount waste'],
     ['Revenue & Growth Trend',      'Monthly net revenue line chart + MoM growth % bar chart'],
     ['Revenue Leakage Waterfall',   'Gross revenue → minus discounts → minus refunds → minus cancellations → realized revenue'],
     ['Category Profitability',      'Gross margin % and revenue vs gross profit side by side for all 5 categories'],
     ['Churn by Channel',            'Churn rate % and average LTV per acquisition channel'],
     ['RFM Segment Treemap',         'All 8 customer segments sized by total value, coloured by average spend'],
     ['Churn Risk Distribution',     'Histogram of churn probability scores + pie of Low/Medium/High risk bands'],
    ],
    col_widths=[5.5*cm, 11.5*cm]
))
story += [sp(6),
    body('To regenerate: python dashboard/app.py --static'),
    body('To run live interactive version: pip install dash, then python dashboard/app.py'),
    PageBreak()]

# ── SECTION 8: REPORTS ───────────────────────────────────────────────────────
story += [section_header('8.  Reports Folder — All 22 Charts', BLUE), sp(8)]
story.append(make_table(
    ['Chart File', 'Made By', 'What It Shows'],
    [['data_quality_report.png',      'Notebook 01', 'Null counts and row counts before vs after cleaning'],
     ['revenue_trend.png',            'Notebook 02', 'Monthly revenue (Gross / Net / Realized) + MoM growth'],
     ['rca_waterfall.png',            'Notebook 02', 'Month 7 revenue drop decomposed into Volume + Price + Mix'],
     ['discount_refund_trend.png',    'Notebook 02', 'Discount % and refund rate month by month'],
     ['revenue_leakage.png',          'Notebook 02', 'Leakage pie chart by source'],
     ['churn_by_channel.png',         'Notebook 02', 'Churn rate and LTV by acquisition channel'],
     ['churn_feature_correlation.png','Notebook 03', 'Which features correlate most with churning'],
     ['churn_model_evaluation.png',   'Notebook 03', 'ROC curves + Precision-Recall curves for both models'],
     ['churn_confusion_matrix.png',   'Notebook 03', 'How many customers correctly classified as Active vs Churned'],
     ['churn_feature_importance.png', 'Notebook 03', 'Top 15 most predictive features in Gradient Boosting model'],
     ['churn_risk_distribution.png',  'Notebook 03', 'Distribution of churn probabilities + risk band pie chart'],
     ['rfm_segments.png',             'Notebook 04', 'Customer count + revenue + recency/frequency scatter'],
     ['rfm_revenue_share.png',        'Notebook 04', 'Revenue share pie by RFM segment'],
     ['rfm_churn_by_segment.png',     'Notebook 04', 'Churn rate per RFM segment vs overall average'],
     ['profitability_category.png',   'Notebook 05', 'Revenue vs gross profit + margin % by category'],
     ['profitability_products.png',   'Notebook 05', 'Top 10 products by profit + revenue rank vs profit rank'],
     ['margin_trend.png',             'Notebook 05', 'Margin % monthly trend + stacked COGS/profit/discount bar'],
     ['leakage_waterfall.png',        'Notebook 06', 'Gross → Net → Realized revenue waterfall'],
     ['leakage_trend.png',            'Notebook 06', 'Monthly leakage amount and % trend'],
     ['leakage_recovery_scenarios.png','Notebook 06','3 recovery scenarios side by side'],
     ['category_profitability.png',   'Notebook 05', 'Category profitability deep-dive'],
     ['executive_summary.md',         'src/recommendations.py', '6 recommendations with $ impact, actions, timelines'],
    ],
    col_widths=[5.5*cm, 3*cm, 8.5*cm]
))
story += [PageBreak()]

# ── SECTION 9: WHY NOT X ─────────────────────────────────────────────────────
story += [section_header('9.  Why We Did Not Use Other Things', DARK), sp(8)]
story.append(make_table(
    ['Alternative', 'Why We Did Not Use It'],
    [['Real Kaggle dataset',         'No public dataset has all 5 dimensions (orders + customers + products + support + engagement) with engineered business scenarios'],
     ['TensorFlow / PyTorch (deep learning)', 'Deep learning is for images, text, audio. For tabular spreadsheet-style data, Gradient Boosting wins and is far easier to explain to stakeholders'],
     ['Power BI / Tableau',          'Requires licenses and separate software. Cannot be committed to GitHub as code. Plotly produces same quality charts in pure Python.'],
     ['Excel',                       'Breaks at 50k rows, no version control, no ML, no reproducibility. Cannot run programmatic recommendations.'],
     ['SQL only (no Python)',         'SQL needs a database server. Python+pandas runs directly on CSV files — anyone can run it with just Python installed. SQL files are provided as a bonus.'],
     ['One big script',              'Splitting into 6 notebooks lets you show your reasoning step by step. Recruiters can read each one like a chapter. Reusable src/ modules prevent code duplication.'],
    ],
    col_widths=[4.5*cm, 12.5*cm]
))
story += [PageBreak()]

# ── SECTION 10: HOW TO RUN ────────────────────────────────────────────────────
story += [section_header('10. How to Run the Project', BLUE), sp(8)]
story.append(make_table(
    ['Step', 'Command', 'What Happens'],
    [['1', 'pip install -r requirements.txt',        'Installs all Python libraries'],
     ['2', 'python src/generate_data.py',             'Creates 5 raw CSV files in data/raw/'],
     ['3', 'jupyter notebook',                        'Opens browser — run notebooks 01→02→03→04→05→06 in order'],
     ['4', 'open dashboard/dashboard_export.html',    'Opens the interactive dashboard in your browser (no server needed)'],
     ['5', 'python src/recommendations.py',           'Re-generates reports/executive_summary.md'],
    ],
    col_widths=[1*cm, 6.5*cm, 9.5*cm]
))
story += [sp(10)]
story.append(info_box(
    '<b>Quick start (skip notebooks, just see the dashboard):</b><br/><br/>'
    'The notebooks have already been executed. All outputs are saved. '
    'You can open dashboard/dashboard_export.html right now in any browser '
    'and see all charts without running a single line of code.'
))
story += [PageBreak()]

# ── SECTION 11: KEY FINDINGS ─────────────────────────────────────────────────
story += [section_header('11. Key Findings', DARK), sp(8)]
story.append(make_table(
    ['Finding', 'Evidence', 'Recommended Action'],
    [['Month 7 revenue drop was caused by 3 things simultaneously',
      'Bridge analysis: Volume −8%, AOV −3%, Mix/Quality −4%',
      'Address volume (churn), AOV (discount policy), and quality (returns) separately'],
     ['Affiliate channel has ~35% churn, Organic has ~10%',
      'churn_by_channel.png + customers_clean.csv',
      'Reallocate 20% of affiliate budget to organic/email campaigns'],
     ['Discount waste = $1.96M (6.7% of gross revenue)',
      'leakage_summary.csv',
      'Implement discount approval workflow for orders >15% off'],
     ['Software & Subscriptions have >70% margins but receive the most discounts',
      'category_profitability.csv + discount_refund_trend.png',
      'Remove automatic discounts on high-margin categories'],
     ['Satisfaction < 2.5 correlates with 3× higher churn probability',
      'churn_feature_correlation.png + churn_model_evaluation.png',
      'Fix support SLA: 100% first response within 8 hours'],
     ['20 specific customers identified as high-value and high-risk right now',
      'data/processed/retention_priority_list.csv',
      'Personal outreach within 2 weeks'],
    ],
    col_widths=[4.5*cm, 5.5*cm, 7*cm]
))
story += [sp(10)]
story.append(info_box(
    '<b>One-sentence summary for interviews:</b><br/><br/>'
    '"I built an end-to-end revenue intelligence system in Python and SQL — I generated realistic '
    'Australian healthcare data, cleaned it, diagnosed a 15% revenue drop using root cause analysis, '
    'predicted patient churn with machine learning, segmented patients into 7 RFV tiers, quantified '
    'billing leakage across 5 buckets, and delivered 6 dollar-quantified recommendations in an '
    'automated report with an interactive Plotly dashboard."',
    bg=colors.HexColor('#eafaf1'),
    border=GREEN
))

# ── Build PDF ────────────────────────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 7)
    canvas.setFillColor(MID)
    canvas.drawString(2*cm, 1.2*cm, 'HealthFirst Australia — Revenue Intelligence — Project Guide')
    canvas.drawRightString(19*cm, 1.2*cm, f'Page {doc.page}')
    canvas.restoreState()

doc = SimpleDocTemplate(
    OUT,
    pagesize=A4,
    leftMargin=2*cm, rightMargin=2*cm,
    topMargin=2.2*cm, bottomMargin=2*cm,
    title='HealthFirst Australia — Revenue Intelligence Guide',
    author='Revenue Intelligence System',
)
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print(f'PDF saved: {OUT}')
