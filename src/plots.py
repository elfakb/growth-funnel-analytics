"""Matplotlib charts (no seaborn dependency)."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np


def plot_funnel(f, title="Conversion funnel"):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    y = np.arange(len(f))[::-1]
    ax.barh(y, f["users"], color="#4C78A8")
    for yi, (_, r) in zip(y, f.iterrows()):
        txt = f"{int(r['users']):,}  ({r['overall_conversion']:.1%} of visitors)"
        if not np.isnan(r["step_conversion"]):
            txt += f"   step: {r['step_conversion']:.1%} | drop-off: {r['step_dropoff']:.1%}"
        ax.text(r["users"], yi, "  " + txt, va="center", fontsize=8)
    ax.set_yticks(y, f["stage"])
    ax.set_xlim(0, f["users"].max() * 1.9)
    ax.set_xlabel("Users")
    ax.set_title(title)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def plot_retention_heatmap(ret, sizes=None, title="Monthly retention by first-visit cohort"):
    fig, ax = plt.subplots(figsize=(9, 0.8 * len(ret) + 2))
    im = ax.imshow(ret.values, cmap="Blues", vmin=0, vmax=max(0.5, np.nanmax(ret.values[:, 1:]) if ret.shape[1] > 1 else 1))
    ax.set_xticks(range(ret.shape[1]), ret.columns)
    ylabels = [f"{c} (n={int(sizes[c]):,})" if sizes is not None else c for c in ret.index]
    ax.set_yticks(range(len(ret)), ylabels)
    for i in range(ret.shape[0]):
        for j in range(ret.shape[1]):
            v = ret.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.0%}", ha="center", va="center", fontsize=9,
                        color="white" if v > 0.35 else "black")
    ax.set_xlabel("Months since first visit")
    ax.set_title(title)
    fig.colorbar(im, ax=ax, fraction=0.03)
    fig.tight_layout()
    return fig


def plot_ab_rates(r, labels=("Control (PSA)", "Treatment (Ad)")):
    """Conversion rate per group with 95% Wilson intervals + CI of the difference."""
    from scipy import stats
    z = stats.norm.ppf(1 - r["alpha"] / 2)

    def wilson(p, n):
        centre = (p + z**2 / (2 * n)) / (1 + z**2 / n)
        half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
        return centre - half, centre + half

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4), gridspec_kw={"width_ratios": [1.2, 1]})
    ps = [r["conv_control"], r["conv_treatment"]]
    ns = [r["n_control"], r["n_treatment"]]
    errs = np.array([[p - wilson(p, n)[0], wilson(p, n)[1] - p] for p, n in zip(ps, ns)]).T * 100
    a1.bar(labels, np.array(ps) * 100, yerr=errs, capsize=6, color=["#9ecae1", "#3182bd"])
    for i, p in enumerate(ps):
        a1.text(i, p * 100 + errs[1, i] + 0.05, f"{p:.2%}", ha="center", fontsize=10)
    a1.set_ylabel("Conversion rate (%)")
    a1.set_title("Conversion by group (95% CI)")

    d, (lo, hi) = r["abs_diff"] * 100, (np.array(r["abs_diff_ci"]) * 100)
    a2.errorbar([d], [0], xerr=[[d - lo], [hi - d]], fmt="o", capsize=8, color="#3182bd")
    a2.axvline(0, color="red", ls="--", lw=1)
    a2.set_yticks([])
    a2.set_xlabel("Difference in conversion (percentage points)")
    a2.set_title(f"Treatment - Control: {d:+.2f} pp  [{lo:+.2f}, {hi:+.2f}]")
    for a in (a1, a2):
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig
