"""Draw a proportionally-allocated stratified sample from a voterfile
DataFrame that has already been run through strata.assign_strata().
"""
import numpy as np
import pandas as pd


def draw_stratified_sample(df, sample_size, strata_col="strata_id", random_seed=None):
    """Allocate `sample_size` rows across strata in proportion to each
    stratum's share of `df`, then sample without replacement within each
    stratum (capped at the stratum's available rows).

    Returns a new DataFrame of the sampled rows.
    """
    if sample_size > len(df):
        raise ValueError(
            f"sample_size ({sample_size}) exceeds available population ({len(df)})"
        )

    rng = np.random.default_rng(random_seed)
    strata_sizes = df[strata_col].value_counts()
    allocations = _proportional_allocation(strata_sizes, sample_size)

    sampled_parts = []
    for stratum, n in allocations.items():
        if n == 0:
            continue
        stratum_rows = df[df[strata_col] == stratum]
        chosen_idx = rng.choice(stratum_rows.index, size=n, replace=False)
        sampled_parts.append(stratum_rows.loc[chosen_idx])

    return pd.concat(sampled_parts) if sampled_parts else df.iloc[0:0]


def _proportional_allocation(strata_sizes, sample_size):
    """Largest-remainder allocation of `sample_size` across strata
    proportional to `strata_sizes`, capped at each stratum's own size.
    """
    population = strata_sizes.sum()
    exact = strata_sizes * sample_size / population
    base = np.minimum(np.floor(exact).astype(int), strata_sizes)
    remainder = sample_size - base.sum()

    remainders = (exact - base).sort_values(ascending=False)
    for stratum in remainders.index:
        if remainder <= 0:
            break
        if base[stratum] < strata_sizes[stratum]:
            base[stratum] += 1
            remainder -= 1

    return base
