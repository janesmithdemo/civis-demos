"""Pull ACS population marginals from the public Census API and recode them
into the voterfile's category labels (age_bucket_noncommercial,
gender_noncommercial, race5way_noncommercial) using config/crosswalks.yaml.

Only `fetch_census_table` talks to the network; everything else is a pure
function over already-fetched values, so recoding logic can be tested
against a saved fixture response without a live HTTP call.
"""
import pandas as pd
import requests


def fetch_census_table(base_url, dataset, variables, for_param, api_key=None):
    """Call the Census API for one table and return the raw JSON response.

    The Census API returns a list of lists: a header row of variable/geo
    names followed by one row per requested geography.
    """
    params = {"get": ",".join(variables), "for": for_param}
    if api_key:
        params["key"] = api_key
    url = f"{base_url}/{dataset}"
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def parse_census_response(raw_json):
    """Convert a raw Census API response into {variable: value} for the
    first (and only expected) geography row.
    """
    header, *rows = raw_json
    if not rows:
        raise ValueError("Census API response contained no geography rows")
    row = rows[0]
    values = dict(zip(header, row))
    return {k: int(v) for k, v in values.items() if k.startswith("B0")}


def recode_age_gender(values, crosswalk):
    """values: {acs_variable: count}. crosswalk: age_bucket_by_gender dict
    from crosswalks.yaml, e.g. {"Male": {"18-34": [...], ...}, "Female": {...}}.

    Returns a tidy DataFrame with columns [gender_noncommercial,
    age_bucket_noncommercial, population].
    """
    records = []
    for gender, buckets in crosswalk.items():
        for age_bucket, acs_vars in buckets.items():
            population = sum(values[v] for v in acs_vars)
            records.append(
                {
                    "gender_noncommercial": gender,
                    "age_bucket_noncommercial": age_bucket,
                    "population": population,
                }
            )
    return pd.DataFrame.from_records(records)


def recode_race(values, crosswalk):
    """values: {acs_variable: count}. crosswalk: race5way dict from
    crosswalks.yaml, e.g. {"White": [...], "AfAm": [...], ...}.

    Returns a tidy DataFrame with columns [race5way_noncommercial, population].
    """
    records = [
        {
            "race5way_noncommercial": race,
            "population": sum(values[v] for v in acs_vars),
        }
        for race, acs_vars in crosswalk.items()
    ]
    return pd.DataFrame.from_records(records)


def get_acs_marginals(state_fips, acs_variables_config, crosswalks_config, api_key=None):
    """Fetch and recode both ACS marginal tables for one state.

    Returns {"age_gender": DataFrame, "race": DataFrame}.
    """
    base_url = acs_variables_config["base_url"]
    dataset = acs_variables_config["dataset"]
    for_param = acs_variables_config["geography"]["for_param_template"].format(fips=state_fips)

    age_sex_table = acs_variables_config["tables"]["age_by_sex"]
    race_table = acs_variables_config["tables"]["race_hispanic"]

    age_sex_raw = fetch_census_table(
        base_url, dataset, age_sex_table["variables"], for_param, api_key
    )
    race_raw = fetch_census_table(
        base_url, dataset, race_table["variables"], for_param, api_key
    )

    age_gender_df = recode_age_gender(
        parse_census_response(age_sex_raw), crosswalks_config["age_bucket_by_gender"]
    )
    race_df = recode_race(parse_census_response(race_raw), crosswalks_config["race5way"])

    return {"age_gender": age_gender_df, "race": race_df}
