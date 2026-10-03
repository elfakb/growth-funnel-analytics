"""Cohort retention."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _label(idx: int) -> str:
    return f"{idx // 12}-{idx % 12 + 1:02d}"


def cohort_retention(users: pd.DataFrame, activity: pd.DataFrame):
    """Monthly retention by first-seen month.

    cohort  = month of the user's first event
    active  = user has >= 1 event in month (cohort + k)
    Cells beyond the end of the observed data are NaN (not 0), because we cannot
    observe the future.
    Returns (sizes, active_counts, retention_rate).
    """
    fe = users["first_event"]
    cohort_idx = (fe.dt.year * 12 + fe.dt.month - 1).rename("cohort_idx")
    act = activity.join(cohort_idx, on="user_id")
    act["k"] = act["month_idx"] - act["cohort_idx"]
    act = act[act["k"] >= 0]
    last_month = activity["month_idx"].max()

    counts = act.groupby(["cohort_idx", "k"])["user_id"].nunique().unstack(fill_value=0)
    sizes = counts[0].copy()
    retention = counts.div(sizes, axis=0)
    for c in retention.index:
        retention.loc[c, retention.columns > last_month - c] = np.nan

    labels = [_label(int(c)) for c in retention.index]
    sizes.index, counts.index, retention.index = labels, labels, labels
    retention.index.name = "cohort"
    retention.columns.name = "months_since_first_visit"
    return sizes, counts, retention


def repeat_purchase_by_cohort(users: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    """Share of each cohort that bought at all / bought 2+ times."""
    n_orders = orders.groupby("user_id").size()
    u = users.join(n_orders.rename("n_orders"))
    u["n_orders"] = u["n_orders"].fillna(0)
    u["cohort"] = u["first_event"].dt.to_period("M").astype(str)
    g = u.groupby("cohort")
    return pd.DataFrame({
        "users": g.size(),
        "buyer_rate": g["n_orders"].apply(lambda s: (s >= 1).mean()),
        "repeat_rate_of_all": g["n_orders"].apply(lambda s: (s >= 2).mean()),
        "repeat_rate_of_buyers": g["n_orders"].apply(lambda s: (s >= 2).sum() / max((s >= 1).sum(), 1)),
    })
