#!/usr/bin/env python
"""Civis Template script 3/4: simulate survey responses for this survey's
drawn sample.

Stands in for a buyer's own survey vendor -- see survey_demo/responses.py
for what's actually being fabricated and why.

Params (env vars):
    SURVEY_ID               survey identifier, used in input/output table names
    SURVEY_DB_ID            Civis database ID to read/write
    SURVEY_DB_CREDENTIAL_ID Civis credential ID for SURVEY_DB_ID
    OUTPUT_SCHEMA           schema containing the sample table / to write output into
    BASE_RESPONSE_RATE      float in (0, 1], probability a sampled person "responds"
    RANDOM_SEED             optional int seed for reproducibility
"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import civis

import survey_demo.responses as responses

logger = civis.civis_logger(__name__)


def main():
    survey_id = os.environ["SURVEY_ID"]
    schema = os.environ["OUTPUT_SCHEMA"]
    base_response_rate = float(os.environ["BASE_RESPONSE_RATE"])
    random_seed = _optional_int(os.environ.get("RANDOM_SEED"))
    database = {
        "database": int(os.environ["SURVEY_DB_ID"]),
        "credential_id": int(os.environ["SURVEY_DB_CREDENTIAL_ID"]),
    }

    sample_table = f"{schema}.{survey_id}_sample"
    logger.info(f"Reading sample from {sample_table}")
    sample_df = civis.io.read_civis_sql(
        f"select voterbase_id, likely_dem, likely_rep from {sample_table}",
        return_as="pandas",
        **database,
    )

    logger.info(f"Simulating responses at base_response_rate={base_response_rate}")
    responses_df = responses.simulate_responses(
        sample_df, base_response_rate, random_seed=random_seed
    )

    full_table_name = f"{schema}.{survey_id}_responses"
    logger.info(f"Writing {len(responses_df)} rows to {full_table_name}")
    future = civis.io.dataframe_to_civis(
        responses_df, table=full_table_name, existing_table_rows="drop", hidden=True, **database
    )
    future.result()


def _optional_int(value):
    return int(value) if value is not None else None


if __name__ == "__main__":
    main()
