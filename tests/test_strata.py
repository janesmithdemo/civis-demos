import copy
import pathlib

import pandas as pd
import pytest
import yaml

import survey_demo.strata as strata

CONFIG_DIR = pathlib.Path(__file__).parent.parent / "config"


@pytest.fixture
def strata_config():
    with open(CONFIG_DIR / "strata.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture
def crosswalks_config():
    with open(CONFIG_DIR / "crosswalks.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture
def acs_variables_config():
    with open(CONFIG_DIR / "acs_variables.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture
def small_strata_config():
    return {
        "variables": [
            {"column": "age_bucket_noncommercial", "categories": ["18-34", "35-49"]},
            {"column": "gender_noncommercial", "categories": ["Male", "Female"]},
        ]
    }


def test_assign_strata_builds_combined_id(small_strata_config):
    df = pd.DataFrame(
        {
            "age_bucket_noncommercial": ["18-34", "35-49"],
            "gender_noncommercial": ["Male", "Female"],
        }
    )
    result = strata.assign_strata(df, small_strata_config)
    assert result["strata_id"].tolist() == ["18-34|Male", "35-49|Female"]


def test_assign_strata_raises_on_missing_column(small_strata_config):
    df = pd.DataFrame({"age_bucket_noncommercial": ["18-34"]})
    with pytest.raises(ValueError, match="Missing strata column"):
        strata.assign_strata(df, small_strata_config)


def test_assign_strata_raises_on_unexpected_category(small_strata_config):
    df = pd.DataFrame(
        {
            "age_bucket_noncommercial": ["18-34"],
            "gender_noncommercial": ["Nonbinary"],
        }
    )
    with pytest.raises(ValueError, match="not in strata.yaml categories"):
        strata.assign_strata(df, small_strata_config)


def test_real_config_crosswalk_coverage_is_valid(
    strata_config, crosswalks_config, acs_variables_config
):
    """The actual config/*.yaml files ship together; if this fails, the
    crosswalk is out of sync with strata.yaml or acs_variables.yaml.
    """
    strata.validate_crosswalk_coverage(strata_config, crosswalks_config, acs_variables_config)


def test_validate_crosswalk_coverage_catches_missing_gender_category(
    strata_config, crosswalks_config, acs_variables_config
):
    broken = copy.deepcopy(crosswalks_config)
    del broken["age_bucket_by_gender"]["Female"]
    with pytest.raises(ValueError, match="gender_noncommercial"):
        strata.validate_crosswalk_coverage(strata_config, broken, acs_variables_config)


def test_validate_crosswalk_coverage_catches_missing_race_category(
    strata_config, crosswalks_config, acs_variables_config
):
    broken = copy.deepcopy(crosswalks_config)
    del broken["race5way"]["Native"]
    with pytest.raises(ValueError, match="race5way_noncommercial"):
        strata.validate_crosswalk_coverage(strata_config, broken, acs_variables_config)


def test_validate_crosswalk_coverage_catches_double_assigned_acs_variable(
    strata_config, crosswalks_config, acs_variables_config
):
    broken = copy.deepcopy(crosswalks_config)
    broken["race5way"]["AfAm"].append(broken["race5way"]["White"][0])
    with pytest.raises(ValueError, match="double-assigned"):
        strata.validate_crosswalk_coverage(strata_config, broken, acs_variables_config)


def test_validate_crosswalk_coverage_catches_missing_acs_variable(
    strata_config, crosswalks_config, acs_variables_config
):
    broken = copy.deepcopy(crosswalks_config)
    broken["race5way"]["White"] = []
    with pytest.raises(ValueError, match="missing from crosswalk"):
        strata.validate_crosswalk_coverage(strata_config, broken, acs_variables_config)
