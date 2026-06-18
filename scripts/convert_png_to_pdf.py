"""Convert all PNG figures in analysis/figures/ to PDF vector format.

Historical note
---------------
This script previously re-embedded the PNG bitmaps into a PDF canvas via
``matplotlib.image.imread`` + ``imshow``. That produced a *raster* PDF whose
only "vector" content was the page wrapper — the figure itself was still a
300-DPI bitmap, which is unsuitable for publication submission.

The current implementation regenerates the PDFs directly from
``analysis/generate_figures.py``, which calls ``plt.savefig(..., format='pdf')``
so the resulting PDF contains true vector graphics (scalable, no pixel
artifacts). PNG copies are still produced alongside the PDFs for quick
previewing.

Usage: python scripts/convert_png_to_pdf.py
"""

import runpy
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GENERATE_FIGURES = PROJECT_ROOT / "analysis" / "generate_figures.py"
FIGURES_DIR = PROJECT_ROOT / "analysis" / "figures"


def _has_raster_only_pdf(pdf_path: Path) -> bool:
    """Heuristic: detect legacy raster-embedded PDFs by inspecting /Filter.

    Vector PDFs from matplotlib do not embed a /DCTDecode or /FlateDecode image
    XObject spanning the whole page; raster-embedded ones do. This helper is
    used only for reporting, not for conversion.
    """
    try:
        with open(pdf_path, "rb") as fh:
            head = fh.read(4096)
        return b"/DCTDecode" in head or b"/FlateDecode" in head and b"/Image" in head
    except OSError:
        return False


def main():
    if not GENERATE_FIGURES.exists():
        print(f"ERROR: generate_figures.py not found at {GENERATE_FIGURES}")
        sys.exit(1)

    pre_pdfs = {p.name: p.stat().st_size for p in FIGURES_DIR.glob("*.pdf")}

    print("Regenerating vector PDFs via analysis/generate_figures.py ...")
    # Re-execute the figure pipeline in-place. generate_figures.py already
    # writes both .png (dpi=300 raster preview) and .pdf (vector) per figure.
    runpy.run_path(str(GENERATE_FIGURES), run_name="__main__")

    new_pdfs = sorted(FIGURES_DIR.glob("*.pdf"))
    print(f"\nVector PDF generation complete: {len(new_pdfs)} PDF file(s) in {FIGURES_DIR}")
    for pdf in new_pdfs:
        raster = _has_raster_only_pdf(pdf)
        prev_size = pre_pdfs.get(pdf.name)
        size_note = ""
        if prev_size is not None:
            size_note = f" (was {prev_size} bytes, now {pdf.stat().st_size})"
        tag = " [raster-embedded — legacy]" if raster else " [vector]"
        print(f"  - {pdf.name}{tag}{size_note}")

    print("\nNote: PNG copies are also written for quick preview. For publication")
    print("submission, use the .pdf files — they are true vector graphics.")


if __name__ == "__main__":
    main()
