# HealthFirst Australia — Business Problem

## 1. Organisation Overview

**HealthFirst Australia** is a private healthcare network operating 20 clinics across six Australian states (NSW, VIC, QLD, WA, SA, TAS) and two territories (ACT, NT). The network employs 80 clinical and allied health staff spanning General Practice, Cardiology, Mental Health, Physiotherapy, Paediatrics, Dermatology, Oncology, and Orthopaedics.

---

## 2. The Business Problem

In **Month 7** of the analysis period, HealthFirst Australia experienced a simultaneous decline across three key metrics:

| Metric | Direction | Magnitude |
|---|---|---|
| Gross Revenue | ↓ | −15% month-on-month |
| Bulk Billing Rate | ↓ | −8 percentage points |
| Patient No-Show Rate | ↑ | +4 percentage points |

These shifts occurred against a backdrop of:
- A federal **Medicare bulk billing incentive policy change** that reduced rebate rates for certain specialties
- Growing **patient out-of-pocket costs** prompting appointment deferrals
- A **Mental Health backlog** following reduced telehealth funding

The network's leadership needs to understand **why** revenue fell, **which patients are at risk of churning**, and **where the largest financial recovery opportunities** lie.

---

## 3. Key Questions

1. **Root Cause**: Is the Month 7 revenue drop driven by fewer appointments (volume), lower revenue per appointment (rate), or a shift in billing mix toward lower-revenue types?
2. **Churn Risk**: Which patients are likely to switch to another provider in the next 90 days, and what is the total lifetime value at risk?
3. **Billing Leakage**: How much revenue is being lost to Medicare claim rejections, no-shows, bulk billing erosion, and self-pay defaults — and what is recoverable?
4. **Wait Time SLAs**: Which specialties are exceeding wait time benchmarks, and how does this correlate with patient satisfaction and churn?
5. **Segment Strategy**: What are the distinct patient engagement segments, and which require proactive outreach vs. retention campaigns?

---

## 4. Hypotheses

- **H1 (Volume)**: Appointment cancellations and no-shows account for the majority of the Month 7 drop, driven by higher out-of-pocket costs post-policy change.
- **H2 (Rate)**: Bulk billing rate erosion reduced average revenue per completed appointment independently of volume.
- **H3 (Churn)**: Patients with long wait times (>14 days for GP) and low satisfaction scores (<6/10) have significantly higher churn probability.
- **H4 (Leakage)**: Medicare claim rejections and no-show lost revenue together represent more than $50,000 AUD in recoverable annual leakage.

---

## 5. Success Metrics

| Metric | Current | Target (12 months) |
|---|---|---|
| Bulk Billing Rate | ~72% | ≥78% |
| No-Show Rate | ~17% | ≤10% |
| Patient Churn Rate | ~24% | ≤15% |
| Avg GP Wait Time | ~9 days | ≤7 days (SLA) |
| Medicare Claim Rejection Rate | ~12% | ≤6% |
| Patient NPS | ~42 | ≥55 |

---

## 6. Scope

- **Period**: 12 months of synthetic appointment, billing, and satisfaction data
- **Geographies**: All Australian states and territories
- **Billing types**: Bulk bill, gap payment, private, self-pay
- **Specialties**: 8 clinical specialties across metro and regional clinics
- **Data sources**: Appointments, patient demographics, staff records, satisfaction surveys, Medicare billing claims
