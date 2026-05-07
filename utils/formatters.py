"""
Output formatting utilities: ANSI color, aligned tables, and numeric display.

All commands route through these helpers so color/no-color is controlled centrally.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Color control
# ---------------------------------------------------------------------------

_USE_COLOR = True


def set_color(enabled: bool) -> None:
    global _USE_COLOR
    _USE_COLOR = enabled


def _c(code: str, text: str) -> str:
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def green(text: str) -> str:
    return _c("32", text)


def yellow(text: str) -> str:
    return _c("33", text)


def red(text: str) -> str:
    return _c("31", text)


def bold(text: str) -> str:
    return _c("1", text)


def dim(text: str) -> str:
    return _c("2", text)


def status_color(status: str) -> str:
    s = status.upper()
    if s == "GREEN":
        return green(status)
    if s == "YELLOW":
        return yellow(status)
    if s == "RED":
        return red(status)
    return status


# ---------------------------------------------------------------------------
# Table rendering (no tabulate dependency)
# ---------------------------------------------------------------------------

def table(headers: list[str], rows: list[list[str]], indent: int = 0) -> str:
    all_rows = [headers] + rows
    widths = [max(len(str(cell)) for cell in col) for col in zip(*all_rows)]
    pad = " " * indent
    sep = pad + "  ".join("-" * w for w in widths)
    lines: list[str] = []
    lines.append(pad + "  ".join(bold(str(h).ljust(w)) for h, w in zip(headers, widths)))
    lines.append(sep)
    for row in rows:
        lines.append(pad + "  ".join(str(c).ljust(w) for c, w in zip(row, widths)))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Numeric formatting helpers
# ---------------------------------------------------------------------------

def fmt_float(v: float, decimals: int = 3) -> str:
    if abs(v) >= 1e9:
        return f"{v/1e9:.{decimals}f}B"
    if abs(v) >= 1e6:
        return f"{v/1e6:.{decimals}f}M"
    if abs(v) >= 1e3:
        return f"{v/1e3:.{decimals}f}K"
    return f"{v:.{decimals}f}"


def fmt_pct(v: float, decimals: int = 1) -> str:
    return f"{v * 100:.{decimals}f}%"


def fmt_eps(v: float) -> str:
    return f"{v:.3f}"
