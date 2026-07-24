import json
import logging
import sys
from typing import Dict, List, Optional

from models import EvaluationData
from llm_utils import initialize_llm_provider, extract_json_from_response
from prompt import DEFAULT_MODEL, MODEL_PARAMETERS

logger = logging.getLogger(__name__)


def _build_improvement_prompt(
    evaluation: EvaluationData, resume_text: str = ""
) -> tuple[str, str]:
    scores_summary = []
    for cat in ["open_source", "self_projects", "production", "technical_skills"]:
        cs = getattr(evaluation.scores, cat, None)
        if cs:
            scores_summary.append(
                f"- {cat}: {cs.score}/{cs.max} \u2014 Evidence: {cs.evidence}"
            )

    user = "=== RESUME EVALUATION ===\n\n"
    user += "Category Scores:\n" + "\n".join(scores_summary) + "\n\n"

    if evaluation.areas_for_improvement:
        user += "Areas for Improvement:\n"
        for a in evaluation.areas_for_improvement:
            user += f"- {a}\n"
        user += "\n"

    if evaluation.key_strengths:
        user += "Key Strengths:\n"
        for s in evaluation.key_strengths:
            user += f"- {s}\n"
        user += "\n"

    if resume_text:
        user += "=== RESUME TEXT ===\n"
        user += resume_text[:3000] + "\n"
        if len(resume_text) > 3000:
            user += "... [truncated]\n"
        user += "\n"

    user += "Generate improvement suggestions in the specified JSON format."

    system = (
        "You are an expert resume improvement advisor. "
        "Given a resume evaluation with scores across multiple categories, "
        "generate specific, actionable improvement suggestions for each category. "
        "Focus on concrete steps the candidate can take to improve their resume and profile. "
        "Return your response as a JSON object with exactly four keys: "
        "'open_source', 'self_projects', 'production', 'technical_skills'. "
        "Each key maps to a list of improvement items. "
        "Each improvement item is an object with these fields:\n"
        "- 'category': one of 'open_source', 'self_projects', 'production', 'technical_skills'\n"
        "- 'suggestion': a detailed, actionable suggestion (1-3 sentences)\n"
        "- 'impact': 'high', 'medium', or 'low'\n"
        "- 'effort': 'high', 'medium', or 'low'\n"
        "- 'priority_score': integer 0-10 (10 = most important to act on)\n\n"
        "Generate 2-4 suggestions per category. "
        "Prioritize suggestions that address low scores or gaps revealed by the evidence. "
        "Ensure suggestions are specific, not generic platitudes."
    )

    return system, user


def _fallback_improvements(
    evaluation: EvaluationData,
) -> Dict[str, List[dict]]:
    categories = [
        "open_source",
        "self_projects",
        "production",
        "technical_skills",
    ]
    fallback = {}
    for cat in categories:
        cs = getattr(evaluation.scores, cat, None)
        score_ratio = cs.score / cs.max if cs and cs.max > 0 else 0.5
        if score_ratio < 0.7:
            fallback[cat] = [
                {
                    "category": cat,
                    "suggestion": f"Review the evidence for {cat} and identify concrete ways to improve your score.",
                    "impact": "medium",
                    "effort": "medium",
                    "priority_score": 5,
                }
            ]
        else:
            fallback[cat] = []
    return fallback


def generate_improvements(
    evaluation: EvaluationData,
    resume_text: str = "",
    model_name: Optional[str] = None,
) -> Dict[str, List[dict]]:
    if model_name is None:
        model_name = DEFAULT_MODEL

    params = MODEL_PARAMETERS.get(model_name, {"temperature": 0.5, "top_p": 0.9})
    provider = initialize_llm_provider(model_name)
    system, prompt = _build_improvement_prompt(evaluation, resume_text)

    try:
        response = provider.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            options={
                "temperature": params.get("temperature", 0.5),
                "top_p": params.get("top_p", 0.9),
            },
        )

        raw = extract_json_from_response(response["message"]["content"])
        improvements = json.loads(raw)

        valid_categories = {
            "open_source",
            "self_projects",
            "production",
            "technical_skills",
        }
        validated = {}
        for cat in valid_categories:
            items = improvements.get(cat, [])
            cleaned = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                cleaned.append(
                    {
                        "category": item.get("category", cat),
                        "suggestion": item.get("suggestion", ""),
                        "impact": item.get("impact", "medium"),
                        "effort": item.get("effort", "medium"),
                        "priority_score": item.get("priority_score", 5),
                    }
                )
            validated[cat] = cleaned

        return validated

    except Exception as e:
        logger.error(f"Failed to generate improvements: {e}")
        return _fallback_improvements(evaluation)


def get_top_recommendations(
    improvements: Dict[str, List[dict]],
    n: int = 3,
) -> List[dict]:
    all_items = []
    for items in improvements.values():
        all_items.extend(items)
    all_items.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
    return all_items[:n]


def generate_improvement_report(
    improvements: Dict[str, List[dict]],
    fmt: str = "text",
) -> str:
    if fmt == "html":
        return _generate_html_report(improvements)
    return _generate_text_report(improvements)


def _generate_text_report(improvements: Dict[str, List[dict]]) -> str:
    lines = []
    lines.append("=" * 80)
    lines.append("IMPROVEMENT RECOMMENDATIONS")
    lines.append("=" * 80)

    category_labels = {
        "open_source": "Open Source Contributions",
        "self_projects": "Self Projects",
        "production": "Production Experience",
        "technical_skills": "Technical Skills",
    }

    category_order = [
        "open_source",
        "self_projects",
        "production",
        "technical_skills",
    ]

    for cat in category_order:
        items = improvements.get(cat, [])
        if not items:
            continue
        label = category_labels.get(cat, cat)
        lines.append(f"\n{label}")
        lines.append("-" * len(label))
        for i, item in enumerate(items, 1):
            lines.append(f"  {i}. {item.get('suggestion', '')}")
            impact = item.get("impact", "medium")
            effort = item.get("effort", "medium")
            priority = item.get("priority_score", 0)
            lines.append(
                f"     Impact: {impact.upper()}  |  Effort: {effort.upper()}  |  Priority: {priority}/10"
            )
            lines.append("")

    top = get_top_recommendations(improvements, 3)
    if top:
        lines.append("=" * 80)
        lines.append("TOP 3 PRIORITY RECOMMENDATIONS")
        lines.append("=" * 80)
        for i, item in enumerate(top, 1):
            lines.append(
                f"  {i}. [{item.get('category', '').upper()}] {item.get('suggestion', '')}"
            )
            lines.append("")

    return "\n".join(lines)


def _generate_html_report(improvements: Dict[str, List[dict]]) -> str:
    category_labels = {
        "open_source": "Open Source",
        "self_projects": "Self Projects",
        "production": "Production Experience",
        "technical_skills": "Technical Skills",
    }

    category_icons = {
        "open_source": "\U0001f310",
        "self_projects": "\U0001f680",
        "production": "\U0001f3e2",
        "technical_skills": "\U0001f4bb",
    }

    parts = [
        '<div class="improvement-report" style="font-family: system-ui, sans-serif; max-width: 900px; margin: 0 auto;">'
    ]

    parts.append(
        """
<style>
.improvement-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.improvement-card h4 { margin: 0 0 8px 0; font-size: 15px; }
.tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; margin-right: 6px; }
.tag-high { background: #fee2e2; color: #991b1b; }
.tag-medium { background: #fef3c7; color: #92400e; }
.tag-low { background: #dbeafe; color: #1e40af; }
.priority-bar {
    height: 4px; border-radius: 2px; margin-top: 8px;
    background: linear-gradient(90deg, #22c55e, #eab308, #ef4444);
}
.section-title {
    font-size: 18px; font-weight: 700; margin: 24px 0 12px 0;
    padding-bottom: 6px; border-bottom: 2px solid #e2e8f0;
}
</style>
"""
    )

    category_order = [
        "open_source",
        "self_projects",
        "production",
        "technical_skills",
    ]

    for cat in category_order:
        items = improvements.get(cat, [])
        if not items:
            continue
        label = category_labels.get(cat, cat)
        icon = category_icons.get(cat, "")
        parts.append(f'<div class="section-title">{icon} {label}</div>')
        for item in items:
            suggestion = item.get("suggestion", "")
            impact = item.get("impact", "medium")
            effort = item.get("effort", "medium")
            priority = item.get("priority_score", 5)
            pct = (priority / 10) * 100
            parts.append(
                f"""
<div class="improvement-card">
    <h4>{suggestion}</h4>
    <div>
        <span class="tag tag-{impact}">Impact: {impact.title()}</span>
        <span class="tag tag-{effort}">Effort: {effort.title()}</span>
        <span style="font-size: 12px; color: #64748b;">Priority: {priority}/10</span>
    </div>
    <div class="priority-bar" style="width: {pct}%;"></div>
</div>"""
            )

    top = get_top_recommendations(improvements, 3)
    if top:
        parts.append(
            '<div class="section-title">\u2b50 Top 3 Priority Recommendations</div>'
        )
        for i, item in enumerate(top, 1):
            cat_label = category_labels.get(
                item.get("category", ""), item.get("category", "")
            )
            suggestion = item.get("suggestion", "")
            parts.append(
                f"""
<div class="improvement-card" style="border-left: 4px solid #f59e0b;">
    <h4>#{i} [{cat_label}] {suggestion}</h4>
</div>"""
            )

    parts.append("</div>")
    return "\n".join(parts)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python improvement.py <evaluation_json_path> [resume_text_path]")
        sys.exit(1)

    eval_path = sys.argv[1]
    resume_text = ""
    if len(sys.argv) > 2:
        resume_path = sys.argv[2]
        with open(resume_path, "r", encoding="utf-8") as f:
            resume_text = f.read()

    with open(eval_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    evaluation = EvaluationData(**data)
    improvements = generate_improvements(evaluation, resume_text)
    report = generate_improvement_report(improvements, fmt="text")
    print(report)
