"""Assign sampling strata and validate that the ACS crosswalk actually
covers the raking dimensions before any sampling/weighting runs.

Category mismatches between the voterfile and the ACS crosswalk are the
most likely way this pipeline breaks silently (empty joins, dropped
population mass); validate_crosswalk_coverage() is meant to be called
before sampling or weighting, not just at the raking step itself.
"""
import pandas as pd


def assign_strata(df, strata_config):
    """Validate that each strata column's values are within the configured
    categories, then add a `strata_id` column combining all strata
    variables (used by sampling.draw_stratified_sample).
    """
    df = df.copy()
    strata_columns = [v["column"] for v in strata_config["variables"]]

    for variable in strata_config["variables"]:
        column, categories = variable["column"], set(variable["categories"])
        if column not in df.columns:
            raise ValueError(f"Missing strata column '{column}' on input data")
        observed = set(df[column].dropna().unique())
        unexpected = observed - categories
        if unexpected:
            raise ValueError(
                f"Column '{column}' has values not in strata.yaml categories: {sorted(unexpected)}"
            )

    df["strata_id"] = df[strata_columns].astype(str).agg("|".join, axis=1)
    return df


def validate_crosswalk_coverage(strata_config, crosswalks_config, acs_variables_config):
    """Confirm that:
    1. Every raking dimension's categories in strata.yaml has a matching
       entry in crosswalks.yaml.
    2. Every ACS variable listed in acs_variables.yaml is assigned to
       exactly one crosswalk bucket (no double-counted or dropped
       population mass).

    Raises ValueError describing the mismatch; returns None on success.
    """
    strata_by_column = {v["column"]: set(v["categories"]) for v in strata_config["variables"]}

    _check_age_gender_coverage(strata_by_column, crosswalks_config["age_bucket_by_gender"])
    _check_race_coverage(strata_by_column, crosswalks_config["race5way"])

    _check_acs_variable_coverage(
        acs_variables_config["tables"]["age_by_sex"]["variables"],
        crosswalks_config["age_bucket_by_gender"],
        table_name="age_by_sex",
    )
    _check_acs_variable_coverage(
        acs_variables_config["tables"]["race_hispanic"]["variables"],
        crosswalks_config["race5way"],
        table_name="race_hispanic",
    )


def _check_age_gender_coverage(strata_by_column, age_gender_crosswalk):
    expected_genders = strata_by_column["gender_noncommercial"]
    expected_ages = strata_by_column["age_bucket_noncommercial"]

    crosswalk_genders = set(age_gender_crosswalk.keys())
    if crosswalk_genders != expected_genders:
        raise ValueError(
            "gender_noncommercial categories in strata.yaml "
            f"{sorted(expected_genders)} do not match crosswalks.yaml "
            f"{sorted(crosswalk_genders)}"
        )

    for gender, buckets in age_gender_crosswalk.items():
        crosswalk_ages = set(buckets.keys())
        if crosswalk_ages != expected_ages:
            raise ValueError(
                f"age_bucket_noncommercial categories under gender='{gender}' "
                f"in crosswalks.yaml {sorted(crosswalk_ages)} do not match "
                f"strata.yaml {sorted(expected_ages)}"
            )


def _check_race_coverage(strata_by_column, race_crosswalk):
    expected_races = strata_by_column["race5way_noncommercial"]
    crosswalk_races = set(race_crosswalk.keys())
    if crosswalk_races != expected_races:
        raise ValueError(
            "race5way_noncommercial categories in strata.yaml "
            f"{sorted(expected_races)} do not match crosswalks.yaml "
            f"{sorted(crosswalk_races)}"
        )


def _check_acs_variable_coverage(acs_variables, crosswalk, table_name):
    # ACS variables that are aggregate totals (e.g. B01001_001E, B01001_002E,
    # B01001_026E) are never assigned to a bucket themselves; every other
    # variable in the table must appear in exactly one bucket.
    detail_variables = {v for v in acs_variables if not v.endswith(("_001E", "_002E", "_026E"))}

    assigned = []
    for buckets in crosswalk.values():
        if isinstance(buckets, dict):
            for variables in buckets.values():
                assigned.extend(variables)
        else:
            assigned.extend(buckets)

    assigned_set = set(assigned)
    duplicates = {v for v in assigned if assigned.count(v) > 1}
    missing = detail_variables - assigned_set
    extra = assigned_set - detail_variables

    if duplicates or missing or extra:
        problems = []
        if duplicates:
            problems.append(f"double-assigned: {sorted(duplicates)}")
        if missing:
            problems.append(f"missing from crosswalk: {sorted(missing)}")
        if extra:
            problems.append(f"assigned but not in acs_variables.yaml: {sorted(extra)}")
        raise ValueError(f"ACS table '{table_name}' crosswalk coverage problem: " + "; ".join(problems))
