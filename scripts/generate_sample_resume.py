"""
Generate a realistic sample Indian resume PDF with multi-column layout.
This mimics common Indian resume formats from Naukri, Indeed, etc.
"""
from fpdf import FPDF
import os

class IndianResumePDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def generate_resume(path="sample_indian_resume.pdf"):
    pdf = IndianResumePDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    # ── LEFT COLUMN (darker bg, ~35% width) ──
    left_x = 10
    left_w = 65
    right_x = 80
    right_w = 120

    # Draw left column background
    pdf.set_fill_color(240, 240, 245)
    pdf.rect(left_x, 10, left_w, 280, "F")

    # ── LEFT: Name & Title ──
    pdf.set_xy(left_x + 3, 15)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(left_w - 6, 6, "Ravi Kumar\nSharma")

    pdf.set_xy(left_x + 3, 32)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(left_w - 6, 5, "Senior Full Stack Engineer")

    # ── LEFT: Contact ──
    pdf.set_xy(left_x + 3, 48)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(left_w - 6, 5, "CONTACT")

    contact_lines = [
        "+91-98765 43210",
        "ravi.sharma@email.com",
        "Bangalore, Karnataka",
        "linkedin.com/in/ravisharma",
        "github.com/ravisharma",
        "ravisharma.dev",
    ]
    pdf.set_xy(left_x + 3, 55)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(100, 100, 100)
    for line in contact_lines:
        pdf.cell(left_w - 6, 4, line)
        pdf.ln(4)

    # ── LEFT: Skills ──
    pdf.set_xy(left_x + 3, 85)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(left_w - 6, 5, "SKILLS")

    skills = [
        ("Languages", "Python, TypeScript, Go, Java"),
        ("Frameworks", "React, Django, FastAPI, Spring Boot"),
        ("Databases", "PostgreSQL, MongoDB, Redis"),
        ("Cloud", "AWS, Docker, Kubernetes, CI/CD"),
        ("Tools", "Git, Jira, Grafana, Prometheus"),
    ]
    y = 92
    for cat, items in skills:
        pdf.set_xy(left_x + 3, y)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(left_w - 6, 4, cat)
        y += 4
        pdf.set_xy(left_x + 3, y)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(120, 120, 120)
        pdf.multi_cell(left_w - 6, 3.5, items)
        y = pdf.get_y() + 1

    # ── LEFT: Education ──
    pdf.set_xy(left_x + 3, y + 3)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(left_w - 6, 5, "EDUCATION")

    y = pdf.get_y() + 2
    pdf.set_xy(left_x + 3, y)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(left_w - 6, 4, "B.Tech Computer Science")
    y += 4
    pdf.set_xy(left_x + 3, y)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(left_w - 6, 4, "IIT Delhi, 2014-2018")
    y += 4
    pdf.set_xy(left_x + 3, y)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(left_w - 6, 4, "GPA: 8.5/10")

    # ── LEFT: Languages ──
    y = pdf.get_y() + 6
    pdf.set_xy(left_x + 3, y)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(left_w - 6, 5, "LANGUAGES")

    y += 6
    for lang, level in [("English", "Fluent"), ("Hindi", "Native"), ("Kannada", "Basic")]:
        pdf.set_xy(left_x + 3, y)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(left_w - 6, 4, f"{lang} - {level}")
        y += 4

    # ── RIGHT COLUMN: Professional Summary ──
    pdf.set_xy(right_x, 15)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(right_w, 6, "PROFESSIONAL SUMMARY")

    pdf.set_xy(right_x, 23)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(right_w, 4,
        "Senior Full Stack Engineer with 6+ years of experience building scalable "
        "web applications and microservices. Proven track record of leading engineering "
        "teams, reducing infrastructure costs by 40%, and mentoring junior developers. "
        "Open source contributor with 500+ GitHub stars across projects."
    )

    # ── RIGHT: Work Experience ──
    y = pdf.get_y() + 4
    pdf.set_xy(right_x, y)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(right_w, 6, "WORK EXPERIENCE")

    experiences = [
        {
            "role": "Senior Software Engineer",
            "company": "TechCorp India Pvt Ltd, Bangalore",
            "period": "Mar 2021 - Present",
            "bullets": [
                "Lead a team of 5 engineers building microservices architecture serving 50K+ users",
                "Reduced API response time by 40% through Redis caching and query optimization",
                "Designed and implemented CI/CD pipeline reducing deployment time from 2hrs to 15min",
                "Mentored 3 junior developers through structured code review and pair programming",
                "Migrated monolithic application to 12 microservices with zero downtime",
            ],
        },
        {
            "role": "Software Engineer",
            "company": "StartupXYZ Technologies, Hyderabad",
            "period": "Jul 2018 - Feb 2021",
            "bullets": [
                "Built real-time analytics dashboard using React and WebSockets serving 10K+ DAU",
                "Developed RESTful APIs in Django serving 1M+ requests/day with 99.9% uptime",
                "Implemented automated testing achieving 85% code coverage",
                "Reduced cloud costs by 30% through right-sizing EC2 instances and reserved pricing",
            ],
        },
        {
            "role": "Intern",
            "company": "WebAgency Solutions, Noida",
            "period": "Jan 2018 - Jun 2018",
            "bullets": [
                "Developed responsive web pages using React and Bootstrap",
                "Built REST API endpoints for client onboarding system",
            ],
        },
    ]

    for exp in experiences:
        y = pdf.get_y() + 2
        pdf.set_xy(right_x, y)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(right_w, 5, f"{exp['role']} | {exp['company']}")

        y += 5
        pdf.set_xy(right_x, y)
        pdf.set_font("Helvetica", "I", 7)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(right_w, 4, exp["period"])

        y = pdf.get_y() + 2
        for bullet in exp["bullets"]:
            pdf.set_xy(right_x, y)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(right_w - 4, 3.5, f"  * {bullet}")
            y = pdf.get_y() + 0.5

    # ── RIGHT: Projects ──
    y = pdf.get_y() + 3
    pdf.set_xy(right_x, y)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(right_w, 6, "PROJECTS")

    projects = [
        ("K8s Dashboard", "TypeScript, Go, React",
         "Open-source Kubernetes monitoring dashboard with 500+ GitHub stars. "
         "Features real-time cluster visualization, pod health monitoring, and alerting."),
        ("Blog Engine", "Python, FastAPI, PostgreSQL",
         "High-performance markdown blog platform with SEO optimization, "
         "serving 50K monthly visitors with <100ms response times."),
    ]

    for name, tech, desc in projects:
        y = pdf.get_y() + 2
        pdf.set_xy(right_x, y)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(right_w, 4, f"{name} ({tech})")

        y = pdf.get_y() + 1
        pdf.set_xy(right_x, y)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(right_w, 3.5, desc)

    # ── RIGHT: Certifications ──
    y = pdf.get_y() + 3
    pdf.set_xy(right_x, y)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(right_w, 6, "CERTIFICATIONS")

    certs = [
        "AWS Certified Solutions Architect (2023)",
        "Google Cloud Professional Developer (2022)",
        "Python for Data Science - NPTEL (2017)",
    ]
    y = pdf.get_y() + 2
    for cert in certs:
        pdf.set_xy(right_x, y)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(right_w, 4, f"  * {cert}")
        y += 4

    # Save
    pdf.output(path)
    print(f"[OK] Sample resume PDF generated: {path} ({os.path.getsize(path)} bytes)")
    return path


if __name__ == "__main__":
    generate_resume()
