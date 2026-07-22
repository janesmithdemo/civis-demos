#!/usr/bin/env python
"""Step 4: Run the four backing scripts individually in dependency order.

Patches each script's arguments then runs them: 01 and 02 in parallel,
then 03, then 04. Fails fast if any run ends in an error state.

Reads script IDs from dev/script_ids.json (written by 03_create_scripts.py);
individual IDs can be overridden with flags.

Usage:
    python dev/04_run_scripts.py \\
        --survey-id demo_oh_2026 \\
        --output-schema surveys \\
        --state OH \\
        --voterfile-schema surveys \\
        --voterfile-table oh_voterfile \\
        --sample-size 1000 \\
        --base-response-rate 0.03 \\
        [--random-seed 42] \\
        [--db-id 32] \\
        [--credential-id 2078]
"""
import argparse
import json
import pathlib
import sys

import civis

logger = civis.civis_logger(__name__)

SCRIPT_IDS_PATH = pathlib.Path(__file__).resolve().parent / "script_ids.json"


def patch_and_run(client, script_id, label, arguments):
    logger.info(f"Patching arguments for {label} (script_id={script_id})")
    client.scripts.patch_containers(script_id, arguments=arguments)
    logger.info(f"Starting {label}")
    run = client.scripts.post_containers_runs(script_id)
    logger.info(f"  run_id={run.id} launched")
    return run


def wait_for(client, script_id, run_id, label):
    fut = civis.futures.ContainerFuture(script_id, run_id, client=client)
    fut.result()
    if fut._civis_state != "succeeded":
        logger.error(f"{label} ended in state={fut._civis_state}; aborting")
        sys.exit(1)
    logger.info(f"  {label} succeeded")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--survey-id", required=True)
    parser.add_argument("--output-schema", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--voterfile-schema", required=True)
    parser.add_argument("--voterfile-table", required=True)
    parser.add_argument("--sample-size", type=int, required=True)
    parser.add_argument("--base-response-rate", type=float, required=True)
    parser.add_argument("--random-seed", type=int, default=None)
    parser.add_argument("--db-id", type=int, default=32)
    parser.add_argument("--credential-id", type=int, default=None)
    parser.add_argument("--script-id-01", type=int)
    parser.add_argument("--script-id-02", type=int)
    parser.add_argument("--script-id-03", type=int)
    parser.add_argument("--script-id-04", type=int)
    args = parser.parse_args()

    ids = {}
    if SCRIPT_IDS_PATH.exists():
        with open(SCRIPT_IDS_PATH) as f:
            data = json.load(f)
        ids = {
            "01": data.get("pull_acs_benchmarks"),
            "02": data.get("draw_sample"),
            "03": data.get("simulate_responses"),
            "04": data.get("weight_and_report"),
        }

    id_01 = args.script_id_01 or ids.get("01")
    id_02 = args.script_id_02 or ids.get("02")
    id_03 = args.script_id_03 or ids.get("03")
    id_04 = args.script_id_04 or ids.get("04")

    missing = [k for k, v in [("01", id_01), ("02", id_02), ("03", id_03), ("04", id_04)] if not v]
    if missing:
        raise ValueError(
            f"Missing script IDs for: {missing}. "
            "Run 03_create_scripts.py first or pass --script-id-* flags."
        )

    db_args = {"SURVEY_DB_ID": str(args.db_id)}
    if args.credential_id:
        db_args["SURVEY_DB_CREDENTIAL_ID"] = str(args.credential_id)
    random_seed = {"RANDOM_SEED": str(args.random_seed)} if args.random_seed is not None else {}

    client = civis.APIClient()

    # Stage 1: 01 and 02 are independent — patch and kick off both, then wait.
    logger.info("Stage 1: launching 01_pull_acs_benchmarks and 02_draw_sample in parallel")
    run_01 = patch_and_run(client, id_01, "01_pull_acs_benchmarks", {
        "SURVEY_ID": args.survey_id,
        "OUTPUT_SCHEMA": args.output_schema,
        "STATE": args.state,
        **db_args,
    })
    run_02 = patch_and_run(client, id_02, "02_draw_sample", {
        "SURVEY_ID": args.survey_id,
        "OUTPUT_SCHEMA": args.output_schema,
        "VOTERFILE_SCHEMA": args.voterfile_schema,
        "VOTERFILE_TABLE": args.voterfile_table,
        "SAMPLE_SIZE": str(args.sample_size),
        **db_args,
        **random_seed,
    })

    wait_for(client, id_01, run_01.id, "01_pull_acs_benchmarks")
    wait_for(client, id_02, run_02.id, "02_draw_sample")

    # Stage 2: 03 depends on 02
    run_03 = patch_and_run(client, id_03, "03_simulate_responses", {
        "SURVEY_ID": args.survey_id,
        "OUTPUT_SCHEMA": args.output_schema,
        "BASE_RESPONSE_RATE": str(args.base_response_rate),
        **db_args,
        **random_seed,
    })
    wait_for(client, id_03, run_03.id, "03_simulate_responses")

    # Stage 3: 04 depends on both 01 and 03
    run_04 = patch_and_run(client, id_04, "04_weight_and_report", {
        "SURVEY_ID": args.survey_id,
        "OUTPUT_SCHEMA": args.output_schema,
        **db_args,
    })
    wait_for(client, id_04, run_04.id, "04_weight_and_report")

    logger.info("All four scripts completed successfully.")


if __name__ == "__main__":
    main()
