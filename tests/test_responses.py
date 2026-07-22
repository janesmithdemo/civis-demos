import numpy as np
import pandas as pd

import survey_demo.responses as responses


def _make_sample(n, likely_dem, likely_rep, seed=0):
    return pd.DataFrame(
        {
            "voterbase_id": [f"v{i}" for i in range(n)],
            "likely_dem": likely_dem,
            "likely_rep": likely_rep,
        }
    )


def test_simulate_responses_returns_expected_columns():
    sample = _make_sample(1000, 0.5, 0.5)
    result = responses.simulate_responses(sample, base_response_rate=0.5, random_seed=1)
    assert list(result.columns) == ["voterbase_id", "vote_choice", "approval_rating"]


def test_simulate_responses_response_rate_is_approximately_correct():
    sample = _make_sample(20000, 0.5, 0.5)
    result = responses.simulate_responses(sample, base_response_rate=0.2, random_seed=1)
    observed_rate = len(result) / len(sample)
    assert abs(observed_rate - 0.2) < 0.02


def test_simulate_responses_vote_choice_follows_likely_dem_signal():
    sample = _make_sample(5000, likely_dem=0.95, likely_rep=0.02)
    result = responses.simulate_responses(sample, base_response_rate=1.0, random_seed=1)
    dem_share = (result["vote_choice"] == "Democrat").mean()
    assert dem_share > 0.8


def test_simulate_responses_vote_choice_follows_likely_rep_signal():
    sample = _make_sample(5000, likely_dem=0.02, likely_rep=0.95)
    result = responses.simulate_responses(sample, base_response_rate=1.0, random_seed=1)
    rep_share = (result["vote_choice"] == "Republican").mean()
    assert rep_share > 0.8


def test_simulate_responses_approval_rating_within_bounds():
    sample = _make_sample(5000, likely_dem=np.random.default_rng(0).random(5000), likely_rep=0)
    result = responses.simulate_responses(sample, base_response_rate=1.0, random_seed=1)
    assert result["approval_rating"].between(1, 5).all()


def test_simulate_responses_is_reproducible_with_same_seed():
    sample = _make_sample(500, 0.4, 0.4)
    first = responses.simulate_responses(sample, base_response_rate=0.5, random_seed=99)
    second = responses.simulate_responses(sample, base_response_rate=0.5, random_seed=99)
    pd.testing.assert_frame_equal(first, second)
