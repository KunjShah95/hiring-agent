import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

HISTORY_FILE = "resume_history.json"


def load_history() -> List[Dict]:
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load history: {e}")
        return []


def save_entry(entry: Dict):
    history = load_history()
    history.append(entry)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def record_score(
    file_name: str,
    candidate_name: str,
    overall_score: float,
    max_score: float,
    open_source: int,
    self_projects: int,
    production: int,
    technical_skills: int,
    bonus: int,
    deductions: int,
):
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "file": file_name,
        "name": candidate_name,
        "overall_score": overall_score,
        "max_score": max_score,
        "pct": round(overall_score / max_score * 100, 1) if max_score else 0,
        "open_source": open_source,
        "self_projects": self_projects,
        "production": production,
        "technical_skills": technical_skills,
        "bonus": bonus,
        "deductions": deductions,
    }
    save_entry(entry)
    return entry


def show_history(name_filter: Optional[str] = None, n: int = 10):
    history = load_history()
    if not history:
        print("No score history yet. Run `python score.py <resume.pdf>` first.")
        return

    if name_filter:
        history = [h for h in history if name_filter.lower() in h.get("name", "").lower()]

    if not history:
        print(f"No history found for filter: {name_filter}")
        return

    history.sort(key=lambda x: x.get("date", ""))
    recent = history[-n:]

    print("\n" + "=" * 90)
    print(f"📈 RESUME SCORE HISTORY (last {len(recent)} of {len(history)} runs)")
    print("=" * 90)

    header = f"{'Date':<20} {'Name':<20} {'Score':<8} {'OS':<4} {'Proj':<5} {'Prod':<5} {'Skills':<7} {'Bonus':<6} {'Δ':<6}"
    print(header)
    print("-" * 90)

    cand_deltas = {}
    for h in recent:
        cname = h.get("name", "")
        dt = h.get("date", "?")
        name = cname[:18] if cname else "?"
        sc = f"{h.get('overall_score', 0):.0f}/{h.get('max_score', 100)}"
        os_ = h.get("open_source", 0)
        proj = h.get("self_projects", 0)
        prod = h.get("production", 0)
        sk = h.get("technical_skills", 0)
        bn = h.get("bonus", 0)

        prev_score = cand_deltas.get(cname)
        if prev_score is not None:
            delta = h.get("overall_score", 0) - prev_score
            delta_str = f"+{delta:.0f}" if delta > 0 else f"{delta:.0f}" if delta < 0 else " 0"
        else:
            delta_str = "-"
        cand_deltas[cname] = h.get("overall_score", 0)

        print(f"{dt:<20} {name:<20} {sc:<8} {os_:<4} {proj:<5} {prod:<5} {sk:<7} {bn:<6} {delta_str:<6}")

    print("=" * 90)


def show_trend(name_filter: Optional[str] = None, as_html: bool = False) -> Optional[str]:
    history = load_history()
    if not history:
        return None

    if name_filter:
        history = [h for h in history if name_filter.lower() in h.get("name", "").lower()]

    history.sort(key=lambda x: x.get("date", ""))
    if len(history) < 2:
        return None

    if as_html:
        return _trend_html(history)
    return _trend_ascii(history)


def _trend_ascii(history: List[Dict]) -> str:
    scores = [h.get("overall_score", 0) for h in history]
    dates = [h.get("date", "")[:10] for h in history]
    max_v = max(scores) if scores else 100
    min_v = min(scores) if scores else 0
    rng = max(max_v - min_v, 1) or 1
    h_ = 10
    lines = []
    for row in range(h_, 0, -1):
        threshold = min_v + (rng * row / h_)
        line = ""
        for s in scores:
            line += "█" if s >= threshold else " "
        lines.append(line)
    return "\n".join(lines)


def _trend_html(history: List[Dict]) -> str:
    scores = [h.get("overall_score", 0) for h in history]
    dates = [h.get("date", "")[:10] for h in history]
    max_v = max(scores) if scores else 100
    bars = ""
    for i, (d, s) in enumerate(zip(dates, scores)):
        pct = (s / max_v * 100) if max_v else 0
        bars += f"""<div style="display:flex;align-items:end;gap:4px;flex-direction:column;">
          <div style="font-size:11px;color:#8b8bb0;">{s:.0f}</div>
          <div style="width:30px;height:{pct}px;background:linear-gradient(180deg,#667eea,#764ba2);border-radius:4px 4px 0 0;min-height:4px;"></div>
          <div style="font-size:10px;color:#4a4a6a;transform:rotate(-45deg);">{d[-5:]}</div>
        </div>"""
    return f"""<div style="display:flex;gap:8px;align-items:end;padding:20px 0;overflow-x:auto;">{bars}</div>"""
