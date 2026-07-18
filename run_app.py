"""
Desktop launcher for PDF Table Reader.

This is the entry point PyInstaller compiles into the Windows ``.exe``. It boots
the Streamlit app headless and opens the user's browser once the server is ready,
so there is no terminal command to type and no config to set up by hand.

Run directly during development too:  ``python3 run_app.py``
"""

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.request import urlopen

PORT = 8501
URL = f"http://localhost:{PORT}"


def _resource(rel: str) -> str:
    """Resolve a bundled data file, whether frozen (PyInstaller) or in dev."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def _ensure_credentials() -> None:
    """
    Write an empty-email Streamlit credentials file if none exists, so the
    first-run email prompt never appears. Idempotent and silent.
    """
    cred = Path.home() / ".streamlit" / "credentials.toml"
    if cred.exists():
        return
    try:
        cred.parent.mkdir(parents=True, exist_ok=True)
        cred.write_text('[general]\nemail = ""\n')
    except OSError:
        # Non-fatal: headless mode already suppresses the prompt.
        pass


def _open_when_ready() -> None:
    """Poll Streamlit's real health endpoint, then open the browser once."""
    health = f"{URL}/_stcore/health"
    for _ in range(120):  # up to ~60s for a cold one-file exe to unpack + boot
        try:
            with urlopen(health, timeout=1) as resp:
                if resp.status == 200:
                    break
        except Exception:
            time.sleep(0.5)
    webbrowser.open(URL)


def _selftest() -> int:
    """
    Import the modules that are reachable only through app.py/core so a packaged
    build can prove it actually bundled them (PyInstaller can't see these via
    static analysis — see packaging/pdf_table_reader.spec). Used by CI:
    running the built exe with PDFTR_SELFTEST=1 must print "selftest OK".
    """
    import bs4  # noqa: F401
    import cv2  # noqa: F401
    import img2table  # noqa: F401
    import polars  # noqa: F401

    import core.ocr_engine  # noqa: F401
    import core.pdf_renderer  # noqa: F401

    print("selftest OK")
    return 0


def main() -> int:
    if os.environ.get("PDFTR_SELFTEST") == "1":
        return _selftest()
    _ensure_credentials()
    threading.Thread(target=_open_when_ready, daemon=True).start()

    sys.argv = [
        "streamlit",
        "run",
        _resource("app.py"),
        f"--server.port={PORT}",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
    ]
    import streamlit.web.cli as stcli

    return stcli.main()


if __name__ == "__main__":
    sys.exit(main())
