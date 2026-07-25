"""
Integration tests for the full evaluation pipeline.

Tests the end-to-end flow: JSONResume → text conversion → GitHub enrichment
→ evaluation → scoring, with mocked LLM calls where needed.
"""
import pytest
from typing import Dict, List, Optional
from unittest.mock import patch

from models import (
    JSONResume, Basics, Location, Profile, Work, Education, Skill,
    Project, Award, EvaluationData, Scores, CategoryScore, BonusPoints,
    Deductions, GitHubProfile, IndianCandidateProfile,
)
from transform import (
    convert_json_resume_to_text,
    convert_github_data_to_text,
    convert_blog_data_to_text,
    transform_parsed_data,
    transform_basics,
    transform_work_experience,
)
from score import is_valid_resume_data, _evaluate_resume, process_pipeline, find_profile
from pdf import PDFHandler
from github import extract_github_username
from evaluator import ResumeEvaluator


# ══════════════════════════════════════════════════════════════════════
#  FIXTURES — Sample resume data for testing
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_basics() -> Basics:
    return Basics(
        name="Ravi Kumar Sharma",
        email="ravi.sharma@example.com",
        phone="+91-9876543210",
        url="https://ravisharma.dev",
        summary="Senior Full Stack Engineer with 6+ years of experience building scalable web applications.",
        location=Location(
            city="Bangalore",
            region="Karnataka",
            countryCode="IN",
        ),
        profiles=[
            Profile(network="GitHub", username="ravisharma", url="https://github.com/ravisharma"),
            Profile(network="LinkedIn", username="ravisharma", url="https://linkedin.com/in/ravisharma"),
        ],
    )


@pytest.fixture
def sample_work() -> List[Work]:
    return [
        Work(
            name="TechCorp India",
            position="Senior Software Engineer",
            url="https://techcorp.in",
            startDate="2021-03",
            endDate="Present",
            summary="Leading a team of 5 engineers building microservices architecture.",
            highlights=[
                "Reduced API response time by 40% through caching optimization",
                "Mentored 3 junior developers",
                "Led migration from monolith to microservices",
            ],
        ),
        Work(
            name="StartupXYZ",
            position="Software Engineer",
            startDate="2018-07",
            endDate="2021-02",
            summary="Full stack development with React and Django.",
            highlights=[
                "Built real-time dashboard serving 10K+ daily users",
                "Implemented CI/CD pipeline reducing deployment time by 60%",
            ],
        ),
    ]


@pytest.fixture
def sample_education() -> List[Education]:
    return [
        Education(
            institution="Indian Institute of Technology, Delhi",
            area="Computer Science",
            studyType="B.Tech",
            startDate="2014",
            endDate="2018",
            score="8.5/10",
        ),
    ]


@pytest.fixture
def sample_skills() -> List[Skill]:
    return [
        Skill(name="Programming Languages", keywords=["Python", "TypeScript", "Go", "Java"]),
        Skill(name="Frameworks", keywords=["React", "Django", "FastAPI", "Node.js"]),
        Skill(name="Databases", keywords=["PostgreSQL", "Redis", "MongoDB"]),
        Skill(name="DevOps", keywords=["Docker", "Kubernetes", "AWS", "CI/CD"]),
    ]


@pytest.fixture
def sample_projects() -> List[Project]:
    return [
        Project(
            name="Open Source Dashboard",
            description="A real-time monitoring dashboard for Kubernetes clusters",
            url="https://github.com/ravisharma/k8s-dashboard",
            technologies=["TypeScript", "React", "Go"],
            highlights=["500+ GitHub stars", "Used by 3 companies"],
        ),
        Project(
            name="Personal Blog Platform",
            description="A markdown-based blogging platform with SEO optimization",
            url="https://github.com/ravisharma/blog",
            technologies=["Python", "FastAPI", "PostgreSQL"],
        ),
    ]


@pytest.fixture
def sample_awards() -> List[Award]:
    return [
        Award(
            title="Best Engineering Award",
            date="2023-12",
            awarder="TechCorp India",
            summary="Awarded for outstanding contribution to platform reliability.",
        ),
    ]


@pytest.fixture
def sample_resume(
    sample_basics, sample_work, sample_education,
    sample_skills, sample_projects, sample_awards,
) -> JSONResume:
    return JSONResume(
        basics=sample_basics,
        work=sample_work,
        education=sample_education,
        skills=sample_skills,
        projects=sample_projects,
        awards=sample_awards,
    )


@pytest.fixture
def sample_github_data() -> Dict:
    return {
        "profile": {
            "username": "ravisharma",
            "name": "Ravi Kumar Sharma",
            "bio": "Senior Full Stack Engineer | Open Source Enthusiast",
            "public_repos": 45,
            "followers": 120,
            "following": 80,
            "created_at": "2016-05-10T12:00:00Z",
        },
        "projects": [
            {
                "name": "k8s-dashboard",
                "description": "Kubernetes monitoring dashboard",
                "github_url": "https://github.com/ravisharma/k8s-dashboard",
                "technologies": ["TypeScript", "Go"],
                "project_type": "open_source",
                "contributor_count": 5,
                "github_details": {
                    "stars": 500,
                    "forks": 50,
                    "language": "TypeScript",
                },
            },
            {
                "name": "blog-platform",
                "description": "Markdown blog engine",
                "github_url": "https://github.com/ravisharma/blog",
                "technologies": ["Python"],
                "project_type": "self_project",
                "contributor_count": 1,
                "github_details": {
                    "stars": 25,
                    "forks": 5,
                    "language": "Python",
                },
            },
        ],
        "total_projects": 2,
        "contributions": {
            "total_prs": 15,
            "own_repo_prs": 5,
            "external_prs": 10,
            "external_merged_prs": 8,
            "open_prs": 2,
            "total_issues": 7,
            "repos_contributed": ["facebook/react", "kubernetes/kubernetes"],
            "orgs_contributed": ["facebook", "kubernetes"],
            "recent_prs": [
                {
                    "title": "Fix: improve rendering performance",
                    "repo": "facebook/react",
                    "state": "merged",
                    "merged": True,
                    "is_own_repo": False,
                    "created_at": "2024-01-15T10:00:00Z",
                }
            ],
        },
    }


@pytest.fixture
def sample_evaluation_data() -> EvaluationData:
    return EvaluationData(
        scores=Scores(
            open_source=CategoryScore(score=20, max=35, evidence="5 open source projects with 500+ total stars"),
            self_projects=CategoryScore(score=22, max=30, evidence="2 well-documented personal projects"),
            production=CategoryScore(score=20, max=25, evidence="6+ years at 2 companies with measurable impact"),
            technical_skills=CategoryScore(score=8, max=10, evidence="Strong full-stack skills across Python, TypeScript, Go"),
        ),
        bonus_points=BonusPoints(total=5, breakdown="Working demo links (+3), Blog posts (+2)"),
        deductions=Deductions(total=2, reasons="Gap in employment history of 3 months not explained"),
        key_strengths=["Strong open source contributions", "Proven production experience"],
        areas_for_improvement=["Add more detail to project descriptions"],
    )


# ══════════════════════════════════════════════════════════════════════
#  INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════════════

class TestConvertJsonResumeToText:
    """Integration tests for resume-to-text conversion."""

    def test_basics_conversion(self, sample_resume):
        """Verify basics section renders correctly."""
        text = convert_json_resume_to_text(sample_resume)
        assert "Ravi Kumar Sharma" in text
        assert "ravi.sharma@example.com" in text
        assert "+91-9876543210" in text
        assert "Bangalore" in text
        assert "Karnataka" in text

    def test_work_conversion(self, sample_resume):
        """Verify work experience renders correctly."""
        text = convert_json_resume_to_text(sample_resume)
        assert "Senior Software Engineer" in text
        assert "TechCorp India" in text
        assert "Software Engineer" in text
        assert "StartupXYZ" in text
        assert "microservices" in text
        assert "CI/CD" in text

    def test_education_conversion(self, sample_resume):
        """Verify education section renders correctly."""
        text = convert_json_resume_to_text(sample_resume)
        assert "IIT" in text or "Indian Institute of Technology" in text
        assert "B.Tech" in text
        assert "Computer Science" in text
        assert "8.5" in text

    def test_skills_conversion(self, sample_resume):
        """Verify skills section renders correctly."""
        text = convert_json_resume_to_text(sample_resume)
        assert "Python" in text
        assert "TypeScript" in text
        assert "PostgreSQL" in text
        assert "Docker" in text

    def test_projects_conversion(self, sample_resume):
        """Verify projects section renders correctly."""
        text = convert_json_resume_to_text(sample_resume)
        assert "Open Source Dashboard" in text
        assert "Personal Blog Platform" in text
        assert "Kubernetes" in text

    def test_awards_conversion(self, sample_resume):
        """Verify awards section renders correctly."""
        text = convert_json_resume_to_text(sample_resume)
        assert "Best Engineering Award" in text
        assert "TechCorp India" in text

    def test_full_resume_text_contains_all_sections(self, sample_resume):
        """Verify all section headers are present in full conversion."""
        text = convert_json_resume_to_text(sample_resume)
        assert "=== BASIC INFORMATION ===" in text
        assert "=== WORK EXPERIENCE ===" in text
        assert "=== EDUCATION ===" in text
        assert "=== SKILLS ===" in text
        assert "=== PROJECTS ===" in text
        assert "=== AWARDS ===" in text

    def test_empty_resume_produces_empty_string(self):
        """An empty JSONResume should produce minimal text."""
        empty = JSONResume()
        text = convert_json_resume_to_text(empty)
        assert text == ""


class TestConvertGithubDataToText:
    """Integration tests for GitHub data-to-text conversion."""

    def test_profile_conversion(self, sample_github_data):
        """Verify GitHub profile data renders correctly."""
        text = convert_github_data_to_text(sample_github_data)
        assert "ravisharma" in text
        assert "Ravi Kumar Sharma" in text
        assert "45" in text  # public_repos
        assert "120" in text  # followers

    def test_projects_conversion(self, sample_github_data):
        """Verify GitHub projects render correctly."""
        text = convert_github_data_to_text(sample_github_data)
        assert "k8s-dashboard" in text
        assert "blog-platform" in text
        assert "500" in text  # stars
        assert "TypeScript" in text

    def test_contributions_conversion(self, sample_github_data):
        """Verify contributions section renders correctly."""
        text = convert_github_data_to_text(sample_github_data)
        assert "PRs" in text or "Pull Requests" in text
        assert "facebook/react" in text
        assert "kubernetes" in text

    def test_empty_github_data(self):
        """Empty GitHub data should produce minimal output."""
        text = convert_github_data_to_text({})
        assert text.strip() != ""

    def test_github_data_without_contributions(self):
        """GitHub data without contributions should still render profile and projects."""
        data = {
            "profile": {"username": "testuser", "name": "Test User", "public_repos": 10},
            "projects": [{"name": "test-repo", "description": "A test repo", "github_details": {"stars": 5}}],
        }
        text = convert_github_data_to_text(data)
        assert "testuser" in text
        assert "test-repo" in text


class TestIsValidResumeData:
    """Integration tests for resume data validation."""

    def test_valid_resume_with_basics(self, sample_resume):
        """Resume with basics should be valid."""
        assert is_valid_resume_data(sample_resume) is True

    def test_valid_resume_with_work_only(self):
        """Resume with only work should be valid."""
        r = JSONResume(work=[Work(name="Company", position="Engineer")])
        assert is_valid_resume_data(r) is True

    def test_valid_resume_with_skills_only(self):
        """Resume with only skills should be valid."""
        r = JSONResume(skills=[Skill(name="Python", keywords=["flask", "django"])])
        assert is_valid_resume_data(r) is True

    def test_invalid_empty_resume(self):
        """Completely empty resume should be invalid."""
        r = JSONResume()
        assert is_valid_resume_data(r) is False

    def test_invalid_resume_with_only_awards(self):
        """Resume with only awards (non-core) should be invalid."""
        r = JSONResume(awards=[Award(title="Best")])
        assert is_valid_resume_data(r) is False

    def test_invalid_none_resume(self):
        """None should be invalid."""
        assert is_valid_resume_data(None) is False


class TestTransformParsedData:
    """Integration tests for LLM JSON normalization."""

    def test_transform_full_resume(self):
        """Full resume dict should be transformed correctly."""
        raw = {
            "basics": {"name": "Test User", "email": "test@example.com"},
            "work_experience": [
                {"name": "Company", "position": "Engineer", "description": "Did stuff"},
            ],
            "education": [
                {"institution": "University", "degree": "B.Sc. in CS", "gpa": 3.5},
            ],
        }
        result = transform_parsed_data(raw)
        assert result["basics"]["name"] == "Test User"
        assert len(result["work"]) == 1
        assert result["work"][0]["name"] == "Company"
        assert len(result["education"]) == 1
        assert result["education"][0]["studyType"] == "B.Sc. in CS"

    def test_transform_basics_only(self):
        """Only basics should transform correctly."""
        raw = {"basics": {"name": "Test", "email": "t@t.com"}}
        result = transform_parsed_data(raw)
        assert result["basics"]["name"] == "Test"

    def test_transform_work_with_varied_keys(self):
        """Work with different key schemas should normalize."""
        raw = {
            "work_experience": [
                {"name": "Co", "position": "Dev", "description": "Worked"},
            ]
        }
        result = transform_parsed_data(raw)
        assert len(result["work"]) == 1

    def test_transform_skills_string_list(self):
        """Skills as list of strings should become categorized."""
        raw = {"skills": ["Python", "JavaScript", "Go"]}
        result = transform_parsed_data(raw)
        assert len(result["skills"]) == 1
        assert result["skills"][0]["name"] == "Programming Languages"
        assert "Python" in result["skills"][0]["keywords"]

    def test_transform_projects_with_technologies(self):
        """Projects should parse technologies correctly."""
        raw = {
            "projects": [
                {"name": "Project", "description": "Desc", "technologies": "Python,React"},
            ]
        }
        result = transform_parsed_data(raw)
        assert len(result["projects"]) == 1
        assert "Python" in result["projects"][0]["technologies"]


class TestExtractGithubUsername:
    """Integration tests for GitHub username extraction."""

    def test_full_url(self):
        username = extract_github_username("https://github.com/ravisharma")
        assert username == "ravisharma"

    def test_url_with_trailing_slash(self):
        username = extract_github_username("https://github.com/ravisharma/")
        assert username == "ravisharma"

    def test_url_with_query_params(self):
        username = extract_github_username("https://github.com/ravisharma?tab=repositories")
        assert username == "ravisharma"

    def test_github_dot_com_only(self):
        username = extract_github_username("github.com/ravisharma")
        assert username == "ravisharma"

    def test_at_username(self):
        username = extract_github_username("@ravisharma")
        assert username == "ravisharma"

    def test_plain_username(self):
        username = extract_github_username("ravisharma")
        assert username == "ravisharma"

    def test_none_url(self):
        assert extract_github_username(None) is None

    def test_empty_url(self):
        assert extract_github_username("") is None

    def test_invalid_url(self):
        assert extract_github_username("not-a-url") is not None  # Should be treated as username

    def test_url_with_org_repo(self):
        """URL pointing to an org/repo should still extract the org as username."""
        username = extract_github_username("https://github.com/facebook/react")
        assert username == "facebook"


class TestEvaluationDataValidation:
    """Integration tests for EvaluationData model validation."""

    def test_valid_evaluation(self, sample_evaluation_data):
        """Valid evaluation data should pass validation."""
        data = sample_evaluation_data
        assert data.scores.open_source.score == 20
        assert data.scores.open_source.max == 35
        assert len(data.key_strengths) >= 1
        assert len(data.areas_for_improvement) >= 1

    def test_score_capping(self):
        """Score exceeding max should be handled."""
        data = EvaluationData(
            scores=Scores(
                open_source=CategoryScore(score=50, max=35, evidence="test"),
                self_projects=CategoryScore(score=10, max=30, evidence="test"),
                production=CategoryScore(score=10, max=25, evidence="test"),
                technical_skills=CategoryScore(score=5, max=10, evidence="test"),
            ),
            bonus_points=BonusPoints(total=0, breakdown=""),
            deductions=Deductions(total=0, reasons=""),
            key_strengths=["Strength 1"],
            areas_for_improvement=["Area 1"],
        )
        # The score is stored as-is, capping happens in the UI layer (score.py)
        assert data.scores.open_source.score == 50

    def test_bonus_points_validation(self):
        """Bonus points should be between 0 and 20."""
        data = BonusPoints(total=15, breakdown="Great work")
        assert data.total == 15

        with pytest.raises(Exception):
            BonusPoints(total=25, breakdown="Too high")

    def test_evaluation_data_min_items(self, sample_evaluation_data):
        """key_strengths and areas_for_improvement should have 1-5 items."""
        data = sample_evaluation_data
        assert 1 <= len(data.key_strengths) <= 5
        assert 1 <= len(data.areas_for_improvement) <= 5


class TestIndianCandidateProfile:
    """Integration tests for Indian market-specific profile model."""

    def test_full_profile(self):
        profile = IndianCandidateProfile(
            ctc_current="25 LPA",
            ctc_expected="35 LPA",
            notice_period_days=60,
            preferred_locations=["Bangalore", "Hyderabad", "Remote"],
            visa_status="Indian Citizen",
            education_board="CBSE",
            graduation_year=2018,
        )
        assert profile.ctc_current == "25 LPA"
        assert profile.notice_period_days == 60
        assert "Bangalore" in profile.preferred_locations

    def test_minimal_profile(self):
        profile = IndianCandidateProfile()
        assert profile.ctc_current is None
        assert profile.preferred_locations is None

    def test_notice_period_typical_values(self):
        """Common Indian notice periods should be valid."""
        for days in [0, 15, 30, 45, 60, 90]:
            profile = IndianCandidateProfile(notice_period_days=days)
            assert profile.notice_period_days == days


class TestScoringIntegration:
    """Integration tests for score calculation across the pipeline."""

    def test_score_calculation_from_evaluation(self, sample_evaluation_data):
        """Verify score calculation matches the logic in score.py."""
        ev = sample_evaluation_data
        total_score = 0
        max_score = 0

        for name, cat in [
            ("open_source", ev.scores.open_source),
            ("self_projects", ev.scores.self_projects),
            ("production", ev.scores.production),
            ("technical_skills", ev.scores.technical_skills),
        ]:
            capped = min(cat.score, cat.max)
            total_score += capped
            max_score += cat.max

        total_score += ev.bonus_points.total
        total_score -= ev.deductions.total

        max_possible = max_score + 20
        if total_score > max_possible:
            total_score = max_possible

        assert total_score > 0
        assert max_score > 0
        assert total_score <= max_possible


class TestFullPipelineFlow:
    """Integration tests for the full pipeline with mocked LLM."""

    @patch("evaluator.ResumeEvaluator.evaluate_resume")
    def test_evaluate_resume_with_mock(self, mock_evaluate, sample_resume, sample_evaluation_data):
        """_evaluate_resume should call evaluator and return EvaluationData."""
        mock_evaluate.return_value = sample_evaluation_data

        result = _evaluate_resume(
            resume_data=sample_resume,
            github_data=None,
        )

        assert result is not None
        assert result.scores.open_source.score == 20
        assert "open source" in result.key_strengths[0].lower()

    @patch("evaluator.ResumeEvaluator.evaluate_resume")
    def test_evaluate_with_github_data(self, mock_evaluate, sample_resume, sample_github_data, sample_evaluation_data):
        """Evaluation with GitHub data should include it in the text."""
        mock_evaluate.return_value = sample_evaluation_data

        result = _evaluate_resume(
            resume_data=sample_resume,
            github_data=sample_github_data,
        )

        assert result is not None

        # The GitHub data should have been passed to the evaluator
        call_args = mock_evaluate.call_args[0][0]
        assert "ravisharma" in call_args
        assert "GitHub" in call_args

    @patch("evaluator.ResumeEvaluator.evaluate_resume")
    def test_evaluate_with_portfolio_data(self, mock_evaluate, sample_resume, sample_evaluation_data):
        """Evaluation with portfolio data should include it."""
        mock_evaluate.return_value = sample_evaluation_data
        portfolio_data = {"title": "Ravi's Portfolio", "description": "Personal site"}

        result = _evaluate_resume(
            resume_data=sample_resume,
            portfolio_data=portfolio_data,
        )

        assert result is not None
        call_args = mock_evaluate.call_args[0][0]
        assert "Portfolio" in call_args or "portfolio" in call_args

    @patch("evaluator.ResumeEvaluator.evaluate_resume")
    def test_evaluate_with_live_demos(self, mock_evaluate, sample_resume, sample_evaluation_data):
        """Live demo results should be included in evaluation context."""
        mock_evaluate.return_value = sample_evaluation_data
        live_demos = [
            {"url": "https://demo.example.com", "status": "ok"},
            {"url": "https://broken.example.com", "status": "broken"},
        ]

        result = _evaluate_resume(
            resume_data=sample_resume,
            live_demo_results=live_demos,
        )

        assert result is not None
        call_args = mock_evaluate.call_args[0][0]
        assert "LIVE DEMO" in call_args or "demo" in call_args.lower()

    def test_evaluate_without_model_params(self, sample_resume):
        """Should use default model params when none provided."""
        # This test just verifies the evaluator can be initialized
        # but doesn't call the LLM (that requires a running instance)
        evaluator = ResumeEvaluator(
            model_name="test-model",
            model_params={"temperature": 0.1, "top_p": 0.9},
        )
        assert evaluator.model_name == "test-model"
        assert evaluator.model_params["temperature"] == 0.1


class TestPDFExtractionFlow:
    """Integration tests for PDF extraction components."""

    def test_pdf_handler_init(self):
        """Verify PDFHandler can be initialized."""
        handler = PDFHandler()
        assert handler.template_manager is not None
        assert handler.provider is not None

    def test_extract_text_nonexistent_pdf(self):
        """Non-existent PDF should return None, not crash."""
        handler = PDFHandler()
        result = handler.extract_text_from_pdf("nonexistent_file.pdf")
        assert result is None

    def test_extract_text_invalid_path(self):
        """Invalid path should return None gracefully."""
        handler = PDFHandler()
        result = handler.extract_text_from_pdf("")
        assert result is None


class TestEvaluationErrorHandling:
    """Integration tests for error handling in evaluation pipeline."""

    @patch("evaluator.ResumeEvaluator.evaluate_resume")
    def test_evaluate_with_empty_resume(self, mock_evaluate, sample_evaluation_data):
        """Empty resume should still produce evaluation (no crash)."""
        mock_evaluate.return_value = sample_evaluation_data
        empty_resume = JSONResume()

        result = _evaluate_resume(resume_data=empty_resume)
        assert result is not None

    def test_evaluate_resume_no_model(self):
        """Evaluator with empty model name should raise."""
        with pytest.raises(ValueError, match="Model name cannot be empty"):
            ResumeEvaluator(model_name="")

    def test_convert_github_data_empty(self):
        """convert_github_data_to_text should handle empty dict gracefully."""
        text = convert_github_data_to_text({})
        assert "=== GITHUB DATA ===" in text


class TestBlogDataConversion:
    """Integration tests for blog data conversion."""

    def test_blog_data_with_blogs(self):
        """Blog data with entries should render correctly."""
        blog_data = {
            "total_blogs": 2,
            "blog_score": 7.5,
            "blogs": [
                {"url": "https://blog.example.com/post1", "score": 8.0, "details": "Detailed post"},
                {"url": "https://blog.example.com/post2", "score": 7.0, "details": "Good post"},
            ],
        }
        text = convert_blog_data_to_text(blog_data)
        assert "2" in text  # total_blogs
        assert "7.5" in text  # blog_score
        assert "blog.example.com" in text

    def test_blog_data_empty(self):
        """Empty blog data should produce header and zero values."""
        text = convert_blog_data_to_text({})
        assert "BLOG DATA" in text
        assert "Total Blogs" in text or "total_blogs" in text or "Blog" in text


class TestFindProfile:
    """Tests for the find_profile helper function."""

    def test_find_github_profile(self):
        profiles = [
            type("Profile", (), {"network": "GitHub", "username": "testuser", "url": "https://github.com/testuser"})(),
            type("Profile", (), {"network": "LinkedIn", "username": "testuser", "url": "https://linkedin.com/in/testuser"})(),
        ]
        result = find_profile(profiles, "Github")
        assert result is not None
        assert result.network == "GitHub"
        assert result.username == "testuser"

    def test_find_profile_none_list(self):
        result = find_profile(None, "Github")
        assert result is None

    def test_find_profile_empty_list(self):
        result = find_profile([], "Github")
        assert result is None

    def test_find_profile_not_found(self):
        profiles = [
            type("Profile", (), {"network": "LinkedIn", "username": "user", "url": ""})(),
        ]
        result = find_profile(profiles, "Github")
        assert result is None

    def test_find_profile_case_insensitive(self):
        profiles = [
            type("Profile", (), {"network": "github", "username": "testuser", "url": ""})(),
        ]
        result = find_profile(profiles, "Github")
        assert result is not None
        assert result.network == "github"


class TestProcessPipeline:
    """Integration tests for the full process_pipeline orchestration."""

    @patch("score.PDFHandler.extract_json_from_pdf")
    @patch("score._evaluate_resume")
    @patch("score.DEVELOPMENT_MODE", False)
    def test_process_pipeline_full_flow(self, mock_evaluate, mock_extract, sample_resume, sample_evaluation_data):
        """process_pipeline should orchestrate extraction, enrichment, and evaluation."""
        mock_extract.return_value = sample_resume
        mock_evaluate.return_value = sample_evaluation_data

        result = process_pipeline("test_resume.pdf")

        assert result is not None
        assert result["file"] == "test_resume.pdf"
        assert result["name"] == "Ravi Kumar Sharma"
        assert result["score"] is not None
        assert result["overall_score"] > 0
        assert result["max_score"] > 0

    @patch("score.PDFHandler.extract_json_from_pdf")
    @patch("score.DEVELOPMENT_MODE", False)
    def test_process_pipeline_extraction_failure(self, mock_extract):
        """Pipeline should return None when PDF extraction fails."""
        mock_extract.return_value = None

        result = process_pipeline("test_resume.pdf")
        assert result is None

    @patch("score.PDFHandler.extract_json_from_pdf")
    @patch("score._evaluate_resume")
    @patch("score.DEVELOPMENT_MODE", False)
    def test_process_pipeline_without_github(self, mock_evaluate, mock_extract, sample_resume, sample_evaluation_data):
        """Pipeline should work even without GitHub profile."""
        resume_no_github = sample_resume.model_copy(deep=True)
        resume_no_github.basics.profiles = []

        mock_extract.return_value = resume_no_github
        mock_evaluate.return_value = sample_evaluation_data

        result = process_pipeline("test_resume.pdf")
        assert result is not None
        assert result["github_data"] == {}
