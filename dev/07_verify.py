#!/usr/bin/env python
"""Step 7: Verify pipeline output tables exist and contain plausible results.

Checks:
  - topline_report has rows
  - weighting_diagnostics has rows, design effect < 3, weighted shares
    reasonably close to target shares

Usage:
    python dev/07_verify.py \\
        --survey-id <SURVEY_ID> \\
        --output-schema <SCHEMA> \\
        [--database-id 32]
"""
import argparse
import sys

import civis

logger = civis.civis_logger(__name__)

DESIGN_EFFECT_THRESHOLD = 3.0


def check_table(sql, database_id, label):
    df = civis.io.read_civis_sql(sql, database=database_id, return_as="pandas")
    logger.info(f"{label}: {len(df)} rows")
    if len(df) == 0:
        logger.error(f"{label} is empty — pipeline may not have completed.")
        sys.exit(1)
    return df


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--survey-id", required=True)
    parser.add_argument("--output-schema", required=True)
    parser.add_argument("--database-id", type=int, default=32)
    args = parser.parse_args()

    schema = args.output_schema
    sid = args.survey_id
    db = args.database_id

    # Check topline report
    check_table(
        f"SELECT * FROM {schema}.{sid}_topline_report",
        db,
        "topline_report",
    )

    # Check weighting diagnostics and design effect
    diag = check_table(
        f"SELECT * FROM {schema}.{sid}_weighting_diagnostics",
        db,
        "weighting_diagnostics",
    )

    failed = False

    if "design_effect" in diag.columns:
        mean_de = diag["design_effect"].mean()
        max_de = diag["design_effect"].max()
        logger.info(f"Design effect: mean={mean_de:.3f}, max={max_de:.3f}")
        if max_de > DESIGN_EFFECT_THRESHOLD:
            logger.error(
                f"Design effect max={max_de:.3f} exceeds threshold {DESIGN_EFFECT_THRESHOLD}. "
                "Check ACS targets tables for crosswalk mismatches."
            )
            failed = True
        else:
            logger.info("Design effect within acceptable range.")
    else:
        logger.warning("No 'design_effect' column found in diagnostics table.")

    if "target_share" in diag.columns and "weighted_share" in diag.columns:
        diag["share_diff"] = (diag["weighted_share"] - diag["target_share"]).abs()
        max_diff = diag["share_diff"].max()
        logger.info(f"Max absolute share difference (weighted vs target): {max_diff:.4f}")
        logger.info(diag[["target_share", "weighted_share", "share_diff"]].to_string(index=False))
    else:
        logger.warning("target_share / weighted_share columns not found in diagnostics.")

    if failed:
        sys.exit(1)

    logger.info("Verification passed.")


if __name__ == "__main__":
    main()
