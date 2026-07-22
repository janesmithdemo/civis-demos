import pandas as pd
import pytest

import survey_demo.weighting as weighting

# A deliberately imbalanced respondent pool (skewed toward 35-49 / Female /
# White) that we rake back toward uniform-ish targets, so a bug in the
# raking math would show up as a large mismatch, not a coincidental match.
CELL_COUNTS = {
    ("18-34", "Male", "White"): 20,
    ("18-34", "Male", "AfAm"): 5,
    ("18-34", "Female", "White"): 15,
    ("18-34", "Female", "AfAm"): 5,
    ("35-49", "Male", "White"): 10,
    ("35-49", "Male", "AfAm"): 5,
    ("35-49", "Female", "White"): 30,
    ("35-49", "Female", "AfAm"): 10,
}


@pytest.fixture
def respondents_df():
    rows = []
    for (age, gender, race), n in CELL_COUNTS.items():
        rows.extend([{"age_bucket_noncommercial": age, "gender_noncommercial": gender, "race5way_noncommercial": race}] * n)
    return pd.DataFrame(rows)


@pytest.fixture
def age_gender_targets():
    # Uniform 25% across the 4 age x gender combinations.
    return pd.DataFrame(
        [
            {"age_bucket_noncommercial": "18-34", "gender_noncommercial": "Male", "population": 25},
            {"age_bucket_noncommercial": "18-34", "gender_noncommercial": "Female", "population": 25},
            {"age_bucket_noncommercial": "35-49", "gender_noncommercial": "Male", "population": 25},
            {"age_bucket_noncommercial": "35-49", "gender_noncommercial": "Female", "population": 25},
        ]
    )


@pytest.fixture
def race_targets():
    return pd.DataFrame(
        [
            {"race5way_noncommercial": "White", "population": 70},
            {"race5way_noncommercial": "AfAm", "population": 30},
        ]
    )


def test_rake_weights_matches_age_and_gender_targets(respondents_df, age_gender_targets, race_targets):
    weighted_df, diagnostics = weighting.rake_weights(respondents_df, age_gender_targets, race_targets)

    comparison = diagnostics["target_vs_weighted"]
    age_rows = comparison[comparison["variable"] == "age_bucket_noncommercial"]
    for _, row in age_rows.iterrows():
        assert row["weighted_share"] == pytest.approx(0.5, abs=0.01)

    gender_rows = comparison[comparison["variable"] == "gender_noncommercial"]
    for _, row in gender_rows.iterrows():
        assert row["weighted_share"] == pytest.approx(0.5, abs=0.01)


def test_rake_weights_matches_race_target(respondents_df, age_gender_targets, race_targets):
    _, diagnostics = weighting.rake_weights(respondents_df, age_gender_targets, race_targets)

    comparison = diagnostics["target_vs_weighted"]
    race_rows = comparison[comparison["variable"] == "race5way_noncommercial"].set_index("category")
    assert race_rows.loc["White", "weighted_share"] == pytest.approx(0.7, abs=0.01)
    assert race_rows.loc["AfAm", "weighted_share"] == pytest.approx(0.3, abs=0.01)


def test_rake_weights_normalizes_mean_weight_to_one(respondents_df, age_gender_targets, race_targets):
    weighted_df, _ = weighting.rake_weights(respondents_df, age_gender_targets, race_targets)
    assert weighted_df["weight"].mean() == pytest.approx(1.0)


def test_rake_weights_design_effect_is_at_least_one(respondents_df, age_gender_targets, race_targets):
    _, diagnostics = weighting.rake_weights(respondents_df, age_gender_targets, race_targets)
    assert diagnostics["design_effect"] >= 1.0
    assert diagnostics["weight_min"] <= diagnostics["weight_max"]


def test_rake_weights_uniform_sample_against_uniform_target_yields_equal_weights():
    ages, genders, races = ["18-34"], ["Male"], ["White", "AfAm"]
    respondents_df = pd.DataFrame(
        [{"age_bucket_noncommercial": "18-34", "gender_noncommercial": "Male", "race5way_noncommercial": r} for r in races * 10]
    )
    age_gender_targets = pd.DataFrame(
        [{"age_bucket_noncommercial": "18-34", "gender_noncommercial": "Male", "population": 100}]
    )
    race_targets = pd.DataFrame(
        [
            {"race5way_noncommercial": "White", "population": 50},
            {"race5way_noncommercial": "AfAm", "population": 50},
        ]
    )
    weighted_df, diagnostics = weighting.rake_weights(respondents_df, age_gender_targets, race_targets)
    assert weighted_df["weight"].nunique() == 1
    assert diagnostics["design_effect"] == pytest.approx(1.0)
