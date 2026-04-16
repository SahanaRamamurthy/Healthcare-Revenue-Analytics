"""
src/load_to_postgres.py
=======================
Loads cleaned CSV data into the PostgreSQL healthfirst database.

Run: python src/load_to_postgres.py
"""

import os
import pandas as pd
from sqlalchemy import create_engine

# ── Connection ──────────────────────────────────────────────────────────────
DB_URL = "postgresql://localhost/healthfirst"
engine = create_engine(DB_URL)

CLEAN = os.path.join(os.path.dirname(__file__), '..', 'data', 'cleaned')

def load(fname, **kw):
    path = os.path.join(CLEAN, fname)
    return pd.read_csv(path, **kw)

# ── Drop all tables first (cascade handles foreign keys) ────────────────────
with engine.connect() as conn:
    conn.execute(__import__('sqlalchemy').text("""
        DROP TABLE IF EXISTS billing_claims CASCADE;
        DROP TABLE IF EXISTS satisfaction_surveys CASCADE;
        DROP TABLE IF EXISTS appointments CASCADE;
        DROP TABLE IF EXISTS staff CASCADE;
        DROP TABLE IF EXISTS patients CASCADE;
    """))
    conn.commit()
print("Existing tables dropped.")

# ── Load tables in order (patients and staff first — foreign keys depend on them) ──
print("Loading patients...")
patients = load('patients.csv', parse_dates=['date_of_birth', 'registration_date', 'last_visit_date'])
patients.to_sql('patients', engine, if_exists='replace', index=False)
print(f"  {len(patients):,} rows loaded")

print("Loading staff...")
staff = load('staff.csv')
staff.to_sql('staff', engine, if_exists='replace', index=False)
print(f"  {len(staff):,} rows loaded")

print("Loading appointments...")
appointments = load('appointments.csv', parse_dates=['appointment_date'])
appointments.to_sql('appointments', engine, if_exists='replace', index=False)
print(f"  {len(appointments):,} rows loaded")

print("Loading satisfaction surveys...")
surveys = load('satisfaction_surveys.csv', parse_dates=['survey_date'])
surveys.to_sql('satisfaction_surveys', engine, if_exists='replace', index=False)
print(f"  {len(surveys):,} rows loaded")

print("Loading billing claims...")
claims = load('billing_claims.csv', parse_dates=['claim_date'])
claims.to_sql('billing_claims', engine, if_exists='replace', index=False)
print(f"  {len(claims):,} rows loaded")

print("\nAll data loaded successfully into PostgreSQL!")
