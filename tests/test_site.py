import re

from near_posterior import out, site, thesis

PAGE = out.ROOT / "site" / "index.html"


def test_page_and_svgs_regenerate_byte_identically_and_are_ascii():
    res = thesis.load_results()
    text = PAGE.read_text(encoding="ascii")
    assert site.render(res) == text and "\r" not in text
    for rel, svg_text in site.standalone(res).items():
        assert (out.ROOT / rel).read_text(encoding="ascii") == svg_text


def test_every_chart_and_table_has_its_query_and_one_sentence():
    text = PAGE.read_text(encoding="ascii")
    sections = [s for s in re.findall(r"<section[^>]*>(.*?)</section>", text, re.S) if "Query:" in s]
    assert len(sections) >= 12
    for s in sections:
        assert "<h2>" in s and ("<svg" in s or "<table>" in s)
        assert s.count('<p class="q">Query: <code>') == 1
        assert len(re.findall(r"\n<p>[^<]+</p>", s)) == 1


def test_top_has_question_number_interval_date_and_links():
    text = PAGE.read_text(encoding="ascii")
    head = text.split("</header>")[0]
    for needle in ('class="big"', "90% interval", "t0 =", "../THESIS.md", "../PREREG.md",
                   "../PREREG_2.md", "at the 24-month mark"):
        assert needle in head, needle


def test_inline_scripts_only_and_no_external_request():
    text = PAGE.read_text(encoding="ascii")
    scripts = re.findall(r"<script([^>]*)>(.*?)</script>", text, re.S)
    assert len(scripts) == 3 and all(attrs == "" for attrs, _ in scripts)
    for _, body in scripts:
        assert not re.search(r"fetch\(|XMLHttpRequest|import\(|https?:", body)
    assert not re.search(r"""src\s*=\s*["']?(https?:)?//""", text, re.I)
    assert not re.search(r"""<link[^>]*href\s*=\s*["']?(https?:)?//""", text, re.I)
    assert "@import" not in text and "url(" not in text


def test_verify_page_regenerates_and_loads_no_external_resource():
    text = (out.ROOT / "site" / "verify.html").read_text(encoding="ascii")
    assert site.verify_page() == text and "\r" not in text
    assert not re.search(r"""src\s*=\s*["']?(https?:)?//""", text, re.I)
    assert not re.search(r"""<link[^>]*href\s*=\s*["']?(https?:)?//""", text, re.I)
    assert 'href="verify.html"' in PAGE.read_text(encoding="ascii")


def test_correction_block_has_its_tag_chart_and_three_numbers():
    text = PAGE.read_text(encoding="ascii")
    block = [s for s in re.findall(r"<section[^>]*>(.*?)</section>", text, re.S)
             if "Correcting for past over-forecasting" in s]
    assert len(block) == 1
    s = block[0]
    assert '<span class="tag">tertiary</span>' in s and "<svg" in s
    for col in ("Registered P", "Recency-weighted P", "P_cal", "P_cal tested out of sample"):
        assert col in s
    assert "../PREREG_3.md" in text.split("</header>")[0]
