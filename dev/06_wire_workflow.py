#!/usr/bin/env python
"""Step 6: Replace template ID placeholders in the workflow YAML, commit it
to version control, and create/update the workflow in Civis Platform.

The filled YAML is written back to workflows/survey_pipeline.yaml and
committed so git tracks the deployed definition. The Civis workflow is
created (or updated if --workflow-id is given) from that same definition.

Reads template IDs from dev/template_ids.json by default; individual IDs
can also be passed as flags to override.

Usage:
    python dev/06_wire_workflow.py [--name survey_demo_pipeline] \\
        [--workflow-id <ID>] \\
        [--template-id-01 <ID>] \\
        [--template-id-02 <ID>] \\
        [--template-id-03 <ID>] \\
        [--template-id-04 <ID>]
"""
import argparse
import json
import pathlib
import subprocess

import civis

logger = civis.civis_logger(__name__)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW_YAML = REPO_ROOT / "workflows" / "survey_pipeline.yaml"
TEMPLATE_IDS_PATH = pathlib.Path(__file__).resolve().parent / "template_ids.json"

PLACEHOLDERS = {
    "pull_acs_benchmarks": "REPLACE_WITH_PULL_ACS_BENCHMARKS_TEMPLATE_ID",
    "draw_sample": "REPLACE_WITH_DRAW_SAMPLE_TEMPLATE_ID",
    "conduct_survey": "REPLACE_WITH_CONDUCT_SURVEY_TEMPLATE_ID",
    "weight_and_report": "REPLACE_WITH_WEIGHT_AND_REPORT_TEMPLATE_ID",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="survey_demo_pipeline")
    parser.add_argument("--workflow-id", type=int, default=None,
                        help="Update an existing workflow instead of creating a new one.")
    parser.add_argument("--template-id-01", type=int)
    parser.add_argument("--template-id-02", type=int)
    parser.add_argument("--template-id-03", type=int)
    parser.add_argument("--template-id-04", type=int)
    args = parser.parse_args()

    # Load template IDs: flags override file values
    template_ids = {}
    if TEMPLATE_IDS_PATH.exists():
        with open(TEMPLATE_IDS_PATH) as f:
            template_ids = json.load(f)
        logger.info(f"Loaded template IDs from {TEMPLATE_IDS_PATH}")

    overrides = {
        "pull_acs_benchmarks": args.template_id_01,
        "draw_sample": args.template_id_02,
        "conduct_survey": args.template_id_03,
        "weight_and_report": args.template_id_04,
    }
    for key, val in overrides.items():
        if val is not None:
            template_ids[key] = val

    missing = [k for k in PLACEHOLDERS if k not in template_ids]
    if missing:
        raise ValueError(
            f"Missing template IDs for: {missing}. "
            f"Run 05_publish_templates.py first or pass --template-id-* flags."
        )

    with open(WORKFLOW_YAML) as f:
        definition = f.read()

    for key, placeholder in PLACEHOLDERS.items():
        definition = definition.replace(placeholder, str(template_ids[key]))

    if "REPLACE_WITH_" in definition:
        raise RuntimeError("Unreplaced placeholders remain in workflow YAML after substitution.")

    # Write the filled definition back to the YAML file and commit it so git
    # tracks the deployed workflow state.
    with open(WORKFLOW_YAML, "w") as f:
        f.write(definition)
    logger.info(f"Wrote filled workflow definition to {WORKFLOW_YAML}")

    subprocess.run(
        ["git", "add", str(WORKFLOW_YAML)],
        cwd=REPO_ROOT, check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", f"deploy: wire workflow with real template IDs\n\n{_id_summary(template_ids)}"],
        cwd=REPO_ROOT, check=True,
    )
    subprocess.run(
        ["git", "push"],
        cwd=REPO_ROOT, check=True,
    )
    logger.info("Committed and pushed workflow YAML to version control")

    client = civis.APIClient()
    if args.workflow_id:
        wf = client.workflows.patch(args.workflow_id, name=args.name, definition=definition)
        logger.info(f"Workflow updated: id={wf.id} name='{args.name}'")
    else:
        wf = client.workflows.post(name=args.name, definition=definition)
        logger.info(f"Workflow created: id={wf.id} name='{args.name}'")


def _id_summary(template_ids):
    return "\n".join(f"  {k}: {v}" for k, v in sorted(template_ids.items()))


if __name__ == "__main__":
    main()
