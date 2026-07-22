import numpy as np
import pandas as pd
import pytest

import survey_demo.sampling as sampling


def _make_population(strata_counts):
    strata_id = np.concatenate(
        [np.full(count, stratum) for stratum, count in strata_counts.items()]
    )
    return pd.DataFrame({"strata_id": strata_id, "value": np.arange(len(strata_id))})


def test_draw_stratified_sample_returns_exact_sample_size():
    df = _make_population({"A": 60, "B": 30, "C": 10})
    result = sampling.draw_stratified_sample(df, sample_size=20, random_seed=1)
    assert len(result) == 20


def test_draw_stratified_sample_allocates_proportionally():
    df = _make_population({"A": 600, "B": 300, "C": 100})
    result = sampling.draw_stratified_sample(df, sample_size=100, random_seed=1)
    counts = result["strata_id"].value_counts()
    assert counts["A"] == 60
    assert counts["B"] == 30
    assert counts["C"] == 10


def test_draw_stratified_sample_never_exceeds_stratum_size():
    # A's proportional share of 100 (~1) is already below its own size (5),
    # so this checks the cap is respected, not that A gets maxed out.
    df = _make_population({"A": 5, "B": 500})
    result = sampling.draw_stratified_sample(df, sample_size=100, random_seed=1)
    counts = result["strata_id"].value_counts()
    assert counts["A"] <= 5
    assert counts["B"] <= 500
    assert len(result) == 100


def test_draw_stratified_sample_raises_when_sample_exceeds_population():
    df = _make_population({"A": 10})
    with pytest.raises(ValueError, match="exceeds available population"):
        sampling.draw_stratified_sample(df, sample_size=11)


def test_draw_stratified_sample_is_reproducible_with_same_seed():
    df = _make_population({"A": 60, "B": 40})
    first = sampling.draw_stratified_sample(df, sample_size=20, random_seed=42)
    second = sampling.draw_stratified_sample(df, sample_size=20, random_seed=42)
    assert sorted(first["value"].tolist()) == sorted(second["value"].tolist())


def test_draw_stratified_sample_has_no_duplicate_rows():
    df = _make_population({"A": 60, "B": 40})
    result = sampling.draw_stratified_sample(df, sample_size=50, random_seed=7)
    assert result["value"].is_unique
