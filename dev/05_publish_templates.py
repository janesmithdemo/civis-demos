#!/usr/bin/env python
"""Step 5: Publish each backing script as a Civis script template.

Records the resulting template IDs to dev/template_ids.json for use by
06_wire_workflow.py.

Reads script IDs from dev/script_ids.json by default (written by
03_create_scripts.py); individual IDs can be passed as flags to override.

Usage:
    python dev/05_publish_templates.py \\
        [--script-id-01 <ID>] \\
        [--script-id-02 <ID>] \\
        [--script-id-03 <ID>] \\
        [--script-id-04 <ID>] \\
        [--name-prefix survey_demo]
"""
import argparse
import json
import pathlib

import civis

logger = civis.civis_logger(__name__)

SCRIPT_NAMES = [
    "01_pull_acs_benchmarks",
    "02_draw_sample",
    "03_conduct_survey",
    "04_weight_and_report",
]

SCRIPT_IDS_PATH = pathlib.Path(__file__).resolve().parent / "script_ids.json"
OUTPUT_PATH = pathlib.Path(__file__).resolve().parent / "template_ids.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script-id-01", type=int)
    parser.add_argument("--script-id-02", type=int)
    parser.add_argument("--script-id-03", type=int)
    parser.add_argument("--script-id-04", type=int)
    parser.add_argument("--name-prefix", default="survey_demo")
    args = parser.parse_args()

    ids = {}
    if SCRIPT_IDS_PATH.exists():
        with open(SCRIPT_IDS_PATH) as f:
            data = json.load(f)
        ids = [
            data.get("pull_acs_benchmarks"),
            data.get("draw_sample"),
            data.get("simulate_responses"),
            data.get("weight_and_report"),
        ]
    else:
        ids = [None, None, None, None]

    script_ids = [
        args.script_id_01 or ids[0],
        args.script_id_02 or ids[1],
        args.script_id_03 or ids[2],
        args.script_id_04 or ids[3],
    ]

    missing = [SCRIPT_NAMES[i] for i, v in enumerate(script_ids) if not v]
    if missing:
        raise ValueError(
            f"Missing script IDs for: {missing}. "
            "Run 03_create_scripts.py first or pass --script-id-* flags."
        )

    client = civis.APIClient()
    template_ids = {}

    for script_id, short_name in zip(script_ids, SCRIPT_NAMES):
        template_name = f"{args.name_prefix}_{short_name}"
        logger.info(f"Publishing script_id={script_id} as template '{template_name}'")
        tmpl = client.templates.post_scripts(script_id=script_id, name=template_name)
        logger.info(f"  template_id={tmpl.id}")
        key = short_name.split("_", 1)[1]  # e.g. "pull_acs_benchmarks"
        template_ids[key] = tmpl.id

    with open(OUTPUT_PATH, "w") as f:
        json.dump(template_ids, f, indent=2)
    logger.info(f"Template IDs written to {OUTPUT_PATH}: {template_ids}")


if __name__ == "__main__":
    main()
