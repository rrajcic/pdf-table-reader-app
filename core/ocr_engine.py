import os
import sys
import tempfile

import pandas as pd
from img2table.document import Image as Img2TableImage
from img2table.ocr import TesseractOCR
from PIL import Image

_ocr: TesseractOCR | None = None


def _configure_tesseract() -> str | None:
    """
    Make a bundled tesseract usable inside a PyInstaller build.

    When frozen, PyInstaller sets ``sys._MEIPASS`` to the unpacked bundle dir;
    the packaging step places ``tesseract/`` (the exe + DLLs + tessdata) there.
    We prepend that dir to PATH so img2table's ``TesseractOCR`` — which resolves
    a bare ``tesseract`` command from a copy of ``os.environ`` — finds it, and
    return the tessdata dir to pass as ``tessdata_dir``.

    In normal dev runs there is no bundle, so this is a no-op and the system
    tesseract (e.g. Homebrew) on PATH is used unchanged.
    """
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        return None
    tess_dir = os.path.join(base, "tesseract")
    os.environ["PATH"] = tess_dir + os.pathsep + os.environ.get("PATH", "")
    return os.path.join(tess_dir, "tessdata")


def _clean_cell(val: object) -> str:
    """Normalise a raw OCR cell value for display."""
    s = str(val).strip()
    # Collapse embedded newlines to a single space (e.g. "87\n4680" → "87 4680")
    s = s.replace("\n", " ").replace("\r", " ")
    # Collapse runs of whitespace
    s = " ".join(s.split())
    return s


def _split_newline_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Split columns where cells contain embedded newlines into two columns."""
    parts = []
    for col in df.columns:
        series = df[col].astype(str)
        if series.str.contains('\n', regex=False).any():
            split = series.str.split('\n', n=1, expand=True)
            split.columns = [f"{col}_1", f"{col}_2"]
            parts.append(split)
        else:
            parts.append(df[[col]])
    return pd.concat(parts, axis=1) if parts else df


def _get_ocr() -> TesseractOCR:
    global _ocr
    if _ocr is None:
        _ocr = TesseractOCR(lang="eng", tessdata_dir=_configure_tesseract())
    return _ocr


def extract_table_from_region(
    image: Image.Image,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
) -> pd.DataFrame | None:
    """
    Crop image to the given bounding box and extract the table inside it.
    Returns a DataFrame, or None if no table is detected.
    """
    cropped = image.crop((x1, y1, x2, y2))

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
        cropped.save(tmp_path)

    try:
        ocr = _get_ocr()
        doc = Img2TableImage(src=tmp_path)
        tables = doc.extract_tables(
            ocr=ocr,
            implicit_rows=True,
            borderless_tables=True,
            min_confidence=40,
        )

        if not tables:
            return None

        # Return the largest table found by cell count
        largest = max(tables, key=lambda t: t.df.size)
        df = largest.df

        # Replace None with empty string, split stacked-value columns, then normalise cell text
        df = df.fillna("")
        df = _split_newline_columns(df)
        df = df.apply(lambda col: col.map(_clean_cell))
        # Normalise column names to strings so ag-Grid round-trips are stable
        df.columns = [str(c) for c in df.columns]
        return df

    finally:
        os.unlink(tmp_path)
