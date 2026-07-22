# Handoff: Civis Survey Infrastructure Demo

Read this before touching anything in a new session. It covers state,
architecture, all live Platform IDs, and hard-won discoveries that aren't
obvious from the code alone.

---

## What this is

A greenfield demo pipeline showing Civis Platform's infrastructure
capabilities for survey-running buyers. The pitch: standardised
code-based process, reproducible Docker+Git execution, Civis Templates and
Workflows, and structured input/output storage.

The demo models a buyer who conducts surveys in-house. It is split into
**two workflows**:

| Workflow | Name | Purpose |
|---|---|---|
| 1 | `field_prep_pipeline` | Pull ACS benchmarks + draw voterfile sample → export field file to survey team |
| 2 | `results_pipeline` | Ingest returned results via file import → rake weights → publish HTML report |

A buyer runs the **Setup Workflows** template once per survey. It creates
both workflows, pre-populates the import job with synthetic data, and
immediately fires Workflow 1.

---

## Constraints — do not violate

1. **Never touch real buyer data.** The voterfile is either the synthetic
   generator (`dev/generate_synthetic_voterfile.py`) or the uploaded table
   `surveys.oh_voterfile` — never a real client table.
2. **Never query live Civis Platform data without being asked.** Don't use
   MCP tools (`run_query`, `list_tables`, etc.) to browse real data on your
   own initiative. Ask Owen for schemas/data dictionaries instead.
3. **Never log, print, or commit secrets.** The Census API key lives as a
   Civis credential (id 39492); it never appears in code or output.

---

## Repository layout

```
scripts/
  01_pull_acs_benchmarks.py   ← ACS marginals → {survey_id}_acs_targets_*
  02_draw_voterfile_sample.py ← stratified sample → {survey_id}_sample
  03_export_field_file.py     ← export sample as Civis file for survey team
  04_weight_and_report.py     ← rake weights, topline/crosstabs/diagnostics

dev/
  setup_workflows.py          ← ONE-SHOT: creates both workflows, fires WF1
  03_create_scripts.py        ← create all backing container scripts
  04_run_scripts.py           ← run all 4 pipeline scripts in order (debug)
  05_publish_templates.py     ← publish backing scripts as templates
  06_wire_workflow.py         ← lower-level single-workflow wiring utility
  07_verify.py                ← verify output tables after a run
  08_publish_report.py        ← build + publish HTML report to Civis
  generate_synthetic_voterfile.py
  verify_acs_pull.py
  script_ids.json             ← gitignored, local IDs from 03_create_scripts
  template_ids.json           ← gitignored, template IDs (see table below)

workflows/
  field_prep_pipeline.yaml    ← Workflow 1 (deployed, git-backed, IDs filled)
  results_pipeline.yaml       ← Workflow 2 (deployed, git-backed, IDs filled)

survey_demo/                  ← pure-function package (no civis.io inside)
  acs.py, strata.py, sampling.py, responses.py, weighting.py, reporting.py

config/
  strata.yaml, crosswalks.yaml, acs_variables.yaml, state_fips.yaml
```

---

## Everything that is live on Civis Platform right now

### Database & credentials

| Thing | Value | Notes |
|---|---|---|
| Database name | Civis Database | managed Redshift |
| Database ID | **326** | use this, not 32 (SKILL.md default is wrong for this org) |
| Remote host ID | 326 | same integer happens to match |
| Default credential | **2078** (`jsmith_default`) | works for reads/writes from local API sessions and when set as a fixed param in backing scripts |
| Census API credential | **39492** (`CENSUS API KEY 2026`) | stored as `credential_custom` type → exposed in containers as `CENSUS_API_KEY_PASSWORD` |

### Backing scripts (container)

| ID | Name | Script |
|---|---|---|
| 362557800 | 00 Setup Survey Workflows | `dev/setup_workflows.py` |
| 362535366 | 01 Pull ACS Benchmarks | `scripts/01_pull_acs_benchmarks.py` |
| 362535368 | 02 Draw Voterfile Sample | `scripts/02_draw_voterfile_sample.py` |
| 362535370 | 03 Export Field File | `scripts/03_export_field_file.py` |
| 362535371 | 04 Weight and Report | `scripts/04_weight_and_report.py` |
| 362544213 | 08 Publish Report | `dev/08_publish_report.py` |

### Templates

| ID | Key in `template_ids.json` |
|---|---|
| 318584 | `setup_workflows` |
| 318569 | `pull_acs_benchmarks` |
| 318570 | `draw_voterfile_sample` |
| 318571 | `export_field_file` |
| 318572 | `weight_and_report` |
| 318573 | `publish_report` |

### Workflows (both git-backed to `surveys-demo` branch)

| ID | Name | YAML |
|---|---|---|
| 121604 | `field_prep_pipeline` | `workflows/field_prep_pipeline.yaml` |
| 121605 | `results_pipeline` | `workflows/results_pipeline.yaml` |

The workflow YAMLs committed to `surveys-demo` contain **real template
IDs** (filled by `setup_workflows.py` / `06_wire_workflow.py`). The
placeholder strings (`REPLACE_WITH_...`) only exist before a setup run.
To update a git-backed workflow after pushing changes, use
`POST /workflows/{id}/git/checkout-latest` — patching `definition`
inline is rejected once git is attached.

### Demo survey data

| Thing | Value |
|---|---|
| Survey ID | `demo_oh_2026` |
| Output schema | `surveys` |
| Voterfile | `surveys.oh_voterfile` (20 000 synthetic OH rows) |
| Sample size | 1 000 |
| Base response rate | 0.03 |
| State | OH |
| Import job (results ingest) | **362555881** — pre-populated with synthetic responses |
| Published report | id 130568 |

---

## How the two-workflow setup works

### Running from scratch for a new survey

```bash
python dev/setup_workflows.py \
  --survey-id <ID> \
  --output-schema <SCHEMA> \
  --state <XX> \
  --voterfile-schema <SCHEMA> \
  --voterfile-table <TABLE> \
  --sample-size <N> \
  --base-response-rate <0.0-1.0>
```

`setup_workflows.py` does in one shot:
1. Generates synthetic responses from the existing `{survey_id}_sample`
   table (demo pre-population)
2. Uploads CSV as a Civis file; creates a static `post_files_csv` import
   job targeting `{schema}.{survey_id}_responses`
3. Fills both workflow YAML placeholders with real IDs, commits + pushes
4. Creates Workflow 1 and Workflow 2, attaches git to both
5. Fires Workflow 1 (`post_executions` with `input=`, not `arguments=`)

### Running from the Platform UI

The buyer creates a custom script from template **318584**
(`survey_demo_00_setup_workflows`), fills in parameters, and runs it. All
parameters are also available as env vars so the script works as a
container.

### After Workflow 1 completes

The `export_field_file` task writes the sample as a downloadable Civis
file. The buyer downloads it, conducts the survey, then:
1. Opens import job **362555881** in Platform
2. Uploads the completed CSV (drag and drop)
3. Runs Workflow 2

---

## Hard-won discoveries — don't repeat these

**Civis container credentials:**
- Run-scoped container API keys do NOT resolve `client.default_database_credential_id`
  the same way a personal API key does. Always set `SURVEY_DB_CREDENTIAL_ID` as a fixed
  param on backing scripts (value `2078`) rather than relying on the default.
- Fixed params are injected as env vars and **cannot be overridden** via
  `patch_containers(arguments={...})`. Arguments only affect non-fixed params.

**Database IDs:**
- This org has three databases: 326 (Civis Database / Redshift), 2697 (BigQuery), 1094 (postgis-demo).
  There is no database with ID 32. SKILL.md defaults are wrong for this org.

**Census API key:**
- Stored as a Civis credential (type `credential_custom`, id 39492).
  In containers it is exposed as `CENSUS_API_KEY_PASSWORD` (not `CENSUS_API_KEY`).
  `scripts/01_pull_acs_benchmarks.py` reads `CENSUS_API_KEY_PASSWORD`.

**civis Python client gotchas:**
- `civis.ContainerFuture` does not exist — use `civis.futures.ContainerFuture`.
- `ContainerFuture` has `._civis_state`, not `.state`.
- `client.scripts.post_containers` requires `required_resources` as a positional arg.
- `repo_http_uri` (not `repo_http_clone_url`) is the git param for container scripts.
- `client.workflows.post_executions(id, input={...})` — the kwarg is `input`, not `arguments`.
- `client.imports.post_files_csv` source must have `file_ids` (list of Civis file IDs).

**Git-backed workflows:**
- Attach git: `PUT /workflows/{id}/git` with `gitRepoUrl`, `gitBranch`, `gitPath`, `gitRefType`.
- Check if git-backed: `GET /workflows/{id}/git` — look for `gitRepo` key (not `gitRepoUrl`).
- Sync after a push: `POST /workflows/{id}/git/checkout-latest` — cannot patch `definition`
  inline once `pull_from_git` is active.

**`ipfn` mutation bug (pre-existing, already fixed):**
- `ipfn.ipfn().iteration()` mutates its input in place. `weighting.py` passes `seed.copy()`.
  Never remove that `.copy()` — it causes weights to silently all equal 1.

---

## Local development

```bash
# Install
python3 -m venv .venv
source .venv/bin/activate
pip install -e . -r dev-requirements.txt

# Tests (35 passing, all offline)
pytest tests/ -q

# Verify ACS pull (needs real key — user runs this, not you)
python dev/verify_acs_pull.py --state OH
```

The `.venv/` is gitignored. `dev/script_ids.json` and `dev/template_ids.json`
are also gitignored (environment-specific). `dev/data/` is gitignored.

---

## Git remote

```
origin  https://github.com/janesmithdemo/civis-demos.git (branch: surveys-demo)
```

The branch `surveys-demo` is the working branch. `master` is the base.
The workflow YAMLs on this branch contain filled-in template IDs — they
reflect the currently deployed state.

---

## What's left / possible next steps

- **End-to-end workflow run:** Workflow 1 execution 11279425 was fired at
  the end of the last session. Verify it completed, then run Workflow 2
  (`dev/07_verify.py` can check the output tables).
- **DEPLOYMENT.md is stale** — it describes the old single-workflow manual
  deployment process. Consider updating or replacing it with a doc that
  describes `setup_workflows.py` as the entry point.
- **Tests:** 35 tests pass locally against pure functions. No integration
  tests against the live Platform; adding a smoke-test run against
  `surveys.demo_oh_2026_*` tables would be valuable before showing buyers.
- **Custom Docker image:** The backing scripts currently do
  `pip install -r requirements.txt` at run time (slow). Once stable, build
  from `Dockerfile` and remove the runtime install step.
- **Workflow 1 dependency note:** `pull_acs_benchmarks` runs in parallel
  with `draw_voterfile_sample` and has no `on-success`. Workflow 1 is
  considered complete when both `pull_acs_benchmarks` AND `export_field_file`
  finish. The ACS targets are read by `weight_and_report` in Workflow 2, so
  both must complete before Workflow 2 is meaningful.
