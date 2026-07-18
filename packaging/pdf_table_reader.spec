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

from PyInstaller.utils.hooks import collect_all, copy_metadata

datas = []
binaries = []
hiddenimports = []


def _collect(pkg):
    """collect_all a package, tolerating names that vary across versions."""
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
        datas.extend(pkg_datas)
        binaries.extend(pkg_binaries)
        hiddenimports.extend(pkg_hidden)
        return True
    except Exception:
        return False


# --- Packages reachable only through app.py / core/ ------------------------
# CRITICAL: PyInstaller analyses run_app.py, which imports only Streamlit.
# app.py and core/ are shipped as *data* (Streamlit runs app.py as a script),
# so their imports are invisible to static analysis. Every dependency reached
# only through them must be collected explicitly or it will be missing from the
# bundle and the app will crash the first time a table is extracted:
#   fitz (PyMuPDF)  -> core/pdf_renderer.py
#   img2table 2.x   -> core/ocr_engine.py  (pulls cv2, bs4, pypdfium2)
#   st_aggrid, streamlit_drawable_canvas -> app.py (also ship a JS frontend)
# Streamlit's own deps (pandas, numpy, PIL, pyarrow) arrive via the run_app.py
# import graph, but we collect a couple explicitly for safety.
for pkg in (
    "streamlit",
    "st_aggrid",
    "streamlit_drawable_canvas",
    "img2table",
    "cv2",
    "bs4",
    "pypdfium2",
    "PIL",
):
    _collect(pkg)

# PyMuPDF's importable name changed across versions ("fitz" and/or "pymupdf");
# collect whichever exist so binaries travel with the build.
if not any(_collect(name) for name in ("pymupdf", "fitz")):
    raise SystemExit("packaging: PyMuPDF (fitz/pymupdf) could not be collected.")

# --- Runtime version lookups (importlib.metadata) --------------------------
# Several libraries read their own dist metadata at import/runtime.
for pkg in ("streamlit", "img2table", "pandas", "numpy", "pyarrow", "PyMuPDF"):
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

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
