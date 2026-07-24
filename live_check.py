import re
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def extract_urls_from_github(github_data: dict) -> List[str]:
    urls = []
    if "projects" in github_data:
        for repo in github_data["projects"]:
            gh = repo.get("github_details", {})
            homepage = repo.get("homepage") or gh.get("homepage", "")
            if homepage and homepage.startswith("http"):
                urls.append(homepage)
    return urls


def extract_urls_from_portfolio(portfolio_data: dict) -> List[str]:
    urls = []
    if not portfolio_data:
        return urls
    links = portfolio_data.get("links", [])
    for link in links:
        if isinstance(link, str) and link.startswith("http"):
            urls.append(link)
    return urls


def check_url(url: str, timeout: int = 8) -> dict:
    try:
        resp = requests.get(
            url, timeout=timeout, allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; HiringAgent/1.0)"}
        )
        if resp.status_code == 200:
            return {"url": url, "status": "ok", "code": 200}
        else:
            return {"url": url, "status": "broken", "code": resp.status_code}
    except requests.Timeout:
        return {"url": url, "status": "timeout", "code": None}
    except requests.ConnectionError:
        return {"url": url, "status": "unreachable", "code": None}
    except Exception as e:
        return {"url": url, "status": "error", "code": str(e)}


def verify_urls(urls: List[str], max_workers: int = 5) -> List[dict]:
    if not urls:
        return []
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        fut = {pool.submit(check_url, u): u for u in urls}
        for f in as_completed(fut):
            results.append(f.result())
    results.sort(key=lambda x: ("ok" != x["status"], x["url"]))
    return results


def count_working(url_statuses: List[dict]) -> int:
    return sum(1 for r in url_statuses if r["status"] == "ok")


def get_bonus_points(url_statuses: List[dict]) -> int:
    working = count_working(url_statuses)
    return min(working, 5)


def format_demo_evidence(url_statuses: List[dict]) -> str:
    if not url_statuses:
        return ""
    working = count_working(url_statuses)
    total = len(url_statuses)
    parts = [f"+{get_bonus_points(url_statuses)} bonus points for {working}/{total} working demos"]
    broken = [r for r in url_statuses if r["status"] != "ok"]
    if broken:
        parts.append(f"Broken links ({len(broken)}): " + ", ".join(r["url"] for r in broken[:3]))
    return " | ".join(parts)
