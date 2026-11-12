"""Write results as deterministic, pure-ASCII, LF-terminated files."""

import csv
import io
import json
import math
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"


def tidy(obj):
    """Return obj with every float rounded to 12 significant digits and non-finite floats as None."""
    if isinstance(obj, float):
        return float(f"{obj:.12g}") if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {str(k): tidy(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [tidy(v) for v in obj]
    return obj


def json_text(obj) -> str:
    """Return the canonical JSON text of obj (sorted keys, 2-space indent, ASCII, final LF)."""
    return json.dumps(tidy(obj), indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def csv_text(header: list[str], rows: list[list]) -> str:
    """Return CSV text with LF line ends; floats rounded as in `tidy`."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for row in rows:
        w.writerow(["" if v is None else v for v in tidy(list(row))])
    return buf.getvalue()


def write_text(path: pathlib.Path, text: str) -> None:
    """Write ASCII text with LF line ends, creating the parent directory."""
    text.encode("ascii")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="ascii", newline="\n")
