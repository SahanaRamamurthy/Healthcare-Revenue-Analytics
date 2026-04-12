"""
generate_data.py  —  HealthFirst Australia
==========================================
Generates realistic synthetic healthcare data for a fictional Australian
private healthcare network operating across 8 cities.

Business scenarios engineered in:
  Months 1–6  : Stable operations, bulk billing rate ~82%
  Month 7     : Federal bulk-billing incentive reduced → revenue drop,
                patient out-of-pocket costs rise, some defer care
  Months 8–24 : Recovery via telehealth expansion; Mental Health backlog grows

Data quality issues intentionally introduced (fixed in Notebook 01):
  - NULL patient_gap values (should be 0 for bulk-billed appointments)
  - ~60 duplicate appointment rows
  - Inconsistent specialty names ('mental health' vs 'Mental Health' vs 'MH')
  - Impossible survey dates (survey before appointment)
  - NULL satisfaction scores (~4%)
  - Invalid Medicare number formats (~2%)
  - Appointments marked 'completed' with no billing record
"""

import random, math, csv, os
from datetime import date, timedelta

random.seed(42)

START_DATE   = date(2024, 1, 1)
END_DATE     = date(2025, 12, 31)
TOTAL_MONTHS = 24

OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
os.makedirs(OUT, exist_ok=True)

def rand_date(s, e):
    return s + timedelta(days=random.randint(0, (e-s).days))

def month_of(d):
    return (d.year - START_DATE.year)*12 + (d.month - START_DATE.month) + 1

def write_csv(fname, rows, fields):
    path = os.path.join(OUT, fname)
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)
    print(f'  {len(rows):>6,} rows  →  {fname}')

# ── Australian reference data ─────────────────────────────────────────────
STATES = {
    'NSW': 0.32, 'VIC': 0.26, 'QLD': 0.20,
    'WA':  0.10, 'SA':  0.07, 'TAS': 0.02,
    'ACT': 0.02, 'NT':  0.01,
}
STATE_CITIES = {
    'NSW': ['Sydney', 'Newcastle', 'Wollongong'],
    'VIC': ['Melbourne', 'Geelong', 'Ballarat'],
    'QLD': ['Brisbane', 'Gold Coast', 'Cairns'],
    'WA':  ['Perth', 'Fremantle', 'Bunbury'],
    'SA':  ['Adelaide', 'Mount Gambier'],
    'TAS': ['Hobart', 'Launceston'],
    'ACT': ['Canberra'],
    'NT':  ['Darwin'],
}
MALE_NAMES   = ['James','William','Oliver','Noah','Jack','Henry','Thomas','Liam',
                'Ethan','Lucas','Mason','Hugo','Daniel','Samuel','Benjamin']
FEMALE_NAMES = ['Charlotte','Olivia','Amelia','Isla','Mia','Ava','Grace','Sophie',
                'Lily','Ruby','Emma','Chloe','Isabella','Hannah','Zoe']
SURNAMES     = ['Smith','Jones','Williams','Brown','Wilson','Taylor','Johnson',
                'White','Martin','Anderson','Thompson','Harris','Walker','Hall',
                'Clarke','Mitchell','Roberts','Turner','Campbell','Evans']

HEALTH_FUNDS = {
    'Medibank':          0.27,
    'Bupa':              0.25,
    'HCF':               0.13,
    'NIB':               0.09,
    'HBF':               0.09,
    'ahm':               0.08,
    'Australian Unity':  0.05,
    'GMHBA':             0.04,
}

SPECIALTIES = ['GP','Cardiology','Mental Health','Oncology',
               'Orthopaedics','Paediatrics','Emergency','Dermatology']

# Specialty: (bulk_bill_base_rate, schedule_fee, private_multiplier, avg_staff_cost)
SPEC_CONFIG = {
    'GP':           (0.85, 42.85,  2.2, 18),
    'Cardiology':   (0.40, 155.00, 2.8, 65),
    'Mental Health':(0.62, 131.65, 2.0, 55),
    'Oncology':     (0.50, 195.00, 3.0, 80),
    'Orthopaedics': (0.32, 178.00, 2.9, 75),
    'Paediatrics':  (0.70, 85.50,  2.3, 35),
    'Emergency':    (0.90, 75.00,  1.8, 30),
    'Dermatology':  (0.38, 110.00, 2.5, 45),
}

CHRONIC_CONDITIONS = ['Diabetes','Hypertension','Mental Health Disorder',
                      'Cardiovascular Disease','Respiratory Disease','None']

REFERRAL_SOURCES = ['GP Referral','Specialist Referral','Self-Referral',
                    'Emergency','Online Booking','Health Fund Referral']

COMPLAINT_CATS = ['None','Wait Time','Billing','Communication','Care Quality','Facility']

# ── 1. STAFF (80) ─────────────────────────────────────────────────────────
print('Generating staff…')
CLINICS = [
    (1,'HealthFirst Sydney CBD',     'Sydney',     'NSW','metro'),
    (2,'HealthFirst Melbourne Central','Melbourne','VIC','metro'),
    (3,'HealthFirst Brisbane North',  'Brisbane',  'QLD','metro'),
    (4,'HealthFirst Perth West',      'Perth',     'WA', 'metro'),
    (5,'HealthFirst Adelaide',        'Adelaide',  'SA', 'metro'),
    (6,'HealthFirst Canberra',        'Canberra',  'ACT','metro'),
    (7,'HealthFirst Hobart',          'Hobart',    'TAS','regional'),
    (8,'HealthFirst Darwin',          'Darwin',    'NT', 'regional'),
]

staff = []
staff_map = {}
sid = 1
roles_spec = [
    ('GP',         'GP',           40),
    ('Specialist', 'Cardiology',    4),
    ('Specialist', 'Mental Health', 5),
    ('Specialist', 'Oncology',      3),
    ('Specialist', 'Orthopaedics',  4),
    ('Specialist', 'Paediatrics',   4),
    ('Specialist', 'Emergency',     8),
    ('Specialist', 'Dermatology',   4),
    ('Nurse',      None,           8),
]
for role, spec, count in roles_spec:
    for _ in range(count):
        gender = random.choice(['M','F'])
        fname  = random.choice(MALE_NAMES if gender=='M' else FEMALE_NAMES)
        clinic = random.choice(CLINICS)
        row = {
            'staff_id':       sid,
            'full_name':      f'Dr {fname} {random.choice(SURNAMES)}' if role in ('GP','Specialist') else f'{fname} {random.choice(SURNAMES)}',
            'role':           role,
            'specialty':      spec if spec else 'General Nursing',
            'clinic_id':      clinic[0],
            'clinic_name':    clinic[1],
            'city':           clinic[2],
            'state':          clinic[3],
            'clinic_type':    clinic[4],
            'years_experience': random.randint(2, 30),
            'avg_patient_rating': round(random.uniform(3.5, 5.0), 1),
        }
        staff.append(row)
        staff_map[sid] = row
        sid += 1

write_csv('staff.csv', staff,
    ['staff_id','full_name','role','specialty','clinic_id','clinic_name',
     'city','state','clinic_type','years_experience','avg_patient_rating'])

# ── 2. PATIENTS (3,000) ──────────────────────────────────────────────────
print('Generating patients…')
NUM_PATIENTS = 3000

state_pop   = list(STATES.keys())
state_wts   = list(STATES.values())
fund_names  = list(HEALTH_FUNDS.keys())
fund_wts    = list(HEALTH_FUNDS.values())

patients   = []
pat_map    = {}

for pid in range(1, NUM_PATIENTS+1):
    gender  = random.choice(['Male','Female','Non-binary'])
    fname   = random.choice(MALE_NAMES if gender=='Male' else FEMALE_NAMES)
    state   = random.choices(state_pop, weights=state_wts)[0]
    city    = random.choice(STATE_CITIES[state])
    age     = int(random.gauss(48, 18))
    age     = max(0, min(95, age))
    dob     = START_DATE - timedelta(days=age*365 + random.randint(0,364))

    ins_type = random.choices(
        ['bulk_bill','private_fund','self_pay'], weights=[0.45, 0.38, 0.17]
    )[0]
    fund = random.choices(fund_names, weights=fund_wts)[0] if ins_type=='private_fund' else 'None'

    n_conditions = random.choices([0,1,2], weights=[0.45,0.40,0.15])[0]
    if n_conditions == 0:
        condition = 'None'
    elif n_conditions == 1:
        condition = random.choice(CHRONIC_CONDITIONS[:-1])
    else:
        condition = 'Multiple'

    reg_date = rand_date(START_DATE - timedelta(days=365*3), date(2025,6,30))

    # Churn: higher for younger self-pay patients; higher in rural states
    churn_base = 0.18
    if ins_type == 'self_pay': churn_base += 0.08
    if state in ('NT','TAS'):  churn_base += 0.06
    if age < 35:               churn_base += 0.04
    churned = random.random() < churn_base
    last_visit = rand_date(START_DATE, END_DATE)
    if churned:
        last_visit = END_DATE - timedelta(days=random.randint(91, 500))
        if last_visit < reg_date:
            last_visit = reg_date + timedelta(days=30)

    # Invalid Medicare number format on ~2% of rows (quality issue)
    mc_num = f'{random.randint(1000,9999)} {random.randint(10000,99999)} {random.randint(1,9)}'
    if random.random() < 0.02:
        mc_num = f'INVALID-{random.randint(100,999)}'  # bad format

    row = {
        'patient_id':           pid,
        'full_name':            f'{fname} {random.choice(SURNAMES)}',
        'gender':               gender,
        'age':                  age,
        'age_group':            ('0-17' if age<18 else '18-34' if age<35 else
                                 '35-54' if age<55 else '55-74' if age<75 else '75+'),
        'date_of_birth':        dob,
        'state':                state,
        'city':                 city,
        'postcode':             f'{random.randint(2000,7999):04d}',
        'medicare_number':      mc_num,
        'insurance_type':       ins_type,
        'health_fund':          fund,
        'chronic_conditions':   condition,
        'referral_source':      random.choice(REFERRAL_SOURCES),
        'registration_date':    reg_date,
        'last_visit_date':      last_visit,
        'churn_flag':           1 if churned else 0,
        'total_appointments':   0,   # filled after appointments generated
        'total_billed':         0.0,
    }
    patients.append(row)
    pat_map[pid] = row

# ── 3. APPOINTMENTS (20,000) ─────────────────────────────────────────────
print('Generating appointments…')
NUM_APPTS = 20000

# Volume weight — month 7 drops 14%
def appt_weight(m):
    if m <= 6:   return 1.0 + (m-1)*0.015
    elif m == 7: return 0.86
    elif m <= 12:return 0.88 + (m-8)*0.008
    else:        return 0.94 + (m-12)*0.004

# Build dated appointment slots
all_dates = []
for m in range(1, TOTAL_MONTHS+1):
    ms = START_DATE + timedelta(days=(m-1)*30)
    me = min(ms + timedelta(days=29), END_DATE)
    n  = int(NUM_APPTS / TOTAL_MONTHS * appt_weight(m))
    for _ in range(n):
        all_dates.append(rand_date(ms, me))
while len(all_dates) < NUM_APPTS:
    all_dates.append(rand_date(START_DATE, END_DATE))
random.shuffle(all_dates)
all_dates = all_dates[:NUM_APPTS]

APP_TYPES   = ['in_person','telehealth','emergency']
APP_STATUSES= ['completed','completed','completed','completed','no_show','cancelled','rescheduled']

appointments = []
pat_appt_count = {p: 0 for p in pat_map}
pat_total_billed = {p: 0.0 for p in pat_map}

# Specialty-capable staff by specialty
spec_staff = {}
for sp_name in SPECIALTIES:
    spec_staff[sp_name] = [s['staff_id'] for s in staff
                           if s['specialty'] == sp_name or s['role'] == 'GP' and sp_name == 'GP']

for aid, adate in enumerate(all_dates, start=1):
    m   = month_of(adate)
    pid = random.randint(1, NUM_PATIENTS)
    pat = pat_map[pid]
    spec= random.choices(SPECIALTIES, weights=[40,8,12,4,6,8,10,12])[0]
    cfg = SPEC_CONFIG[spec]

    # Billing type: bulk billing rate drops in month 7+
    bb_rate = cfg[0] * (0.88 if m >= 7 else 1.0)
    if pat['insurance_type'] == 'bulk_bill':
        billing = random.choices(['bulk_bill','self_pay'], weights=[bb_rate, 1-bb_rate])[0]
    elif pat['insurance_type'] == 'private_fund':
        billing = random.choices(['gap_payment','private','bulk_bill'], weights=[0.5,0.35,0.15])[0]
    else:
        billing = random.choices(['self_pay','bulk_bill'], weights=[0.70,0.30])[0]

    sched_fee = cfg[1]
    if billing == 'bulk_bill':
        billed   = sched_fee
        rebate   = sched_fee
        gap      = 0.0
        ins_paid = 0.0
    elif billing == 'gap_payment':
        billed   = round(sched_fee * cfg[2], 2)
        rebate   = sched_fee
        gap      = round(billed - rebate, 2)
        ins_paid = round(gap * random.uniform(0.3, 0.8), 2)
    elif billing == 'private':
        billed   = round(sched_fee * cfg[2], 2)
        rebate   = 0.0
        gap      = 0.0
        ins_paid = round(billed * random.uniform(0.6, 0.95), 2)
    else:  # self_pay
        billed   = round(sched_fee * random.uniform(0.9, 1.4), 2)
        rebate   = 0.0
        gap      = billed
        ins_paid = 0.0

    status = random.choices(APP_STATUSES)[0]
    # Higher no-show in month 7+ (cost pressure)
    if m >= 7 and random.random() < 0.04:
        status = 'no_show'

    wait = max(0, int(random.gauss(
        14 if spec=='GP' else 28 if spec in ('Cardiology','Oncology','Orthopaedics') else
        45 if spec=='Mental Health' else 7 if spec=='Emergency' else 20,
        8
    )))
    # Mental health wait times blow out from month 8
    if spec == 'Mental Health' and m >= 8:
        wait = max(wait, int(random.gauss(55, 15)))

    # Appointment type: telehealth grows over time
    telehealth_prob = min(0.08 + m*0.012, 0.30)
    appt_type = 'emergency' if spec=='Emergency' else (
        'telehealth' if random.random() < telehealth_prob else 'in_person'
    )

    staff_pool = spec_staff.get(spec, [s['staff_id'] for s in staff])
    assigned   = random.choice(staff_pool) if staff_pool else 1
    clinic     = staff_map[assigned]['clinic_id']

    # Quality issue: ~3% NULL patient_gap (should be 0 for bulk_bill)
    gap_val = None if (random.random() < 0.03) else gap

    # Inconsistent specialty naming on ~10% of Mental Health rows
    spec_val = spec
    if spec == 'Mental Health' and random.random() < 0.10:
        spec_val = random.choice(['mental health','MH','Mental_Health'])

    row = {
        'appointment_id':   aid,
        'patient_id':       pid,
        'staff_id':         assigned,
        'clinic_id':        clinic,
        'appointment_date': adate,
        'specialty':        spec_val,
        'appointment_type': appt_type,
        'wait_days':        wait,
        'status':           status,
        'billing_type':     billing,
        'scheduled_fee':    sched_fee,
        'billed_amount':    billed if status=='completed' else 0.0,
        'medicare_rebate':  rebate if status=='completed' else 0.0,
        'patient_gap':      gap_val if status=='completed' else 0.0,
        'insurance_paid':   ins_paid if status=='completed' else 0.0,
        'staff_cost':       round(cfg[3] * random.uniform(0.9,1.1), 2),
    }
    appointments.append(row)
    if status == 'completed':
        pat_appt_count[pid]   += 1
        pat_total_billed[pid] += billed

# Inject ~60 duplicate rows
dupes = random.sample(appointments, 60)
for d in dupes:
    appointments.append(dict(d))

write_csv('appointments.csv', appointments,
    ['appointment_id','patient_id','staff_id','clinic_id','appointment_date',
     'specialty','appointment_type','wait_days','status','billing_type',
     'scheduled_fee','billed_amount','medicare_rebate','patient_gap',
     'insurance_paid','staff_cost'])

# Update patient totals
for pid in pat_map:
    pat_map[pid]['total_appointments'] = pat_appt_count[pid]
    pat_map[pid]['total_billed']       = round(pat_total_billed[pid], 2)

write_csv('patients.csv', patients,
    ['patient_id','full_name','gender','age','age_group','date_of_birth','state',
     'city','postcode','medicare_number','insurance_type','health_fund',
     'chronic_conditions','referral_source','registration_date','last_visit_date',
     'churn_flag','total_appointments','total_billed'])

# ── 4. SATISFACTION SURVEYS (6,000) ──────────────────────────────────────
print('Generating satisfaction surveys…')
surveys = []
# Only completed appointments can have surveys; ~35% response rate
completed_appts = [a for a in appointments if a['status']=='completed']
surveyed        = random.sample(completed_appts, min(6000, int(len(completed_appts)*0.35)))

for sid_s, appt in enumerate(surveyed, start=1):
    m    = month_of(appt['appointment_date'])
    spec = appt['specialty']

    # Mental Health and month 7-12 get worse scores
    if spec in ('Mental Health','MH','mental health') and m >= 7:
        overall    = random.choices([1,2,3,4,5,6,7,8,9,10], weights=[4,6,8,10,12,15,18,14,8,5])[0]
        wait_r     = random.choices([1,2,3,4,5], weights=[15,20,25,25,15])[0]
    elif m >= 7:
        overall    = random.choices([1,2,3,4,5,6,7,8,9,10], weights=[2,3,5,8,10,15,20,18,12,7])[0]
        wait_r     = random.choices([1,2,3,4,5], weights=[8,12,20,30,30])[0]
    else:
        overall    = random.choices([1,2,3,4,5,6,7,8,9,10], weights=[1,2,3,5,8,12,18,22,17,12])[0]
        wait_r     = random.choices([1,2,3,4,5], weights=[3,7,15,35,40])[0]

    doctor_r   = random.choices([1,2,3,4,5], weights=[1,3,8,28,60])[0]
    facility_r = random.choices([1,2,3,4,5], weights=[2,4,10,30,54])[0]
    recommend  = 1 if overall >= 7 else 0
    nps        = overall*10 - 50   # simplified NPS proxy

    # Complaint category
    if overall <= 4:
        complaint = random.choices(
            COMPLAINT_CATS[1:], weights=[30,20,15,25,10]
        )[0]
    elif wait_r <= 2:
        complaint = 'Wait Time'
    else:
        complaint = 'None'

    # Quality issue: ~4% NULL scores
    overall_val  = None if random.random() < 0.04 else overall
    # Quality issue: survey date sometimes before appointment (impossible)
    appt_date = appt['appointment_date']
    if isinstance(appt_date, str):
        from datetime import datetime
        appt_date = datetime.strptime(appt_date, '%Y-%m-%d').date()
    survey_date = appt_date + timedelta(days=random.randint(1, 14))
    if random.random() < 0.015:
        survey_date = appt_date - timedelta(days=random.randint(1, 5))  # impossible

    surveys.append({
        'survey_id':        sid_s,
        'patient_id':       appt['patient_id'],
        'appointment_id':   appt['appointment_id'],
        'survey_date':      survey_date,
        'specialty':        appt['specialty'],
        'overall_score':    overall_val,
        'wait_time_rating': wait_r,
        'doctor_rating':    doctor_r,
        'facility_rating':  facility_r,
        'would_recommend':  recommend,
        'nps_score':        nps,
        'complaint_category': complaint,
    })

write_csv('satisfaction_surveys.csv', surveys,
    ['survey_id','patient_id','appointment_id','survey_date','specialty',
     'overall_score','wait_time_rating','doctor_rating','facility_rating',
     'would_recommend','nps_score','complaint_category'])

# ── 5. BILLING CLAIMS (12,000) ───────────────────────────────────────────
print('Generating billing claims…')
claims = []
claimable = [a for a in appointments[:NUM_APPTS] if a['status']=='completed']
claim_sample = random.sample(claimable, min(12000, len(claimable)))

for cid, appt in enumerate(claim_sample, start=1):
    m    = month_of(appt['appointment_date'])
    btype= appt['billing_type']

    if btype == 'bulk_bill':
        claim_type = 'Medicare'
        claimed    = appt['billed_amount']
        # Rejection rate rises in month 7+ (policy change confusion)
        rej_prob   = 0.03 if m < 7 else 0.07
        if random.random() < rej_prob:
            status = 'rejected'
            approved = 0.0
            rejected = claimed
            reason   = random.choice(['Incorrect_Item_Number','Duplicate_Claim','Eligibility_Expired'])
        else:
            status   = 'approved'
            approved = claimed
            rejected = 0.0
            reason   = 'None'
    elif btype in ('gap_payment','private'):
        claim_type = 'Private_Insurance'
        claimed    = appt['insurance_paid']
        rej_prob   = 0.08
        if random.random() < rej_prob:
            status = 'rejected'
            approved = 0.0; rejected = claimed
            reason = random.choice(['Not_Covered','Pre_Auth_Required','Out_Of_Network'])
        elif random.random() < 0.05:
            status = 'partial'
            approved = round(claimed * random.uniform(0.5, 0.8), 2)
            rejected = round(claimed - approved, 2)
            reason = 'Benefit_Limit_Reached'
        else:
            status = 'approved'
            approved = claimed; rejected = 0.0; reason = 'None'
    else:
        claim_type = 'Self_Pay'
        claimed    = appt['billed_amount']
        if random.random() < 0.12:  # self-pay default rate
            status = 'unpaid'
            approved = 0.0; rejected = 0.0; reason = 'Patient_Non_Payment'
        else:
            status = 'paid'; approved = claimed; rejected = 0.0; reason = 'None'

    claim_date = appt['appointment_date'] + timedelta(days=random.randint(0, 14))

    claims.append({
        'claim_id':         cid,
        'appointment_id':   appt['appointment_id'],
        'patient_id':       appt['patient_id'],
        'claim_date':       claim_date,
        'claim_type':       claim_type,
        'claimed_amount':   round(claimed, 2),
        'approved_amount':  round(approved, 2),
        'rejected_amount':  round(rejected, 2),
        'claim_status':     status,
        'rejection_reason': reason,
    })

write_csv('billing_claims.csv', claims,
    ['claim_id','appointment_id','patient_id','claim_date','claim_type',
     'claimed_amount','approved_amount','rejected_amount','claim_status','rejection_reason'])

print('\nAll datasets generated successfully.')
print(f'Output: {os.path.abspath(OUT)}')
