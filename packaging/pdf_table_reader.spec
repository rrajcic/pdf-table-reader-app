# PyInstaller spec for PDF Table Reader (Windows one-file build).
#
# Build:  pyinstaller packaging/pdf_table_reader.spec
# Run from the repo root; the GitHub Actions Windows job does exactly that.
#
# Produces dist/PDFTableReader.exe — a single, self-contained executable that
# bundles Python, every dependency, the Streamlit frontend assets, and a full
# Tesseract install (exe + DLLs + eng traineddata). No system installs needed
# on the target machine.

import os

from PyInstaller.utils.hooks import collect_all, collect_data_files, copy_metadata

datas = []
binaries = []
hiddenimports = []

# --- Streamlit + custom components -----------------------------------------
# These ship a compiled frontend (static/ and frontend/build) plus package
# metadata that must travel with them, or the app 500s at runtime.
for pkg in ("streamlit", "st_aggrid", "streamlit_drawable_canvas"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

# --- Runtime version lookups (importlib.metadata) --------------------------
# Several libraries read their own dist metadata at import/runtime.
for pkg in ("streamlit", "img2table", "pandas", "numpy", "pyarrow", "PyMuPDF"):
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

# --- img2table bundled resources -------------------------------------------
datas += collect_data_files("img2table")

# --- Application source -----------------------------------------------------
# app.py is executed as a script by Streamlit (not imported), so it and the
# core/ package are shipped as data and resolved via sys._MEIPASS at runtime.
datas += [("app.py", "."), ("core", "core")]

# --- Bundled Tesseract ------------------------------------------------------
# CI copies "C:\Program Files\Tesseract-OCR" to ./tesseract before building.
# core/ocr_engine.py:_configure_tesseract() adds <bundle>/tesseract to PATH and
# points TESSDATA_PREFIX at <bundle>/tesseract/tessdata.
if os.path.isdir("tesseract"):
    datas += [("tesseract", "tesseract")]
else:
    raise SystemExit(
        "packaging: ./tesseract not found. The CI 'Stage Tesseract' step must "
        "copy C:\\Program Files\\Tesseract-OCR to ./tesseract before building."
    )

# Streamlit's dynamic imports that PyInstaller's static analysis can miss.
hiddenimports += [
    "streamlit_drawable_canvas",
    "st_aggrid",
    "streamlit.runtime.scriptrunner.magic_funcs",
]


a = Analysis(
    ["run_app.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PDFTableReader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,  # keep the console: Streamlit/deps write to stdout, and it
                   # gives the user feedback during the one-file cold start.
    disable_windowed_traceback=False,
    icon=None,
)
