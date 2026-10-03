"""Funnel metrics: conversion, drop-off, per-cohort funnels."""
from __future__ import annotations

import pandas as pd

from .config import ENGAGED_MIN_VIEWS

STAGES = ["Visitors", "Engaged", "Add to Cart", "Purchase", "Repeat Purchase"]


def add_order_counts(users: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    n_orders = orders.groupby("user_id").size().rename("n_orders")
    u = users.join(n_orders)
    u["n_orders"] = u["n_orders"].fillna(0).astype(int)
    return u


def compute_funnel(users: pd.DataFrame, orders: pd.DataFrame,
                   min_views: int = ENGAGED_MIN_VIEWS, strict: bool = True) -> pd.DataFrame:
    """User-level funnel.

    Stage definitions
      Visitors        any user with >= 1 event
      Engaged         >= `min_views` product views   (activation proxy)
      Add to Cart     >= 1 cart event
      Purchase        >= 1 order
      Repeat Purchase >= 2 distinct orders (sessions)
    strict=True makes every stage a subset of the previous one (a proper funnel).
    """
    u = add_order_counts(users, orders)
    conds = [pd.Series(True, index=u.index), u["views"] >= min_views, u["carts"] >= 1,
             u["n_orders"] >= 1, u["n_orders"] >= 2]
    mask = pd.Series(True, index=u.index)
    counts = []
    for c in conds:
        mask = (mask & c) if strict else c
        counts.append(int(mask.sum()))

    df = pd.DataFrame({"stage": STAGES, "users": counts})
    df["step_conversion"] = df["users"] / df["users"].shift(1)
    df["step_dropoff"] = 1 - df["step_conversion"]
    df["overall_conversion"] = df["users"] / df["users"].iloc[0]
    return df


def funnel_by_cohort(users: pd.DataFrame, orders: pd.DataFrame, **kw) -> pd.DataFrame:
    """Overall conversion (% of cohort visitors) at each stage, per first-seen month."""
    cohort = users["first_event"].dt.to_period("M").astype(str)
    out = {}
    for name, grp in users.groupby(cohort):
        f = compute_funnel(grp, orders, **kw)
        out[name] = f.set_index("stage")["overall_conversion"]
    return pd.DataFrame(out).T[STAGES]
