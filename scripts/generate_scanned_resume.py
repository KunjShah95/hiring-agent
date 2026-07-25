"""
Generate a realistic *scanned* Indian resume PDF (image-based, no selectable text).
Simulates how Naukri/Indeed/WhatsApp-shared resumes look after scanning/photographing.

Output: sample_scanned_indian_resume.pdf (image-based, ~200-500KB)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Force UTF-8 for Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def generate_base_pdf(path="scanned_base_resume.pdf"):
    """Generate the resume layout as a clean PDF first, using fpdf."""
    from fpdf import FPDF

    class IndianResumePDF(FPDF):
        def header(self):
            pass

        def footer(self):
            pass

    pdf = IndianResumePDF("P", "mm", "A4")
    pdf.add_page()

    # ── HEADER: Name & Contact Bar ──
    pdf.set_fill_color(41, 65, 128)
    pdf.rect(0, 0, 210, 40, "F")

    pdf.set_xy(15, 8)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(180, 10, "PRIYA VERMA", align="C")

    pdf.set_xy(15, 20)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(200, 210, 230)
    pdf.cell(180, 6, "Senior Data Scientist  |  ML Engineer", align="C")

    pdf.set_xy(15, 28)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(180, 195, 220)
    pdf.cell(180, 5, "priya.verma@email.com  |  +91-98765-01234  |  Bangalore, India  |  linkedin.com/in/priyaverma", align="C")

    # ── LEFT COLUMN (200mm wide, split 60mm | 135mm with 5mm gap) ──
    left_x = 12
    left_w = 58
    right_x = 75
    right_w = 128
    cur_y = 48

    # ── LEFT: Profile Photo placeholder ──
    pdf.set_draw_color(180, 180, 180)
    pdf.set_fill_color(235, 238, 245)
    pdf.rect(left_x, cur_y, left_w, 50, "DF")
    pdf.set_xy(left_x, cur_y + 12)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(left_w, 5, "[PHOTO]", align="C")
    pdf.set_xy(left_x, cur_y + 18)
    pdf.cell(left_w, 5, "Passport-size", align="C")
    pdf.set_xy(left_x, cur_y + 24)
    pdf.cell(left_w, 5, "photograph", align="C")
    cur_y += 55

    # ── LEFT: Personal Details ──
    pdf.set_xy(left_x, cur_y)
    pdf.set_fill_color(41, 65, 128)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(left_w, 5, "  PERSONAL DETAILS", fill=True)
    cur_y += 6

    details = [
        ("Date of Birth", "15-Aug-1995"),
        ("Gender", "Female"),
        ("Marital Status", "Single"),
        ("Nationality", "Indian"),
        ("Languages", "English, Hindi, Kannada"),
        ("Visa Status", "Valid US B1/B2"),
    ]
    pdf.set_text_color(60, 60, 60)
    for label, value in details:
        pdf.set_xy(left_x + 1, cur_y)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(left_w - 2, 3.5, label)
        cur_y += 3.5
        pdf.set_xy(left_x + 1, cur_y)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(130, 130, 130)
        pdf.cell(left_w - 2, 3.5, value)
        cur_y += 4.5

    # ── LEFT: Technical Skills ──
    cur_y += 2
    pdf.set_xy(left_x, cur_y)
    pdf.set_fill_color(41, 65, 128)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(left_w, 5, "  TECHNICAL SKILLS", fill=True)
    cur_y += 6

    skill_sections = [
        ("Programming", "Python, R, SQL, Scala, Java"),
        ("ML/DL", "TensorFlow, PyTorch, scikit-learn, XGBoost"),
        ("Data", "Spark, Hadoop, Airflow, Kafka, dbt"),
        ("Cloud", "AWS SageMaker, GCP AI Platform, Azure ML"),
        ("Visualization", "Tableau, Power BI, Matplotlib, Plotly"),
        ("MLOps", "Docker, Kubernetes, MLflow, Kubeflow"),
        ("NLP", "Transformers, BERT, GPT, spaCy, NLTK"),
    ]
    for cat, items in skill_sections:
        pdf.set_xy(left_x + 1, cur_y)
        pdf.set_font("Helvetica", "B", 6.5)
        pdf.set_text_color(90, 90, 90)
        pdf.cell(left_w - 2, 3.5, cat)
        cur_y += 3.5
        pdf.set_xy(left_x + 1, cur_y)
        pdf.set_font("Helvetica", "", 6.5)
        pdf.set_text_color(120, 120, 120)
        # Use multi_cell in case it wraps
        old_y = cur_y
        pdf.multi_cell(left_w - 2, 3, items)
        cur_y = pdf.get_y() + 1

    # ── LEFT: Education ──
    cur_y += 1
    pdf.set_xy(left_x, cur_y)
    pdf.set_fill_color(41, 65, 128)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(left_w, 5, "  EDUCATION", fill=True)
    cur_y += 6

    edu_entries = [
        ("M.Tech in AI", "IIT Bombay, 2018-2020", "CPI: 9.2/10"),
        ("B.E. Computer Science", "BITS Pilani, 2014-2018", "GPA: 8.8/10"),
    ]
    for degree, uni, grade in edu_entries:
        pdf.set_xy(left_x + 1, cur_y)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(90, 90, 90)
        pdf.cell(left_w - 2, 3.5, degree)
        cur_y += 3.5
        pdf.set_xy(left_x + 1, cur_y)
        pdf.set_font("Helvetica", "", 6.5)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(left_w - 2, 3, uni)
        cur_y += 3
        pdf.set_xy(left_x + 1, cur_y)
        pdf.set_font("Helvetica", "I", 6.5)
        pdf.set_text_color(140, 140, 140)
        pdf.cell(left_w - 2, 3, grade)
        cur_y += 5

    # ── LEFT: Certifications ──
    cur_y += 1
    pdf.set_xy(left_x, cur_y)
    pdf.set_fill_color(41, 65, 128)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(left_w, 5, "  CERTIFICATIONS", fill=True)
    cur_y += 6

    certs = [
        "AWS Certified ML Specialty (2024)",
        "Google Professional Data Engineer (2023)",
        "NVIDIA DLI - Deep Learning (2022)",
    ]
    for cert in certs:
        pdf.set_xy(left_x + 1, cur_y)
        pdf.set_font("Helvetica", "", 6.5)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(left_w - 2, 3.5, f"  * {cert}")
        cur_y += 4

    # ── RIGHT: Professional Summary ──
    pdf.set_xy(right_x, 48)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(41, 65, 128)
    pdf.cell(right_w, 6, "PROFESSIONAL SUMMARY")

    pdf.set_xy(right_x, 56)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(right_w, 4,
        "Results-driven Senior Data Scientist with 5+ years of experience in building and "
        "deploying ML models at scale. Specialized in NLP, recommendation systems, and "
        "predictive analytics. Reduced customer churn by 25% through ML-driven interventions "
        "and improved model inference latency by 60% via model optimization. Published 3 "
        "research papers in peer-reviewed journals. Experienced in leading cross-functional "
        "teams and mentoring junior data scientists."
    )

    # ── RIGHT: Work Experience ──
    cur_y = pdf.get_y() + 3
    pdf.set_xy(right_x, cur_y)

    # Section header with underline
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(41, 65, 128)
    pdf.cell(right_w, 6, "WORK EXPERIENCE")
    pdf.set_draw_color(41, 65, 128)
    pdf.set_line_width(0.4)
    pdf.line(right_x, cur_y + 6.5, right_x + right_w, cur_y + 6.5)

    experiences = [
        {
            "role": "Senior Data Scientist",
            "company": "FinCorp Analytics Pvt Ltd",
            "location": "Bangalore",
            "period": "Mar 2022 - Present",
            "bullets": [
                "Designed and deployed real-time fraud detection system processing 100K+ transactions/day with 95% precision",
                "Reduced customer churn by 25% using ensemble ML models (XGBoost + Neural Networks) with SHAP explanations",
                "Led migration of 15 ML models from on-prem to AWS SageMaker, reducing inference cost by 40%",
                "Built automated ML pipeline using Airflow and MLflow serving 5 production models simultaneously",
                "Mentored team of 4 data scientists through structured code reviews and knowledge sharing sessions",
            ],
        },
        {
            "role": "Data Scientist",
            "company": "TechRetail Solutions",
            "location": "Hyderabad",
            "period": "Jun 2020 - Feb 2022",
            "bullets": [
                "Developed product recommendation engine using collaborative filtering (ALS) increasing CTR by 35%",
                "Built NLP pipeline for sentiment analysis on 500K+ customer reviews using BERT fine-tuning",
                "Created customer segmentation model using K-means clustering improving targeting efficiency by 28%",
                "Implemented A/B testing framework for model evaluation reducing experiment cycle time by 50%",
            ],
        },
        {
            "role": "Junior Data Scientist",
            "company": "DataStartup Inc.",
            "location": "Pune",
            "period": "Sep 2018 - May 2020",
            "bullets": [
                "Built predictive maintenance model for manufacturing equipment reducing downtime by 20%",
                "Developed automated reporting dashboards in Tableau serving C-level executives",
                "Processed and cleaned 10TB+ of sensor data using PySpark and Apache Spark",
            ],
        },
    ]

    for exp in experiences:
        cur_y = pdf.get_y() + 3
        pdf.set_xy(right_x, cur_y)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(right_w, 4.5, f"{exp['role']}")

        cur_y += 4.5
        pdf.set_xy(right_x, cur_y)
        pdf.set_font("Helvetica", "I", 7.5)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(right_w, 4, f"{exp['company']}, {exp['location']}  |  {exp['period']}")

        cur_y = pdf.get_y() + 1
        for bullet in exp["bullets"]:
            pdf.set_xy(right_x, cur_y)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(right_w - 2, 3.5, f"  * {bullet}")
            cur_y = pdf.get_y() + 0.3

    # ── RIGHT: Research Publications ──
    cur_y = pdf.get_y() + 3
    pdf.set_xy(right_x, cur_y)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(41, 65, 128)
    pdf.cell(right_w, 6, "RESEARCH PUBLICATIONS")
    pdf.line(right_x, cur_y + 6.5, right_x + right_w, cur_y + 6.5)

    pubs = [
        "Verma, P. et al. (2024). 'Efficient Transformers for Low-Resource NLP'. ACL 2024.",
        "Verma, P. et al. (2023). 'Transfer Learning for Code-Switched Sentiment Analysis'. EMNLP 2023.",
        "Sharma, R., Verma, P. (2022). 'Attention-Based Fraud Detection in Imbalanced Datasets'. IEEE BigData 2022.",
    ]
    cur_y += 7
    for pub in pubs:
        pdf.set_xy(right_x, cur_y)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(right_w, 3.5, f"  * {pub}")
        cur_y = pdf.get_y() + 0.5

    # ── RIGHT: Awards & Achievements ──
    cur_y = pdf.get_y() + 3
    pdf.set_xy(right_x, cur_y)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(41, 65, 128)
    pdf.cell(right_w, 6, "AWARDS & ACHIEVEMENTS")
    pdf.line(right_x, cur_y + 6.5, right_x + right_w, cur_y + 6.5)

    awards = [
        "Best Paper Award - ACM COMPUTE Conference 2024",
        "FinCorp Spot Award for Excellence in AI Innovation (Q3 2023)",
        "Kaggle Grandmaster (Top 0.1% - 5 Gold Medals)",
        "Google Summer of Code Mentor (2022, 2023)",
    ]
    cur_y += 7
    for award in awards:
        pdf.set_xy(right_x, cur_y)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(right_w, 4, f"  * {award}")
        cur_y += 4.5

    # Add page background aging effect (slight yellowing)
    pdf.add_page()
    pdf.set_fill_color(255, 252, 245)
    pdf.rect(0, 0, 210, 297, "F")

    # Page 2: Additional details
    pdf.set_xy(15, 15)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(41, 65, 128)
    pdf.cell(180, 6, "ADDITIONAL PROJECTS")

    projects = [
        ("AutoML Pipeline", "Python, MLflow, Docker, AWS",
         "Built end-to-end automated ML pipeline that handles data validation, feature engineering, "
         "model training, and deployment. Used at FinCorp for rapid prototyping."),
        ("Real-time Dashboard", "React, D3.js, WebSockets, FastAPI",
         "Real-time data visualization dashboard for monitoring model performance metrics and drift detection. "
         "Reduced alert response time by 70%."),
        ("Chatbot Framework", "LangChain, GPT-4, Pinecone, FastAPI",
         "RAG-based internal knowledge base chatbot serving 2000+ employees. Handles 500+ queries daily."),
    ]
    cur_y = 25
    for name, tech, desc in projects:
        pdf.set_xy(15, cur_y)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(180, 5, f"{name} ({tech})")
        cur_y += 5
        pdf.set_xy(15, cur_y)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(180, 3.5, desc)
        cur_y = pdf.get_y() + 3

    # Work sample / code repositories
    cur_y += 2
    pdf.set_xy(15, cur_y)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(41, 65, 128)
    pdf.cell(180, 6, "OPEN SOURCE CONTRIBUTIONS")

    oss = [
        "Contributed to HuggingFace Transformers - Multi-lingual BERT improvements",
        "Core maintainer of 'ml-monitoring' open-source library (1.2K GitHub stars)",
        "Contributed to Apache Spark - MLlib performance optimizations",
    ]
    cur_y += 7
    for item in oss:
        pdf.set_xy(15, cur_y)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(180, 4.5, f"  * {item}")
        cur_y += 5

    # Declaration
    cur_y = 260
    pdf.set_xy(15, cur_y)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(180, 4, "I hereby declare that all the above information is true and correct to the best of my knowledge.")

    cur_y += 8
    pdf.set_xy(15, cur_y)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(60, 5, "(Priya Verma)")

    pdf.set_xy(130, cur_y)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(60, 5, "Date: 15-July-2026", align="R")

    pdf.output(path)
    print(f"[OK] Base resume PDF generated: {path} ({os.path.getsize(path)} bytes)")
    return path


def render_as_scanned(source_pdf, output_path="sample_scanned_indian_resume.pdf", dpi=150):
    """
    Render each page of the source PDF as a high-DPI raster image,
    then embed those images into a new PDF (simulating a scanned document).
    """
    import pymupdf  # PyMuPDF

    src = pymupdf.open(source_pdf)
    dst = pymupdf.open()

    total_pages = src.page_count

    for i in range(total_pages):
        page = src[i]
        # Render page to a pixmap (image) at specified DPI
        zoom = dpi / 72  # 72 is base PDF DPI
        mat = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        # Convert pixmap to bytes (PNG format)
        img_bytes = pix.tobytes("png")

        # Get page dimensions in points (A4 = 595 x 842 pts)
        rect = page.rect

        # Create new page in destination PDF with same dimensions
        dst_page = dst.new_page(width=rect.width, height=rect.height)

        # Insert the rasterized image covering the entire page
        dst_page.insert_image(
            rect,
            stream=img_bytes,
        )

        print(f"  Rendered page {i+1}/{total_pages} at {dpi} DPI ({pix.width}x{pix.height} px)")

    src.close()
    dst.save(output_path)
    dst.close()
    print(f"\n[OK] Scanned PDF saved: {output_path} ({os.path.getsize(output_path)} bytes)")


def generate_scanned_resume(path="sample_scanned_indian_resume.pdf", dpi=150):
    """Full pipeline: generate base PDF → render as scanned image PDF."""
    base_path = path.replace(".pdf", "_base.pdf")
    generate_base_pdf(base_path)
    render_as_scanned(base_path, path, dpi=dpi)
    # Clean up base file
    if os.path.exists(base_path):
        os.remove(base_path)
        print(f"  Cleaned up temporary: {base_path}")
    return path


if __name__ == "__main__":
    generate_scanned_resume()
    print("\nDone! Ready for benchmark.")
