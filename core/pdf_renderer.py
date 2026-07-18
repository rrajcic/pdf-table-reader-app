from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image


def get_page_count(pdf_path: str) -> int:
    with fitz.open(pdf_path) as doc:
        return doc.page_count


def render_page(pdf_path: str, page_number: int, dpi: int = 200) -> Image.Image:
    """Render a single PDF page as a PIL Image. page_number is 1-indexed."""
    with fitz.open(pdf_path) as doc:
        page = doc.load_page(page_number - 1)  # fitz pages are 0-indexed
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def find_pdfs(root: str = ".") -> list[str]:
    """Return all PDF paths under root, sorted alphabetically."""
    return sorted(str(p) for p in Path(root).rglob("*.pdf"))
