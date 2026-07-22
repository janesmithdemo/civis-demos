# Survey Infrastructure Demo (Civis Platform)

This is a **demonstration only**. It shows how a survey sampling → fielding → weighting →
reporting pipeline can be built as a standardized, code-based, configurable process on Civis
Platform (Git-integrated container scripts, Civis Templates, and Workflows). It does not run
against any buyer data and there is no live engagement behind it — every input here is either
Civis's own demo data or fabricated locally by `dev/generate_synthetic_voterfile.py`.

Nothing outside this `DEMO OUTPUTS/` directory is part of this demo. The rest of the repo is a
legacy survey SDK kept only as background context and is not used by any code here.

## Pipeline

Four scripts, each a candidate Civis script template, each independently runnable and
parameterized:

```
scripts/01_pull_acs_benchmarks.py   ACS population marginals (age x gender, race)  for STATE
                                     -> {SURVEY_ID}_acs_targets_age_gender, {SURVEY_ID}_acs_targets_race

scripts/02_draw_sample.py           stratified sample from a voterfile table
                                     -> {SURVEY_ID}_sample

scripts/03_simulate_responses.py    synthetic survey responses for the sample
                                     -> {SURVEY_ID}_responses

scripts/04_weight_and_report.py     rake responses to ACS marginals, summarize
                                     -> {SURVEY_ID}_weighted, {SURVEY_ID}_topline_report,
                                        {SURVEY_ID}_crosstabs, {SURVEY_ID}_weighting_diagnostics
```

`01` and `02` have independent inputs and can run in parallel; `03` depends on `02`; `04` depends
on both `01` (ACS targets) and `03` (responses). See `workflows/survey_pipeline.yaml`.

The `{SURVEY_ID}_*` naming convention is deliberate: every survey run through this pipeline lands
in the same schema with the same table suffixes, so multiple surveys can be compared or unioned
later without bespoke plumbing per survey — one of the enablement goals for this engagement.

### Why simulated responses?

The buyer runs their own surveys with their own vendor; Civis isn't fielding anything here. `03`
fabricates plausible answers (`vote_choice`, `approval_rating`) from the sample's modeled
`likely_dem`/`likely_rep` propensity scores, purely so `04` has something real to weight and
report on. In a real deployment `03` would be replaced by however the buyer's vendor delivers
responses.

### Why ACS, and why a crosswalk?

Post-hoc weighting rakes the survey's demographic composition to match the general population.
ACS is the standard population benchmark for this. ACS's category labels (Census age brackets,
`B03002` race/Hispanic-origin categories) don't match the voterfile's labels
(`age_bucket_noncommercial`, `race5way_noncommercial`) out of the box — `config/crosswalks.yaml`
defines that recode explicitly, and `survey_demo.strata.validate_crosswalk_coverage()` checks it's
complete (no ACS variable double-counted or dropped, every voterfile category covered) before
`01` runs. This is the most likely place a demo like this silently breaks, so it's checked eagerly
rather than assumed.

`vf_reg_party` and `urbanicity` are used to balance the drawn *sample* in `02` (see
`config/strata.yaml`) but are not raking targets in `04` — ACS has no equivalent for either.

## Local setup

```bash
cd "DEMO OUTPUTS"
python3 -m venv .venv && source .venv/bin/activate
pip install -e . -r dev-requirements.txt
pytest tests/ -q
```

To generate a local synthetic voterfile to run `02_draw_sample.py` against (dev-only, never real
data — see the module docstring):

```bash
python dev/generate_synthetic_voterfile.py --state OH --n-rows 20000 --random-seed 1 \
    --output dev/data/synthetic_voterfile_oh.csv
```

### Census API key

As of this writing, the public Census API rejects every request without a key, including minimal
ones. `01_pull_acs_benchmarks.py` requires `CENSUS_API_KEY` (free, from
census.gov/data/key_signup.html). When publishing this script as a template, set it as a **fixed**
parameter on the backing script so template/workflow users never see or supply it (see
"Publishing as templates" below).

### What's actually verified here vs. on Platform

`pytest` exercises every pure function in `survey_demo/` (strata assignment, sampling allocation,
response simulation, raking convergence and diagnostics, reporting, and ACS recoding against the
real `config/*.yaml` crosswalk) entirely offline, using synthetic DataFrames and a hand-authored,
clearly-labeled fixture standing in for a Census API response (`tests/fixtures/`). What is **not**
verified in this repo: the `civis.io` read/write round trip in `scripts/*.py`, and
`workflows/survey_pipeline.yaml` actually executing. Those need to be run on Civis Platform.

## Reproducible execution: Docker + Git

Each script is a thin wrapper: read params from env vars → `civis.io` read → call the pure
functions in `survey_demo/` → `civis.io` write, logging via `civis.civis_logger()`. All
non-trivial logic lives in `survey_demo/`, which is unit tested independently of Platform access.

**While iterating**, skip building a custom Docker image. Attach this repo to a Civis container
script and run:

```bash
cd /app/DEMO\ OUTPUTS && pip install -r requirements.txt && python scripts/02_draw_sample.py
```

(the repo is cloned to `/app`; the container script's working directory is not automatically
inside this subfolder, so the `cd` is required).

**Once stable**, build `Dockerfile` (multi-stage, based on `civisanalytics/datascience-python:8.4`)
into a custom image so `pip install` isn't needed at run time:

```bash
docker build -t survey-demo:latest .
```

## Publishing as templates and chaining with a Workflow

Each of `scripts/01-04` follows the standard Civis lifecycle: develop/test as a normal container
script (backing script) → **Code > Publish as Template** → the template can then be run as a
custom script or referenced from a Workflow via `from_template_id`.

Recommended parameter setup per backing script:
- `SURVEY_DB_ID` / `SURVEY_DB_CREDENTIAL_ID` (Database-type param) and `CENSUS_API_KEY`: mark
  these **fixed** so they're hidden from anyone running the published template.
- `SURVEY_ID`, `OUTPUT_SCHEMA`, `STATE`, `VOTERFILE_SCHEMA`, `VOTERFILE_TABLE`, `SAMPLE_SIZE`,
  `BASE_RESPONSE_RATE`, `RANDOM_SEED`: exposed, so each survey run can vary them.

`workflows/survey_pipeline.yaml` chains the four templates with the correct dependencies (`01`
and `02` in parallel, `03` after `02`, `04` joining both `01` and `03`). Replace the
`REPLACE_WITH_..._TEMPLATE_ID` placeholders with the real template IDs after publishing, then
run the workflow with `survey_id`, `state`, `voterfile_schema`, `voterfile_table`, `sample_size`,
and `base_response_rate` as inputs.

**See `DEPLOYMENT.md` for the full ordered checklist** (loading a demo voterfile onto Platform,
exact parameters per script, publishing, wiring up the workflow, and verifying a run).

## Making changes without breaking production

1. Branch off `master`.
2. Change code in `survey_demo/` (the pure-function layer) or `config/*.yaml`.
3. `pytest tests/ -q` — this exercises the real logic without needing Platform access.
4. Open a PR.
5. Merge. A custom script/template created from a backing script automatically picks up changes
   to that backing script on its next run — no republishing needed for code changes, only for
   parameter changes.
