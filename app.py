from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_drawable_canvas import st_canvas

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
def _init():
    defaults: dict = {
        "pdf_path": None,
        "page_count": 0,
        "current_page": 1,
        "page_cache": {},   # page_number -> PIL Image
        "extracted_df": None,
        "last_bbox": None,
        "session": SessionManager(),
        "status_msg": None,   # ("success"|"error", text)
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
    st.session_state.current_page = n
    st.session_state.extracted_df = None
    st.session_state.last_bbox = None


def get_page_image(pdf_path: str, page_num: int):
    if page_num not in st.session_state.page_cache:
        with st.spinner(f"Rendering page {page_num}…"):
            st.session_state.page_cache[page_num] = render_page(pdf_path, page_num)
    return st.session_state.page_cache[page_num]


def safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_ " else "_" for c in name).strip().replace(" ", "_")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("📋 PDF Table Reader")
    st.divider()

    # --- PDF selector ---
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
        st.caption("No PDF files found in project folder.")

    st.divider()

    # --- Session panel ---
    st.subheader("Session")

    session: SessionManager = st.session_state.session
    extractions = session.extractions

    if extractions:
        st.caption(f"{len(extractions)} table(s) saved this session")
        for ex in extractions:
            with st.expander(f"p.{ex['page_number']} — {ex['table_name']}", expanded=False):
                st.caption(f"CSV: `{Path(ex['csv_path']).name}`")
                if ex.get("notes"):
                    st.caption(ex["notes"])
    else:
        st.caption("No tables saved yet.")

    st.divider()

    # --- Load a previous session ---
    session_files = sorted(SESSIONS_DIR.glob("*.json"), reverse=True)
    if session_files:
        st.subheader("Resume session")
        to_load = st.selectbox(
            "Load",
            ["—"] + [f.name for f in session_files],
            label_visibility="collapsed",
        )
        if to_load != "—":
            loaded = SessionManager.load(SESSIONS_DIR / to_load)
            st.session_state.session = loaded
            st.success(f"Loaded — {len(loaded.extractions)} extraction(s)")


# ---------------------------------------------------------------------------
# Main — no PDF loaded
# ---------------------------------------------------------------------------
if not st.session_state.pdf_path:
    st.markdown("## Welcome to PDF Table Reader")
    st.info("Select a PDF from the sidebar to get started.")
    st.stop()


# ---------------------------------------------------------------------------
# Page navigation bar
# ---------------------------------------------------------------------------
pdf_name = Path(st.session_state.pdf_path).name
total = st.session_state.page_count
cur = st.session_state.current_page

st.markdown(f"### {pdf_name}")

nav1, nav2, nav3, nav4, nav5 = st.columns([1, 1, 2, 1, 3])

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
    if jump != cur:
        go_to_page(int(jump))
        st.rerun()

with nav4:
    st.markdown(f"**{cur}** / {total}")

# Show which pages have already been extracted in this session
extracted_pages = {ex["page_number"] for ex in session.extractions}
if extracted_pages:
    done_str = ", ".join(str(p) for p in sorted(extracted_pages))
    with nav5:
        st.caption(f"✅ Done: p.{done_str}")

st.divider()

# ---------------------------------------------------------------------------
# Main two-column layout
# ---------------------------------------------------------------------------
page_image = get_page_image(st.session_state.pdf_path, cur)
img_w, img_h = page_image.size
display_h = int(img_h * DISPLAY_WIDTH / img_w)

col_left, col_right = st.columns([1.05, 1], gap="large")

# ---- LEFT: PDF canvas ----
with col_left:
    st.subheader(f"Page {cur}")
    st.caption("Draw a rectangle around the table you want to extract.")

    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.2)",
        stroke_width=2,
        stroke_color="#e74c3c",
        background_image=page_image,
        update_streamlit=True,
        height=display_h,
        width=DISPLAY_WIDTH,
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
        obj = objects[-1]  # use the last drawn rectangle
        scale_x = img_w / DISPLAY_WIDTH
        scale_y = img_h / display_h
        x1 = max(0, int(obj["left"] * scale_x))
        y1 = max(0, int(obj["top"] * scale_y))
        x2 = min(img_w, int((obj["left"] + obj["width"]) * scale_x))
        y2 = min(img_h, int((obj["top"] + obj["height"]) * scale_y))

        with st.spinner("Running OCR…"):
            df = extract_table_from_region(page_image, x1, y1, x2, y2)

        if df is not None and not df.empty:
            st.session_state.extracted_df = df
            st.session_state.last_bbox = (x1, y1, x2, y2)
            st.session_state.status_msg = None
        else:
            st.session_state.status_msg = (
                "error",
                "No table detected in the selected region. Try a larger or more precise selection.",
            )
        st.rerun()

    if st.session_state.status_msg and st.session_state.status_msg[0] == "error":
        st.error(st.session_state.status_msg[1])

# ---- RIGHT: Data editor + save ----
with col_right:
    st.subheader("Extracted Table")

    if st.session_state.extracted_df is None:
        st.info(
            "Draw a rectangle around a table on the left, then click **Extract Table**."
        )
    else:
        df: pd.DataFrame = st.session_state.extracted_df

        # Metadata
        table_name = st.text_input(
            "Table name *",
            placeholder="e.g. Takeoff Performance – 16300 lbs",
            key=f"tname_p{cur}",
        )
        notes = st.text_area(
            "Notes",
            placeholder="Optional: source context, units, caveats…",
            height=72,
            key=f"notes_p{cur}",
        )

        st.caption(
            f"Extracted {df.shape[0]} rows × {df.shape[1]} columns. "
            "Click any cell to edit."
        )

        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic",
            height=380,
            key=f"editor_p{cur}",
        )

        btn_col1, btn_col2 = st.columns([1, 1])

        with btn_col1:
            if st.button("💾 Save as CSV", type="primary", use_container_width=True):
                if not table_name.strip():
                    st.error("Enter a table name before saving.")
                else:
                    fname = f"{safe_filename(table_name)}_p{cur}.csv"
                    csv_path = OUTPUT_DIR / fname
                    # Handle duplicate filenames
                    counter = 1
                    while csv_path.exists():
                        csv_path = OUTPUT_DIR / f"{safe_filename(table_name)}_p{cur}_{counter}.csv"
                        counter += 1

                    edited_df.to_csv(csv_path, index=False)

                    # Record in session (auto-saves session JSON)
                    session.save(SESSIONS_DIR)  # ensure save path is initialised
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
                    st.session_state.status_msg = ("success", f"Saved → `{csv_path}`")
                    st.rerun()

        with btn_col2:
            if st.button("✕ Discard", use_container_width=True):
                st.session_state.extracted_df = None
                st.session_state.last_bbox = None
                st.rerun()

    # Show success banner outside the else block so it persists after save
    if (
        st.session_state.status_msg
        and st.session_state.status_msg[0] == "success"
    ):
        st.success(st.session_state.status_msg[1])
