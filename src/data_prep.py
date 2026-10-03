"""Turn the raw REES46 event logs into three compact user-level tables.

Raw logs have tens of millions of rows, so we stream them in chunks and keep only:
  users.csv.gz     one row per user: first event time + counts of view / cart / purchase
  activity.csv.gz  unique (user_id, month_idx) pairs -> used for retention
  orders.csv.gz    one row per order (user_id + user_session): time and revenue

Usage:
    python -m src.data_prep                 # all users
    python -m src.data_prep --sample 10     # deterministic 10% user sample (fast)
"""
from __future__ import annotations

import argparse

import pandas as pd

from .config import EVENTS_GLOB, PROCESSED, RAW

USECOLS = ["event_time", "event_type", "price", "user_id", "user_session"]
DTYPES = {"event_type": "category", "price": "float32", "user_id": "int64", "user_session": "string"}
EVENT_TYPES = ["view", "cart", "purchase"]


def _month_idx(ts: pd.Series) -> pd.Series:
    """Integer month index (year*12 + month-1) - cheap to subtract for cohort ages."""
    return ts.dt.year * 12 + ts.dt.month - 1


def build_tables(events_glob: str = EVENTS_GLOB, chunksize: int = 1_000_000,
                 sample_pct: int | None = None, raw_dir=RAW, out_dir=PROCESSED) -> None:
    files = sorted(raw_dir.glob(events_glob))
    if not files:
        raise FileNotFoundError(f"No event files found at {raw_dir / events_glob}. See README, 'Get the data'.")

    user_parts, act_parts, order_parts = [], [], []
    for f in files:
        print(f"Reading {f.name} ...")
        for chunk in pd.read_csv(f, usecols=USECOLS, dtype=DTYPES, chunksize=chunksize):
            chunk["event_time"] = pd.to_datetime(chunk["event_time"].str.slice(0, 19), errors="coerce")
            chunk = chunk.dropna(subset=["event_time", "user_id"])
            if sample_pct:  # deterministic sample by user_id so a user is never split
                chunk = chunk[chunk["user_id"] % 100 < sample_pct]
            if chunk.empty:
                continue

            counts = (chunk.groupby(["user_id", "event_type"], observed=True).size()
                      .unstack(fill_value=0).reindex(columns=EVENT_TYPES, fill_value=0))
            counts.columns.name = None
            counts["first_event"] = chunk.groupby("user_id")["event_time"].min()
            user_parts.append(counts)

            act_parts.append(pd.DataFrame({"user_id": chunk["user_id"],
                                           "month_idx": _month_idx(chunk["event_time"])}).drop_duplicates())

            p = chunk[chunk["event_type"] == "purchase"]
            if not p.empty:
                order_parts.append(p.groupby(["user_id", "user_session"])
                                   .agg(order_time=("event_time", "min"), revenue=("price", "sum"))
                                   .reset_index())

    users = (pd.concat(user_parts).groupby(level=0)
             .agg(first_event=("first_event", "min"), views=("view", "sum"),
                  carts=("cart", "sum"), purchases=("purchase", "sum")))
    users.index.name = "user_id"
    activity = pd.concat(act_parts).drop_duplicates().reset_index(drop=True)
    if order_parts:
        orders = (pd.concat(order_parts).groupby(["user_id", "user_session"], as_index=False)
                  .agg(order_time=("order_time", "min"), revenue=("revenue", "sum")))
    else:
        orders = pd.DataFrame(columns=["user_id", "user_session", "order_time", "revenue"])

    out_dir.mkdir(parents=True, exist_ok=True)
    users.to_csv(out_dir / "users.csv.gz")
    activity.to_csv(out_dir / "activity.csv.gz", index=False)
    orders.to_csv(out_dir / "orders.csv.gz", index=False)
    print(f"Saved: {len(users):,} users, {len(activity):,} user-months, {len(orders):,} orders -> {out_dir}")


def load_processed(out_dir=PROCESSED):
    """Load the three processed tables (builds them first if missing)."""
    if not (out_dir / "users.csv.gz").exists():
        build_tables(out_dir=out_dir)
    users = pd.read_csv(out_dir / "users.csv.gz", parse_dates=["first_event"], index_col="user_id")
    activity = pd.read_csv(out_dir / "activity.csv.gz")
    orders = pd.read_csv(out_dir / "orders.csv.gz", parse_dates=["order_time"])
    return users, activity, orders


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=None, help="keep N%% of users (1-99)")
    ap.add_argument("--chunksize", type=int, default=1_000_000)
    args = ap.parse_args()
    build_tables(sample_pct=args.sample, chunksize=args.chunksize)
