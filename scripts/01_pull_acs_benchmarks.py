#!/usr/bin/env python
"""Civis Template script 1/4: pull ACS population marginals for STATE and
write them as the raking targets used by 04_weight_and_report.py.

Params (env vars):
    SURVEY_ID               survey identifier, used in output table names
    SURVEY_DB_ID            Civis database ID to write to
    SURVEY_DB_CREDENTIAL_ID Civis credential ID for SURVEY_DB_ID
    OUTPUT_SCHEMA           schema to write output tables into
    STATE                   two-letter state abbreviation, e.g. "OH"
    CENSUS_API_KEY          Census API key (census.gov/data/key_signup.html) --
                             mandatory as of this writing, the Census API
                             rejects unauthenticated requests entirely.

NOTE: the exact env var names Civis exposes for a Database-type template
parameter should be confirmed against the published template's actual
parameters -- SURVEY_DB_ID / SURVEY_DB_CREDENTIAL_ID here are this demo's
assumed convention, not verified against a live Platform run.
"""
import os
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import civis
import yaml

import survey_demo.acs as acs
import survey_demo.strata as strata

CONFIG_DIR = REPO_ROOT / "config"
logger = civis.civis_logger(__name__)


def main():
    survey_id = os.environ["SURVEY_ID"]
    schema = os.environ["OUTPUT_SCHEMA"]
    state = os.environ["STATE"]
    census_api_key = os.environ["CENSUS_API_KEY"]
    database = {
        "database": int(os.environ["SURVEY_DB_ID"]),
        "credential_id": int(os.environ["SURVEY_DB_CREDENTIAL_ID"]),
    }

    strata_config = _load_yaml("strata.yaml")
    crosswalks_config = _load_yaml("crosswalks.yaml")
    acs_variables_config = _load_yaml("acs_variables.yaml")
    state_fips = _load_yaml("state_fips.yaml")[state]

    logger.info("Validating ACS crosswalk coverage against strata.yaml")
    strata.validate_crosswalk_coverage(strata_config, crosswalks_config, acs_variables_config)

    logger.info(f"Pulling ACS 5-year marginals for state={state} (fips={state_fips})")
    marginals = acs.get_acs_marginals(
        state_fips, acs_variables_config, crosswalks_config, api_key=census_api_key
    )

    _write_table(marginals["age_gender"], schema, f"{survey_id}_acs_targets_age_gender", database)
    _write_table(marginals["race"], schema, f"{survey_id}_acs_targets_race", database)


def _load_yaml(filename):
    with open(CONFIG_DIR / filename) as f:
        return yaml.safe_load(f)


def _write_table(df, schema, table_name, database):
    full_table_name = f"{schema}.{table_name}"
    logger.info(f"Writing {len(df)} rows to {full_table_name}")
    future = civis.io.dataframe_to_civis(
        df, table=full_table_name, existing_table_rows="drop", hidden=True, **database
    )
    future.result()


if __name__ == "__main__":
    main()
