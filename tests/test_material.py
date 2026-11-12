import re

from near_posterior import out, site, thesis

ROOT = out.ROOT


def test_x_post_says_built_at_near_hackathon_within_the_limit():
    text = (ROOT / "docs" / "X_POST.md").read_text(encoding="ascii")
    post1 = re.search(r"Post 1 \((\d+) characters\):\n\n> (.*)\n", text)
    assert post1 and int(post1.group(1)) == len(post1.group(2)) <= 280
    for needle in ("Built at NEAR HACKATHON", "@NEARProtocol", "#NEARHackathon"):
        assert needle in post1.group(2)


def test_root_index_redirects_to_the_page():
    text = (ROOT / "index.html").read_text(encoding="ascii")
    assert text == site.root_index()
    assert 'http-equiv="refresh" content="0; url=site/"' in text and 'href="site/"' in text


def test_page_and_readme_show_the_headline_as_a_percentage_and_keep_the_exact_line():
    res = thesis.load_results()
    pc = f"{100 * res['headline']['P']:.1f}%"
    page = (ROOT / "site" / "index.html").read_text(encoding="ascii")
    readme = (ROOT / "README.md").read_text(encoding="ascii")
    assert f'class="big">{pc}<' in page and f"**{pc}**" in readme
    assert thesis.headline_line(res) in page and thesis.headline_line(res) in readme


def test_page_uses_a_short_secondary_tag_explained_once():
    page = (ROOT / "site" / "index.html").read_text(encoding="ascii")
    assert "[secondary (specified" not in page
    assert page.count('<span class="tag">secondary</span>') >= 5
    head = page.split("</header>")[0]
    assert "specified after the primary results" in head and "../PREREG_2.md" in head


def test_thesis_has_investor_sentences_and_calibration_tables():
    text = (ROOT / "THESIS.md").read_text(encoding="ascii")
    summary = text.split("## 2. The question")[0]
    assert "For an investor, this means" in summary and "governance ones" in summary
    assert text.count("| Model | Event | Forecast bin | Targets | Mean forecast | Observed |") == 2
    assert "secondary (specified after the primary results)" in text
