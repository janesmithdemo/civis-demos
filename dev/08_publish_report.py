#!/usr/bin/env python
"""Publish a Civis HTML report summarising the survey pipeline outputs.

Reads topline_report, crosstabs, and weighting_diagnostics tables and
publishes a self-contained HTML report to Civis Platform.

Usage:
    python dev/08_publish_report.py \\
        --survey-id demo_oh_2026 \\
        --output-schema surveys \\
        [--database-id 326] \\
        [--name "Ohio Survey 2026"]
"""
import argparse

import civis

logger = civis.civis_logger(__name__)

PARTY_COLORS = {
    "Democrat": "#2166ac",
    "Republican": "#d6604d",
    "Undecided": "#878787",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--survey-id", required=True)
    parser.add_argument("--output-schema", required=True)
    parser.add_argument("--database-id", type=int, default=326)
    parser.add_argument("--name", default=None)
    args = parser.parse_args()

    db = args.database_id
    s, sid = args.output_schema, args.survey_id

    topline = civis.io.read_civis_sql(
        f"SELECT metric, category, value::float FROM {s}.{sid}_topline_report",
        database=db, return_as="pandas",
    )
    crosstabs = civis.io.read_civis_sql(
        f"SELECT variable, category, vote_choice, weighted_share::float FROM {s}.{sid}_crosstabs ORDER BY variable, category, vote_choice",
        database=db, return_as="pandas",
    )
    diag = civis.io.read_civis_sql(
        f"SELECT variable, category, target_share::float, weighted_share::float FROM {s}.{sid}_weighting_diagnostics ORDER BY variable, category",
        database=db, return_as="pandas",
    )

    html = _build_html(args.name or sid, topline, crosstabs, diag)

    client = civis.APIClient()
    report = client.reports.post(
        name=args.name or sid,
        code_body=html,
        hidden=False,
    )
    logger.info(f"Report published: id={report.id} — https://platform.civisanalytics.com/spa/#/reports/{report.id}")


# ── HTML generation ──────────────────────────────────────────────────────────

def _build_html(title, topline, crosstabs, diag):
    vote = topline[topline.metric == "vote_choice_share"].set_index("category")["value"]
    approval = topline[topline.metric == "approval_rating_mean"]["value"].iloc[0]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          margin: 0; background: #f5f6fa; color: #2d3748; }}
  .page {{ max-width: 900px; margin: 0 auto; padding: 32px 24px; }}
  h1 {{ font-size: 1.6rem; font-weight: 700; margin: 0 0 4px; color: #1a202c; }}
  .subtitle {{ color: #718096; font-size: 0.9rem; margin: 0 0 32px; }}
  h2 {{ font-size: 1.05rem; font-weight: 600; color: #2d3748;
        border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin: 32px 0 16px; }}
  .card {{ background: #fff; border-radius: 8px; padding: 24px;
           box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 24px; }}
  /* vote bars */
  .vote-grid {{ display: grid; gap: 10px; }}
  .vote-row {{ display: flex; align-items: center; gap: 12px; }}
  .vote-label {{ width: 100px; font-size: 0.88rem; font-weight: 500; flex-shrink: 0; }}
  .bar-track {{ flex: 1; background: #edf2f7; border-radius: 4px; height: 28px; overflow: hidden; }}
  .bar-fill  {{ height: 100%; border-radius: 4px; transition: width .4s; }}
  .vote-pct  {{ width: 46px; text-align: right; font-size: 0.9rem; font-weight: 600; flex-shrink: 0; }}
  /* approval */
  .approval-block {{ display: flex; align-items: baseline; gap: 10px; }}
  .approval-num {{ font-size: 2.8rem; font-weight: 700; color: #2166ac; }}
  .approval-denom {{ font-size: 1.1rem; color: #718096; }}
  /* crosstabs */
  .xtab-section {{ margin-bottom: 20px; }}
  .xtab-label {{ font-size: 0.82rem; font-weight: 600; color: #718096;
                 text-transform: uppercase; letter-spacing: .05em; margin-bottom: 8px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
  thead th {{ background: #edf2f7; padding: 8px 12px; text-align: left;
              font-weight: 600; color: #4a5568; }}
  tbody td {{ padding: 7px 12px; border-bottom: 1px solid #f0f0f0; }}
  tbody tr:last-child td {{ border-bottom: none; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .diff {{ text-align: right; font-size: 0.82rem; }}
  .diff.ok {{ color: #38a169; }}
  .diff.warn {{ color: #e53e3e; }}
</style>
</head>
<body>
<div class="page">
  <h1>{title}</h1>
  <p class="subtitle">Weighted survey results &nbsp;·&nbsp; n={_n_label(diag)}</p>

  <h2>Vote Choice</h2>
  <div class="card">
    <div class="vote-grid">
{_vote_bars(vote)}
    </div>
  </div>

  <h2>Approval Rating</h2>
  <div class="card">
    <div class="approval-block">
      <span class="approval-num">{approval:.2f}</span>
      <span class="approval-denom">/ 5</span>
    </div>
  </div>

  <h2>Vote Choice by Subgroup</h2>
  <div class="card">
{_crosstabs_section(crosstabs)}
  </div>

  <h2>Weighting Diagnostics</h2>
  <div class="card">
{_diag_table(diag)}
  </div>
</div>
</body>
</html>"""


def _n_label(diag):
    return "~1,000"


def _vote_bars(vote):
    lines = []
    for party in ["Democrat", "Republican", "Undecided"]:
        pct = vote.get(party, 0.0)
        color = PARTY_COLORS.get(party, "#999")
        lines.append(f"""\
      <div class="vote-row">
        <span class="vote-label">{party}</span>
        <div class="bar-track">
          <div class="bar-fill" style="width:{pct*100:.1f}%;background:{color}"></div>
        </div>
        <span class="vote-pct" style="color:{color}">{pct*100:.1f}%</span>
      </div>""")
    return "\n".join(lines)


def _crosstabs_section(crosstabs):
    sections = []
    for variable, grp in crosstabs.groupby("variable", sort=False):
        label = variable.replace("_noncommercial", "").replace("_", " ").title()
        pivot = grp.pivot(index="category", columns="vote_choice", values="weighted_share").fillna(0)
        pivot = pivot[sorted(pivot.columns, key=lambda c: ["Democrat","Republican","Undecided"].index(c) if c in ["Democrat","Republican","Undecided"] else 99)]

        header_cells = "".join(f"<th>{c}</th>" for c in pivot.columns)
        rows = ""
        for cat, row in pivot.iterrows():
            cells = "".join(f'<td class="num">{v*100:.1f}%</td>' for v in row)
            rows += f"<tr><td>{cat}</td>{cells}</tr>\n"

        sections.append(f"""\
    <div class="xtab-section">
      <div class="xtab-label">{label}</div>
      <table>
        <thead><tr><th>Group</th>{header_cells}</tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>""")
    return "\n".join(sections)


def _diag_table(diag):
    rows = ""
    for _, r in diag.iterrows():
        diff = r.weighted_share - r.target_share
        cls = "warn" if abs(diff) > 0.02 else "ok"
        rows += (
            f"<tr>"
            f"<td>{r.variable.replace('_noncommercial','').replace('_',' ').title()}</td>"
            f"<td>{r.category}</td>"
            f'<td class="num">{r.target_share*100:.2f}%</td>'
            f'<td class="num">{r.weighted_share*100:.2f}%</td>'
            f'<td class="diff {cls}">{diff*100:+.2f}pp</td>'
            f"</tr>\n"
        )
    return f"""\
    <table>
      <thead>
        <tr><th>Variable</th><th>Category</th><th>Target</th><th>Weighted</th><th>Δ</th></tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""


if __name__ == "__main__":
    main()
