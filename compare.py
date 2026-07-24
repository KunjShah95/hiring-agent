"""
Multi-Candidate Compare Tool
Compares multiple resumes side-by-side using the same pipeline as score.py.
"""

import os
import sys
import csv
import io
import logging

from score import process_pipeline

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)5s - %(lineno)5d - %(funcName)33s - %(levelname)5s - %(message)s",
)


def process_candidate(pdf_path: str) -> dict:
    """
    Run the complete pipeline for a single candidate with error handling.

    Args:
        pdf_path: Path to the PDF resume file

    Returns:
        dict with all pipeline results, or error dict on failure
    """
    try:
        if not os.path.exists(pdf_path):
            return {
                "file": os.path.basename(pdf_path),
                "error": f"File not found: {pdf_path}",
            }

        result = process_pipeline(pdf_path)
        if result is None:
            return {
                "file": os.path.basename(pdf_path),
                "error": "Failed to extract resume data from PDF",
            }

        return result
    except Exception as e:
        logger.error(f"Error processing {pdf_path}: {e}", exc_info=True)
        return {"file": os.path.basename(pdf_path), "error": str(e)}


def _get_category_score(result: dict, category: str):
    """Get (capped_score, max_score) for a category, or (0, 0)."""
    score = result.get("score")
    if score and hasattr(score, "scores") and score.scores:
        cat = getattr(score.scores, category, None)
        if cat:
            return (min(cat.score, cat.max), cat.max)
    return (0, 0)


def _get_bonus(result: dict) -> float:
    score = result.get("score")
    if score and hasattr(score, "bonus_points") and score.bonus_points:
        return score.bonus_points.total
    return 0


def _get_evidence(result: dict, category: str) -> str:
    score = result.get("score")
    if score and hasattr(score, "scores") and score.scores:
        cat = getattr(score.scores, category, None)
        if cat and hasattr(cat, "evidence"):
            return cat.evidence
    return ""


def _get_strengths(result: dict) -> list:
    score = result.get("score")
    if score and hasattr(score, "key_strengths") and score.key_strengths:
        return score.key_strengths
    return []


def _get_improvements(result: dict) -> list:
    score = result.get("score")
    if score and hasattr(score, "areas_for_improvement") and score.areas_for_improvement:
        return score.areas_for_improvement
    return []


def _get_deductions(result: dict) -> float:
    score = result.get("score")
    if score and hasattr(score, "deductions") and score.deductions:
        return score.deductions.total
    return 0


def generate_comparison_table(results: list[dict]) -> str:
    """
    Generate an ASCII formatted comparison table.

    Columns: Rank, Name, Overall Score, Open Source, Self Projects,
             Production, Technical Skills, Bonus
    """
    valid = [r for r in results if "error" not in r]
    valid.sort(key=lambda r: r.get("overall_score", 0), reverse=True)

    lines = []
    lines.append("=" * 130)
    lines.append(f"{'MULTI-CANDIDATE COMPARISON':^130}")
    lines.append("=" * 130)
    lines.append("")

    if not valid:
        lines.append("No candidates processed successfully.")
        if any("error" in r for r in results):
            lines.append("")
            lines.append("FAILED:")
            for r in results:
                if "error" in r:
                    lines.append(f"  - {r['file']}: {r['error']}")
        return "\n".join(lines)

    header = (
        f"{'Rank':<6} {'Name':<22} {'Overall':<12} "
        f"{'Open Source':<18} {'Self Projects':<18} "
        f"{'Production':<16} {'Technical':<14} {'Bonus':<8}"
    )
    lines.append(header)
    lines.append("-" * len(header))

    for i, r in enumerate(valid, 1):
        name = r.get("name", "Unknown")[:20]
        os_s, os_m = _get_category_score(r, "open_source")
        sp_s, sp_m = _get_category_score(r, "self_projects")
        prod_s, prod_m = _get_category_score(r, "production")
        tech_s, tech_m = _get_category_score(r, "technical_skills")
        overall = r.get("overall_score", 0)
        max_total = r.get("max_score", 100)
        bonus = _get_bonus(r)

        lines.append(
            f"{i:<6} {name:<22} {overall:<4}/{max_total:<6} "
            f"{os_s:<3}/{os_m:<12} {sp_s:<3}/{sp_m:<12} "
            f"{prod_s:<3}/{prod_m:<10} {tech_s:<3}/{tech_m:<8} "
            f"+{bonus:<6.0f}"
        )

    errors = [r for r in results if "error" in r]
    if errors:
        lines.append("")
        lines.append("-" * 130)
        lines.append("FAILED CANDIDATES:")
        for r in errors:
            lines.append(f"  - {r['file']}: {r['error']}")

    return "\n".join(lines)


def generate_comparison_html(results: list[dict]) -> str:
    """
    Generate a side-by-side HTML comparison with color coding.

    Features:
    - Leaderboard at top
    - Per-category breakdown with score bars
    - Strengths/weaknesses per candidate
    """
    valid = [r for r in results if "error" not in r]
    valid.sort(key=lambda r: r.get("overall_score", 0), reverse=True)

    # Leaderboard table
    lb_rows = ""
    for i, r in enumerate(valid, 1):
        name = r.get("name", "Unknown")
        overall = r.get("overall_score", 0)
        max_total = r.get("max_score", 100)
        pct = round(overall / max_total * 100) if max_total else 0
        color = "#43e97b" if pct >= 70 else "#fa709a" if pct >= 50 else "#f5576c"
        lb_rows += f"""
            <tr>
                <td>#{i}</td>
                <td>{name}</td>
                <td style="font-weight:700;color:{color}">{overall:.0f}/{max_total}</td>
                <td>{pct}%</td>
            </tr>"""

    # Per-category breakdown
    categories = [
        ("open_source", "Open Source", 35),
        ("self_projects", "Self Projects", 30),
        ("production", "Production", 25),
        ("technical_skills", "Technical Skills", 10),
    ]

    cat_rows = ""
    for cat_key, cat_label, cat_max in categories:
        cells = f'<td><strong>{cat_label}</strong><br><span class="weak">max {cat_max}</span></td>'
        for r in valid:
            s, m = _get_category_score(r, cat_key)
            pct = round(s / m * 100) if m else 0
            evidence = _get_evidence(r, cat_key)
            ev_short = (evidence[:80] + "...") if len(evidence) > 80 else evidence
            cells += f"""
                <td>
                    <div class="score-row">
                        <div class="score-bar-wrap">
                            <div class="score-bar {cat_key}" style="width:{pct}%"></div>
                        </div>
                        <div class="score-value">{s}/{m}</div>
                    </div>
                    <div class="evidence">{ev_short}</div>
                </td>"""
        cat_rows += f"<tr>{cells}</tr>\n"

    # Strengths / Improvements grid
    sw_cards = ""
    for r in valid:
        name = r.get("name", "Unknown")
        strengths = _get_strengths(r)
        improvements = _get_improvements(r)
        bonus = _get_bonus(r)
        deductions = _get_deductions(r)
        sw_cards += f"""
            <div class="card">
                <div class="card-body">
                    <h3>{name}</h3>
                    {f'<p class="bonus">Bonus: +{bonus:.0f}</p>' if bonus else ''}
                    {f'<p class="deduction">Deductions: -{deductions:.0f}</p>' if deductions else ''}
                    <div class="section">
                        <h2>Strengths</h2>
                        <ul class="strengths">
                            {''.join(f'<li>{s}</li>' for s in strengths)}
                        </ul>
                    </div>
                    <div class="section">
                        <h2>Improvements</h2>
                        <ul class="improvements">
                            {''.join(f'<li>{a}</li>' for a in improvements)}
                        </ul>
                    </div>
                </div>
            </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Multi-Candidate Comparison</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; padding: 40px; }}
  .container {{ max-width: 1200px; margin: 0 auto; }}
  .header {{ text-align: center; padding: 30px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; border-radius: 12px 12px 0 0; }}
  .header h1 {{ font-size: 28px; }}
  .card {{ background: white; border-radius: 12px; margin: 20px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow: hidden; }}
  .card-body {{ padding: 24px; }}
  .section {{ margin-bottom: 24px; }}
  .section h2 {{ font-size: 18px; margin-bottom: 12px; color: #555; border-bottom: 2px solid #eee; padding-bottom: 8px; }}
  h3 {{ font-size: 20px; margin-bottom: 12px; color: #333; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #eee; vertical-align: top; }}
  th {{ background: #f8f9fa; font-weight: 600; color: #555; }}
  .score-row {{ display: flex; align-items: center; margin: 4px 0; }}
  .score-bar-wrap {{ flex: 1; height: 20px; background: #eee; border-radius: 10px; overflow: hidden; position: relative; }}
  .score-bar {{ height: 100%; border-radius: 10px; transition: width 0.6s ease; }}
  .score-bar.open_source {{ background: linear-gradient(90deg, #f093fb, #f5576c); }}
  .score-bar.self_projects {{ background: linear-gradient(90deg, #4facfe, #00f2fe); }}
  .score-bar.production {{ background: linear-gradient(90deg, #43e97b, #38f9d7); }}
  .score-bar.technical_skills {{ background: linear-gradient(90deg, #fa709a, #fee140); }}
  .score-value {{ width: 60px; text-align: right; font-weight: 600; margin-left: 8px; font-size: 14px; }}
  .evidence {{ color: #666; font-size: 12px; margin: 2px 0 6px; }}
  .bonus {{ color: #2e7d32; font-weight: 500; }}
  .deduction {{ color: #c62828; font-weight: 500; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ padding: 8px 12px; margin: 4px 0; border-radius: 6px; }}
  .strengths li {{ background: #e8f5e9; color: #2e7d32; }}
  .improvements li {{ background: #fff3e0; color: #e65100; }}
  .weak {{ color: #999; font-size: 12px; }}
  .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; padding-bottom: 30px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>Multi-Candidate Comparison</h1>
    <p>{len(valid)} candidate(s) evaluated</p>
  </div>

  <div class="card">
    <div class="card-body">
      <h2>Leaderboard</h2>
      <table>
        <thead>
          <tr><th>Rank</th><th>Name</th><th>Score</th><th>%</th></tr>
        </thead>
        <tbody>
          {lb_rows}
        </tbody>
      </table>
    </div>
  </div>

  <div class="card">
    <div class="card-body">
      <h2>Per-Category Breakdown</h2>
      <table>
        <thead>
          <tr>
            <th>Category</th>
            {''.join(f'<th>{r["name"]}</th>' for r in valid)}
          </tr>
        </thead>
        <tbody>
          {cat_rows}
        </tbody>
      </table>
    </div>
  </div>

  <h2>Strengths & Areas for Improvement</h2>
  <div class="grid">
    {sw_cards}
  </div>

  <div class="footer">Generated by Hiring Agent &middot; Comparison Report</div>
</div>
</body>
</html>"""
    return html


def write_comparison_csv(results: list[dict], filepath: str = "comparison_results.csv"):
    """Write comparison results to CSV sorted by overall score descending."""
    valid = [r for r in results if "error" not in r]
    valid.sort(key=lambda r: r.get("overall_score", 0), reverse=True)

    fieldnames = [
        "rank",
        "name",
        "overall_score",
        "max_score",
        "open_source_score",
        "open_source_max",
        "self_projects_score",
        "self_projects_max",
        "production_score",
        "production_max",
        "technical_skills_score",
        "technical_skills_max",
        "bonus_points",
        "deductions",
        "key_strengths",
        "areas_for_improvement",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, r in enumerate(valid, 1):
            os_s, os_m = _get_category_score(r, "open_source")
            sp_s, sp_m = _get_category_score(r, "self_projects")
            prod_s, prod_m = _get_category_score(r, "production")
            tech_s, tech_m = _get_category_score(r, "technical_skills")

            writer.writerow(
                {
                    "rank": i,
                    "name": r.get("name", "Unknown"),
                    "overall_score": r.get("overall_score", 0),
                    "max_score": r.get("max_score", 100),
                    "open_source_score": os_s,
                    "open_source_max": os_m,
                    "self_projects_score": sp_s,
                    "self_projects_max": sp_m,
                    "production_score": prod_s,
                    "production_max": prod_m,
                    "technical_skills_score": tech_s,
                    "technical_skills_max": tech_m,
                    "bonus_points": _get_bonus(r),
                    "deductions": _get_deductions(r),
                    "key_strengths": "; ".join(_get_strengths(r)),
                    "areas_for_improvement": "; ".join(_get_improvements(r)),
                }
            )

    print(f"📊 CSV saved to {filepath}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Multi-Candidate Resume Comparison"
    )
    parser.add_argument("pdfs", nargs="+", help="PDF resume files to compare")
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML comparison report",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Save CSV comparison file (always enabled, flag for explicit use)",
    )
    args = parser.parse_args()

    results = []
    for pdf_path in args.pdfs:
        print(f"\n{'=' * 60}")
        print(f"Processing: {pdf_path}")
        print(f"{'=' * 60}")
        result = process_candidate(pdf_path)
        results.append(result)
        if "error" in result:
            print(f"❌ {result['error']}")
        else:
            name = result.get("name", "Unknown")
            score = result.get("overall_score", 0)
            max_s = result.get("max_score", 100)
            print(f"✅ {name}: {score:.0f}/{max_s}")

    print("\n")
    table = generate_comparison_table(results)
    print(table)

    write_comparison_csv(results)

    if args.html:
        html = generate_comparison_html(results)
        html_path = "comparison_report.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"📄 HTML comparison report saved to {html_path}")


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    main()
