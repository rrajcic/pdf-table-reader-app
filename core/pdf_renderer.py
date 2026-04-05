from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image
from pypdf import PdfReader


def get_page_count(pdf_path: str) -> int:
    reader = PdfReader(pdf_path)
    return len(reader.pages)


def render_page(pdf_path: str, page_number: int, dpi: int = 200) -> Image.Image:
    """Render a single PDF page as a PIL Image. page_number is 1-indexed."""
    pages = convert_from_path(
        pdf_path,
        dpi=dpi,
        first_page=page_number,
        last_page=page_number,
    )
    return pages[0]


def find_pdfs(root: str = ".") -> list[str]:
    """Return all PDF paths under root, sorted alphabetically."""
    return sorted(str(p) for p in Path(root).rglob("*.pdf"))
