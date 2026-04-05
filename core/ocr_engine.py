import os
import tempfile

import pandas as pd
from img2table.document import Image as Img2TableImage
from img2table.ocr import TesseractOCR
from PIL import Image

_ocr: TesseractOCR | None = None


def _get_ocr() -> TesseractOCR:
    global _ocr
    if _ocr is None:
        _ocr = TesseractOCR(lang="eng")
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

        # Replace None with empty string for clean display
        df = df.fillna("")
        return df

    finally:
        os.unlink(tmp_path)
