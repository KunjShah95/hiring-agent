"""
Warm-cache benchmark: tests Docling and pymupdf4llm on both clean digital PDF
AND scanned/image-based PDF to compare real-world speeds.

Run AFTER:
  scripts/generate_sample_resume.py   -> sample_indian_resume.pdf (clean digital)
  scripts/generate_scanned_resume.py  -> sample_scanned_indian_resume.pdf (scanned)
"""
import time
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CLEAN_PDF = "sample_indian_resume.pdf"
SCANNED_PDF = "sample_scanned_indian_resume.pdf"


def warm_up_docling():
    """Force Docling to load models into cache by running one extraction."""
    print("  Warming up Docling (loading models)...")
    from pdf import PDFHandler
    handler = PDFHandler()
    start = time.time()
    text = handler.extract_text_from_pdf(CLEAN_PDF)
    elapsed = time.time() - start
    print(f"    Docling warm-up: {elapsed:.3f}s ({len(text) if text else 0} chars)")
    return elapsed


def benchmark_docling(pdf_path, iterations=5, label="Docling (cached)"):
    """Benchmark Docling (cached converter) across multiple runs."""
    from pdf import PDFHandler
    handler = PDFHandler()

    times = []
    char_counts = []
    errors = []
    for i in range(iterations):
        start = time.time()
        try:
            text = handler.extract_text_from_pdf(pdf_path)
            elapsed = time.time() - start
            char_counts.append(len(text) if text else 0)
        except Exception as e:
            elapsed = time.time() - start
            char_counts.append(0)
            errors.append(str(e)[:60])
            print(f"    Run {i+1}: FAILED - {str(e)[:60]}")
        times.append(elapsed)
        if not errors:
            print(f"    Run {i+1}: {elapsed:.3f}s ({char_counts[-1]} chars)")

    if errors:
        print(f"    !! {len(errors)}/{iterations} runs errored")

    return {
        "tool": label,
        "times": times,
        "avg": sum(times) / len(times),
        "min": min(times),
        "max": max(times),
        "chars": char_counts[0] if char_counts else 0,
        "errors": errors,
    }


def benchmark_pymupdf4llm(pdf_path, iterations=5):
    """Benchmark pymupdf4llm across multiple runs."""
    times = []
    char_counts = []
    errors = []
    for i in range(iterations):
        start = time.time()
        try:
            import pymupdf4llm
            import pymupdf
            doc = pymupdf.open(pdf_path)
            text = pymupdf4llm.to_markdown(doc, pages=list(range(doc.page_count)))
            doc.close()
            elapsed = time.time() - start
        except Exception as e:
            elapsed = time.time() - start
            text = ""
            errors.append(str(e)[:60])
            print(f"    Run {i+1}: FAILED - {str(e)[:60]}")
            times.append(elapsed)
            char_counts.append(0)
            continue

        times.append(elapsed)
        char_counts.append(len(text))
        print(f"    Run {i+1}: {elapsed:.3f}s ({len(text)} chars)")

    if errors:
        print(f"    !! {len(errors)}/{iterations} runs errored")

    return {
        "tool": "pymupdf4llm",
        "times": times,
        "avg": sum(times) / len(times) if times else 0,
        "min": min(times) if times else 0,
        "max": max(times) if times else 0,
        "chars": char_counts[0] if char_counts else 0,
        "errors": errors,
    }


def print_results_for_pdf(pdf_label, results, cold_time=None):
    """Print formatted benchmark results for one PDF type."""
    print(f"\n{'=' * 80}")
    print(f"  {pdf_label}")
    print(f"{'=' * 80}")
    print(f"{'Tool':<25} {'Avg (s)':<12} {'Min (s)':<12} {'Max (s)':<12} {'Chars':<10}")
    print(f"{'-' * 80}")
    for r in results:
        label = r['tool']
        if r['errors']:
            print(f"{label:<25} {'XX ERROR':<46} {r['chars']:<10}")
        else:
            print(f"{label:<25} {r['avg']:<12.3f} {r['min']:<12.3f} {r['max']:<12.3f} {r['chars']:<10}")

    if len(results) >= 2 and not results[1]['errors']:
        docling = results[0]
        legacy = results[1]
        ratio = legacy["avg"] / docling["avg"] if docling["avg"] > 0 else 0
        if ratio > 1:
            print(f"\n  >> Docling is {ratio:.1f}x FASTER than pymupdf4llm")
        elif ratio < 1:
            print(f"\n  >> Docling is {1/ratio:.1f}x SLOWER than pymupdf4llm")
        else:
            print(f"\n  >> Both tools perform similarly")
        print(f"  Stability: Docling range={docling['max']-docling['min']:.3f}s, "
              f"pymupdf4llm range={legacy['max']-legacy['min']:.3f}s")
    if cold_time:
        print(f"  Cold start: {cold_time:.3f}s")
    print(f"{'=' * 80}")


def run_benchmark_pdf(pdf_path, pdf_label, iterations=5):
    """Run full benchmark for one PDF type."""
    print(f"\n{'=' * 80}")
    print(f"  Testing: {os.path.basename(pdf_path)} ({os.path.getsize(pdf_path) / 1024:.1f} KB)")
    print(f"{'=' * 80}")

    print(f"\n  -> Docling...")
    d_results = benchmark_docling(pdf_path, iterations, label="Docling (cached)")

    print(f"\n  -> pymupdf4llm...")
    p_results = benchmark_pymupdf4llm(pdf_path, iterations)

    print_results_for_pdf(pdf_label, [d_results, p_results])
    return d_results, p_results


def print_combined_comparison(clean_results, scanned_results):
    """Print a combined table comparing both PDF types."""
    print(f"\n{'=' * 90}")
    print(f"  COMBINED COMPARISON - Clean vs Scanned PDF")
    print(f"{'=' * 90}")
    print(f"{'Tool':<25} {'PDF Type':<15} {'Avg (s)':<12} {'Min (s)':<12} {'Max (s)':<12}")
    print(f"{'-' * 90}")

    for tool_label in ["Docling (cached)", "pymupdf4llm"]:
        for pdf_type, results in [("Clean", clean_results), ("Scanned", scanned_results)]:
            r = results[0] if "Docling" in tool_label else results[1]
            if r['errors']:
                print(f"{tool_label:<25} {pdf_type:<15} {'XX ERROR':<36}")
            else:
                print(f"{tool_label:<25} {pdf_type:<15} {r['avg']:<12.3f} {r['min']:<12.3f} {r['max']:<12.3f}")
        if tool_label == "Docling (cached)":
            print()

    # Speedup analysis
    print(f"\n{'-' * 90}")
    print(f"  SPEED ANALYSIS")
    print(f"{'-' * 90}")

    for pdf_type, results in [("Clean digital", clean_results), ("Scanned", scanned_results)]:
        d = results[0]
        p = results[1]
        if not d['errors'] and not p['errors']:
            ratio = p['avg'] / d['avg'] if d['avg'] > 0 else 0
            if ratio > 1:
                print(f"  {pdf_type:15}: Docling is {ratio:.1f}x FASTER ({d['avg']:.3f}s vs {p['avg']:.3f}s)")
            else:
                print(f"  {pdf_type:15}: pymupdf4llm is {1/ratio:.1f}x FASTER ({p['avg']:.3f}s vs {d['avg']:.3f}s)")

    # Quality analysis: compare char counts
    print(f"\n{'-' * 90}")
    print(f"  EXTRACTION QUALITY (chars extracted)")
    print(f"{'-' * 90}")
    for pdf_type, results in [("Clean digital", clean_results), ("Scanned", scanned_results)]:
        d_chars = results[0]['chars']
        p_chars = results[1]['chars']
        ratio = d_chars / p_chars if p_chars > 0 else 0
        print(f"  {pdf_type:15}: Docling={d_chars:<6} | pymupdf4llm={p_chars:<6} | Ratio={ratio:.2f}x")
    print(f"{'=' * 90}")
    print()


if __name__ == "__main__":
    # Ensure both PDFs exist
    for pdf_path, gen_script in [
        (CLEAN_PDF, "scripts/generate_sample_resume.py"),
        (SCANNED_PDF, "scripts/generate_scanned_resume.py"),
    ]:
        if not os.path.exists(pdf_path):
            print(f"Generating {pdf_path}...")
            if "scanned" in pdf_path:
                from scripts.generate_scanned_resume import generate_scanned_resume
                generate_scanned_resume(pdf_path)
            else:
                from scripts.generate_sample_resume import generate_resume
                generate_resume(pdf_path)

    print(f"\nSample PDFs:")
    print(f"  Clean digital: {CLEAN_PDF} ({os.path.getsize(CLEAN_PDF) / 1024:.1f} KB)")
    print(f"  Scanned (img): {SCANNED_PDF} ({os.path.getsize(SCANNED_PDF) / 1024:.1f} KB)")

    # Warm up Docling once (cold start on clean PDF)
    print(f"\n{'=' * 80}")
    print(f"  WARMUP PHASE")
    print(f"{'=' * 80}")
    cold_time = warm_up_docling()

    # Benchmark: Clean PDF (5 runs each)
    clean_d, clean_p = run_benchmark_pdf(CLEAN_PDF, "CLEAN DIGITAL PDF", iterations=5)

    # Benchmark: Scanned PDF (3 runs each -- slower due to OCR)
    scanned_d, scanned_p = run_benchmark_pdf(SCANNED_PDF, "SCANNED PDF (image-based)", iterations=3)

    # Print combined comparison
    print_combined_comparison(
        [clean_d, clean_p],
        [scanned_d, scanned_p],
    )
