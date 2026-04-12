"""
churn_model.py
==============
Reusable module for building, evaluating, and scoring
the HealthFirst Australia patient churn prediction model.

Usage:
    from src.churn_model import build_features, train_model, score_customers
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report, roc_auc_score, confusion_matrix,
    precision_recall_curve, average_precision_score,
)
from sklearn.pipeline import Pipeline
import warnings
warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# Feature Engineering
# ---------------------------------------------------------------------------

def build_features(patients: pd.DataFrame,
                   appointments: pd.DataFrame,
                   surveys: pd.DataFrame,
                   snapshot_date: pd.Timestamp = None) -> pd.DataFrame:
    """
    Build a feature matrix for patient churn prediction.

    Parameters
    ----------
    patients     : cleaned patients DataFrame
    appointments : cleaned appointments DataFrame (appointment_date must be datetime)
    surveys      : cleaned satisfaction_surveys DataFrame
    snapshot_date: date to compute recency from (defaults to max appointment_date)

    Returns
    -------
    DataFrame with one row per patient, columns = features + target (churn_flag)
    """
    appointments = appointments.copy()
    appointments["appointment_date"] = pd.to_datetime(appointments["appointment_date"])

    if snapshot_date is None:
        snapshot_date = appointments["appointment_date"].max()

    # ---- Recency / Frequency / Value ----
    rfv = (
        appointments.groupby("patient_id")
        .agg(
            last_visit          = ("appointment_date", "max"),
            appointment_count   = ("appointment_id",   "count"),
            total_billed        = ("billed_amount",    "sum"),
            avg_billed          = ("billed_amount",    "mean"),
            avg_wait_days       = ("wait_days",        "mean"),
            no_show_count       = ("status",           lambda x: (x == "no_show").sum()),
            telehealth_count    = ("appointment_type", lambda x: (x == "telehealth").sum()),
        )
        .reset_index()
    )
    rfv["days_since_visit"]  = (snapshot_date - rfv["last_visit"]).dt.days
    rfv["no_show_rate"]      = rfv["no_show_count"]  / rfv["appointment_count"]
    rfv["telehealth_rate"]   = rfv["telehealth_count"] / rfv["appointment_count"]

    # ---- Satisfaction features ----
    if not surveys.empty and "overall_score" in surveys.columns:
        sat = (
            surveys.groupby("patient_id")
            .agg(
                avg_overall_score = ("overall_score",    "mean"),
                avg_wait_rating   = ("wait_time_rating", "mean"),
                complaint_count   = ("complaint_category",
                                     lambda x: (x != "None").sum()),
            )
            .reset_index()
        )
    else:
        sat = pd.DataFrame(
            columns=["patient_id", "avg_overall_score", "avg_wait_rating", "complaint_count"]
        )

    # ---- Merge with patient profile ----
    features = patients[[
        "patient_id", "insurance_type", "state",
        "chronic_conditions", "churn_flag",
    ]].merge(rfv, on="patient_id", how="left") \
      .merge(sat, on="patient_id", how="left")

    # Fill patients with no appointment/survey history
    fill_zeros = [
        "appointment_count", "total_billed", "avg_billed", "avg_wait_days",
        "no_show_count", "telehealth_count", "no_show_rate", "telehealth_rate",
        "complaint_count",
    ]
    features[fill_zeros] = features[fill_zeros].fillna(0)
    features["days_since_visit"]    = features["days_since_visit"].fillna(999)
    features["avg_overall_score"]   = features["avg_overall_score"].fillna(5)
    features["avg_wait_rating"]     = features["avg_wait_rating"].fillna(3)

    # ---- Encode categoricals ----
    features = pd.get_dummies(
        features,
        columns=["insurance_type", "state", "chronic_conditions"],
        drop_first=False,
    )

    return features


# ---------------------------------------------------------------------------
# Model Training
# ---------------------------------------------------------------------------

def train_model(features: pd.DataFrame,
                model_type: str = "xgboost",
                test_size: float = 0.2,
                random_state: int = 42):
    """
    Train a patient churn prediction model.

    Parameters
    ----------
    features     : output of build_features()
    model_type   : 'logistic' or 'xgboost'
    test_size    : fraction held out for testing
    random_state : reproducibility seed

    Returns
    -------
    dict with keys: model, X_test, y_test, feature_names, metrics
    """
    drop_cols = ["patient_id", "churn_flag", "last_visit"]
    feature_cols = [c for c in features.columns if c not in drop_cols]

    X = features[feature_cols].astype(float)
    y = features["churn_flag"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    if model_type == "logistic":
        clf = Pipeline([
            ("scaler", StandardScaler()),
            ("model",  LogisticRegression(
                max_iter=1000, random_state=random_state, class_weight="balanced"
            )),
        ])
    else:  # gradient boosting
        clf = GradientBoostingClassifier(
            n_estimators=150,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            random_state=random_state,
        )

    clf.fit(X_train, y_train)

    y_prob = clf.predict_proba(X_test)[:, 1]
    y_pred = clf.predict(X_test)

    metrics = {
        "roc_auc":               round(roc_auc_score(y_test, y_prob), 4),
        "avg_precision":         round(average_precision_score(y_test, y_prob), 4),
        "classification_report": classification_report(y_test, y_pred),
        "confusion_matrix":      confusion_matrix(y_test, y_pred),
    }

    cv_scores = cross_val_score(clf, X, y, cv=5, scoring="roc_auc")
    metrics["cv_roc_auc_mean"] = round(cv_scores.mean(), 4)
    metrics["cv_roc_auc_std"]  = round(cv_scores.std(), 4)

    return {
        "model":         clf,
        "X_test":        X_test,
        "y_test":        y_test,
        "feature_names": feature_cols,
        "metrics":       metrics,
    }


# ---------------------------------------------------------------------------
# Scoring & Risk Segmentation
# ---------------------------------------------------------------------------

def score_customers(features: pd.DataFrame, model) -> pd.DataFrame:
    """
    Apply trained model to the full patient feature set.

    Returns DataFrame with patient_id, churn_probability, risk_band.
    """
    drop_cols = ["patient_id", "churn_flag", "last_visit"]
    feature_cols = [c for c in features.columns if c not in drop_cols]

    X = features[feature_cols].astype(float)
    probs = model.predict_proba(X)[:, 1]

    keep_cols = ["patient_id", "churn_flag",
                 "total_billed", "days_since_visit",
                 "appointment_count", "avg_overall_score"]
    available = [c for c in keep_cols if c in features.columns]

    scored = features[available].copy()
    scored["churn_probability"] = probs.round(4)
    scored["risk_band"] = pd.cut(
        probs,
        bins=[0, 0.30, 0.60, 1.0],
        labels=["Low", "Medium", "High"],
        right=True,
    )

    return scored.sort_values("churn_probability", ascending=False)


# ---------------------------------------------------------------------------
# Feature Importance (for tree models)
# ---------------------------------------------------------------------------

def get_feature_importance(result: dict, top_n: int = 15) -> pd.DataFrame:
    """Extract and rank feature importances from a trained model."""
    model = result["model"]
    names = result["feature_names"]

    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    elif hasattr(model, "named_steps"):
        inner = model.named_steps.get("model")
        if hasattr(inner, "coef_"):
            importances = np.abs(inner.coef_[0])
        else:
            importances = inner.feature_importances_
    else:
        return pd.DataFrame()

    df = pd.DataFrame({"feature": names, "importance": importances})
    return df.sort_values("importance", ascending=False).head(top_n).reset_index(drop=True)
