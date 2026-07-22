#!/usr/bin/env python
"""DEV-ONLY TOOL. Manual connectivity check for survey_demo.acs against the
live public Census API. Reads CENSUS_API_KEY from the environment -- never
pass it as a CLI argument, and this script never prints it.

Usage:
    export CENSUS_API_KEY=...   # in your own shell, not via this script
    python dev/verify_acs_pull.py --state OH
"""
import argparse
import os
import pathlib

import yaml

import survey_demo.acs as acs

CONFIG_DIR = pathlib.Path(__file__).resolve().parent.parent / "config"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, help="Two-letter state abbreviation, e.g. OH")
    args = parser.parse_args()

    api_key = os.environ["CENSUS_API_KEY"]
    with open(CONFIG_DIR / "acs_variables.yaml") as f:
        acs_variables_config = yaml.safe_load(f)
    with open(CONFIG_DIR / "crosswalks.yaml") as f:
        crosswalks_config = yaml.safe_load(f)
    with open(CONFIG_DIR / "state_fips.yaml") as f:
        state_fips = yaml.safe_load(f)[args.state]

    marginals = acs.get_acs_marginals(
        state_fips, acs_variables_config, crosswalks_config, api_key=api_key
    )

    print(f"Live ACS pull for state={args.state} (fips={state_fips}) succeeded.\n")
    print("age_gender marginals:")
    print(marginals["age_gender"].to_string(index=False))
    print(f"\ntotal population (age/gender): {marginals['age_gender']['population'].sum():,}")
    print("\nrace marginals:")
    print(marginals["race"].to_string(index=False))
    print(f"\ntotal population (race): {marginals['race']['population'].sum():,}")


if __name__ == "__main__":
    main()
