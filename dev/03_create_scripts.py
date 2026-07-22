#!/usr/bin/env python
"""Step 3: Create the four backing container scripts in Civis Platform.

Creates each script with the correct git repo, command, and parameters
(fixed params pre-filled). Prints the resulting script IDs.

Usage:
    python dev/03_create_scripts.py \\
        [--repo-url https://github.com/janesmithdemo/civis-demos.git] \\
        [--repo-ref surveys-demo] \\
        [--census-credential-id 39492]
"""
import argparse
import json
import pathlib

import civis

logger = civis.civis_logger(__name__)

DB_ID = 326
DB_CREDENTIAL_ID = 2078
DOCKER_IMAGE = "civisanalytics/datascience-python"
DOCKER_TAG = "8.4"

OUTPUT_PATH = pathlib.Path(__file__).resolve().parent / "script_ids.json"

SCRIPTS = [
    {
        "name": "01 Pull ACS Benchmarks",
        "command": "cd /app && pip install -r requirements.txt && python scripts/01_pull_acs_benchmarks.py",
        "params": [
            {"name": "SURVEY_ID", "type": "string", "required": True},
            {"name": "OUTPUT_SCHEMA", "type": "string", "required": True},
            {"name": "STATE", "type": "string", "required": True},
            {"name": "SURVEY_DB_ID", "type": "integer", "value": str(DB_ID)},
            # value set below once census_credential_id is known
            {"name": "CENSUS_API_KEY", "type": "credential_custom"},
        ],
        "key": "pull_acs_benchmarks",
    },
    {
        "name": "02 Draw Sample",
        "command": "cd /app && pip install -r requirements.txt && python scripts/02_draw_sample.py",
        "params": [
            {"name": "SURVEY_ID", "type": "string", "required": True},
            {"name": "OUTPUT_SCHEMA", "type": "string", "required": True},
            {"name": "VOTERFILE_SCHEMA", "type": "string", "required": True},
            {"name": "VOTERFILE_TABLE", "type": "string", "required": True},
            {"name": "SAMPLE_SIZE", "type": "integer", "required": True},
            {"name": "RANDOM_SEED", "type": "integer", "required": False},
            {"name": "SURVEY_DB_ID", "type": "integer", "value": str(DB_ID)},
            {"name": "SURVEY_DB_CREDENTIAL_ID", "type": "integer", "value": str(DB_CREDENTIAL_ID)},
        ],
        "key": "draw_sample",
    },
    {
        "name": "03 Simulate Responses",
        "command": "cd /app && pip install -r requirements.txt && python scripts/03_simulate_responses.py",
        "params": [
            {"name": "SURVEY_ID", "type": "string", "required": True},
            {"name": "OUTPUT_SCHEMA", "type": "string", "required": True},
            {"name": "BASE_RESPONSE_RATE", "type": "float", "required": True},
            {"name": "RANDOM_SEED", "type": "integer", "required": False},
            {"name": "SURVEY_DB_ID", "type": "integer", "value": str(DB_ID)},
            {"name": "SURVEY_DB_CREDENTIAL_ID", "type": "integer", "value": str(DB_CREDENTIAL_ID)},
        ],
        "key": "simulate_responses",
    },
    {
        "name": "04 Weight and Report",
        "command": "cd /app && pip install -r requirements.txt && python scripts/04_weight_and_report.py",
        "params": [
            {"name": "SURVEY_ID", "type": "string", "required": True},
            {"name": "OUTPUT_SCHEMA", "type": "string", "required": True},
            {"name": "SURVEY_DB_ID", "type": "integer", "value": str(DB_ID)},
            {"name": "SURVEY_DB_CREDENTIAL_ID", "type": "integer", "value": str(DB_CREDENTIAL_ID)},
        ],
        "key": "weight_and_report",
    },
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-url", default="https://github.com/janesmithdemo/civis-demos.git")
    parser.add_argument("--repo-ref", default="surveys-demo")
    parser.add_argument("--census-credential-id", type=int, default=39492)
    args = parser.parse_args()

    # Inject census credential ID into script 01's CENSUS_API_KEY param
    for p in SCRIPTS[0]["params"]:
        if p["name"] == "CENSUS_API_KEY":
            p["value"] = str(args.census_credential_id)

    client = civis.APIClient()
    script_ids = {}

    for s in SCRIPTS:
        logger.info(f"Creating backing script: {s['name']}")
        script = client.scripts.post_containers(
            name=s["name"],
            required_resources={"cpu": 1024, "memory": 2048, "disk_space": 10},
            docker_image_name=DOCKER_IMAGE,
            docker_image_tag=DOCKER_TAG,
            repo_http_uri=args.repo_url,
            repo_ref=args.repo_ref,
            docker_command=s["command"],
            params=s["params"],
        )
        logger.info(f"  Created script_id={script.id} name='{script.name}'")
        script_ids[s["key"]] = script.id

    with open(OUTPUT_PATH, "w") as f:
        json.dump(script_ids, f, indent=2)
    logger.info(f"Script IDs written to {OUTPUT_PATH}: {script_ids}")


if __name__ == "__main__":
    main()
