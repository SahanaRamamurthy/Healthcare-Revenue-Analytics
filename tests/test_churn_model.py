"""
Unit tests for src/churn_model.py
Run with: pytest tests/test_churn_model.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import pandas as pd
import numpy as np
from src.churn_model import (
    build_features,
    train_model,
    score_customers,
    get_feature_importance,
)


# ── Fixtures — minimal synthetic data matching HealthFirst schema ─────────────

@pytest.fixture
def patients():
    n = 30
    np.random.seed(42)
    return pd.DataFrame({
        'patient_id':         list(range(1, n + 1)),
        'insurance_type':     (['bulk_bill', 'private_fund'] * n)[:n],
        'state':              (['NSW', 'VIC', 'QLD', 'SA', 'WA'] * n)[:n],
        'chronic_conditions': (['Hypertension', None, 'Diabetes', None, 'Asthma'] * n)[:n],
        'churn_flag':         ([0, 1] * n)[:n],
    })


@pytest.fixture
def appointments(patients):
    rows = []
    for pid in patients['patient_id']:
        for i in range(3):
            rows.append({
                'patient_id':       pid,
                'appointment_id':   pid * 10 + i,
                'appointment_date': pd.Timestamp('2025-01-01') + pd.Timedelta(days=i * 30),
                'billed_amount':    100 + pid * 10,
                'wait_days':        5 + i,
                'status':           'completed' if i < 2 else 'no_show',
                'appointment_type': 'in_person' if i < 2 else 'telehealth',
            })
    return pd.DataFrame(rows)


@pytest.fixture
def surveys():
    return pd.DataFrame({
        'patient_id':         [1, 2, 3],
        'overall_score':      [8.0, 3.0, 6.0],
        'wait_time_rating':   [7.0, 2.0, 5.0],
        'complaint_category': ['None', 'Wait Time', 'None'],
    })


@pytest.fixture
def features(patients, appointments, surveys):
    return build_features(patients, appointments, surveys)


# ── build_features ────────────────────────────────────────────────────────────

class TestBuildFeatures:
    def test_returns_dataframe(self, features):
        assert isinstance(features, pd.DataFrame)

    def test_one_row_per_patient(self, features, patients):
        assert len(features) == len(patients)

    def test_churn_flag_present(self, features):
        assert 'churn_flag' in features.columns

    def test_no_nulls_in_numeric_cols(self, features):
        numeric = features.select_dtypes(include=[np.number])
        assert numeric.isnull().sum().sum() == 0

    def test_days_since_visit_non_negative(self, features):
        assert (features['days_since_visit'] >= 0).all()

    def test_no_show_rate_between_0_and_1(self, features):
        assert features['no_show_rate'].between(0, 1).all()

    def test_telehealth_rate_between_0_and_1(self, features):
        assert features['telehealth_rate'].between(0, 1).all()


# ── train_model ───────────────────────────────────────────────────────────────

class TestTrainModel:
    def test_returns_expected_keys(self, features):
        result = train_model(features)
        for key in ['model', 'X_test', 'y_test', 'feature_names', 'metrics']:
            assert key in result

    def test_roc_auc_is_float(self, features):
        result = train_model(features)
        assert isinstance(result['metrics']['roc_auc'], float)

    def test_roc_auc_in_valid_range(self, features):
        result = train_model(features)
        assert 0.0 <= result['metrics']['roc_auc'] <= 1.0

    def test_logistic_model_works(self, features):
        result = train_model(features, model_type='logistic')
        assert result['model'] is not None

    def test_feature_names_match_X_test(self, features):
        result = train_model(features)
        assert len(result['feature_names']) == result['X_test'].shape[1]


# ── score_customers ───────────────────────────────────────────────────────────

class TestScoreCustomers:
    def test_returns_dataframe(self, features):
        result = train_model(features)
        scored = score_customers(features, result['model'])
        assert isinstance(scored, pd.DataFrame)

    def test_one_row_per_patient(self, features, patients):
        result = train_model(features)
        scored = score_customers(features, result['model'])
        assert len(scored) == len(patients)

    def test_churn_probability_between_0_and_1(self, features):
        result = train_model(features)
        scored = score_customers(features, result['model'])
        assert scored['churn_probability'].between(0, 1).all()

    def test_risk_band_values_valid(self, features):
        result = train_model(features)
        scored = score_customers(features, result['model'])
        assert set(scored['risk_band'].unique()).issubset({'Low', 'Medium', 'High'})

    def test_sorted_descending_by_probability(self, features):
        result = train_model(features)
        scored = score_customers(features, result['model'])
        probs = scored['churn_probability'].tolist()
        assert probs == sorted(probs, reverse=True)


# ── get_feature_importance ────────────────────────────────────────────────────

class TestGetFeatureImportance:
    def test_returns_dataframe(self, features):
        result = train_model(features)
        fi = get_feature_importance(result)
        assert isinstance(fi, pd.DataFrame)

    def test_has_feature_and_importance_columns(self, features):
        result = train_model(features)
        fi = get_feature_importance(result)
        assert 'feature' in fi.columns
        assert 'importance' in fi.columns

    def test_top_n_respected(self, features):
        result = train_model(features)
        fi = get_feature_importance(result, top_n=3)
        assert len(fi) <= 3

    def test_importances_are_non_negative(self, features):
        result = train_model(features)
        fi = get_feature_importance(result)
        assert (fi['importance'] >= 0).all()
