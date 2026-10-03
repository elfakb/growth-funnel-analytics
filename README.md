# Growth & Funnel Analytics: E-commerce Funnel, Retention and A/B Testing

🇹🇷 Türkçe: [README.tr.md](README.tr.md)

An end-to-end product/growth analytics project built on **real data** (1.6M users, 16.7M events, a 588K-user A/B test). It answers three questions a growth team asks every week:

1. **Funnel:** where do users drop off between first visit and repeat purchase?
2. **Cohorts & retention:** do users come back, and does it differ by acquisition month?
3. **Experimentation:** did a marketing treatment *really* increase conversion? Reported with hypothesis, confidence interval, p-value and effect size, not just "B is better".

## Key findings

- **Only 5.6% of visitors buy and 1.4% buy again.** The biggest absolute loss is the first step: 69.7% of visitors never reach 3 product views.
- **Cart abandonment is 53%**, and **60% of cart users do not purchase** in the observed window.
- **Retention is low:** on average **10.1%** of a cohort returns in month 1, **6.1%** in month 2.
- **The ad campaign worked:** conversion rose from 1.79% (control) to 2.55% (treatment), **+0.77 percentage points** (95% CI [+0.60, +0.94]; relative lift +43%), **p < 0.0001**. That is roughly **4.3K additional conversions** among the 564K exposed users (CI ≈ 3.4K to 5.3K).
- The effect size is small in standardized terms (Cohen's h = 0.053) because the baseline rate is low, so the business value depends on campaign cost per incremental conversion.

## Data (not included, see "Get the data")

| Part | Dataset | Used for |
|---|---|---|
| Funnel, cohorts | [eCommerce Events History in Cosmetics Shop (REES46)](https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-cosmetics-shop): event log (`view`, `cart`, `purchase`), Oct 2019 - Feb 2020, 1,639,358 users, 155,617 orders | Notebooks 01, 02 |
| A/B test | [Marketing A/B Testing](https://www.kaggle.com/datasets/faviovaz/marketing-ab-testing): 588,101 users, `ad` (treatment) vs `psa` (control), binary `converted` | Notebook 03 |

## Methodology

**Funnel (user level, strict: each stage is a subset of the previous one)**

`Visitors → Engaged (≥3 product views) → Add to Cart → Purchase → Repeat Purchase (≥2 orders)`

The event log has no sign-up/activation event, so *Engaged* is used as an activation proxy. For every step I report step conversion, drop-off rate and overall conversion, plus a sensitivity check on the Engaged threshold and a funnel per acquisition cohort.

**Cohorts:** cohort = month of first event; retention(k) = share of the cohort active in month *M+k*. Unobserved future cells are left blank, not zero. The first month is flagged as left-censored (it includes existing customers).

**A/B test**

| Item | Choice |
|---|---|
| H0 / H1 | p_treatment = p_control / p_treatment ≠ p_control (two-sided) |
| Test | two-proportion z-test (pooled), cross-checked with chi-square |
| Interval | 95% CI of the absolute difference (unpooled) + bootstrap CI of relative lift |
| Effect size | Cohen's h, odds ratio, relative lift |
| Power | minimum detectable effect and required sample size |
| Segments | by weekday/hour with Bonferroni correction (exploratory) |

## Results

### 1. Funnel

| Stage | Users | Step conversion | Step drop-off | % of all visitors |
|---|---:|---:|---:|---:|
| Visitors | 1,639,358 | - | - | 100% |
| Engaged (≥3 views) | 496,856 | 30.3% | 69.7% | 30.3% |
| Add to Cart | 231,983 | 46.7% | 53.3% | 14.2% |
| Purchase | 91,986 | 39.7% | 60.3% | 5.6% |
| Repeat Purchase (≥2 orders) | 22,538 | 24.5% | 75.5% | 1.4% |

![Funnel](outputs/funnel.png)

- The largest **absolute** loss is Visitors → Engaged (about 1.14M users). The largest **relative** drop is before repeat purchase (75.5% of buyers do not buy again).
- Only **24.5% of buyers** purchase a second time.

### 2. Cohorts & retention

| Cohort (first visit) | Users | Month 1 | Month 2 | Month 3 | Month 4 |
|---|---:|---:|---:|---:|---:|
| 2019-10* | 399,664 | 13.7% | 9.1% | 7.9% | 6.7% |
| 2019-11 | 313,436 | 11.0% | 7.0% | 5.6% | - |
| 2019-12 | 299,461 | 9.2% | 5.2% | - | - |
| 2020-01 | 328,938 | 10.1% | - | - | - |
| 2020-02 | 297,859 | - | - | - | - |

\*The first cohort includes pre-existing customers (left-censored), so it is not a clean new-user cohort. Weighted average retention excluding it: **month 1 = 10.1%**, **month 2 = 6.1%**, month 3 = 5.6% (a single cohort).

![Retention](outputs/retention_heatmap.png)

Cohort funnels show buyer rate falling from 8.5% (Oct) to 3.1% (Feb) and repeat rate from 3.1% to 0.25%. This is **partly an observation-window effect**: later cohorts simply had less time to buy or re-buy (and the Oct cohort contains existing customers), so these numbers are not evidence of declining customer quality by themselves.

### 3. A/B test: ad vs. PSA (control)

| Metric | Control (PSA) | Treatment (Ad) |
|---|---:|---:|
| Users | 23,524 | 564,577 |
| Conversions | 420 | 14,423 |
| Conversion rate | 1.79% | 2.55% |

| Statistic | Value |
|---|---|
| Absolute difference | **+0.77 pp** (95% CI [+0.60, +0.94]) |
| Relative lift | **+43.1%** (95% bootstrap CI [+30.6%, +57.8%]) |
| z / p-value | z = 7.37, **p = 1.7e-13** (chi-square gives the same p) |
| Cohen's h / odds ratio | h = 0.053 (small in standardized terms) / OR = 1.44 |
| Minimum detectable effect | 0.25 pp at 80% power (the test was well powered) |

![A/B result](outputs/ab_test_result.png)

> **Plain-language result:** In the treatment group, conversion increased by 0.77 percentage points (1.79% → 2.55%; 95% CI [+0.60, +0.94] pp); the result is statistically significant (p < 0.0001).

**Segments (exploratory, Bonferroni-adjusted):** the lift is significant on **Tuesday (+1.60 pp)**, **Monday (+1.07 pp)** and **Wednesday (+0.96 pp)**; it is not significant on Thursday (+0.14 pp), Sunday (+0.40 pp), Friday or Saturday after correction.

## Recommendations

1. **Fix the top of the funnel:** 7 out of 10 visitors never reach 3 product views. Test better search, recommendations and landing pages.
2. **Reduce cart abandonment (53%)** with reminders and checkout friction tests. This is where an A/B test like the one in notebook 03 would fit best.
3. **Build a repeat-purchase programme** (replenishment reminders for consumables like cosmetics): only 24.5% of buyers return, and 10% of a cohort is active in month 1.
4. **Keep the ad campaign if it is profitable:** compare ~4.3K incremental conversions with campaign spend (cost per incremental conversion). Run follow-up tests for weekday targeting, since the effect looks stronger early in the week (exploratory, needs confirmation).

## Project structure

```
├── data/raw/                 # put Kaggle files here (git-ignored)
├── data/processed/           # generated user-level tables (git-ignored)
├── notebooks/
│   ├── 01_funnel_analysis.ipynb
│   ├── 02_cohort_retention.ipynb
│   └── 03_ab_test.ipynb
├── src/                      # data_prep, funnel, cohort, ab_test, plots, summary
├── tests/                    # unit + end-to-end tests (run on tiny fake data)
├── outputs/                  # charts and tables
└── requirements.txt
```

## Get the data & run

```bash
pip install -r requirements.txt

# download manually from the Kaggle links above, then:
# data/raw/cosmetics/*.csv   and   data/raw/marketing_AB.csv

python -m src.data_prep        # build user-level tables (use --sample 10 for a quick run)
python -m src.summary          # print all headline numbers
jupyter lab                    # run notebooks 01 -> 03
pytest -q                      # tests
```

## Limitations

- The funnel is observational; *Engaged* is a proxy for activation (the log has no sign-up event).
- Cohort comparisons are affected by different observation windows; the first cohort (Oct 2019) includes pre-existing customers.
- In the A/B dataset the groups are heavily unbalanced (~96% / 4%) by design, there is no revenue or cost data, and I could not verify the randomization process. Statistical significance does not imply business significance.
- Segment results are exploratory (day of week is the day with the most ads seen).

## Tech
Python, pandas, NumPy, SciPy, Matplotlib, Jupyter, pytest.