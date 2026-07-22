#!/usr/bin/env python
"""Civis Template script 2/4: draw a stratified sample from a voterfile
table and write it as this survey's sample.

This demo always points VOTERFILE_SCHEMA/VOTERFILE_TABLE at Civis's own
demo data (e.g. dev/generate_synthetic_voterfile.py's output, loaded into a
demo schema) -- never at a buyer-supplied table. In a real deployment this
script's parameterization is what would point at a client's actual
voterfile; that connection is not part of this demo.

Params (env vars):
    SURVEY_ID               survey identifier, used in output table names
    SURVEY_DB_ID            Civis database ID to read/write
    SURVEY_DB_CREDENTIAL_ID Civis credential ID for SURVEY_DB_ID
    OUTPUT_SCHEMA           schema to write output tables into
    VOTERFILE_SCHEMA        schema containing the input voterfile table
    VOTERFILE_TABLE         input voterfile table name
    SAMPLE_SIZE             number of rows to sample
    RANDOM_SEED             optional int seed for reproducibility
"""
import os
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import civis
import yaml

import survey_demo.sampling as sampling
import survey_demo.strata as strata

CONFIG_DIR = REPO_ROOT / "config"
logger = civis.civis_logger(__name__)


def main():
    survey_id = os.environ["SURVEY_ID"]
    schema = os.environ["OUTPUT_SCHEMA"]
    voterfile_schema = os.environ["VOTERFILE_SCHEMA"]
    voterfile_table = os.environ["VOTERFILE_TABLE"]
    sample_size = int(os.environ["SAMPLE_SIZE"])
    random_seed = _optional_int(os.environ.get("RANDOM_SEED"))
    database = {
        "database": int(os.environ["SURVEY_DB_ID"]),
        "credential_id": int(os.environ["SURVEY_DB_CREDENTIAL_ID"]),
    }

    with open(CONFIG_DIR / "strata.yaml") as f:
        strata_config = yaml.safe_load(f)

    logger.info(f"Reading voterfile {voterfile_schema}.{voterfile_table}")
    voterfile_df = civis.io.read_civis_sql(
        f"select * from {voterfile_schema}.{voterfile_table}",
        return_as="pandas",
        **database,
    )

    logger.info("Assigning sampling strata")
    strata_df = strata.assign_strata(voterfile_df, strata_config)

    logger.info(f"Drawing stratified sample of {sample_size} from {len(strata_df)} rows")
    sample_df = sampling.draw_stratified_sample(
        strata_df, sample_size, random_seed=random_seed
    )

    full_table_name = f"{schema}.{survey_id}_sample"
    logger.info(f"Writing {len(sample_df)} rows to {full_table_name}")
    future = civis.io.dataframe_to_civis(
        sample_df, table=full_table_name, existing_table_rows="drop", hidden=True, **database
    )
    future.result()


def _optional_int(value):
    return int(value) if value is not None else None


if __name__ == "__main__":
    main()
