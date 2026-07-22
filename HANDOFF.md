# Handoff: Civis Survey Infrastructure Demo

Read this first in a new session. It's the "why" and "what's already true" that isn't fully
captured by reading the code alone. `README.md` and `DEPLOYMENT.md` in this same directory are
the living reference docs — this file is orientation + things that would otherwise take a while
to re-discover.

## What this is, in one paragraph

Civis Analytics is pitching a potential buyer (who runs surveys) on Civis Platform's
infrastructure/enablement capabilities: standardized code-based process, reproducible Docker+Git
execution, Civis Templates, Workflows, and standardized input/output storage for cross-survey
analysis. Civis itself doesn't run surveys anymore. This repo's `DEMO OUTPUTS/` directory is a
**greenfield demo pipeline** built to show that capability — 4 parameterized Python scripts
(pull ACS benchmarks → draw a stratified sample → simulate survey responses → rake weights and
report) that would each become a Civis script template, chained by a Civis Workflow.

## Constraints that shaped every decision here — do not violate these

1. **Never touch real buyer data.** There is no live engagement. Nothing in this codebase reads
   from, writes to, or is parameterized toward any buyer-supplied table. The "voterfile" this
   pipeline samples from is either Civis's own demo data or the locally-fabricated synthetic
   generator (`dev/generate_synthetic_voterfile.py`) — never anything resembling a real client's
   data.
2. **Never query live Civis Platform data on your own initiative.** The user (Owen) explicitly
   corrected this once already: don't use Civis MCP tools (`list_tables`, `get_table`,
   `run_query`, etc.) to browse real platform tables/data, even read-only, without being asked.
   Ask for schemas/data dictionaries directly instead. This applies even for orientation — ask,
   don't poke.
3. **This repo's `.venv` and everything outside `DEMO OUTPUTS/` is a legacy `surveys-sdk-python`
   codebase kept as reference only.** It was never reused, imported, or modified, and shouldn't
   be. It's useful for vocabulary (see below) but nothing in `DEMO OUTPUTS/` depends on it.
4. **Never log/print/commit secrets.** A Census API key was pasted into a chat transcript via `!
   export` during this build (see "Census API key" below) — it never touched any file, and it
   shouldn't in future sessions either. Use env vars indirectly, never inline in code or output.
5. **Nothing has been committed to git yet.** `DEMO OUTPUTS/` is entirely untracked as of this
   handoff. Don't assume anything has been pushed anywhere.

## Where the requirements/design record lives

The original plan (written in plan mode, approved by the user) is the authoritative design
record. It may or may not be present in the new environment — treat the summary below as
equivalent if the original file isn't available:

- 4 scripts, each a Civis Template candidate: `pull_acs_benchmarks`, `draw_sample`,
  `simulate_responses`, `weight_and_report`.
- Pure-function package (`survey_demo/`) with no `civis.io` calls inside; thin scripts wire
  `civis.io` reads/writes around those pure functions. This was an explicit design choice per the
  civis-platform skill's guidance not to wrap `civis.io` in pass-through helpers.
- Weighting: raking-to-marginals via `ipfn`, not a from-scratch calibration implementation —
  deliberately minimal, not a showcase (the pitch is infrastructure, not survey-methodology depth).
- Explicit ACS↔voterfile category crosswalk (`config/crosswalks.yaml`), validated for full
  coverage before any sampling/weighting runs (`survey_demo.strata.validate_crosswalk_coverage`).
  This was flagged as the most likely silent-failure point in a demo like this.
- Reserved Civis parameter names avoided (`SURVEY_DB`, not `DATABASE`).
- Synthetic voterfile generator lives in `dev/`, clearly labeled fabricated data, not one of the
  4 numbered pipeline steps.

## The voterfile schema this targets

The user provided a real data dictionary for Civis's own TargetSmart-style voterfile/consumer-file
product: `DEMO OUTPUTS/Client Modeling and Basic Data Dictionaries (2).xlsx` (only field-level
metadata was read — column names, types, descriptions — never row data). Key fields used
throughout this pipeline: `voterbase_id`, `age_bucket_noncommercial` (`18-34`/`35-49`/`50-64`/`65+`),
`gender_noncommercial` (`Male`/`Female`), `race5way_noncommercial`
(`White`/`AfAm`/`Hispanic`/`Asian`/`Native`), `vf_reg_party`, `urbanicity`, `vote_g*`/`vote_p*`
history, and modeled scores `likely_dem`/`likely_rep`/`ts_presidential_general_turnout`. The xlsx
is a `.xlsx` binary — reading it directly fails; it was parsed via `zipfile` + the raw
`sharedStrings.xml`/`sheetN.xml` (stdlib only, no `openpyxl`/`pandas` install needed for that step).

## Current build status (as of this handoff)

Fully built and passing:
- `survey_demo/{acs,strata,sampling,responses,weighting,reporting}.py` — pure functions, 35
  passing pytest tests (`tests/`), all offline (no live network, no Platform access).
- `config/{strata,crosswalks,acs_variables,state_fips}.yaml` — crosswalk coverage validated
  against real Census variable metadata (spot-checked B01001/B03002 codes against
  `api.census.gov/data/2021/acs/acs5/variables/<code>.json` labels — all matched).
- `scripts/01-04` — thin `civis.io`-wired entry points.
- `dev/generate_synthetic_voterfile.py`, `dev/verify_acs_pull.py`.
- `workflows/survey_pipeline.yaml` — has `REPLACE_WITH_..._TEMPLATE_ID` placeholders, not yet
  filled in (no templates published yet).
- `Dockerfile`, `README.md`, `DEPLOYMENT.md`, `pyproject.toml`, `requirements.txt`.

**Not yet done / not yet verified:**
- Nothing has actually run on Civis Platform. The `civis.io` read/write round trip and the
  Workflow execution are unverified — `README.md` says this explicitly, don't let a future session
  claim otherwise without actually running it.
- Templates not published; workflow YAML placeholders not filled in.
- The live Census API pull was validated function-by-function with a real key run manually by the
  user via `dev/verify_acs_pull.py` (see below) — confirm whether that run actually happened and
  succeeded before assuming it did.
- Two things are documented as **assumptions**, not verified: the exact env var names Civis
  exposes for a Database-type template parameter (assumed `SURVEY_DB_ID` /
  `SURVEY_DB_CREDENTIAL_ID`), and whether container scripts in this org have network egress to
  `api.census.gov` by default. Both are called out in `DEPLOYMENT.md`.

## Bugs already found and fixed (don't reintroduce these)

1. **`ipfn.ipfn(...).iteration()` mutates its input array in place** and returns that same object.
   `survey_demo/weighting.py` passes `seed.copy()` in, not `seed` — if that copy is ever removed,
   `fitted` and `seed` alias and every raking weight silently comes out as 1 (no crash, just wrong
   numbers). This was caught by a test that checked *actual* target-vs-weighted convergence, not
   just "did it run."
2. **`civis.io.dataframe_to_civis`/`read_civis_sql` take `credential_id`, not `credential`.** The
   `{database, credential}` dict shape from the civis-platform skill's *workflow YAML* examples is
   not the same as the Python client's kwarg names. Because both functions accept `**kwargs`,
   passing the wrong key doesn't raise — it silently falls into the kwargs sink and the call
   would've run under a default/wrong credential. Verified against the installed `civis==2.9.1`
   package's actual `inspect.signature()`, not assumed.

Lesson for future work in this repo: when using any Civis Python client kwarg, check
`inspect.signature()` against the installed package rather than relying on skill/doc examples
written for YAML or the UI — the shapes aren't always the same.

## Census API key

The public Census API now rejects all unauthenticated requests, including minimal ones (this
wasn't previously the case). `CENSUS_API_KEY` is a required env var for
`scripts/01_pull_acs_benchmarks.py` and for `dev/verify_acs_pull.py`. The user has a real key,
exported once via `! export CENSUS_API_KEY=...` in a prior session's shell — that shell state does
not persist across sessions or across this tool's separate Bash invocations. If live verification
is needed again, ask the user to re-export it in their own shell and run
`dev/verify_acs_pull.py --state <XX>` themselves; never ask them to paste the key value into chat,
and never write it to a file yourself.

## How to resume local development

```bash
cd "DEMO OUTPUTS"
python3 -m venv .venv   # a homebrew python3.14 was used previously; system python3 lacked pip
source .venv/bin/activate
pip install -e . -r dev-requirements.txt
pytest tests/ -q        # should show 35 passed
```

## Likely next steps

Pick up roughly where this session left off:
1. If not already done: run `dev/verify_acs_pull.py` with a real key to confirm the live ACS path
   (user-run, per the key-handling note above).
2. Commit and push `DEMO OUTPUTS/` (nothing is committed yet — confirm with the user first, per
   this org's git safety norms: only commit when explicitly asked).
3. Follow `DEPLOYMENT.md` step by step to actually deploy: load the synthetic voterfile onto
   Platform, create the 4 container scripts, verify the two assumed-but-unverified items
   (DB param env var names, network egress), run each script once, publish as templates, fill in
   the workflow YAML placeholders, run the workflow, verify via the diagnostics table.
4. Consider whether the hand-authored illustrative test fixtures
   (`tests/fixtures/*_response.json`) should be swapped for real Census API responses now that a
   live pull has been validated — optional, not required; the current fixtures are sufficient for
   offline test coverage since they were generated from the real variable list in
   `config/acs_variables.yaml`.
