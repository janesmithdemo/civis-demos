import pandas as pd
import pytest

import survey_demo.reporting as reporting


@pytest.fixture
def weighted_df():
    return pd.DataFrame(
        {
            "age_bucket_noncommercial": ["18-34", "18-34", "35-49", "35-49"],
            "gender_noncommercial": ["Male", "Female", "Male", "Female"],
            "race5way_noncommercial": ["White", "White", "AfAm", "AfAm"],
            "vote_choice": ["Democrat", "Republican", "Democrat", "Democrat"],
            "approval_rating": [5, 1, 3, 3],
            "weight": [1.0, 1.0, 2.0, 1.0],
        }
    )


def test_vote_choice_topline_shares_sum_to_one(weighted_df):
    summary = reporting.summarize(weighted_df)
    assert summary["vote_choice_topline"]["weighted_share"].sum() == pytest.approx(1.0)


def test_vote_choice_topline_weighted_correctly(weighted_df):
    summary = reporting.summarize(weighted_df)
    topline = summary["vote_choice_topline"].set_index("vote_choice")
    # weights sum to 5; Democrat weight = 1 + 2 + 1 = 4, Republican = 1
    assert topline.loc["Democrat", "weighted_share"] == pytest.approx(4 / 5)
    assert topline.loc["Republican", "weighted_share"] == pytest.approx(1 / 5)


def test_approval_rating_mean_is_weighted(weighted_df):
    summary = reporting.summarize(weighted_df)
    # (5*1 + 1*1 + 3*2 + 3*1) / (1+1+2+1) = 15/5 = 3.0
    assert summary["approval_rating_mean"] == pytest.approx(3.0)


def test_crosstabs_shares_sum_to_one_within_each_category(weighted_df):
    summary = reporting.summarize(weighted_df)
    for variable, df in summary["crosstabs"].items():
        totals = df.groupby(variable)["weighted_share"].sum()
        assert (totals.round(6) == 1.0).all()


def test_crosstabs_include_all_configured_variables(weighted_df):
    summary = reporting.summarize(weighted_df)
    assert set(summary["crosstabs"].keys()) == set(reporting.CROSSTAB_VARIABLES)
