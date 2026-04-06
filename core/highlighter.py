"""
Cell-level issue detection and pandas Styler generation for the review view.

Flags two categories:
  - bad_chars  (red)   : cells containing OCR-artifact characters: ) ( — – |
  - missing    (amber) : blank cells in columns that have at least 2 non-blank values
"""

from __future__ import annotations

import pandas as pd

_BAD_CHARS = {")", "(", "—", "–", "|"}
_BLANK = {"", "nan", "None"}


def _is_blank(val: str) -> bool:
    return val.strip() in _BLANK


def get_issue_cells(df: pd.DataFrame) -> dict[str, set[tuple[int, int]]]:
    """
    Returns {'bad_chars': {(row, col), ...}, 'missing': {(row, col), ...}}.
    Row and col are integer positional indices.
    """
    bad_chars: set[tuple[int, int]] = set()
    missing: set[tuple[int, int]] = set()

    for col_idx in range(len(df.columns)):
        col_vals = [str(df.iloc[r, col_idx]) for r in range(len(df))]
        n_non_blank = sum(1 for v in col_vals if not _is_blank(v))

        for row_idx, val in enumerate(col_vals):
            if _is_blank(val):
                if n_non_blank >= 2:
                    missing.add((row_idx, col_idx))
            else:
                if any(c in val for c in _BAD_CHARS):
                    bad_chars.add((row_idx, col_idx))

    return {"bad_chars": bad_chars, "missing": missing}


def make_styler(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Return a pandas Styler with problematic cells highlighted."""
    issues = get_issue_cells(df)
    bad_chars = issues["bad_chars"]
    missing = issues["missing"]

    def _apply(frame: pd.DataFrame) -> pd.DataFrame:
        styles = pd.DataFrame("", index=frame.index, columns=frame.columns)
        for r, c in bad_chars:
            if r < len(frame) and c < len(frame.columns):
                styles.iloc[r, c] = "background-color: #ffcccc; color: #b91c1c"
        for r, c in missing:
            if r < len(frame) and c < len(frame.columns):
                if (r, c) not in bad_chars:
                    styles.iloc[r, c] = "background-color: #fef3c7; color: #92400e"
        return styles

    return df.style.apply(_apply, axis=None)


def issue_summary(df: pd.DataFrame) -> str | None:
    """Human-readable summary string, or None if no issues."""
    issues = get_issue_cells(df)
    n_bad = len(issues["bad_chars"])
    n_miss = len(issues["missing"])
    parts = []
    if n_bad:
        parts.append(f"**{n_bad}** cell(s) with OCR artifacts (🔴 red)")
    if n_miss:
        parts.append(f"**{n_miss}** blank cell(s) that may be missing values (🟡 amber)")
    return "  |  ".join(parts) if parts else None
