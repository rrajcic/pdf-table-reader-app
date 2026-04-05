# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
# First-time setup (macOS)
brew install poppler tesseract
pip install -r requirements.txt

# Launch
python3 -m streamlit run app.py
```

App runs at http://localhost:8501.

## Project structure

```
app.py                  # Streamlit UI — all page layout and interaction logic
core/
  pdf_renderer.py       # PDF → PIL Image (pdf2image), page count (pypdf), PDF discovery
  ocr_engine.py         # Crop image region → run img2table + TesseractOCR → DataFrame
  session_manager.py    # JSON session: tracks extractions (pdf, page, bbox, csv path)
output/                 # Generated CSVs land here
sessions/               # Session JSON files (auto-saved after each extraction)
testing/                # Sample single-page PDFs for development
```

## Architecture

The app is entirely local — no server, no cloud, no auth.

**Data flow:** PDF file → render page to PIL Image (200 DPI) → display in `streamlit-drawable-canvas` → user draws bounding box → crop to box → `img2table` + Tesseract OCR → `pd.DataFrame` → `st.data_editor` (user edits) → CSV export.

**State:** Managed via `st.session_state`. Page images are cached in `st.session_state.page_cache` (dict keyed by page number) to avoid re-rendering on every interaction.

**Session JSON** is auto-saved to `sessions/` on every `add_extraction()` call once a save path is established. It serves as a manifest mapping each CSV to its source PDF + page + bbox.

## Key technical notes

- The test PDFs are image-based (single embedded PNG per page), not text PDFs. Camelot/tabula will not work on them — the pipeline must go through OCR.
- `img2table` is used for table structure detection (row/column grid), not just raw OCR. It returns the largest detected table from the cropped region.
- Canvas coordinates must be scaled back to image coordinates: `scale = img_width / DISPLAY_WIDTH`.
- The canvas key is `f"canvas_p{page_number}"` — changing page resets the canvas automatically.
- Streamlit first-run email prompt must be bypassed: `~/.streamlit/credentials.toml` with `email = ""`.
