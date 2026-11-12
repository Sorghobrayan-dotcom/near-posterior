"""Minimal inline-SVG drawing in Python: one accent colour, a neutral scale, labels on the chart.

No external request; every chart is plain SVG text, also usable as a standalone file.
"""

import html
import math

ACCENT = "#c2410c"
ACCENT_LIGHT = "#f6d3c1"
INK = "#1f2933"
MID = "#6b7280"
LIGHT = "#d1d5db"
FAINT = "#f3f4f6"
FONT = "Helvetica, Arial, sans-serif"


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
        return f"{v / 1e3:.0f}k"
    if a >= 10 or v == 0:
        return f"{v:.0f}"
    if a >= 1:
        return f"{v:.1f}".rstrip("0").rstrip(".")
    if a >= 0.01:
        return f"{v:.2f}".rstrip("0").rstrip(".")
    return f"{v:.3f}".rstrip("0").rstrip(".")


class Frame:
    """A plotting area with linear or log axes; collects SVG elements."""

    def __init__(self, xlo, xhi, ylo, yhi, xlog=False, ylog=False, w=480, h=280, left=52,
                 right=16, top=18, bottom=42):
        """Store the ranges and margins of the plot."""
        self.xlo, self.xhi, self.ylo, self.yhi = xlo, xhi, ylo, yhi
        self.xlog, self.ylog = xlog, ylog
        self.w, self.h, self.left, self.right, self.top, self.bottom = w, h, left, right, top, bottom
        self.parts: list[str] = []

    def _u(self, v, lo, hi, log):
        """Return v as a fraction of the axis range."""
        if log:
            v, lo, hi = math.log10(max(v, 1e-12)), math.log10(lo), math.log10(hi)
        return (v - lo) / (hi - lo) if hi != lo else 0.5

    def x(self, v) -> float:
        """Return the pixel x of a data value."""
        return self.left + self._u(v, self.xlo, self.xhi, self.xlog) * (self.w - self.left - self.right)

    def y(self, v) -> float:
        """Return the pixel y of a data value."""
        return self.top + (1 - self._u(v, self.ylo, self.yhi, self.ylog)) * (
            self.h - self.top - self.bottom)

    def text(self, x, y, s, anchor="start", colour=INK, size=12, weight="normal") -> None:
        """Add a text label at pixel coordinates."""
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
                          f'text-anchor="{anchor}" fill="{colour}" font-weight="{weight}">'
                          f"{esc(s)}</text>")

    def line(self, pts, colour=INK, width=2.0, dash=None) -> None:
        """Add a polyline through data points (x, y)."""
        d = " ".join(f"{self.x(a):.1f},{self.y(b):.1f}" for a, b in pts)
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<polyline fill="none" stroke="{colour}" stroke-width="{width}"'
                          f'{extra} points="{d}"/>')

    def band(self, xs, lo, hi, colour=ACCENT_LIGHT) -> None:
        """Add a filled band between two curves over xs."""
        top = [f"{self.x(a):.1f},{self.y(b):.1f}" for a, b in zip(xs, hi)]
        bot = [f"{self.x(a):.1f},{self.y(b):.1f}" for a, b in zip(reversed(xs), reversed(lo))]
        self.parts.append(f'<polygon fill="{colour}" stroke="none" points="{" ".join(top + bot)}"/>')

    def rect(self, x0, y0, x1, y1, colour=ACCENT, opacity=1.0, stroke=None) -> None:
        """Add a rectangle between two data corners."""
        px0, px1 = sorted((self.x(x0), self.x(x1)))
        py0, py1 = sorted((self.y(y0), self.y(y1)))
        s = f' stroke="{stroke}"' if stroke else ""
        self.parts.append(f'<rect x="{px0:.1f}" y="{py0:.1f}" width="{px1 - px0:.1f}" '
                          f'height="{py1 - py0:.1f}" fill="{colour}" fill-opacity="{opacity}"{s}/>')

    def dot(self, xv, yv, r=3.0, colour=ACCENT, opacity=1.0) -> None:
        """Add a circle at a data point."""
        self.parts.append(f'<circle cx="{self.x(xv):.1f}" cy="{self.y(yv):.1f}" r="{r:.1f}" '
                          f'fill="{colour}" fill-opacity="{opacity}"/>')

    def vline(self, xv, colour=MID, dash="3 3", label=None, at_top=True) -> None:
        """Add a vertical reference line with an optional label."""
        x = self.x(xv)
        self.parts.append(f'<line x1="{x:.1f}" y1="{self.top}" x2="{x:.1f}" '
                          f'y2="{self.h - self.bottom}" stroke="{colour}" stroke-dasharray="{dash}"/>')
        if label:
            self.text(x + 3, self.top + 10 if at_top else self.h - self.bottom - 4, label,
                      colour=colour, size=11)

    def hline(self, yv, colour=MID, dash="3 3", label=None) -> None:
        """Add a horizontal reference line with an optional label on the right."""
        y = self.y(yv)
        self.parts.append(f'<line x1="{self.left}" y1="{y:.1f}" x2="{self.w - self.right}" '
                          f'y2="{y:.1f}" stroke="{colour}" stroke-dasharray="{dash}"/>')
        if label:
            self.text(self.w - self.right, y - 4, label, anchor="end", colour=colour, size=11)

    def axes(self, xticks, yticks, xlabel="", ylabel="", xfmt=fmt, yfmt=fmt) -> None:
        """Add grid lines, tick labels and axis titles."""
        for v in yticks:
            y = self.y(v)
            self.parts.append(f'<line x1="{self.left}" y1="{y:.1f}" x2="{self.w - self.right}" '
                              f'y2="{y:.1f}" stroke="{FAINT}"/>')
            self.text(self.left - 5, y + 4, yfmt(v), anchor="end", colour=MID, size=11)
        for v in xticks:
            self.text(self.x(v), self.h - self.bottom + 15, xfmt(v), anchor="middle", colour=MID,
                      size=11)
        self.parts.append(f'<line x1="{self.left}" y1="{self.h - self.bottom}" '
                          f'x2="{self.w - self.right}" y2="{self.h - self.bottom}" stroke="{LIGHT}"/>')
        if xlabel:
            self.text((self.left + self.w - self.right) / 2, self.h - 6, xlabel, anchor="middle",
                      colour=MID, size=11)
        if ylabel:
            cy = (self.top + self.h - self.bottom) / 2
            self.parts.append(f'<text x="12" y="{cy:.1f}" font-size="11" fill="{MID}" '
                              f'text-anchor="middle" transform="rotate(-90 12 {cy:.1f})">'
                              f"{esc(ylabel)}</text>")

    def svg(self, title: str, standalone: bool = False) -> str:
        """Return the SVG text; standalone adds the XML namespace header for a file."""
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
                f'role="img" aria-label="{esc(title)}" font-family="{FONT}"'
                + ("" if standalone else ' width="100%" style="max-width:720px;height:auto"')
                + ">")
        return "\n".join([head, f"<title>{esc(title)}</title>",
                          f'<rect x="0" y="0" width="{self.w}" height="{self.h}" fill="#ffffff"/>']
                         + self.parts + ["</svg>"]) + ("\n" if standalone else "")
