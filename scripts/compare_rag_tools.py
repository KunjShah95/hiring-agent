"""
Compare pymupdf4llm vs Docling vs Marker on a sample Indian resume PDF.

Measures:
- Extraction speed
- Output length and structure
- Multi-column layout preservation
- Table/contact info extraction quality
"""
import time
import os
import sys

# Force UTF-8 encoding for Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
elif hasattr(sys.stdout, "buffer"):
    sys.stdout = sys.stdout.buffer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from generate_sample_resume import generate_resume
RESUME_PATH = "sample_indian_resume.pdf"


def test_pymupdf4llm():
    """Test using pymupdf4llm (current implementation)."""
    start = time.time()
    try:
        import pymupdf4llm
        import pymupdf

        doc = pymupdf.open(RESUME_PATH)
        text = pymupdf4llm.to_markdown(doc, pages=list(range(doc.page_count)))
        doc.close()
        elapsed = time.time() - start
        return {
            "tool": "pymupdf4llm",
            "time_s": round(elapsed, 3),
            "chars": len(text),
            "lines": len(text.split("\n")),
            "text": text[:3000],
        }
    except Exception as e:
        return {"tool": "pymupdf4llm", "error": str(e), "time_s": time.time() - start}



def test_docling():
    """Test using Docling by IBM."""
    start = time.time()
    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(RESUME_PATH)
        text = result.document.export_to_markdown()
        elapsed = time.time() - start
        return {
            "tool": "Docling",
            "time_s": round(elapsed, 3),
            "chars": len(text),
            "lines": len(text.split("\n")),
            "text": text[:3000],
        }
    except Exception as e:
        return {"tool": "Docling", "error": str(e), "time_s": time.time() - start}


def test_marker():
    """Test using Marker by Datalab."""
    start = time.time()
    try:
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict

        converter = PdfConverter(artifact_dict=create_model_dict())
        rendered = converter(RESUME_PATH)
        text = rendered.markdown
        elapsed = time.time() - start
        return {
            "tool": "Marker",
            "time_s": round(elapsed, 3),
            "chars": len(text),
            "lines": len(text.split("\n")),
            "text": text[:3000],
        }
    except Exception as e:
        return {"tool": "Marker", "error": str(e), "time_s": time.time() - start}


def analyze_output(result):
    """Analyze the quality of extracted text."""
    if "error" in result:
        return {"error": result["error"], "quality_score": "0/0"}

    text = result.get("text", "")
    analysis = {
        "has_name": any(name in text for name in ["Ravi Kumar", "Sharma", "Ravi"]),
        "has_email": "ravi.sharma" in text or "email.com" in text,
        "has_phone": "98765" in text or "43210" in text,
        "has_location": "Bangalore" in text,
        "has_skills_section": "Python" in text or "TypeScript" in text or "Go" in text,
        "has_work_section": "TechCorp" in text or "StartupXYZ" in text,
        "has_education": "IIT" in text or "Delhi" in text,
        "has_projects": "K8s" in text or "Dashboard" in text,
        "has_certifications": "AWS" in text or "Solutions Architect" in text,
        "bullet_points": text.count("*") + text.count("-"),
    }
    bool_checks = {k: v for k, v in analysis.items() if isinstance(v, bool)}
    analysis["quality_score"] = f"{sum(bool_checks.values())}/{len(bool_checks)}"
    return analysis


def print_comparison(results, analyses):
    """Print a formatted comparison table."""
    print("\n" + "=" * 90)
    print("📊 RAG TOOL COMPARISON — Sample Indian Resume PDF")
    print("=" * 90)

    # Speed & Size table
    print(f"\n{'Tool':<25} {'Time (s)':<12} {'Chars':<10} {'Lines':<10}")
    print("-" * 60)
    for r in results:
        if "error" in r:
            print(f"{r['tool']:<25} {'❌ ERROR':<12} {r.get('error', ''):<30}")
        else:
            print(f"{r['tool']:<25} {r['time_s']:<12} {r['chars']:<10} {r['lines']:<10}")

    # Quality table
    print(f"\n{'Quality Check':<55} {'pymupdf4llm':<18} {'Docling':<18} {'Marker':<18}")
    print("-" * 110)

    checks = ["has_name", "has_email", "has_phone", "has_location",
              "has_skills_section", "has_work_section", "has_education",
              "has_projects", "has_certifications"]

    for check in checks:
        label = check.replace("has_", "Extracted ").replace("_", " ").title()
        vals = []
        for a in analyses:
            v = a.get(check, "N/A")
            vals.append("✅" if v else "❌" if isinstance(v, bool) else str(v))
        print(f"{label:<55} {vals[0]:<18} {vals[1]:<18} {vals[2]:<18}")

    print(f"\n{'Quality Score':<55} ", end="")
    for a in analyses:
        print(f"{a.get('quality_score', 'N/A'):<18} ", end="")
    print()

    # Bullet points comparison
    print(f"\n{'Bullet Points Found':<55} ", end="")
    for a in analyses:
        print(f"{a.get('bullet_points', 0):<18} ", end="")
    print()

    # Output samples
    print("\n" + "=" * 90)
    print("📝 OUTPUT SAMPLES (first 300 chars each)")
    print("=" * 90)
    for r in results:
        if "error" not in r:
            print(f"\n--- {r['tool']} ---")
            print(r["text"][:400])
            print("...")

    print("\n" + "=" * 90)
    print("Recommendation:", " " * 65)
    print("=" * 90)

    # Find best tool
    best_tool = max(
        [(r["tool"], a.get("quality_score", "0/0")) for r, a in zip(results, analyses) if "error" not in r],
        key=lambda x: int(x[1].split("/")[0]) if "/" in x[1] else 0,
        default=("None", "0/0"),
    )
    fastest = min(
        [(r["tool"], r["time_s"]) for r in results if "error" not in r],
        key=lambda x: x[1],
        default=("None", 0),
    )
    print(f"  ✅ Best quality: {best_tool[0]} ({best_tool[1]} extracted)")
    print(f"  ⚡ Fastest: {fastest[0]} ({fastest[1]:.3f}s)")
    print()


if __name__ == "__main__":
    # Generate sample PDF if not exists
    if not os.path.exists(RESUME_PATH):
        print("Generating sample resume PDF...")
        generate_resume(RESUME_PATH)
    else:
        print(f"Using existing: {RESUME_PATH} ({os.path.getsize(RESUME_PATH)} bytes)")

    # Run all tests
    print("\nTesting pymupdf4llm...")
    r1 = test_pymupdf4llm()
    print(f"   {'XX' if 'error' in r1 else 'OK'} {r1.get('time_s', 'ERROR'):.3f}s")

    print("Testing Docling...")
    r2 = test_docling()
    print(f"   {'XX' if 'error' in r2 else 'OK'} {r2.get('time_s', 'ERROR'):.3f}s")

    print("Testing Marker...")
    r3 = test_marker()
    print(f"   {'XX' if 'error' in r3 else 'OK'} {r3.get('time_s', 'ERROR'):.3f}s")

    # Analyze
    results = [r1, r2, r3]
    analyses = [analyze_output(r) for r in results]

    # Print comparison
    print_comparison(results, analyses)
