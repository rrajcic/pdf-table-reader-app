# PLAN — Ship PDF Table Reader as a one-click Windows app

**Goal:** Let a non-technical user (no terminal, no Python, no PATH setup) download a single
file from the repo's Releases page, double-click it, and use the app — while keeping the
original design intent: everything runs locally, nothing is uploaded.

**Diagnosis of what blocked the original install:** the app depends on two *native binaries*
(`poppler`, `tesseract`) that must be installed separately and added to the Windows PATH by
hand. That's the wall. The Streamlit frontend is **not** the problem, so we are **not**
switching frameworks. We remove the native-binary friction, then bundle everything into one
`.exe`.

**Hard constraint:** A Windows `.exe` cannot be built on macOS. The build runs in **GitHub
Actions on a Windows runner** and publishes the `.exe` to the repo's **Releases** page. No
Windows machine is needed on the dev side.

**Accepted caveats:**
1. An unsigned `.exe` triggers a one-time SmartScreen warning ("More info → Run anyway").
   Free fix = document it with a screenshot. Paid fix (code-signing cert) is out of scope.
2. Final end-to-end validation happens on Windows (CI smoke test + a real Windows machine),
   not on the Mac.

---

## Workflow for every phase

After completing each phase:
1. Commit the phase's changes on a dedicated branch (`phase-1-native-deps`,
   `phase-2-launcher`, `phase-3-packaging`).
2. Open a PR against `main`.
3. Run a code-review on the PR (`/code-review`) and address findings.
4. Merge once the review is clean, then start the next phase from updated `main`.

---

## Phase 1 — Remove native-binary dependencies

**Status:** ☑ Done — verified on macOS; PR + code-review pending merge.
**Testable entirely on macOS. Lowest risk, highest value — this is the actual unblocker.**

### Tasks
- [x] **1.1 Swap PDF rendering to PyMuPDF.** Rewrite `core/pdf_renderer.py` to use `fitz`
      (PyMuPDF) for both `render_page()` and `get_page_count()`, removing `pdf2image`+`poppler`
      and `pypdf`. `find_pdfs()` is pure `pathlib` — unchanged.
      ```python
      import fitz
      from PIL import Image

      def get_page_count(pdf_path: str) -> int:
          with fitz.open(pdf_path) as doc:
              return doc.page_count

      def render_page(pdf_path: str, page_number: int, dpi: int = 200) -> Image.Image:
          with fitz.open(pdf_path) as doc:
              page = doc.load_page(page_number - 1)          # fitz is 0-indexed
              pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
              return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
      ```
- [x] **1.2 Make tesseract bundle-aware.** Add a runtime resolver to `core/ocr_engine.py`.
      `img2table`'s `TesseractOCR` resolves a bare `tesseract` command from `PATH` (a copy of
      `os.environ` taken at init) and accepts `tessdata_dir`. So no patching of `img2table` is
      needed — just prepend the bundled binary dir to `PATH` and pass `tessdata_dir`. On the
      Mac this is a no-op (falls back to Homebrew tesseract).
      ```python
      import sys, os

      def _bundle_dir():
          return getattr(sys, "_MEIPASS", None)   # set by PyInstaller; None in dev

      def _configure_tesseract():
          base = _bundle_dir()
          if base is None:
              return None                          # dev: system tesseract on PATH
          tess_dir = os.path.join(base, "tesseract")
          os.environ["PATH"] = tess_dir + os.pathsep + os.environ.get("PATH", "")
          return os.path.join(tess_dir, "tessdata")

      def _get_ocr():
          global _ocr
          if _ocr is None:
              _ocr = TesseractOCR(lang="eng", tessdata_dir=_configure_tesseract())
          return _ocr
      ```
- [x] **1.3 Trim `requirements.txt`.** Remove `pdf2image`, `pypdf`, `pytesseract`,
      `python-decouple` (all confirmed unused after 1.1/1.2). Add `PyMuPDF>=1.24.0`. Keep the
      `streamlit>=1.32,<1.44` pin (required by `streamlit-drawable-canvas` 0.9.3).

### Verification (macOS)
- [x] Render `sample_document.pdf` p.1 with the new code; 1700×2200 RGB — matches old 200-DPI output.
- [x] Run a full `extract_table_from_region()` on a known bbox (p.12); 21×28 DataFrame with the
      usual OCR artifacts — pipeline unchanged.
- [x] App boots headless; `/_stcore/health` returns 200, no import regressions.

### Then
- [ ] PR `phase-1-native-deps` → code-review → merge.

**Risk:** Low. Only the render path changes; OCR output is identical.

---

## Phase 2 — Make it launch like an app

**Status:** ☐ Not started
**Goal:** Double-click → app opens in browser. No terminal, no `credentials.toml` step.

### Tasks
- [ ] **2.1 Launcher entry point.** New `run_app.py` at repo root — the script PyInstaller
      compiles into the `.exe`. Boots Streamlit headless and opens the browser itself once the
      server's real health endpoint responds (reliable for a slow-starting one-file exe).
      ```python
      import os, sys, threading, time, webbrowser
      from urllib.request import urlopen

      def _resource(rel):
          return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(__file__)), rel)

      def _open_when_ready(url):
          for _ in range(60):
              try:
                  urlopen(url + "/_stcore/health", timeout=1); break
              except Exception:
                  time.sleep(0.5)
          webbrowser.open(url)

      if __name__ == "__main__":
          url = "http://localhost:8501"
          threading.Thread(target=_open_when_ready, args=(url,), daemon=True).start()
          sys.argv = ["streamlit", "run", _resource("app.py"),
                      "--server.port=8501", "--server.headless=true",
                      "--browser.gatherUsageStats=false"]
          import streamlit.web.cli as stcli
          sys.exit(stcli.main())
      ```
- [ ] **2.2 Kill the email prompt permanently.** Bundle a `.streamlit/config.toml`
      (`[browser] gatherUsageStats=false`, `[server] headless=true`) AND have the launcher write
      an empty-email `~/.streamlit/credentials.toml` on first run if absent (idempotent). Headless
      mode already suppresses the prompt; this is belt-and-suspenders so the manual setup step
      disappears.

### Verification (macOS)
- [ ] Run `python3 run_app.py` (not `streamlit run`); confirm it boots, opens the browser at the
      right moment, and works end-to-end.

### Then
- [ ] PR `phase-2-launcher` → code-review → merge.

**Risk:** Low–medium. Well-trodden pattern; main thing to confirm is health-poll timing.

---

## Phase 3 — Package + deliver

**Status:** ☐ Not started
**Goal:** A single `.exe` on the Releases page. Fiddliest phase (Streamlit + PyInstaller) —
budget for CI iteration.

### Tasks
- [ ] **3.1 PyInstaller spec** — new `packaging/pdf_table_reader.spec`. Must explicitly include
      what PyInstaller can't auto-discover:
      - `collect_all("streamlit")`, `collect_all("st_aggrid")`,
        `collect_all("streamlit_drawable_canvas")` — these ship frontend build assets + metadata.
      - `copy_metadata` for `streamlit` (reads its own version at runtime); collect data for
        `img2table`, `cv2`/opencv, `polars`, `bs4` as needed.
      - **datas:** `app.py`, the `core/` package, `.streamlit/config.toml`, and the `tesseract/`
        folder (exe + DLLs + `tessdata/eng.traineddata`).
      - `--onefile` for clean download-and-double-click UX, plus a PyInstaller **splash screen**
        to cover the 10–30s cold-start. (If onefile fights us, debug with `--onedir` first, then
        flip back.)
      - Expected size ~300–500 MB (opencv + pyarrow are the weight; **no** PyTorch, since we kept
        tesseract rather than swapping to a neural OCR).
- [ ] **3.2 GitHub Actions workflow** — new `.github/workflows/build-windows.yml`.
      - Triggers: `workflow_dispatch` (manual test) + push of tag `v*` (real release).
      - `runs-on: windows-latest`. Steps:
        1. Checkout + `setup-python@v5` (3.12).
        2. `choco install tesseract -y`, then copy `C:\Program Files\Tesseract-OCR` → `./tesseract/`
           so the spec bundles it (exe + all DLLs + eng data).
        3. `pip install -r requirements.txt pyinstaller`.
        4. `pyinstaller packaging/pdf_table_reader.spec`.
        5. **Smoke test:** launch the built exe, poll `http://localhost:8501/_stcore/health` until
           200 (or timeout), then kill — proves it boots as a packaged app.
        6. `upload-artifact` on manual runs; on a tag, `softprops/action-gh-release` attaches the
           `.exe` to a GitHub Release.
- [ ] **3.3 README for the end user** — add a "**Download & Run (Windows)**" section at the very
      top: Releases → download `PDFTableReader.exe` → double-click; screenshot of the SmartScreen
      "More info → Run anyway" step; "app opens in your browser; close the browser tab and the
      black window to quit." Move the existing dev instructions down under "Build from source."
- [ ] **3.4 Document the release process** — `git tag v1.0.0 && git push origin v1.0.0` → CI
      builds + publishes. Test with a manual `workflow_dispatch` run first (downloadable artifact)
      before cutting a real tag.

### Verification
- [ ] CI smoke test passes (exe boots, health endpoint responds).
- [ ] Manual `workflow_dispatch` artifact runs end-to-end on a real Windows machine.
- [ ] Tagged release produces a downloadable `.exe` on the Releases page.

### Then
- [ ] PR `phase-3-packaging` → code-review → merge, then cut the first tagged release.

**Risks & mitigations:**
- *Streamlit + PyInstaller quirks* (highest risk): iterate in CI; onedir-debug fallback.
- *Missing tesseract DLLs*: copy the whole `Tesseract-OCR` dir, not just the exe.
- *SmartScreen*: accepted caveat; handled with a README screenshot.
- *CI can't fully drive the GUI*: health-endpoint smoke test covers "does it boot"; true
  end-to-end is a real Windows machine.

---

## Sequencing
Phase 1 → 2 are independent and testable on macOS. Phase 3 depends on both. Land and verify
Phase 1 first (the actual unblocker, lowest risk), then Phase 2, then grind through Phase 3 in
CI. One PR + code-review per phase.
