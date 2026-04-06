import json
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_drawable_canvas import st_canvas

from core.highlighter import issue_summary, make_styler
from core.ocr_engine import extract_table_from_region
from core.pdf_renderer import find_pdfs, get_page_count, render_page
from core.session_manager import SessionManager

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="PDF Table Reader",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

DISPLAY_WIDTH = 720
OUTPUT_DIR = Path("output")
SESSIONS_DIR = Path("sessions")

OUTPUT_DIR.mkdir(exist_ok=True)
SESSIONS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
def _init() -> None:
    defaults: dict = {
        "pdf_path": None,
        "page_count": 0,
        "current_page": 1,
        "page_cache": {},       # page_number -> PIL Image
        "extracted_df": None,
        "last_bbox": None,
        "session": SessionManager(),
        "flash": None,          # ("success"|"error"|"info", message)
        "right_panel_open": True,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_pdf(path: str) -> None:
    st.session_state.pdf_path = path
    st.session_state.page_count = get_page_count(path)
    st.session_state.current_page = 1
    st.session_state.page_cache = {}
    st.session_state.extracted_df = None
    st.session_state.last_bbox = None


def go_to_page(n: int) -> None:
    st.session_state.current_page = int(n)
    st.session_state.extracted_df = None
    st.session_state.last_bbox = None


def get_page_image(pdf_path: str, page_num: int):
    if page_num not in st.session_state.page_cache:
        with st.spinner(f"Rendering page {page_num}…"):
            st.session_state.page_cache[page_num] = render_page(pdf_path, page_num)
    return st.session_state.page_cache[page_num]


def safe_filename(name: str) -> str:
    return (
        "".join(c if c.isalnum() or c in "-_ " else "_" for c in name)
        .strip()
        .replace(" ", "_")
    )


def unique_csv_path(name: str, page: int) -> Path:
    base = OUTPUT_DIR / f"{safe_filename(name)}_p{page}.csv"
    if not base.exists():
        return base
    counter = 1
    while True:
        candidate = OUTPUT_DIR / f"{safe_filename(name)}_p{page}_{counter}.csv"
        if not candidate.exists():
            return candidate
        counter += 1


def _session_preview(path: Path) -> tuple[int, str]:
    """Return (n_extractions, created_date_str) without raising."""
    try:
        with open(path) as f:
            data = json.load(f)
        n = len(data.get("extractions", []))
        date = data.get("created", "")[:10]
        return n, date
    except Exception:
        return 0, ""


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("📋 PDF Table Reader")
    st.divider()

    # ── PDF selector ──────────────────────────────────────────────────────
    st.subheader("Load PDF")
    pdf_files = find_pdfs(".")
    if pdf_files:
        options = ["— select a PDF —"] + pdf_files
        current_idx = 0
        if st.session_state.pdf_path in pdf_files:
            current_idx = pdf_files.index(st.session_state.pdf_path) + 1

        selected = st.selectbox(
            "PDF file",
            options,
            index=current_idx,
            label_visibility="collapsed",
        )
        if selected != "— select a PDF —" and selected != st.session_state.pdf_path:
            load_pdf(selected)
            st.rerun()
    else:
        st.caption("No PDF files found in the project folder.")

    st.divider()

    # ── Current session ───────────────────────────────────────────────────
    session: SessionManager = st.session_state.session
    extractions = session.extractions

    st.subheader("Current Session")
    if extractions:
        for ex in extractions:
            c1, c2 = st.columns([5, 1])
            with c1:
                st.caption(f"**p.{ex['page_number']}** — {ex['table_name']}")
            with c2:
                if st.button(
                    "↗",
                    key=f"go_{ex['id']}",
                    help=f"Jump to page {ex['page_number']}",
                ):
                    target = ex["pdf_path"]
                    if st.session_state.pdf_path != target and Path(target).exists():
                        load_pdf(target)
                    go_to_page(ex["page_number"])
                    st.rerun()
    else:
        st.caption("No tables saved yet.")

    st.divider()

    # ── Past sessions ─────────────────────────────────────────────────────
    session_files = sorted(SESSIONS_DIR.glob("*.json"), reverse=True)
    if session_files:
        st.subheader("Past Sessions")
        for sf in session_files[:8]:
            n, date = _session_preview(sf)
            label = f"{sf.stem}"
            with st.expander(f"{label}  ({n} tables)"):
                if date:
                    st.caption(f"Created: {date}")
                # Show first few entries as a preview
                try:
                    with open(sf) as f:
                        data = json.load(f)
                    for ex in data.get("extractions", [])[:4]:
                        st.caption(f"• p.{ex['page_number']}: {ex['table_name']}")
                    if n > 4:
                        st.caption(f"… and {n - 4} more")
                except Exception:
                    pass

                if st.button("Load this session", key=f"load_{sf.name}"):
                    loaded = SessionManager.load(sf)
                    st.session_state.session = loaded
                    # Restore PDF if the file still exists
                    if loaded.extractions:
                        last_pdf = loaded.extractions[-1]["pdf_path"]
                        if Path(last_pdf).exists():
                            load_pdf(last_pdf)
                    st.rerun()


# ---------------------------------------------------------------------------
# Main — no PDF loaded
# ---------------------------------------------------------------------------
if not st.session_state.pdf_path:
    st.markdown("## Welcome to PDF Table Reader")
    st.info(
        "Select a PDF from the sidebar to get started.  \n"
        "All PDFs in the project folder are listed automatically."
    )
    st.stop()


# ---------------------------------------------------------------------------
# Page navigation bar
# ---------------------------------------------------------------------------
pdf_name = Path(st.session_state.pdf_path).name
total = st.session_state.page_count
cur = st.session_state.current_page

st.markdown(f"### {pdf_name}")

nav1, nav2, nav3, nav4, nav5, nav6 = st.columns([1, 1, 2, 1, 2, 1])

with nav1:
    if st.button("◀ Prev", disabled=(cur <= 1)):
        go_to_page(cur - 1)
        st.rerun()

with nav2:
    if st.button("Next ▶", disabled=(cur >= total)):
        go_to_page(cur + 1)
        st.rerun()

with nav3:
    jump = st.number_input(
        "Go to page",
        min_value=1,
        max_value=total,
        value=cur,
        step=1,
        label_visibility="collapsed",
        key="page_jump",
    )
    if int(jump) != cur:
        go_to_page(int(jump))
        st.rerun()

with nav4:
    st.markdown(f"**{cur}** / {total}")

extracted_pages = {ex["page_number"] for ex in session.extractions}
if extracted_pages:
    with nav5:
        done_str = ", ".join(str(p) for p in sorted(extracted_pages))
        st.caption(f"✅ Done: p.{done_str}")

panel_open = st.session_state.right_panel_open
with nav6:
    label = "▶ Table" if not panel_open else "◀ Hide"
    if st.button(label, key="toggle_panel"):
        st.session_state.right_panel_open = not panel_open
        st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# Main layout — right panel is collapsible
# ---------------------------------------------------------------------------
page_image = get_page_image(st.session_state.pdf_path, cur)
img_w, img_h = page_image.size

if panel_open:
    col_left, col_right = st.columns([1.05, 1], gap="large")
else:
    col_left = st.columns([1])[0]

# ═══════════════════════════════════════════════════════════════════════════
# LEFT: PDF canvas
# ═══════════════════════════════════════════════════════════════════════════
with col_left:
    st.subheader(f"Page {cur}")
    st.caption("Draw a rectangle around a table, then click **Extract Table**.")

    display_width = DISPLAY_WIDTH
    display_height = int(img_h * display_width / img_w)

    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.2)",
        stroke_width=2,
        stroke_color="#e74c3c",
        background_image=page_image,
        update_streamlit=True,
        height=display_height,
        width=display_width,
        drawing_mode="rect",
        key=f"canvas_p{cur}",
    )

    objects = (canvas_result.json_data or {}).get("objects", [])
    has_selection = len(objects) > 0

    if st.button(
        "Extract Table",
        type="primary",
        disabled=not has_selection,
        use_container_width=True,
    ):
        obj = objects[-1]
        scale_x = img_w / display_width
        scale_y = img_h / display_height
        x1 = max(0, int(obj["left"] * scale_x))
        y1 = max(0, int(obj["top"] * scale_y))
        x2 = min(img_w, int((obj["left"] + obj["width"]) * scale_x))
        y2 = min(img_h, int((obj["top"] + obj["height"]) * scale_y))

        with st.spinner("Running OCR…"):
            df = extract_table_from_region(page_image, x1, y1, x2, y2)

        if df is not None and not df.empty:
            st.session_state.extracted_df = df
            st.session_state.last_bbox = (x1, y1, x2, y2)
            st.session_state.flash = None
        else:
            st.session_state.flash = (
                "error",
                "No table detected in the selected region. "
                "Try a larger or more precise selection.",
            )
        st.rerun()

    flash = st.session_state.flash
    if flash and flash[0] == "error":
        st.error(flash[1])


# ═══════════════════════════════════════════════════════════════════════════
# RIGHT: Data editor (collapsible)
# ═══════════════════════════════════════════════════════════════════════════
if not panel_open:
    st.stop()

with col_right:
    st.subheader("Extracted Table")

    if st.session_state.extracted_df is None:
        st.info(
            "Draw a rectangle around a table on the left, "
            "then click **Extract Table**."
        )
        # Show success flash even when no df is loaded (post-save state)
        if flash and flash[0] == "success":
            st.success(flash[1])
    else:
        df: pd.DataFrame = st.session_state.extracted_df

        # ── Metadata ──────────────────────────────────────────────────────
        table_name = st.text_input(
            "Table name *(required to save)*",
            placeholder="e.g. Takeoff Performance – 16300 lbs",
            key=f"tname_p{cur}",
        )
        notes = st.text_area(
            "Notes",
            placeholder="Optional: source context, units, caveats…",
            height=68,
            key=f"notes_p{cur}",
        )

        # ── Issue summary banner ───────────────────────────────────────────
        summary = issue_summary(df)
        if summary:
            st.warning(f"⚠️ Issues detected: {summary}")

        # ── Tabs: Review (highlighted) / Edit & Save ───────────────────────
        tab_review, tab_edit = st.tabs(["🔍 Review", "✏️ Edit & Save"])

        with tab_review:
            st.caption(
                "🔴 Red = OCR artifact character (e.g. `)`  or em-dash).  "
                "🟡 Amber = blank cell in a column that has other values."
            )
            st.dataframe(
                make_styler(df),
                use_container_width=True,
                height=400,
            )

        with tab_edit:
            st.caption(
                f"{df.shape[0]} rows × {df.shape[1]} cols — click any cell to edit."
            )
            edited_df = st.data_editor(
                df,
                use_container_width=True,
                num_rows="dynamic",
                height=360,
                key=f"editor_p{cur}",
            )

            st.divider()

            btn1, btn2 = st.columns([1, 1])

            with btn1:
                if st.button(
                    "💾 Save as CSV", type="primary", use_container_width=True
                ):
                    if not table_name.strip():
                        st.error("Enter a table name before saving.")
                    else:
                        csv_path = unique_csv_path(table_name.strip(), cur)
                        edited_df.to_csv(csv_path, index=False)

                        session.save(SESSIONS_DIR)
                        session.add_extraction(
                            pdf_path=st.session_state.pdf_path,
                            page_number=cur,
                            table_name=table_name.strip(),
                            notes=notes.strip(),
                            csv_path=str(csv_path),
                            bbox=st.session_state.last_bbox,
                        )

                        st.session_state.extracted_df = None
                        st.session_state.last_bbox = None
                        st.session_state.flash = (
                            "success",
                            f"Saved → `{csv_path}`",
                        )
                        st.rerun()

            with btn2:
                if st.button("✕ Discard", use_container_width=True):
                    st.session_state.extracted_df = None
                    st.session_state.last_bbox = None
                    st.session_state.flash = None
                    st.rerun()

        # Show success flash while df is still displayed (shouldn't normally
        # happen, but guard against it)
        if flash and flash[0] == "success":
            st.success(flash[1])
