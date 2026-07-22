#!/usr/bin/env python
"""Civis Template script 3/5: export the drawn sample as a Civis file so it
can be downloaded and sent to the in-house survey team.

In a live deployment this script produces the "field file" — the CSV of
sampled contacts handed off to the team that will conduct the survey. When
the survey returns, results are ingested via the file import job in the
results pipeline.

Params (env vars):
    SURVEY_ID               survey identifier, used in input table names
    SURVEY_DB_ID            Civis database ID to read from
    SURVEY_DB_CREDENTIAL_ID Civis credential ID for SURVEY_DB_ID (optional)
    OUTPUT_SCHEMA           schema containing the sample table
"""
import io
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import civis

logger = civis.civis_logger(__name__)


def main():
    survey_id = os.environ["SURVEY_ID"]
    schema = os.environ["OUTPUT_SCHEMA"]
    database = {"database": int(os.environ["SURVEY_DB_ID"])}
    if os.environ.get("SURVEY_DB_CREDENTIAL_ID"):
        database["credential_id"] = int(os.environ["SURVEY_DB_CREDENTIAL_ID"])

    sample_table = f"{schema}.{survey_id}_sample"
    logger.info(f"Reading sample from {sample_table}")
    sample_df = civis.io.read_civis_sql(
        f"SELECT * FROM {sample_table}",
        return_as="pandas",
        **database,
    )

    buf = io.BytesIO()
    sample_df.to_csv(buf, index=False, encoding="utf-8")
    buf.seek(0)

    file_name = f"{survey_id}_field_file.csv"
    file_id = civis.io.file_to_civis(buf, name=file_name)
    logger.info(
        f"Field file exported: {len(sample_df)} contacts — "
        f"file_id={file_id} name='{file_name}'"
    )


if __name__ == "__main__":
    main()
