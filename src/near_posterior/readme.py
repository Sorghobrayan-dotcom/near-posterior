"""Fill the generated blocks of README.md (headline line, limits) from the results."""

import re

from near_posterior import out, thesis

README = out.ROOT / "README.md"


def blocks(res: dict) -> dict:
    """Return the text of each generated README block."""
    return {
        "headline": "```\n" + thesis.headline_line(res) + "\n```",
        "limits": "\n".join(f"- {t}" for t in thesis.limits(res)),
    }


def fill(text: str, parts: dict) -> str:
    """Return text with each `<!-- BEGIN GENERATED name -->` block replaced by parts[name]."""
    for name, body in parts.items():
        pat = re.compile(rf"(<!-- BEGIN GENERATED {name} -->\n).*?(<!-- END GENERATED {name} -->)",
                         re.S)
        if not pat.search(text):
            raise ValueError(f"README.md has no generated block {name}")
        text = pat.sub(lambda m: m.group(1) + body + "\n" + m.group(2), text)
    return text
