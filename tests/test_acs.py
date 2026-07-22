import json
import pathlib

import pytest
import yaml

import survey_demo.acs as acs

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"
CONFIG_DIR = pathlib.Path(__file__).parent.parent / "config"


@pytest.fixture
def crosswalks_config():
    with open(CONFIG_DIR / "crosswalks.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture
def acs_variables_config():
    with open(CONFIG_DIR / "acs_variables.yaml") as f:
        return yaml.safe_load(f)


def test_parse_census_response_extracts_acs_variables_only():
    raw = [
        ["B01001_001E", "B01001_002E", "NAME", "state"],
        ["1000", "500", "Ohio", "39"],
    ]
    assert acs.parse_census_response(raw) == {"B01001_001E": 1000, "B01001_002E": 500}


def test_parse_census_response_raises_on_no_rows():
    with pytest.raises(ValueError):
        acs.parse_census_response([["B01001_001E", "state"]])


def test_recode_age_gender_sums_variables_per_bucket():
    values = {
        "M18": 10,
        "M19": 20,
        "F18": 5,
        "F19": 15,
    }
    crosswalk = {
        "Male": {"18-34": ["M18", "M19"]},
        "Female": {"18-34": ["F18", "F19"]},
    }
    result = acs.recode_age_gender(values, crosswalk)

    expected_male = result.loc[result["gender_noncommercial"] == "Male", "population"].iloc[0]
    expected_female = result.loc[result["gender_noncommercial"] == "Female", "population"].iloc[0]
    assert expected_male == 30
    assert expected_female == 20
    assert set(result.columns) == {"gender_noncommercial", "age_bucket_noncommercial", "population"}


def test_recode_race_sums_variables_per_bucket():
    values = {"W": 100, "N1": 4, "N2": 6}
    crosswalk = {"White": ["W"], "Native": ["N1", "N2"]}
    result = acs.recode_race(values, crosswalk)

    white_pop = result.loc[result["race5way_noncommercial"] == "White", "population"].iloc[0]
    native_pop = result.loc[result["race5way_noncommercial"] == "Native", "population"].iloc[0]
    assert white_pop == 100
    assert native_pop == 10


def test_get_acs_marginals_conserves_population_and_uses_real_crosswalk(
    monkeypatch, crosswalks_config, acs_variables_config
):
    """No live Census call: fetch_census_table is monkeypatched to return
    saved illustrative fixtures shaped like a real API response. This
    exercises the real config/*.yaml crosswalk end-to-end.
    """
    age_sex_response = json.loads((FIXTURES_DIR / "age_by_sex_response.json").read_text())
    race_response = json.loads((FIXTURES_DIR / "race_hispanic_response.json").read_text())

    responses_by_table = {"B01001": age_sex_response, "B03002": race_response}

    def fake_fetch(base_url, dataset, variables, for_param, api_key=None):
        table_id = variables[0].split("_")[0]
        return responses_by_table[table_id]

    monkeypatch.setattr(acs, "fetch_census_table", fake_fetch)

    marginals = acs.get_acs_marginals(
        "39", acs_variables_config, crosswalks_config, api_key="unused"
    )

    age_sex_values = acs.parse_census_response(age_sex_response)
    race_values = acs.parse_census_response(race_response)

    detail_age_sex_total = sum(
        v for k, v in age_sex_values.items() if not k.endswith(("_001E", "_002E", "_026E"))
    )
    assert marginals["age_gender"]["population"].sum() == detail_age_sex_total

    detail_race_total = sum(v for k, v in race_values.items() if k != "B03002_001E")
    assert marginals["race"]["population"].sum() == detail_race_total

    assert set(marginals["age_gender"]["gender_noncommercial"]) == {"Male", "Female"}
    assert set(marginals["age_gender"]["age_bucket_noncommercial"]) == {
        "18-34",
        "35-49",
        "50-64",
        "65+",
    }
    assert set(marginals["race"]["race5way_noncommercial"]) == {
        "White",
        "AfAm",
        "Hispanic",
        "Asian",
        "Native",
    }
