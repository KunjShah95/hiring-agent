"""
Portfolio enrichment module.
Fetches and parses portfolio/website content for resume evaluation.
"""

import re
import logging
import requests
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def fetch_portfolio(url: str) -> Optional[Dict]:
    """Fetch portfolio page and extract relevant content."""
    if not url:
        return None

    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url

    try:
        logger.info(f"Fetching portfolio: {url}")
        response = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (compatible; HiringAgent/1.0)"
        })

        if response.status_code != 200:
            logger.warning(f"Portfolio returned status {response.status_code}")
            return None

        html = response.text
        title = _extract_title(html)
        description = _extract_meta_description(html)
        projects = _extract_project_names(html)
        tech_stack = _extract_tech_stack(html)
        links = _extract_links(html)

        result = {
            "url": url,
            "title": title,
            "description": description,
            "projects": projects,
            "tech_stack": tech_stack,
            "links": links,
        }

        logger.info(
            f"Portfolio: title='{title}', {len(projects)} projects, "
            f"{len(tech_stack)} techs, {len(links)} links"
        )
        return result

    except requests.RequestException as e:
        logger.warning(f"Failed to fetch portfolio {url}: {e}")
        return None


def _extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _extract_meta_description(html: str) -> str:
    m = re.search(
        r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']',
        html, re.IGNORECASE
    )
    return m.group(1).strip() if m else ""


def _extract_project_names(html: str) -> list:
    """Find likely project/section names from headings and links."""
    names = set()
    # Headings
    for tag in ["h1", "h2", "h3", "h4"]:
        for m in re.finditer(
            rf"<{tag}[^>]*>(.*?)</{tag}>", html, re.IGNORECASE | re.DOTALL
        ):
            text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            if text and len(text) < 100:
                names.add(text)
    # Link text that looks like project names
    for m in re.finditer(
        r'<a[^>]*href=["\']/(?:projects?|work)/([^"\']+)["\'][^>]*>(.*?)</a>',
        html, re.IGNORECASE | re.DOTALL
    ):
        text = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if text and len(text) < 100:
            names.add(text)
    return sorted(names)


def _extract_tech_stack(html: str) -> list:
    """Extract technology mentions from the page."""
    techs = set()
    known_techs = [
        "python", "javascript", "typescript", "react", "next.js", "vue",
        "fastapi", "flask", "django", "node.js", "express", "go", "rust",
        "docker", "kubernetes", "postgresql", "mongodb", "redis", "sql",
        "langchain", "autogen", "openai", "gpt", "llm", "rag", "agent",
        "tensorflow", "pytorch", "scikit-learn", "hugging face", "n8n",
        "tailwind", "graphql", "aws", "gcp", "azure", "vercel", "git",
    ]
    lower_html = html.lower()
    for tech in known_techs:
        if tech in lower_html:
            techs.add(tech)
    return sorted(techs)


def _extract_links(html: str) -> list:
    """Extract GitHub and external project links."""
    links = set()
    for m in re.finditer(
        r'href=["\'](https?://[^"\']+)["\']', html, re.IGNORECASE
    ):
        url = m.group(1)
        if any(d in url for d in ["github.com", "gitlab.com", "npmjs.com"]):
            links.add(url)
    return sorted(links)


def convert_portfolio_to_text(portfolio_data: Dict) -> str:
    """Convert portfolio data to text for the evaluator prompt."""
    if not portfolio_data:
        return ""

    text = "\n\n=== PORTFOLIO DATA ===\n"
    text += f"Portfolio URL: {portfolio_data.get('url', 'N/A')}\n"
    text += f"Title: {portfolio_data.get('title', 'N/A')}\n"

    desc = portfolio_data.get("description", "")
    if desc:
        text += f"Description: {desc}\n"

    projects = portfolio_data.get("projects", [])
    if projects:
        text += f"\nSections/Projects found on portfolio: {', '.join(projects)}\n"

    techs = portfolio_data.get("tech_stack", [])
    if techs:
        text += f"Technologies mentioned: {', '.join(techs)}\n"

    links = portfolio_data.get("links", [])
    if links:
        text += f"External project links: {', '.join(links)}\n"

    text += "\n"
    return text
