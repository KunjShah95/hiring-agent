"""
Throughput benchmark: measures how many clean digital PDFs per second the
pipeline can handle — sequentially and concurrently.

Tests three scenarios:
  1. Sequential, single PDFHandler (reused) — simulates queue processing
  2. Sequential, fresh PDFHandler per PDF  — simulates independent requests
  3. Concurrent (ThreadPoolExecutor)      — simulates parallel workers

Run AFTER scripts/generate_sample_resume.py has been executed.
"""
import time
import os
import sys
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean, median, stdev

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CLEAN_PDF = "sample_indian_resume.pdf"
NUM_COPIES = 50        # how many copies to process
BATCH_SIZES = [1, 5, 10, 20]  # concurrent worker counts


def prepare_pdf_copies(source, count):
    """Create `count` copies of the source PDF in a temp directory."""
    tmpdir = tempfile.mkdtemp(prefix="throughput_")
    copies = []
    for i in range(count):
        dest = os.path.join(tmpdir, f"resume_{i:04d}.pdf")
        shutil.copy2(source, dest)
        copies.append(dest)
    return tmpdir, copies


def benchmark_sequential_single_handler(pdf_paths, warm_runs=3):
    """Reuse one PDFHandler across all PDFs. Measures warm throughput."""
    print(f"  Warming up ({warm_runs} runs)...")
    from pdf import PDFHandler
    handler = PDFHandler()
    for i in range(warm_runs):
        handler.extract_text_from_pdf(pdf_paths[0])

    print(f"  Processing {len(pdf_paths)} PDFs sequentially (single handler)...")
    start = time.perf_counter()
    total_chars = 0
    for i, path in enumerate(pdf_paths):
        text = handler.extract_text_from_pdf(path)
        if text:
            total_chars += len(text)
    elapsed = time.perf_counter() - start
    throughput = len(pdf_paths) / elapsed
    print(f"    Done: {elapsed:.3f}s total, {throughput:.1f} PDFs/sec, {total_chars} chars")
    return {
        "scenario": "Sequential (single handler)",
        "pdfs": len(pdf_paths),
        "time_s": round(elapsed, 3),
        "throughput_pdf_per_sec": round(throughput, 1),
        "total_chars": total_chars,
    }


def benchmark_sequential_fresh_handler(pdf_paths, warm_runs=2):
    """Create a new PDFHandler per PDF. Simulates independent API calls."""
    from pdf import PDFHandler

    # Warm up once
    h = PDFHandler()
    h.extract_text_from_pdf(pdf_paths[0])

    print(f"  Processing {len(pdf_paths)} PDFs sequentially (fresh handler each)...")
    start = time.perf_counter()
    total_chars = 0
    for i, path in enumerate(pdf_paths):
        handler = PDFHandler()
        text = handler.extract_text_from_pdf(path)
        if text:
            total_chars += len(text)
    elapsed = time.perf_counter() - start
    throughput = len(pdf_paths) / elapsed
    print(f"    Done: {elapsed:.3f}s total, {throughput:.1f} PDFs/sec, {total_chars} chars")
    return {
        "scenario": "Sequential (fresh handler)",
        "pdfs": len(pdf_paths),
        "time_s": round(elapsed, 3),
        "throughput_pdf_per_sec": round(throughput, 1),
        "total_chars": total_chars,
    }


def benchmark_concurrent(pdf_paths, max_workers, warm_runs=2):
    """Process PDFs concurrently using ThreadPoolExecutor."""
    from pdf import PDFHandler

    # Warm up once
    h = PDFHandler()
    h.extract_text_from_pdf(pdf_paths[0])

    print(f"  Processing {len(pdf_paths)} PDFs with {max_workers} workers...")

    def extract_one(path):
        handler = PDFHandler()
        text = handler.extract_text_from_pdf(path)
        return len(text) if text else 0

    start = time.perf_counter()
    total_chars = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(extract_one, path) for path in pdf_paths]
        for future in as_completed(futures):
            total_chars += future.result()
    elapsed = time.perf_counter() - start
    throughput = len(pdf_paths) / elapsed
    print(f"    Done: {elapsed:.3f}s total, {throughput:.1f} PDFs/sec, {total_chars} chars")
    return {
        "scenario": f"Concurrent ({max_workers} workers)",
        "pdfs": len(pdf_paths),
        "time_s": round(elapsed, 3),
        "throughput_pdf_per_sec": round(throughput, 1),
        "total_chars": total_chars,
    }


def print_table(results):
    """Print a formatted results table."""
    print(f"\n{'=' * 90}")
    print(f"  THROUGHPUT BENCHMARK — {results[0]['pdfs']} clean digital PDFs")
    print(f"{'=' * 90}")
    print(f"{'Scenario':<35} {'PDFs':<8} {'Time (s)':<12} {'PDFs/sec':<12} {'Chars':<10}")
    print(f"{'-' * 90}")
    for r in results:
        print(f"{r['scenario']:<35} {r['pdfs']:<8} {r['time_s']:<12} {r['throughput_pdf_per_sec']:<12} {r['total_chars']:<10}")
    print(f"{'=' * 90}")

    # Summary
    seq_single = results[0]
    seq_fresh = results[1]
    concurrent_results = results[2:]

    print(f"\n  Key takeaways:")
    print(f"    - Reusing handler is {seq_single['throughput_pdf_per_sec']:.1f} PDFs/sec")
    print(f"    - Fresh handler per PDF is {seq_fresh['throughput_pdf_per_sec']:.1f} PDFs/sec")
    print(f"    - Overhead of fresh handler: {seq_fresh['time_s'] / seq_single['time_s']:.1f}x")

    best_concurrent = max(concurrent_results, key=lambda x: x['throughput_pdf_per_sec'])
    speedup = best_concurrent['throughput_pdf_per_sec'] / seq_single['throughput_pdf_per_sec']
    print(f"    - Best concurrent ({best_concurrent['scenario']}): {best_concurrent['throughput_pdf_per_sec']:.1f} PDFs/sec")
    print(f"    - Concurrent speedup over sequential: {speedup:.1f}x")
    print(f"{'=' * 90}")
    print()


if __name__ == "__main__":
    if not os.path.exists(CLEAN_PDF):
        print(f"Generating {CLEAN_PDF} first...")
        from scripts.generate_sample_resume import generate_resume
        generate_resume(CLEAN_PDF)

    pdf_size_kb = os.path.getsize(CLEAN_PDF) / 1024
    print(f"\nSample PDF: {CLEAN_PDF} ({pdf_size_kb:.1f} KB)")
    print(f"Creating {NUM_COPIES} copies for throughput testing...")

    tmpdir, pdf_copies = prepare_pdf_copies(CLEAN_PDF, NUM_COPIES)

    try:
        # 1. Sequential, single handler (reused)
        r1 = benchmark_sequential_single_handler(pdf_copies)

        # 2. Sequential, fresh handler per PDF
        r2 = benchmark_sequential_fresh_handler(pdf_copies)

        # 3. Concurrent — test various batch sizes
        concurrent_results = []
        for workers in BATCH_SIZES:
            r = benchmark_concurrent(pdf_copies, workers)
            concurrent_results.append(r)

        # Print combined table
        print_table([r1, r2] + concurrent_results)

    finally:
        # Cleanup temp directory
        shutil.rmtree(tmpdir, ignore_errors=True)
        print(f"Cleaned up temp directory: {tmpdir}")
