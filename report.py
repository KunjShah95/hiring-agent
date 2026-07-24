import logging
from typing import Dict, List, Optional
from models import EvaluationData, JSONResume

logger = logging.getLogger(__name__)


def generate_html_report(
    candidate_name: str,
    resume_data: Optional[JSONResume],
    evaluation: EvaluationData,
    github_data: Optional[Dict] = None,
    portfolio_data: Optional[Dict] = None,
    live_demo_status: Optional[List[dict]] = None,
    improvements: Optional[Dict[str, list]] = None,
    jd_match_result: Optional[dict] = None,
) -> str:
    scores = evaluation.scores
    total = sum(
        min(s.score, s.max) for s in [
            scores.open_source, scores.self_projects,
            scores.production, scores.technical_skills
        ]
    )
    max_score = sum(
        s.max for s in [
            scores.open_source, scores.self_projects,
            scores.production, scores.technical_skills
        ]
    )
    if evaluation.bonus_points:
        total += evaluation.bonus_points.total
    if evaluation.deductions:
        total -= evaluation.deductions.total
    max_possible = max_score + 20
    total = min(total, max_possible)
    pct = round(total / max_score * 100) if max_score else 0

    score_bars = _render_score_bars(scores, max_score)
    strengths = "".join(
        f'<li class="strength-item"><span class="check">&#10003;</span> {s}</li>'
        for s in (evaluation.key_strengths or [])
    )
    improvements_list = "".join(
        f'<li class="improvement-item"><span class="arrow">&#8594;</span> {a}</li>'
        for a in (evaluation.areas_for_improvement or [])
    )
    bonus_text = evaluation.bonus_points.breakdown if evaluation.bonus_points else ""
    deduction_text = (
        evaluation.deductions.reasons
        if evaluation.deductions and evaluation.deductions.total > 0
        else ""
    )
    deduction_total = evaluation.deductions.total if evaluation.deductions else 0

    gauge = _render_gauge(pct)
    sections = ""

    sections += _render_github_contributions(github_data)
    sections += _render_portfolio(portfolio_data)
    sections += _render_live_demos(live_demo_status)
    sections += _render_jd_match(jd_match_result)
    sections += _render_improvement_details(improvements)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Resume Dashboard - {candidate_name}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif; background: #0f0f1a; color: #e0e0e0; padding: 30px; }}
  .container {{ max-width: 1000px; margin: 0 auto; }}
  .header {{ text-align: center; padding: 40px 30px; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); border-radius: 16px; margin-bottom: 24px; position: relative; overflow: hidden; }}
  .header::before {{ content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: radial-gradient(circle, rgba(102,126,234,0.08) 0%, transparent 60%); }}
  .header h1 {{ font-size: 28px; font-weight: 300; position: relative; letter-spacing: 1px; }}
  .header .name {{ font-size: 36px; font-weight: 700; margin: 8px 0; position: relative; background: linear-gradient(90deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
  .header .sub {{ opacity: 0.6; font-size: 14px; position: relative; }}
  .score-ring {{ position: relative; display: inline-block; margin: 20px auto; }}
  .score-ring svg {{ transform: rotate(-90deg); }}
  .score-ring .score-text {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; }}
  .score-ring .score-text .big {{ font-size: 40px; font-weight: 700; }}
  .score-ring .score-text .small {{ font-size: 16px; opacity: 0.6; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
  .grid-full {{ grid-column: 1 / -1; }}
  .card {{ background: #1a1a2e; border-radius: 12px; overflow: hidden; border: 1px solid #2a2a4a; }}
  .card-header {{ padding: 16px 24px; background: #222240; border-bottom: 1px solid #2a2a4a; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: #8b8bb0; }}
  .card-body {{ padding: 20px 24px; }}
  .score-row {{ display: flex; align-items: center; margin: 10px 0; }}
  .score-label {{ width: 160px; font-size: 14px; font-weight: 500; color: #c0c0d0; }}
  .score-bar-wrap {{ flex: 1; height: 22px; background: #2a2a4a; border-radius: 11px; overflow: hidden; }}
  .score-bar {{ height: 100%; border-radius: 11px; transition: width 1s ease; }}
  .score-bar.open_source {{ background: linear-gradient(90deg, #f093fb, #f5576c); }}
  .score-bar.self_projects {{ background: linear-gradient(90deg, #4facfe, #00f2fe); }}
  .score-bar.production {{ background: linear-gradient(90deg, #43e97b, #38f9d7); }}
  .score-bar.technical_skills {{ background: linear-gradient(90deg, #fa709a, #fee140); }}
  .score-value {{ width: 70px; text-align: right; font-size: 14px; font-weight: 600; margin-left: 12px; color: #c0c0d0; }}
  .evidence {{ color: #8b8bb0; font-size: 13px; margin: 2px 0 10px 20px; padding-left: 12px; border-left: 2px solid #2a2a4a; line-height: 1.5; }}
  .strength-item {{ padding: 8px 12px; margin: 4px 0; border-radius: 8px; background: rgba(46, 125, 50, 0.15); color: #81c784; font-size: 14px; }}
  .strength-item .check {{ color: #4caf50; margin-right: 8px; }}
  .improvement-item {{ padding: 8px 12px; margin: 4px 0; border-radius: 8px; background: rgba(255, 152, 0, 0.12); color: #ffb74d; font-size: 14px; }}
  .improvement-item .arrow {{ margin-right: 8px; }}
  .bonus {{ color: #81c784; font-weight: 500; }}
  .deduction {{ color: #e57373; font-weight: 500; }}
  .section {{ margin-bottom: 20px; }}
  .section h2 {{ font-size: 14px; margin-bottom: 10px; color: #8b8bb0; text-transform: uppercase; letter-spacing: 1px; border-bottom: 1px solid #2a2a4a; padding-bottom: 8px; }}
  .stat-row {{ display: flex; justify-content: space-between; padding: 6px 0; font-size: 14px; border-bottom: 1px solid #1a1a2e; }}
  .stat-row .label {{ color: #8b8bb0; }}
  .stat-row .value {{ color: #e0e0e0; font-weight: 500; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
  .badge-ok {{ background: rgba(76, 175, 80, 0.2); color: #81c784; }}
  .badge-broken {{ background: rgba(244, 67, 54, 0.2); color: #e57373; }}
  .badge-timeout {{ background: rgba(255, 152, 0, 0.2); color: #ffb74d; }}
  .jd-score {{ font-size: 36px; font-weight: 700; text-align: center; }}
  .jd-score.high {{ color: #81c784; }}
  .jd-score.medium {{ color: #ffb74d; }}
  .jd-score.low {{ color: #e57373; }}
  .gap-item {{ padding: 6px 0; font-size: 13px; border-bottom: 1px solid #1a1a2e; }}
  .gap-item .sev-high {{ color: #e57373; }}
  .gap-item .sev-medium {{ color: #ffb74d; }}
  .gap-item .sev-low {{ color: #8b8bb0; }}
  .improvement-card {{ background: #222240; border-radius: 8px; padding: 12px; margin: 6px 0; }}
  .improvement-card .cat {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #8b8bb0; }}
  .improvement-card .suggestion {{ font-size: 13px; margin: 4px 0; color: #e0e0e0; }}
  .improvement-card .meta {{ font-size: 11px; color: #8b8bb0; }}
  .improvement-card .meta .tag-impact {{ color: #81c784; }}
  .improvement-card .meta .tag-effort {{ color: #ffb74d; }}
  .improvement-card .meta .tag-priority {{ color: #e57373; }}
  .footer {{ text-align: center; color: #4a4a6a; font-size: 12px; margin-top: 30px; }}
  @@media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>RESUME EVALUATION</h1>
    <div class="name">{candidate_name}</div>
    <div class="score-ring">
      {gauge}
      <div class="score-text">
        <div class="big">{total:.0f}</div>
        <div class="small">/ {max_score}</div>
      </div>
    </div>
    <div class="sub">{pct}% Overall Score</div>
  </div>

  <div class="grid">
    <div class="card grid-full">
      <div class="card-header">Score Breakdown</div>
      <div class="card-body">{score_bars}</div>
    </div>

    <div class="card">
      <div class="card-header">Key Strengths</div>
      <div class="card-body">
        <ul style="list-style:none;padding:0;">{strengths}</ul>
      </div>
    </div>

    <div class="card">
      <div class="card-header">Areas for Improvement</div>
      <div class="card-body">
        <ul style="list-style:none;padding:0;">{improvements_list}</ul>
      </div>
    </div>

    <div class="card">
      <div class="card-header">Bonuses &amp; Deductions</div>
      <div class="card-body">
        {f'<div class="section"><h2>Bonus</h2><p class="bonus">+{evaluation.bonus_points.total}</p><p class="evidence">{bonus_text}</p></div>' if evaluation.bonus_points and evaluation.bonus_points.total > 0 else '<p class="evidence">No bonus points</p>'}
        {f'<div class="section"><h2>Deductions</h2><p class="deduction">-{deduction_total}</p><p class="evidence">{deduction_text}</p></div>' if deduction_total > 0 else '<p class="evidence">No deductions</p>'}
      </div>
    </div>

    <div class="card">
      <div class="card-header">Quick Stats</div>
      <div class="card-body">
        {_render_quick_stats(resume_data, github_data)}
      </div>
    </div>
  </div>

  {sections}

  <div class="footer">Generated by Hiring Agent &middot; {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
</div>
</body>
</html>"""
    return html


def _render_gauge(pct: int) -> str:
    r = 70
    circumference = 2 * 3.14159 * r
    offset = circumference - (pct / 100) * circumference
    color = "#4caf50" if pct >= 70 else "#ff9800" if pct >= 40 else "#f44336"
    return f"""<svg width="180" height="180" viewBox="0 0 180 180">
  <circle cx="90" cy="90" r="{r}" fill="none" stroke="#2a2a4a" stroke-width="10"/>
  <circle cx="90" cy="90" r="{r}" fill="none" stroke="{color}" stroke-width="10"
    stroke-dasharray="{circumference}" stroke-dashoffset="{offset}"
    stroke-linecap="round" style="transition: stroke-dashoffset 1.5s ease;"/>
</svg>"""


def _render_score_bars(scores, max_score: int) -> str:
    categories = [
        ("open_source", "Open Source", scores.open_source.score, scores.open_source.max,
         scores.open_source.evidence),
        ("self_projects", "Self Projects", scores.self_projects.score, scores.self_projects.max,
         scores.self_projects.evidence),
        ("production", "Production", scores.production.score, scores.production.max,
         scores.production.evidence),
        ("technical_skills", "Technical Skills", scores.technical_skills.score, scores.technical_skills.max,
         scores.technical_skills.evidence),
    ]
    parts = []
    for key, label, score, mx, evidence in categories:
        capped = min(score, mx)
        pct = (capped / mx * 100) if mx else 0
        parts.append(f"""<div class="score-row">
          <div class="score-label">{label}</div>
          <div class="score-bar-wrap">
            <div class="score-bar {key}" style="width:{pct}%"></div>
          </div>
          <div class="score-value">{capped}/{mx}</div>
        </div>
        <div class="evidence">{evidence}</div>""")
    return "\n".join(parts)


def _render_quick_stats(resume_data: Optional[JSONResume], github_data: Optional[Dict]) -> str:
    stats = []
    if resume_data:
        work_count = len(resume_data.work) if resume_data.work else 0
        proj_count = len(resume_data.projects) if resume_data.projects else 0
        edu_count = len(resume_data.education) if resume_data.education else 0
        skills_count = sum(
            len(s.keywords) for s in (resume_data.skills or [])
            if s.keywords
        )
        stats.append(("<span>&#128188;</span> Work Exp", str(work_count)))
        stats.append(("<span>&#128640;</span> Projects", str(proj_count)))
        stats.append(("<span>&#127891;</span> Education", str(edu_count)))
        stats.append(("<span>&#128736;</span> Skills", str(skills_count)))
    if github_data:
        k = github_data.get("public_repos", 0)
        stats.append(("<span>&#128193;</span> GitHub Repos", str(k)))
        f = github_data.get("followers", 0)
        stats.append(("<span>&#128101;</span> Followers", str(f)))
    return "\n".join(
        f'<div class="stat-row"><span class="label">{l}</span><span class="value">{v}</span></div>'
        for l, v in stats
    )


def _render_github_contributions(github_data: Optional[Dict]) -> str:
    if not github_data or "contributions" not in github_data:
        return ""
    c = github_data["contributions"]
    orgs = ", ".join(c.get("orgs_contributed", []))
    return f"""<div class="card grid-full">
  <div class="card-header">Open Source Contributions</div>
  <div class="card-body">
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;">
      <div style="text-align:center;padding:12px;background:#222240;border-radius:8px;">
        <div style="font-size:28px;font-weight:700;color:#81c784;">{c.get('external_merged_prs', 0)}</div>
        <div style="font-size:12px;color:#8b8bb0;">Merged PRs (External)</div>
      </div>
      <div style="text-align:center;padding:12px;background:#222240;border-radius:8px;">
        <div style="font-size:28px;font-weight:700;color:#4facfe;">{c.get('total_prs', 0)}</div>
        <div style="font-size:12px;color:#8b8bb0;">Total PRs ({c.get('own_repo_prs', 0)} own, {c.get('external_prs', 0)} ext)</div>
      </div>
      <div style="text-align:center;padding:12px;background:#222240;border-radius:8px;">
        <div style="font-size:28px;font-weight:700;color:#ffb74d;">{c.get('total_issues', 0)}</div>
        <div style="font-size:12px;color:#8b8bb0;">Issues Authored</div>
      </div>
      <div style="text-align:center;padding:12px;background:#222240;border-radius:8px;">
        <div style="font-size:28px;font-weight:700;color:#ce93d8;">{len(c.get('repos_contributed', []))}</div>
        <div style="font-size:12px;color:#8b8bb0;">External Repos</div>
      </div>
    </div>
    {f'<p style="margin-top:12px;font-size:13px;color:#8b8bb0;">Organizations: <strong style="color:#e0e0e0;">{orgs}</strong></p>' if orgs else ''}
  </div>
</div>"""


def _render_portfolio(portfolio_data: Optional[Dict]) -> str:
    if not portfolio_data:
        return ""
    projects = portfolio_data.get("projects", [])
    techs = portfolio_data.get("tech_stack", [])
    links = portfolio_data.get("links", [])
    return f"""<div class="card grid-full">
  <div class="card-header">Portfolio</div>
  <div class="card-body">
    <div class="stat-row"><span class="label">Site</span><span class="value"><a href="{portfolio_data.get('url', '')}" style="color:#4facfe;text-decoration:none;">{portfolio_data.get('title', 'Portfolio')}</a></span></div>
    {f'<div class="stat-row"><span class="label">Description</span><span class="value" style="font-weight:400;">{portfolio_data.get("description", "")}</span></div>' if portfolio_data.get("description") else ''}
    {f'<div class="stat-row"><span class="label">Projects/Sections</span><span class="value" style="font-weight:400;">{", ".join(projects[:12])}</span></div>' if projects else ''}
    {f'<div class="stat-row"><span class="label">Tech Stack</span><span class="value" style="font-weight:400;">{", ".join(techs)}</span></div>' if techs else ''}
    {f'<div class="stat-row"><span class="label">Links Found</span><span class="value">{len(links)}</span></div>' if links else ''}
  </div>
</div>"""


def _render_live_demos(live_demo_status: Optional[List[dict]]) -> str:
    if not live_demo_status:
        return ""
    rows = ""
    for r in live_demo_status:
        badge_class = {
            "ok": "badge-ok", "broken": "badge-broken",
            "timeout": "badge-timeout", "unreachable": "badge-broken",
            "error": "badge-broken",
        }.get(r["status"], "badge-broken")
        label = {
            "ok": "Working", "broken": f"HTTP {r['code']}",
            "timeout": "Timed Out", "unreachable": "Unreachable",
            "error": "Error",
        }.get(r["status"], r["status"])
        rows += f"""<div class="stat-row">
          <span class="label"><a href="{r['url']}" style="color:#8b8bb0;text-decoration:none;" target="_blank">{r['url'][:60]}{'...' if len(r['url']) > 60 else ''}</a></span>
          <span class="badge {badge_class}">{label}</span>
        </div>"""
    working = sum(1 for r in live_demo_status if r["status"] == "ok")
    return f"""<div class="card grid-full">
  <div class="card-header">Live Demo Status ({working}/{len(live_demo_status)} working)</div>
  <div class="card-body">{rows}</div>
</div>"""


def _render_jd_match(jd_match_result: Optional[dict]) -> str:
    if not jd_match_result:
        return ""
    ms = jd_match_result.get("jd_match_score", 0)
    cls = "high" if ms >= 70 else "medium" if ms >= 40 else "low"
    gap_items = ""
    for g in jd_match_result.get("gap_analysis", []):
        sev = g.get("severity", "medium")
        sev_cls = f"sev-{sev}" if sev in ("high", "medium", "low") else "sev-medium"
        gap_items += f'<div class="gap-item"><span class="{sev_cls}">[{sev.upper()}]</span> {g.get("issue", "")}</div>'
    matched_skills = jd_match_result.get("skill_match", {}).get("matched", [])
    missing_skills = jd_match_result.get("skill_match", {}).get("missing", [])
    return f"""<div class="card grid-full">
  <div class="card-header">JD Match Analysis</div>
  <div class="card-body">
    <div style="text-align:center;margin-bottom:16px;">
      <div class="jd-score {cls}">{ms}/100</div>
      <div style="font-size:13px;color:#8b8bb0;">JD Match Score</div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
      <div>
        <h2 style="font-size:12px;text-transform:uppercase;letter-spacing:1px;color:#81c784;margin-bottom:6px;">&#10003; Matched ({len(matched_skills)})</h2>
        {''.join(f'<span class="badge badge-ok" style="margin:2px;">{s}</span>' for s in matched_skills[:10])}
      </div>
      <div>
        <h2 style="font-size:12px;text-transform:uppercase;letter-spacing:1px;color:#e57373;margin-bottom:6px;">&#10007; Missing ({len(missing_skills)})</h2>
        {''.join(f'<span class="badge badge-broken" style="margin:2px;">{s}</span>' for s in missing_skills[:10])}
      </div>
    </div>
    {f'<div style="margin-top:12px;"><h2 style="font-size:12px;text-transform:uppercase;letter-spacing:1px;color:#ffb74d;margin-bottom:6px;">Gap Analysis</h2>{gap_items}</div>' if gap_items else ''}
    <p style="margin-top:12px;font-size:13px;color:#8b8bb0;">{jd_match_result.get("overall_assessment", "")}</p>
  </div>
</div>"""


def _render_improvement_details(improvements: Optional[Dict[str, list]]) -> str:
    if not improvements:
        return ""
    cards = ""
    cat_labels = {
        "open_source": "Open Source", "self_projects": "Projects",
        "production": "Experience", "technical_skills": "Skills",
    }
    for cat, items in improvements.items():
        label = cat_labels.get(cat, cat)
        for item in items[:2]:
            imp = item.get("impact", "medium")
            eff = item.get("effort", "medium")
            pri = item.get("priority_score", 5)
            cards += f"""<div class="improvement-card">
              <div class="cat">{label}</div>
              <div class="suggestion">{item.get('suggestion', '')}</div>
              <div class="meta">
                <span class="tag-impact">Impact: {imp}</span> &middot;
                <span class="tag-effort">Effort: {eff}</span> &middot;
                <span class="tag-priority">Priority: {pri}/10</span>
              </div>
            </div>"""
    return f"""<div class="card grid-full">
  <div class="card-header">Actionable Improvements</div>
  <div class="card-body">{cards}</div>
</div>"""
