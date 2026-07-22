"""Summarize weighted survey responses into a topline and crosstabs."""
import pandas as pd

CROSSTAB_VARIABLES = [
    "age_bucket_noncommercial",
    "gender_noncommercial",
    "race5way_noncommercial",
]


def summarize(weighted_df, crosstab_variables=CROSSTAB_VARIABLES, weight_col="weight"):
    """Returns a dict with:
    - vote_choice_topline: weighted share per vote_choice category
    - approval_rating_mean: weighted mean approval_rating (float)
    - crosstabs: {variable: DataFrame[category, vote_choice, weighted_share]}
    """
    return {
        "vote_choice_topline": _weighted_share(weighted_df, "vote_choice", weight_col),
        "approval_rating_mean": _weighted_mean(weighted_df, "approval_rating", weight_col),
        "crosstabs": {
            variable: _crosstab(weighted_df, variable, weight_col)
            for variable in crosstab_variables
        },
    }


def _weighted_share(df, column, weight_col):
    weighted = df.groupby(column)[weight_col].sum()
    return (weighted / weighted.sum()).reset_index(name="weighted_share")


def _weighted_mean(df, column, weight_col):
    return float((df[column] * df[weight_col]).sum() / df[weight_col].sum())


def _crosstab(df, by, weight_col):
    grouped = df.groupby([by, "vote_choice"])[weight_col].sum().reset_index(name="weight_sum")
    subgroup_totals = grouped.groupby(by)["weight_sum"].transform("sum")
    grouped["weighted_share"] = grouped["weight_sum"] / subgroup_totals
    return grouped.drop(columns="weight_sum")
