"""Rake survey respondent weights to ACS population marginals via iterative
proportional fitting (the `ipfn` package).

Raking targets are the age_bucket_noncommercial x gender_noncommercial joint
distribution and the race5way_noncommercial distribution pulled from ACS
(see survey_demo.acs). Party and urbanicity are sampling-only dimensions
(no ACS equivalent) and are not raked.
"""
import numpy as np
import pandas as pd
from ipfn import ipfn

# Real respondent counts of 0 in a cell would freeze that cell at 0 forever
# under IPF. This small floor keeps every cell reachable without materially
# changing cells that do have respondents.
_ZERO_CELL_FLOOR = 1e-6


def rake_weights(respondents_df, age_gender_targets, race_targets, max_iterations=500, tol=1e-6):
    """respondents_df must have age_bucket_noncommercial, gender_noncommercial,
    and race5way_noncommercial columns (join responses to sample on
    voterbase_id before calling this).

    Returns (weighted_df, diagnostics) where weighted_df is respondents_df
    plus a `weight` column (mean-normalized to 1), and diagnostics is a dict
    with design_effect, weight_min, weight_max, and a target_vs_weighted
    comparison DataFrame.
    """
    ages, genders, ag_target = _pivot_age_gender(age_gender_targets)
    races, race_target = _pivot_race(race_targets)

    seed = _build_seed(respondents_df, ages, genders, races)
    total_n = len(respondents_df)

    ag_target_counts = ag_target / ag_target.sum() * total_n
    race_target_counts = race_target / race_target.sum() * total_n

    # ipfn.iteration() mutates its `original` array in place and returns
    # that same object, so pass a copy or `seed` and `fitted` would alias
    # and cell_weight would always come out as 1.
    fitted = ipfn.ipfn(
        seed.copy(),
        [ag_target_counts, race_target_counts],
        [[0, 1], [2]],
        convergence_rate=tol,
        max_iteration=max_iterations,
        verbose=0,
    ).iteration()

    cell_weight = fitted / seed
    weight_lookup = _cell_weight_lookup(cell_weight, ages, genders, races)

    weighted_df = respondents_df.merge(
        weight_lookup,
        on=["age_bucket_noncommercial", "gender_noncommercial", "race5way_noncommercial"],
        how="left",
    )
    weighted_df["weight"] = weighted_df["weight"] / weighted_df["weight"].mean()

    diagnostics = _diagnostics(weighted_df, age_gender_targets, race_targets)
    return weighted_df, diagnostics


def _pivot_age_gender(age_gender_targets):
    ages = sorted(age_gender_targets["age_bucket_noncommercial"].unique())
    genders = sorted(age_gender_targets["gender_noncommercial"].unique())
    pivoted = age_gender_targets.pivot(
        index="age_bucket_noncommercial", columns="gender_noncommercial", values="population"
    ).reindex(index=ages, columns=genders)
    return ages, genders, pivoted.to_numpy(dtype=float)


def _pivot_race(race_targets):
    races = sorted(race_targets["race5way_noncommercial"].unique())
    ordered = race_targets.set_index("race5way_noncommercial").reindex(races)
    return races, ordered["population"].to_numpy(dtype=float)


def _build_seed(respondents_df, ages, genders, races):
    counts = (
        respondents_df.groupby(
            ["age_bucket_noncommercial", "gender_noncommercial", "race5way_noncommercial"]
        )
        .size()
        .reindex(pd.MultiIndex.from_product([ages, genders, races]), fill_value=0)
    )
    seed = counts.to_numpy(dtype=float).reshape(len(ages), len(genders), len(races))
    return np.maximum(seed, _ZERO_CELL_FLOOR)


def _cell_weight_lookup(cell_weight, ages, genders, races):
    index = pd.MultiIndex.from_product(
        [ages, genders, races],
        names=["age_bucket_noncommercial", "gender_noncommercial", "race5way_noncommercial"],
    )
    return pd.DataFrame({"weight": cell_weight.reshape(-1)}, index=index).reset_index()


def _diagnostics(weighted_df, age_gender_targets, race_targets):
    weights = weighted_df["weight"].to_numpy()
    n = len(weights)
    design_effect = n * np.sum(weights**2) / np.sum(weights) ** 2

    comparisons = [
        _target_vs_weighted(weighted_df, age_gender_targets, "age_bucket_noncommercial"),
        _target_vs_weighted(weighted_df, age_gender_targets, "gender_noncommercial"),
        _target_vs_weighted(weighted_df, race_targets, "race5way_noncommercial"),
    ]

    return {
        "design_effect": design_effect,
        "weight_min": weights.min(),
        "weight_max": weights.max(),
        "target_vs_weighted": pd.concat(comparisons, ignore_index=True),
    }


def _target_vs_weighted(weighted_df, targets, column):
    target_share = targets.groupby(column)["population"].sum()
    target_share = target_share / target_share.sum()

    weighted_share = weighted_df.groupby(column)["weight"].sum()
    weighted_share = weighted_share / weighted_share.sum()

    comparison = pd.DataFrame(
        {"target_share": target_share, "weighted_share": weighted_share}
    ).reset_index()
    comparison.insert(0, "variable", column)
    comparison = comparison.rename(columns={column: "category"})
    return comparison
