"""Convert all PNG figures in analysis/figures/ to PDF vector format.

Usage: python scripts/convert_png_to_pdf.py
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from pathlib import Path

FIGURES_DIR = Path(__file__).resolve().parent.parent / "analysis" / "figures"


def convert_png_to_pdf(png_path: Path) -> Path:
    pdf_path = png_path.with_suffix(".pdf")
    img = mpimg.imread(str(png_path))
    dpi = 300
    h, w = img.shape[:2]
    figsize = (w / dpi, h / dpi)
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.imshow(img)
    ax.axis("off")
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    fig.savefig(str(pdf_path), dpi=dpi, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    return pdf_path


def main():
    png_files = sorted(FIGURES_DIR.glob("*.png"))
    if not png_files:
        print("No PNG files found in", FIGURES_DIR)
        return

    print(f"Converting {len(png_files)} PNG figures to PDF...")
    for png in png_files:
        pdf = convert_png_to_pdf(png)
        print(f"  {png.name} -> {pdf.name}")

    print(f"\nDone. {len(png_files)} PDF files generated in {FIGURES_DIR}")


if __name__ == "__main__":
    main()
