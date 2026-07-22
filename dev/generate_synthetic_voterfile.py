#!/usr/bin/env python
"""DEV-ONLY TOOL. Generates a fully synthetic voterfile CSV, structurally
mimicking the shape of Civis's real basic_noncommercial_client voterfile
product (see the data dictionary in DEMO OUTPUTS/), for exercising the
demo pipeline locally without touching any real Civis Platform table.

Every row is fabricated by this script -- none of the values are derived
from, or resemble, any real individual's data. This is NOT one of the 4
numbered pipeline steps; in a real deployment, 02_draw_sample.py would read
a real voterfile table via its VOTERFILE_SCHEMA/VOTERFILE_TABLE params
instead of this file.

Usage:
    python dev/generate_synthetic_voterfile.py --state OH --n-rows 20000 \\
        --output dev/data/synthetic_voterfile_oh.csv
"""
import argparse
import pathlib

import numpy as np
import pandas as pd
import yaml

CONFIG_DIR = pathlib.Path(__file__).resolve().parent.parent / "config"

AGE_BUCKETS = ["18-34", "35-49", "50-64", "65+"]
AGE_WEIGHTS = [0.28, 0.26, 0.24, 0.22]
AGE_VOTE_RATE = {"18-34": 0.35, "35-49": 0.55, "50-64": 0.68, "65+": 0.75}

GENDERS = ["Male", "Female"]
GENDER_WEIGHTS = [0.49, 0.51]

RACES = ["White", "AfAm", "Hispanic", "Asian", "Native"]
RACE_WEIGHTS = [0.62, 0.13, 0.17, 0.05, 0.03]

URBANICITIES = ["Urban", "Suburban", "Rural"]
URBANICITY_WEIGHTS = [0.35, 0.40, 0.25]

# (party, weight, mean likely_dem, mean likely_rep)
PARTY_PROFILE = [
    ("Democrat", 0.33, 0.85, 0.05),
    ("Republican", 0.30, 0.05, 0.85),
    ("Independent", 0.18, 0.35, 0.35),
    ("Unaffiliated", 0.10, 0.35, 0.35),
    ("No Party", 0.03, 0.30, 0.30),
    ("Green", 0.01, 0.70, 0.05),
    ("Conservative", 0.01, 0.10, 0.75),
    ("Working Fam", 0.01, 0.65, 0.10),
    ("Libertarian", 0.01, 0.15, 0.55),
    ("Other", 0.01, 0.30, 0.30),
    ("Unknown", 0.01, 0.30, 0.30),
]


def generate_synthetic_voterfile(state, n_rows, random_seed=None):
    rng = np.random.default_rng(random_seed)
    fips = _load_state_fips()[state]

    age_bucket = rng.choice(AGE_BUCKETS, size=n_rows, p=AGE_WEIGHTS)
    gender = rng.choice(GENDERS, size=n_rows, p=GENDER_WEIGHTS)
    race = rng.choice(RACES, size=n_rows, p=RACE_WEIGHTS)
    urbanicity = rng.choice(URBANICITIES, size=n_rows, p=URBANICITY_WEIGHTS)
    county_idx = rng.integers(1, 6, size=n_rows)  # 5 fake counties

    parties = [p[0] for p in PARTY_PROFILE]
    party_weights = [p[1] for p in PARTY_PROFILE]
    party = rng.choice(parties, size=n_rows, p=party_weights)

    likely_dem, likely_rep = _simulate_partisan_scores(party, rng)
    turnout_propensity = _simulate_turnout_propensity(age_bucket, rng)
    vote_g2020 = _simulate_vote_history(age_bucket, rng)
    vote_g2022 = _simulate_vote_history(age_bucket, rng)
    vote_g2024 = _simulate_vote_history(age_bucket, rng)

    return pd.DataFrame(
        {
            "voterbase_id": [f"demo-{state}-{i:08d}" for i in range(n_rows)],
            "state_code": state,
            "tsmart_county_fips": [f"{fips}{idx:03d}" for idx in county_idx],
            "tsmart_county_name": [f"Demo County {idx}" for idx in county_idx],
            "age_bucket_noncommercial": age_bucket,
            "gender_noncommercial": gender,
            "race5way_noncommercial": race,
            "vf_reg_party": party,
            "urbanicity": urbanicity,
            "vote_g2020": vote_g2020,
            "vote_g2022": vote_g2022,
            "vote_g2024": vote_g2024,
            "likely_dem": likely_dem,
            "likely_rep": likely_rep,
            "ts_presidential_general_turnout": turnout_propensity,
        }
    )


def _load_state_fips():
    with open(CONFIG_DIR / "state_fips.yaml") as f:
        return yaml.safe_load(f)


def _simulate_partisan_scores(party, rng):
    profile = {p[0]: (p[2], p[3]) for p in PARTY_PROFILE}
    dem_mean = np.array([profile[p][0] for p in party])
    rep_mean = np.array([profile[p][1] for p in party])

    likely_dem = np.clip(dem_mean + rng.normal(0, 0.1, size=len(party)), 0, 1)
    likely_rep = np.clip(rep_mean + rng.normal(0, 0.1, size=len(party)), 0, 1)
    return likely_dem, likely_rep


def _simulate_turnout_propensity(age_bucket, rng):
    base = np.array([AGE_VOTE_RATE[a] for a in age_bucket])
    return np.clip(base + rng.normal(0, 0.1, size=len(age_bucket)), 0, 1)


def _simulate_vote_history(age_bucket, rng):
    base = np.array([AGE_VOTE_RATE[a] for a in age_bucket])
    return rng.random(len(age_bucket)) < base


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, help="Two-letter state abbreviation, e.g. OH")
    parser.add_argument("--n-rows", type=int, default=20000)
    parser.add_argument("--random-seed", type=int, default=None)
    parser.add_argument("--output", required=True, help="Output CSV path")
    args = parser.parse_args()

    df = generate_synthetic_voterfile(args.state, args.n_rows, args.random_seed)

    output_path = pathlib.Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Wrote {len(df)} synthetic rows to {output_path}")


if __name__ == "__main__":
    main()
