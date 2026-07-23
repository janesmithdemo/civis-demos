# Deploying this demo to Civis Platform

Concrete, ordered steps to get `workflows/survey_pipeline.yaml` running for real on Platform. See
`README.md` for the conceptual background (why each script exists, the storage convention, the
ACS crosswalk). This file assumes you've already confirmed the live ACS pull works locally
(`dev/verify_acs_pull.py`).

Two things below are **assumptions, not verified facts** — confirm them against your Platform org
before trusting the scripts as-is:
- The exact env var names Civis exposes for a Database-type template parameter. This demo assumes
  `SURVEY_DB_ID` and `SURVEY_DB_CREDENTIAL_ID`; if your org's convention differs, update the four
  `os.environ[...]` reads in `scripts/*.py` to match.
- Whether container scripts in your org have network egress to `api.census.gov` by default. If
  step 5 fails to reach the Census API, this is the first thing to check with a Platform admin.

## 0. Push this code somewhere Civis can clone it

Civis container scripts clone a Git repo at run time. Commit and push the `DEMO OUTPUTS/` changes
to a branch (or `master`) on whatever remote your Civis org's Git integration is authorized
against, before step 3.

## 1. Get a Census API key

Free, from census.gov/data/key_signup.html. You already have one — see step 4 for where it's set.

## 2. Load a demo voterfile onto Platform

`02_draw_sample.py` reads `VOTERFILE_SCHEMA`/`VOTERFILE_TABLE` — that table needs to exist before
you run it. Generate the synthetic voterfile locally and upload it:

```bash
cd "DEMO OUTPUTS"
./.venv/bin/python dev/generate_synthetic_voterfile.py --state OH --n-rows 20000 --random-seed 1 \
    --output dev/data/synthetic_voterfile_oh.csv
```

Then upload it with `civis.io.dataframe_to_civis` (run this once, from anywhere with `civis`
installed and `CIVIS_API_KEY` set):

```python
import pandas as pd
import civis

df = pd.read_csv("dev/data/synthetic_voterfile_oh.csv")
future = civis.io.dataframe_to_civis(
    df,
    table="survey_demo_dev.synthetic_voterfile_oh",
    database=<YOUR_DATABASE_ID>,
    credential_id=<YOUR_CREDENTIAL_ID>,
    existing_table_rows="drop",
)
future.result()
```

## 3. Create the four container scripts (backing scripts)

For each of `scripts/01_pull_acs_benchmarks.py`, `02_draw_sample.py`, `03_simulate_responses.py`,
`04_weight_and_report.py`, create a Container Script in Civis Platform:

- **Git repo**: attach the repo from step 0, at the branch you pushed.
- **Command** (dev shortcut — no image build needed while iterating):
  ```bash
  cd /app/DEMO\ OUTPUTS && pip install -r requirements.txt && python scripts/01_pull_acs_benchmarks.py
  ```
  (swap the script name per backing script). The repo is cloned to `/app`; the working directory
  is not automatically set to this subfolder, so the `cd` is required.
- **Parameters** — add these, per script:

  | Script | Parameters |
  |---|---|
  | `01_pull_acs_benchmarks` | `SURVEY_ID`, `OUTPUT_SCHEMA`, `STATE`, `SURVEY_DB_ID`\*, `SURVEY_DB_CREDENTIAL_ID`\*, `CENSUS_API_KEY`\* |
  | `02_draw_sample` | `SURVEY_ID`, `OUTPUT_SCHEMA`, `VOTERFILE_SCHEMA`, `VOTERFILE_TABLE`, `SAMPLE_SIZE`, `RANDOM_SEED`, `SURVEY_DB_ID`\*, `SURVEY_DB_CREDENTIAL_ID`\* |
  | `03_simulate_responses` | `SURVEY_ID`, `OUTPUT_SCHEMA`, `BASE_RESPONSE_RATE`, `RANDOM_SEED`, `SURVEY_DB_ID`\*, `SURVEY_DB_CREDENTIAL_ID`\* |
  | `04_weight_and_report` | `SURVEY_ID`, `OUTPUT_SCHEMA`, `SURVEY_DB_ID`\*, `SURVEY_DB_CREDENTIAL_ID`\* |

  \* Mark these **Fixed** and set the real values directly in the Platform UI (your database ID,
  credential ID, and the Census API key). Fixed params still reach the script as env vars; they're
  just hidden from anyone who later runs a custom script off the published template. This is how
  the Census API key gets to `os.environ["CENSUS_API_KEY"]` without ever being in git.

## 4. Run each script once, individually

Run `01` and `02` first (no dependencies between them), then `03`, then `04`. After each run,
confirm the expected output table exists and has rows (see the table list in `README.md`'s
Pipeline section). This is the easiest point to catch a wrong parameter name or a missing table
before wiring up the workflow.

## 5. Publish each as a template

**Code > Publish as Template** on each backing script. Record the four resulting template IDs.

## 6. Wire up the workflow

Open `workflows/survey_pipeline.yaml` and replace the four `REPLACE_WITH_..._TEMPLATE_ID`
placeholders with the real template IDs from step 5. Create a Workflow in Platform (Workflows >
New Workflow, or paste the YAML directly if your Platform UI supports importing one), then run it
with these inputs: `survey_id`, `output_schema`, `state`, `voterfile_schema`, `voterfile_table`,
`sample_size`, `base_response_rate`, and optionally `random_seed`.

## 7. Verify

Query `{survey_id}_topline_report` and `{survey_id}_weighting_diagnostics` — a design effect
under ~2-3 and weighted shares close to the target shares in the diagnostics table indicate a
healthy run. If the design effect is very high, check `{survey_id}_acs_targets_race` and
`{survey_id}_acs_targets_age_gender` for a category that ended up with implausibly large
population share — that usually means a crosswalk mismatch rather than a real weighting problem.

## 8. (Optional, once stable) Switch to a custom Docker image

Once the pipeline is running reliably with the `pip install -r requirements.txt` dev shortcut,
build the image from `Dockerfile` and push it to whatever registry your Civis org's container
scripts pull custom images from (Docker Hub, ECR, or an internal registry — confirm which with a
Platform admin, this varies by org):

```bash
docker build -t <your-registry>/survey-demo:latest .
docker push <your-registry>/survey-demo:latest
```

Then point each container script's Docker image setting at that image/tag instead of the base
`civisanalytics/datascience-python:8.4` + runtime `pip install`, and simplify each script's
command to just `python scripts/0N_....py` (dependencies are already baked in).
