import re

from near_posterior import out, site, thesis

PAGE = out.ROOT / "site" / "index.html"


def test_page_regenerates_byte_identically_and_is_ascii():
    text = PAGE.read_text(encoding="ascii")
    assert site.render(thesis.load_results()) == text
    assert "\r" not in text


def test_seven_charts_each_with_query_and_sentence():
    text = PAGE.read_text(encoding="ascii")
    sections = [s for s in re.findall(r"<section>(.*?)</section>", text, re.S) if "Query:" in s]
    assert len(sections) == 7
    for s in sections:
        assert "<h2>" in s and ("<svg" in s or "<table>" in s)
        assert s.count('<p class="q">Query: <code>') == 1
        assert len(re.findall(r"\n<p>[^<]+</p>", s)) == 1


def test_no_script_and_no_external_request():
    text = PAGE.read_text(encoding="ascii")
    assert "<script" not in text.lower()
    assert not re.search(r"""(src|href)\s*=\s*["']?(https?:)?//""", text, re.I)
    assert "@import" not in text and "url(" not in text
