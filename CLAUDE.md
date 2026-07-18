# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
# First-time setup (macOS)
brew install poppler tesseract
pip install -r requirements.txt

# One-time: skip Streamlit's first-run email prompt
mkdir -p ~/.streamlit && printf '[general]\nemail = ""\n' > ~/.streamlit/credentials.toml

# Launch
python3 -m streamlit run app.py
```

App runs at http://localhost:8501. There is no test suite, linter, or build step configured in this repo.

To try the app, drop any PDF into the project root (or use `sample_document.pdf` /
`examples/`) — `find_pdfs()` in `core/pdf_renderer.py` lists every `*.pdf` under the
project root in the sidebar.

## Project structure

```
app.py                  # Streamlit UI — all page layout and interaction logic (single file)
core/
  pdf_renderer.py        # PDF → PIL Image (pdf2image), page count (pypdf), PDF discovery
  ocr_engine.py           # Crop image region → img2table + TesseractOCR → cleaned DataFrame
  highlighter.py          # Detect OCR-artifact/blank cells; pandas Styler (Review tab only)
  session_manager.py      # JSON session: tracks extractions (pdf, page, bbox, csv path)
output/                  # Generated CSVs land here
sessions/                # Session JSON files (auto-saved after each extraction)
examples/                # Sample source files (image + spreadsheet) for reference
```

## Architecture

The app is entirely local — no server, no cloud, no auth. `app.py` is a single
top-to-bottom Streamlit script; there's no routing or component layer beyond the
`core/` modules.

**Data flow:** PDF file → render page to PIL Image at 200 DPI (`pdf_renderer.render_page`)
→ display in `streamlit-drawable-canvas` → user draws a bounding box → canvas coords
scaled to image coords → crop → `img2table` + Tesseract OCR
(`ocr_engine.extract_table_from_region`) → cleaned `pd.DataFrame` → editable
`st_aggrid.AgGrid` grid → CSV export.

**Editable grid (ag-Grid, not `st.data_editor`):** The extracted table is rendered with
`streamlit-aggrid`. A hidden `_row_id` column is injected so row deletion survives
sorting/edits. Cell-level highlighting (red = OCR-artifact chars `) ( — – |`, amber =
likely-missing value in an otherwise populated column) is computed **in JS** via a
`cellStyle` `JsCode` callback baked into `gb.configure_column(...)` per column, so
highlights update live as the user types without a Python rerun. `core/highlighter.py`
implements the equivalent logic in Python but is only used for the read-only
`issue_summary()` banner text — keep the two in sync if the artifact-char set changes.
The grid is force-remounted (new `key=f"aggrid_p{cur}_v{st.session_state.aggrid_recheck}"`)
by the "↺ Recheck" button and by "✦ Clean" (which strips artifact chars from every cell).

**State:** Managed via `st.session_state`. Page images are cached in
`st.session_state.page_cache` (dict keyed by page number) to avoid re-rendering on every
interaction. Switching PDFs or pages clears `extracted_df`/`last_bbox`.

**Session JSON** is auto-saved to `sessions/` on every `add_extraction()` call once a
save path is established (`SessionManager.save()`/`_write()`). It serves as a manifest
mapping each CSV to its source PDF + page + bbox, and the sidebar's "Past Sessions"
list reads these files back for preview/reload.

## Key technical notes

- Source PDFs are typically image-based (single embedded image per page), not text
  PDFs — Camelot/tabula will not work; the pipeline must go through OCR.
- `img2table` is used for table structure detection (row/column grid), not just raw
  OCR. `extract_table_from_region` returns the largest detected table by cell count
  from the cropped region, or `None` if nothing is found.
- OCR cleanup in `ocr_engine.py`: cells with embedded newlines get split into two
  columns (`_split_newline_columns`), then all cell text is normalized
  (`_clean_cell` — collapse newlines/whitespace).
- Canvas coordinates must be scaled back to image coordinates:
  `scale = img_width / DISPLAY_WIDTH` (`DISPLAY_WIDTH = 720` in `app.py`).
- The canvas key is `f"canvas_p{page_number}"` — changing page resets the canvas
  automatically. The ag-Grid key is versioned per-page (`aggrid_p{cur}_v{...}`) so
  page changes and Recheck/Clean both force a clean remount.
