# Pipeline Overhaul — Deep OSS + Parallel + Portfolio

## Changes

### 1. Deep OSS Analysis (github.py)
- Add `fetch_user_prs(username)` — uses GitHub Search API to find actual PRs by author
- Add `fetch_user_issues(username)` — issue contributions
- Extract: orgs contributed to, repos, total PRs/Issues, languages used
- Feed into evaluator as structured contribution data
- Score based on real PRs merged, not repo classification

### 2. Parallel Section Extraction (pdf.py)
- Use `concurrent.futures.ThreadPoolExecutor` for 6 LLM calls
- ~17s → ~4s (speed depends on slowest section)

### 3. Portfolio Enrichment (new: portfolio.py)
- Fetch portfolio URL from resume basics
- Extract page title, description, project names, tech stack
- Hand feed to evaluator as additional evidence

### 4. JD Match Scoring (evaluator.py)
- New optional argument: `--job-description <text or file>`
- Evaluator generates fit score + gap analysis

### 5. Report Generation (new: report.py)
- HTML report with score breakdown, evidence, charts
- JSON export with full traceability
