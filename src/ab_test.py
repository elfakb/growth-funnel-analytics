"""A/B test statistics for a binary conversion metric (two independent proportions).

Hypotheses (two-sided)
    H0: p_treatment == p_control      (no effect on conversion)
    H1: p_treatment != p_control
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .config import ALPHA, AB_FILE, SEED

TR_SIZE = {"negligible": "ihmal edilebilir", "small": "küçük", "medium": "orta", "large": "büyük"}
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ----------------------------------------------------------------------------- loading
def load_ab(path=AB_FILE) -> pd.DataFrame:
    """Load Kaggle 'Marketing A/B Testing' and standardise it.
    psa (public service announcement) = control, ad = treatment."""
    df = pd.read_csv(path)
    df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")])
    df = df.rename(columns={"user id": "user_id", "test group": "group", "total ads": "total_ads",
                            "most ads day": "most_ads_day", "most ads hour": "most_ads_hour"})
    df["converted"] = df["converted"].astype(str).str.lower().map({"true": 1, "false": 0, "1": 1, "0": 0})
    df["variant"] = df["group"].map({"psa": "control", "ad": "treatment"})
    return df


# ----------------------------------------------------------------------------- core test
def two_proportion_test(x_c: int, n_c: int, x_t: int, n_t: int, alpha: float = ALPHA,
                        n_boot: int = 20_000, seed: int = SEED) -> dict:
    """Full A/B readout: z-test, chi-square check, CI, effect sizes."""
    p_c, p_t = x_c / n_c, x_t / n_t
    diff = p_t - p_c
    z_crit = stats.norm.ppf(1 - alpha / 2)

    # z-test with pooled variance (variance under H0)
    p_pool = (x_c + x_t) / (n_c + n_t)
    se_pool = np.sqrt(p_pool * (1 - p_pool) * (1 / n_c + 1 / n_t))
    z = diff / se_pool
    p_value = 2 * stats.norm.sf(abs(z))

    # Confidence interval for the difference (unpooled variance)
    se_unp = np.sqrt(p_c * (1 - p_c) / n_c + p_t * (1 - p_t) / n_t)
    ci = (diff - z_crit * se_unp, diff + z_crit * se_unp)

    # Relative lift + parametric-bootstrap CI
    rng = np.random.default_rng(seed)
    pc_b = rng.binomial(n_c, p_c, n_boot) / n_c
    pt_b = rng.binomial(n_t, p_t, n_boot) / n_t
    rel_b = pt_b / pc_b - 1
    rel_ci = tuple(np.percentile(rel_b, [100 * alpha / 2, 100 * (1 - alpha / 2)]))

    # Effect sizes
    h = 2 * np.arcsin(np.sqrt(p_t)) - 2 * np.arcsin(np.sqrt(p_c))   # Cohen's h
    odds_ratio = (p_t / (1 - p_t)) / (p_c / (1 - p_c))

    # Independent cross-check with chi-square test of independence (no continuity correction)
    chi2, p_chi2, _, _ = stats.chi2_contingency([[x_c, n_c - x_c], [x_t, n_t - x_t]], correction=False)

    return {
        "n_control": n_c, "n_treatment": n_t, "conv_control": p_c, "conv_treatment": p_t,
        "abs_diff": diff, "abs_diff_ci": ci, "rel_lift": diff / p_c, "rel_lift_ci": rel_ci,
        "z": z, "p_value": p_value, "chi2": chi2, "p_value_chi2": p_chi2,
        "cohens_h": h, "odds_ratio": odds_ratio, "alpha": alpha, "significant": p_value < alpha,
    }


def cohens_h_label(h: float) -> str:
    a = abs(h)
    return "negligible" if a < 0.2 else "small" if a < 0.5 else "medium" if a < 0.8 else "large"


# ----------------------------------------------------------------------------- power
def minimum_detectable_effect(p_base: float, n_c: int, n_t: int, alpha: float = ALPHA,
                              power: float = 0.8) -> float:
    """Smallest absolute lift detectable with the given power (normal approximation)."""
    z_a, z_b = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    return (z_a + z_b) * np.sqrt(p_base * (1 - p_base) * (1 / n_c + 1 / n_t))


def required_sample_size(p_base: float, mde_abs: float, alpha: float = ALPHA, power: float = 0.8) -> int:
    """Users needed PER GROUP to detect an absolute lift of `mde_abs` (equal allocation)."""
    p1, p2 = p_base, p_base + mde_abs
    p_bar = (p1 + p2) / 2
    z_a, z_b = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    n = (z_a * np.sqrt(2 * p_bar * (1 - p_bar)) + z_b * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2 / mde_abs ** 2
    return int(np.ceil(n))


# ----------------------------------------------------------------------------- segments
def segment_analysis(df: pd.DataFrame, by: str, min_n: int = 500, alpha: float = ALPHA) -> pd.DataFrame:
    """Lift per segment with Bonferroni-adjusted p-values (guards against p-hacking)."""
    rows = []
    for seg, g in df.groupby(by, observed=True):
        c, t = g[g["variant"] == "control"], g[g["variant"] == "treatment"]
        if len(c) < min_n or len(t) < min_n:
            continue
        r = two_proportion_test(int(c["converted"].sum()), len(c), int(t["converted"].sum()), len(t), alpha, n_boot=2000)
        rows.append({by: seg, "n_control": len(c), "n_treatment": len(t), "conv_control": r["conv_control"],
                     "conv_treatment": r["conv_treatment"], "abs_diff_pp": r["abs_diff"] * 100,
                     "ci_low_pp": r["abs_diff_ci"][0] * 100, "ci_high_pp": r["abs_diff_ci"][1] * 100,
                     "p_value": r["p_value"]})
    cols = [by, "n_control", "n_treatment", "conv_control", "conv_treatment", "abs_diff_pp",
            "ci_low_pp", "ci_high_pp", "p_value"]
    out = pd.DataFrame(rows, columns=cols)
    if not out.empty:
        out["p_adj_bonferroni"] = (out["p_value"] * len(out)).clip(upper=1.0)
        out["significant_adj"] = out["p_adj_bonferroni"] < alpha
    else:
        out["p_adj_bonferroni"], out["significant_adj"] = [], []
    return out


# ----------------------------------------------------------------------------- wording
def _fmt_p(p: float) -> str:
    return "p < 0.0001" if p < 1e-4 else f"p = {p:.4f}"


def interpret(r: dict, lang: str = "en", metric: str = "conversion") -> str:
    """Plain-language sentence a stakeholder can act on (never just 'B is better')."""
    d_pp = r["abs_diff"] * 100
    lo, hi = (x * 100 for x in r["abs_diff_ci"])
    rl, rh = (x * 100 for x in r["rel_lift_ci"])
    pc, pt = r["conv_control"] * 100, r["conv_treatment"] * 100
    conf = int((1 - r["alpha"]) * 100)
    p = _fmt_p(r["p_value"])
    size = cohens_h_label(r["cohens_h"])
    if lang == "tr":
        verb = "arttı" if d_pp > 0 else "azaldı"
        verdict = "istatistiksel olarak anlamlı" if r["significant"] else "istatistiksel olarak anlamsız"
        return (f"Treatment grubunda {metric}, control'e göre {abs(d_pp):.2f} yüzde puan {verb} "
                f"(%{pc:.2f} → %{pt:.2f}; göreli değişim %{r['rel_lift']*100:+.1f}, %{conf} GA: [{rl:+.1f}%, {rh:+.1f}%]). "
                f"Fark için %{conf} güven aralığı [{lo:+.2f}, {hi:+.2f}] pp, {p}; sonuç {verdict} bulundu "
                f"(Cohen's h = {r['cohens_h']:.3f}, etki büyüklüğü: {TR_SIZE[size]}).")
    verb = "increased" if d_pp > 0 else "decreased"
    verdict = "statistically significant" if r["significant"] else "not statistically significant"
    return (f"In the treatment group, {metric} {verb} by {abs(d_pp):.2f} percentage points vs. control "
            f"({pc:.2f}% -> {pt:.2f}%; relative change {r['rel_lift']*100:+.1f}%, {conf}% CI [{rl:+.1f}%, {rh:+.1f}%]). "
            f"The {conf}% CI for the difference is [{lo:+.2f}, {hi:+.2f}] pp, {p}; the result is {verdict} "
            f"(Cohen's h = {r['cohens_h']:.3f}, effect size: {size}).")
