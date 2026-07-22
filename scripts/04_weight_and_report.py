#!/usr/bin/env python
"""Civis Template script 4/4: rake this survey's responses to ACS
population marginals and write weighted data + a topline/crosstab summary.

Params (env vars):
    SURVEY_ID               survey identifier, used in input/output table names
    SURVEY_DB_ID            Civis database ID to read/write
    SURVEY_DB_CREDENTIAL_ID Civis credential ID for SURVEY_DB_ID
    OUTPUT_SCHEMA           schema containing sample/responses/acs_targets
                             tables, and to write output into
"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import civis
import pandas as pd

import survey_demo.reporting as reporting
import survey_demo.weighting as weighting

logger = civis.civis_logger(__name__)


def main():
    survey_id = os.environ["SURVEY_ID"]
    schema = os.environ["OUTPUT_SCHEMA"]
    database = {
        "database": int(os.environ["SURVEY_DB_ID"]),
        "credential_id": int(os.environ["SURVEY_DB_CREDENTIAL_ID"]),
    }

    joined_df = _read_joined_sample_and_responses(schema, survey_id, database)
    age_gender_targets, race_targets = _read_acs_targets(schema, survey_id, database)

    logger.info(f"Raking {len(joined_df)} respondents to ACS marginals")
    weighted_df, diagnostics = weighting.rake_weights(joined_df, age_gender_targets, race_targets)
    logger.info(
        f"design_effect={diagnostics['design_effect']:.3f} "
        f"weight_min={diagnostics['weight_min']:.3f} "
        f"weight_max={diagnostics['weight_max']:.3f}"
    )

    summary = reporting.summarize(weighted_df)
    topline_df = _build_topline_table(summary)
    crosstabs_df = _build_crosstabs_table(summary["crosstabs"])

    _write_table(weighted_df, schema, f"{survey_id}_weighted", database)
    _write_table(topline_df, schema, f"{survey_id}_topline_report", database)
    _write_table(crosstabs_df, schema, f"{survey_id}_crosstabs", database)
    _write_table(
        diagnostics["target_vs_weighted"], schema, f"{survey_id}_weighting_diagnostics", database
    )


def _read_joined_sample_and_responses(schema, survey_id, database):
    sample_table = f"{schema}.{survey_id}_sample"
    responses_table = f"{schema}.{survey_id}_responses"

    logger.info(f"Reading {sample_table} and {responses_table}")
    sample_df = civis.io.read_civis_sql(
        "select voterbase_id, age_bucket_noncommercial, gender_noncommercial, "
        f"race5way_noncommercial from {sample_table}",
        return_as="pandas",
        **database,
    )
    responses_df = civis.io.read_civis_sql(
        f"select * from {responses_table}", return_as="pandas", **database
    )
    return responses_df.merge(sample_df, on="voterbase_id", how="inner")


def _read_acs_targets(schema, survey_id, database):
    age_gender_targets = civis.io.read_civis_sql(
        f"select * from {schema}.{survey_id}_acs_targets_age_gender",
        return_as="pandas",
        **database,
    )
    race_targets = civis.io.read_civis_sql(
        f"select * from {schema}.{survey_id}_acs_targets_race", return_as="pandas", **database
    )
    return age_gender_targets, race_targets


def _build_topline_table(summary):
    rows = [
        {"metric": "vote_choice_share", "category": row["vote_choice"], "value": row["weighted_share"]}
        for _, row in summary["vote_choice_topline"].iterrows()
    ]
    rows.append({"metric": "approval_rating_mean", "category": "overall", "value": summary["approval_rating_mean"]})
    return pd.DataFrame(rows)


def _build_crosstabs_table(crosstabs):
    parts = []
    for variable, df in crosstabs.items():
        part = df.rename(columns={variable: "category"})
        part.insert(0, "variable", variable)
        parts.append(part)
    return pd.concat(parts, ignore_index=True)


def _write_table(df, schema, table_name, database):
    full_table_name = f"{schema}.{table_name}"
    logger.info(f"Writing {len(df)} rows to {full_table_name}")
    future = civis.io.dataframe_to_civis(
        df, table=full_table_name, existing_table_rows="drop", hidden=True, **database
    )
    future.result()


if __name__ == "__main__":
    main()
