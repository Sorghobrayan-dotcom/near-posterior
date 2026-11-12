"""Minimal inline-SVG charts drawn in Python, with no external request."""

import html

W, H = 640, 260
PAD_L, PAD_R, PAD_T, PAD_B = 64, 16, 16, 40


def esc(text) -> str:
    """Return text escaped for SVG/HTML."""
    return html.escape(str(text), quote=True)


def fmt(v: float) -> str:
    """Return a short tick label for v."""
    a = abs(v)
    if a >= 1e9:
        return f"{v / 1e9:.1f}B"
    if a >= 1e6:
        return f"{v / 1e6:.1f}M"
    if a >= 1e3:
        return f"{v / 1e3:.1f}k"
    if a >= 10 or v == 0:
        return f"{v:.0f}"
    return f"{v:.2f}"


def frame(lo: float, hi: float, xlabels: list[tuple[float, str]], ylabel: str) -> tuple:
    """Return (svg header parts, x mapper, y mapper) for a plot with y range [lo, hi]."""
    hi = hi if hi > lo else lo + 1.0
    def sx(t):
        return PAD_L + t * (W - PAD_L - PAD_R)
    def sy(v):
        return PAD_T + (1.0 - (v - lo) / (hi - lo)) * (H - PAD_T - PAD_B)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
             f'width="100%" style="max-width:{W}px">',
             f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>']
    for i in range(5):
        v = lo + (hi - lo) * i / 4
        y = sy(v)
        parts.append(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{W - PAD_R}" y2="{y:.1f}" '
                     'stroke="#dddddd" stroke-width="1"/>')
        parts.append(f'<text x="{PAD_L - 6}" y="{y + 4:.1f}" font-size="11" text-anchor="end" '
                     f'fill="#444444">{esc(fmt(v))}</text>')
    for t, label in xlabels:
        parts.append(f'<text x="{sx(t):.1f}" y="{H - PAD_B + 16}" font-size="11" '
                     f'text-anchor="middle" fill="#444444">{esc(label)}</text>')
    parts.append(f'<text x="14" y="{PAD_T + (H - PAD_T - PAD_B) / 2:.1f}" font-size="11" '
                 f'fill="#444444" transform="rotate(-90 14 {PAD_T + (H - PAD_T - PAD_B) / 2:.1f})" '
                 f'text-anchor="middle">{esc(ylabel)}</text>')
    return parts, sx, sy


def line_chart(series: list[tuple[str, list[float], str]], xlabels: list[str], ylabel: str,
               hline: tuple[float, str] | None = None) -> str:
    """Return an SVG line chart; series are (name, values, colour) on a shared x axis."""
    vals = [v for _, ys, _ in series for v in ys if v is not None]
    lo, hi = min(vals + [0.0]), max(vals + ([hline[0]] if hline else []))
    n = max(len(ys) for _, ys, _ in series)
    ticks = [(i / max(n - 1, 1), xlabels[i]) for i in range(0, n, max(1, n // 5))]
    parts, sx, sy = frame(lo, hi * 1.05, ticks, ylabel)
    if hline:
        y = sy(hline[0])
        parts.append(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{W - PAD_R}" y2="{y:.1f}" '
                     'stroke="#b00020" stroke-dasharray="4 3"/>')
        parts.append(f'<text x="{W - PAD_R}" y="{y - 4:.1f}" font-size="11" text-anchor="end" '
                     f'fill="#b00020">{esc(hline[1])}</text>')
    for j, (name, ys, colour) in enumerate(series):
        pts = " ".join(f"{sx(i / max(n - 1, 1)):.1f},{sy(v):.1f}" for i, v in enumerate(ys)
                       if v is not None)
        parts.append(f'<polyline fill="none" stroke="{colour}" stroke-width="2" points="{pts}"/>')
        parts.append(f'<text x="{PAD_L + 8 + 120 * j}" y="{PAD_T + 12}" font-size="11" '
                     f'fill="{colour}">{esc(name)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def bar_chart(labels: list[str], values: list[float], ylabel: str, colour: str = "#3060a0",
              hline: tuple[float, str] | None = None, errors: list[tuple] | None = None,
              colours: list[str] | None = None, every: int = 1) -> str:
    """Return an SVG bar chart, with optional error bars (lo, hi), per-bar colours and a
    reference line; only every `every`-th x label is drawn."""
    tops = [v for v in values] + ([hline[0]] if hline else [])
    if errors:
        tops += [e[1] for e in errors if e]
    lo = min([0.0] + values + ([e[0] for e in errors if e] if errors else []))
    hi = max(tops) * 1.1 if max(tops) > 0 else 1.0
    n = len(values)
    ticks = [((i + 0.5) / n, labels[i]) for i in range(0, n, every)]
    parts, sx, sy = frame(lo, hi, ticks, ylabel)
    bw = (W - PAD_L - PAD_R) / n * 0.6
    for i, v in enumerate(values):
        x = sx((i + 0.5) / n) - bw / 2
        y0, y1 = sy(max(v, 0.0)), sy(min(v, 0.0))
        fill = colours[i] if colours else colour
        parts.append(f'<rect x="{x:.1f}" y="{y0:.1f}" width="{bw:.1f}" height="{y1 - y0:.1f}" '
                     f'fill="{fill}"/>')
        if errors and errors[i]:
            cx = sx((i + 0.5) / n)
            parts.append(f'<line x1="{cx:.1f}" y1="{sy(errors[i][0]):.1f}" x2="{cx:.1f}" '
                         f'y2="{sy(errors[i][1]):.1f}" stroke="#000000" stroke-width="1.5"/>')
    if hline:
        y = sy(hline[0])
        parts.append(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{W - PAD_R}" y2="{y:.1f}" '
                     'stroke="#b00020" stroke-dasharray="4 3"/>')
        parts.append(f'<text x="{W - PAD_R}" y="{y - 4:.1f}" font-size="11" text-anchor="end" '
                     f'fill="#b00020">{esc(hline[1])}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def dot_chart(values: list[float], ylabel: str, mark: int | None = None) -> str:
    """Return an SVG chart of sorted values as dots, one marked in red."""
    lo, hi = min(values + [0.0]), max(values + [1.0])
    n = len(values)
    parts, sx, sy = frame(lo, hi, [(0.0, "1"), (1.0, str(n))], ylabel)
    for i, v in enumerate(values):
        colour, r = ("#b00020", 4) if i == mark else ("#3060a0", 1.5)
        parts.append(f'<circle cx="{sx(i / max(n - 1, 1)):.1f}" cy="{sy(v):.1f}" r="{r}" '
                     f'fill="{colour}"/>')
    parts.append("</svg>")
    return "\n".join(parts)


def strip_chart(categories: list[str], points: list[tuple[int, float]], ylabel: str) -> str:
    """Return an SVG strip chart: points (category index, value) with a zero line."""
    vals = [v for _, v in points] + [0.0]
    lo, hi = min(vals), max(vals)
    pad = 0.1 * (hi - lo if hi > lo else 1.0)
    n = len(categories)
    ticks = [((i + 0.5) / n, c) for i, c in enumerate(categories)]
    parts, sx, sy = frame(lo - pad, hi + pad, ticks, ylabel)
    y0 = sy(0.0)
    parts.append(f'<line x1="{PAD_L}" y1="{y0:.1f}" x2="{W - PAD_R}" y2="{y0:.1f}" '
                 'stroke="#b00020" stroke-dasharray="4 3"/>')
    seen: dict[int, int] = {}
    for c, v in points:
        k = seen.get(c, 0)
        seen[c] = k + 1
        x = sx((c + 0.5) / n) + (k % 6 - 2.5) * 6
        parts.append(f'<circle cx="{x:.1f}" cy="{sy(v):.1f}" r="3.5" fill="#3060a0" '
                     'fill-opacity="0.8"/>')
    parts.append("</svg>")
    return "\n".join(parts)
