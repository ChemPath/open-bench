"""SHAP explainability on an open, synthetic model.

This module demonstrates the explainability layer, not a predictive model.
It builds a synthetic descriptor dataset whose label follows a *known, planted*
rule, trains a gradient-boosted classifier on it, and checks that SHAP
recovers the planted drivers. Because the ground truth is known, the
explanation can be verified.

Nothing here is trained on real bioactivity data, and its outputs are not
bioactivity, efficacy or safety predictions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

FEATURES: tuple[str, ...] = (
    "logp_crippen",
    "tpsa",
    "molecular_weight",
    "h_bond_donors",
    "h_bond_acceptors",
    "rotatable_bonds",
    "aromatic_rings",
    "fraction_csp3",
)

PLANTED_DRIVERS: tuple[str, ...] = ("logp_crippen", "tpsa")
"""Features that determine the synthetic label; all others are noise."""


@dataclass
class ExplainResult:
    """Outcome of the SHAP demo."""

    test_accuracy: float
    global_importance: pd.Series
    planted_drivers_recovered: bool
    local: pd.DataFrame


def synthetic_dataset(n: int = 2000, seed: int = 7) -> tuple[pd.DataFrame, np.ndarray]:
    """Sample descriptor rows and a label from a planted rule.

    The label is a noisy logistic function of logP (positive) and TPSA
    (negative), loosely shaped like a passive-permeability heuristic.

    Args:
        n: Number of rows.
        seed: RNG seed for reproducibility.

    Returns:
        ``(X, y)`` with columns :data:`FEATURES` and binary labels.
    """
    rng = np.random.default_rng(seed)
    X = pd.DataFrame({
        "logp_crippen": rng.normal(3.0, 2.0, n),
        "tpsa": rng.gamma(4.0, 18.0, n),
        "molecular_weight": rng.normal(320.0, 90.0, n),
        "h_bond_donors": rng.poisson(2.0, n),
        "h_bond_acceptors": rng.poisson(4.0, n),
        "rotatable_bonds": rng.poisson(5.0, n),
        "aromatic_rings": rng.integers(0, 4, n),
        "fraction_csp3": rng.uniform(0.0, 1.0, n),
    })
    logit = 1.4 * (X["logp_crippen"] - 3.0) - 0.05 * (X["tpsa"] - 72.0)
    y = (logit + rng.normal(0.0, 0.8, n) > 0).astype(int).to_numpy()
    return X, y


def run(local_rows: list[dict[str, Any]] | None = None, n: int = 2000, seed: int = 7) -> ExplainResult:
    """Train the synthetic model, compute SHAP values and check recovery.

    Args:
        local_rows: Optional ``{"name": ..., **descriptors}`` rows to explain
            individually, e.g. reference-library compounds.
        n: Synthetic training rows.
        seed: RNG seed.

    Returns:
        An :class:`ExplainResult` with mean |SHAP| per feature and per-row
        SHAP contributions for ``local_rows``.
    """
    import shap
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.model_selection import train_test_split

    X, y = synthetic_dataset(n, seed)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=seed, stratify=y)
    model = GradientBoostingClassifier(random_state=seed).fit(X_tr, y_tr)

    explainer = shap.TreeExplainer(model)
    shap_te = np.asarray(explainer.shap_values(X_te))
    importance = (pd.Series(np.abs(shap_te).mean(axis=0), index=list(FEATURES))
                  .sort_values(ascending=False))
    recovered = set(importance.index[: len(PLANTED_DRIVERS)]) == set(PLANTED_DRIVERS)

    local = pd.DataFrame()
    if local_rows:
        frame = pd.DataFrame(local_rows).set_index("name")[list(FEATURES)]
        local = pd.DataFrame(np.asarray(explainer.shap_values(frame)),
                             index=frame.index, columns=list(FEATURES))
        local.insert(0, "p_synthetic", model.predict_proba(frame)[:, 1])

    return ExplainResult(
        test_accuracy=float(model.score(X_te, y_te)),
        global_importance=importance,
        planted_drivers_recovered=recovered,
        local=local,
    )
