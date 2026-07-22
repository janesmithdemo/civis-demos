#!/usr/bin/env python
"""Create both survey pipelines and run Workflow 1 (Field Prep).

This script wires the full two-workflow survey demo:

  Workflow 1 — Field Prep  (field_prep_pipeline.yaml)
    pull_acs_benchmarks + draw_voterfile_sample → export_field_file

  Workflow 2 — Results Processing  (results_pipeline.yaml)
    ingest_survey_results (static file import) → weight_and_report → publish_report

Setup steps performed:
  1. Generate synthetic survey responses CSV (demo pre-population)
  2. Upload CSV as a Civis file and create a static file import job targeting
     {output_schema}.{survey_id}_responses — the buyer uploads real results here
  3. Fill template ID placeholders in both workflow YAMLs, commit + push to git
  4. Create both Civis workflow objects and attach git version control
  5. Run Workflow 1 immediately

When Workflow 1 completes the buyer can download the field file, conduct
the survey, then upload results via the import job and run Workflow 2.
The import job has been pre-populated with synthetic data so Workflow 2
can be demonstrated immediately.

Usage:
    python dev/setup_workflows.py \\
        --survey-id demo_oh_2026 \\
        --output-schema surveys \\
        --state OH \\
        --voterfile-schema surveys \\
        --voterfile-table oh_voterfile \\
        --sample-size 1000 \\
        --base-response-rate 0.03 \\
        [--db-id 326] \\
        [--random-seed 42] \\
        [--repo-url https://github.com/janesmithdemo/civis-demos.git] \\
        [--repo-ref surveys-demo]
"""
import argparse
import io
import json
import os
import pathlib
import subprocess
import sys

import requests

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import civis
import survey_demo.responses as sim_responses

logger = civis.civis_logger(__name__)

TEMPLATE_IDS_PATH = pathlib.Path(__file__).resolve().parent / "template_ids.json"

FIELD_PREP_YAML = REPO_ROOT / "workflows" / "field_prep_pipeline.yaml"
RESULTS_YAML = REPO_ROOT / "workflows" / "results_pipeline.yaml"

FIELD_PREP_PLACEHOLDERS = {
    "pull_acs_benchmarks": "REPLACE_WITH_PULL_ACS_BENCHMARKS_TEMPLATE_ID",
    "draw_voterfile_sample": "REPLACE_WITH_DRAW_VOTERFILE_SAMPLE_TEMPLATE_ID",
    "export_field_file": "REPLACE_WITH_EXPORT_FIELD_FILE_TEMPLATE_ID",
}
RESULTS_PLACEHOLDERS = {
    "weight_and_report": "REPLACE_WITH_WEIGHT_AND_REPORT_TEMPLATE_ID",
    "publish_report": "REPLACE_WITH_PUBLISH_REPORT_TEMPLATE_ID",
}


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
    parser.add_argument("--db-id", type=int, default=326)
    parser.add_argument("--repo-url",
                        default="https://github.com/janesmithdemo/civis-demos.git")
    parser.add_argument("--repo-ref", default="surveys-demo")
    args = parser.parse_args()

    client = civis.APIClient()
    template_ids = json.loads(TEMPLATE_IDS_PATH.read_text())

    # ── Step 1: generate synthetic responses for demo pre-population ──────────
    logger.info("Generating synthetic survey responses for demo pre-population")
    database = {"database": args.db_id}
    sample_df = civis.io.read_civis_sql(
        f"SELECT voterbase_id, likely_dem, likely_rep "
        f"FROM {args.output_schema}.{args.survey_id}_sample",
        return_as="pandas",
        **database,
    )
    responses_df = sim_responses.simulate_responses(
        sample_df, args.base_response_rate, random_seed=args.random_seed
    )
    logger.info(f"  Generated {len(responses_df)} synthetic responses")

    # ── Step 2: upload responses CSV as a Civis file ──────────────────────────
    buf = io.BytesIO()
    responses_df.to_csv(buf, index=False, encoding="utf-8")
    buf.seek(0)
    file_name = f"{args.survey_id}_responses_demo.csv"
    file_id = civis.io.file_to_civis(buf, name=file_name)
    logger.info(f"  Uploaded demo responses: file_id={file_id} name='{file_name}'")

    # ── Step 3: create static file import job ────────────────────────────────
    import_job = client.imports.post_files_csv(
        name=f"Survey Results — {args.survey_id}",
        source={"file_ids": [file_id]},
        destination={
            "schema": args.output_schema,
            "table": f"{args.survey_id}_responses",
            "remote_host_id": args.db_id,
            "credential_id": 2078,
        },
        first_row_is_header=True,
        existing_table_rows="drop",
        hidden=False,
    )
    logger.info(
        f"  Import job created: id={import_job.id} — "
        f"open in Platform to upload real survey results"
    )

    # ── Step 4: fill workflow YAMLs, commit, push ────────────────────────────
    field_prep_def = _fill_yaml(
        FIELD_PREP_YAML,
        {**{k: template_ids[k] for k in FIELD_PREP_PLACEHOLDERS}, **FIELD_PREP_PLACEHOLDERS},
        template_ids,
        FIELD_PREP_PLACEHOLDERS,
    )
    results_def = _fill_yaml(
        RESULTS_YAML,
        {},
        {**template_ids, "import_job": import_job.id},
        {**RESULTS_PLACEHOLDERS, "import_job": "REPLACE_WITH_IMPORT_JOB_ID"},
    )

    _commit_and_push([FIELD_PREP_YAML, RESULTS_YAML], template_ids, import_job.id)

    # ── Step 5: create / update both workflow objects ─────────────────────────
    wf1 = _upsert_workflow(client, "field_prep_pipeline", field_prep_def,
                           args.repo_url, args.repo_ref, "workflows/field_prep_pipeline.yaml")
    wf2 = _upsert_workflow(client, "results_pipeline", results_def,
                           args.repo_url, args.repo_ref, "workflows/results_pipeline.yaml")

    # ── Step 6: run Workflow 1 ────────────────────────────────────────────────
    logger.info(f"Running Workflow 1 (id={wf1.id}): field_prep_pipeline")
    execution = client.workflows.post_executions(
        wf1.id,
        arguments={
            "survey_id": args.survey_id,
            "output_schema": args.output_schema,
            "state": args.state,
            "voterfile_schema": args.voterfile_schema,
            "voterfile_table": args.voterfile_table,
            "sample_size": str(args.sample_size),
            **({"random_seed": str(args.random_seed)} if args.random_seed else {}),
        },
    )
    logger.info(f"  Execution started: id={execution.id}")
    logger.info("")
    logger.info("─" * 60)
    logger.info(f"Workflow 1 id : {wf1.id}")
    logger.info(f"Workflow 2 id : {wf2.id}")
    logger.info(f"Import job id : {import_job.id}")
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Wait for Workflow 1 to complete")
    logger.info("  2. Download the field file from the export_field_file run outputs")
    logger.info("  3. Conduct the survey and collect results")
    logger.info(f"  4. Open import job {import_job.id} in Platform and upload the results CSV")
    logger.info(f"  5. Run Workflow 2 (id={wf2.id}) with survey_id={args.survey_id!r} "
                f"output_schema={args.output_schema!r}")
    logger.info("─" * 60)


# ── helpers ───────────────────────────────────────────────────────────────────

def _fill_yaml(yaml_path, _, ids, placeholders):
    definition = yaml_path.read_text()
    for key, placeholder in placeholders.items():
        definition = definition.replace(placeholder, str(ids[key]))
    if "REPLACE_WITH_" in definition:
        missing = [p for p in placeholders.values() if p in definition]
        raise RuntimeError(f"Unfilled placeholders in {yaml_path.name}: {missing}")
    yaml_path.write_text(definition)
    return definition


def _commit_and_push(paths, template_ids, import_job_id):
    for p in paths:
        subprocess.run(["git", "add", str(p)], cwd=REPO_ROOT, check=True)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO_ROOT)
    if diff.returncode != 0:
        msg = (
            "deploy: wire field_prep and results workflows\n\n"
            + "\n".join(f"  {k}: {v}" for k, v in sorted(template_ids.items()))
            + f"\n  import_job: {import_job_id}"
        )
        subprocess.run(["git", "commit", "-m", msg], cwd=REPO_ROOT, check=True)
        subprocess.run(["git", "push"], cwd=REPO_ROOT, check=True)
        logger.info("Committed and pushed workflow YAMLs")
    else:
        logger.info("Workflow YAMLs unchanged — skipping commit")


def _upsert_workflow(client, name, definition, repo_url, repo_ref, yaml_path):
    wf = client.workflows.post(name=name, definition=definition)
    logger.info(f"Workflow '{name}' created: id={wf.id}")
    _attach_git(wf.id, repo_url, repo_ref, yaml_path)
    return wf


def _attach_git(workflow_id, repo_url, repo_ref, yaml_path):
    api_key = os.environ["CIVIS_API_KEY"]
    resp = requests.put(
        f"https://api.civisanalytics.com/workflows/{workflow_id}/git",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "gitRepoUrl": repo_url,
            "gitBranch": repo_ref,
            "gitPath": yaml_path,
            "gitRefType": "branch",
        },
    )
    resp.raise_for_status()
    logger.info(f"  Git attached: {yaml_path} @ {repo_ref}")


if __name__ == "__main__":
    main()
