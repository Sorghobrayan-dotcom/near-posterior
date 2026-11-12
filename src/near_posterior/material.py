"""Material for the author, generated from results/: a 75-second demo script and a draft X post.

The author records the demo and posts; nothing here is sent anywhere.
"""

from near_posterior import thesis
from near_posterior.thesis import f, interval

REPO = "https://github.com/Sorghobrayan-dotcom/near-posterior"
PAGES = "https://sorghobrayan-dotcom.github.io/near-posterior/site/"


def demo_script(res: dict) -> str:
    """Return docs/DEMO_SCRIPT.md: a 75-second demo, shot by shot."""
    h, c = res["headline"], res["coverage"]
    w90 = next(w for w in c["windows"] if w["window"] == "90")
    hit = [r for r in res["entities_R_rows"] if r["h"] == "24"
           and int(r["successes_at_k_star"]) > 0]
    grid = [r for r in res["levers_rows"] if r["label"] == "lever grid"]
    best = max(grid, key=lambda r: float(r["P"]))
    b = thesis.largest_bin(res["validation"], "24")
    shots = [
        ("0:00-0:08", "Terminal",
         "`uv run python -m near_posterior.verify` scrolling to the last PASS line.",
         "Every number you will see is rebuilt offline from public data and checked."),
        ("0:08-0:20", "Terminal", "`uv run python -m near_posterior.ask`",
         f"Buybacks cover {f(w90['C'])} of NEAR's net issuance today, so NEAR Intents fees must "
         f"grow {f(h['k_star'], 2)}x in 24 months. Among {h['entities']} comparable protocols, "
         f"the share that did that is {f(h['P'])} (90 percent interval "
         f"{interval(h['interval'])})."),
        ("0:20-0:32", "Page, explorer", "Open `site/index.html`, drag the k slider from 1x to k*.",
         "This is the base rate for any growth multiple; the triangles are what other NEAR theses "
         "say is needed."),
        ("0:32-0:42", "Page, table 'Who reached k*'", "Scroll to the table.",
         f"{len(hit)} protocols ever made it; their best runs started between "
         f"{min(r['largest_growth_origin'][:4] for r in hit)} and "
         f"{max(r['largest_growth_origin'][:4] for r in hit)}."
         if hit else "No protocol of the class reached it."),
        ("0:42-0:54", "Page, lever heat map", "Point at the darkest cell.",
         f"Governance can move capture and issuance; the best cell in the whole table is "
         f"{f(best['P'])}, so no lever alone or together reaches even odds."
         if float(best["P"]) <= 0.5 else
         f"Governance levers can reach even odds: the best cell is {f(best['P'])}."),
        ("0:54-1:05", "Page, calibration chart", "Point at the C0 and B2 dots.",
         f"We tested the method on {res['validation']['S1']['12']['scored']} past forecasts: it "
         f"beats trend extrapolation, and it was if anything too optimistic "
         f"({f(b['mean_forecast'], 2)} forecast, {f(b['observed'], 2)} observed)."),
        ("1:05-1:15", "Repository, PREREG.md and RESOLUTION.md", "Show the commit dates.",
         "The rules were committed before the data was downloaded, and the forecast resolves on "
         f"{res['registered_forecast']['forecasts']['24']['resolution_date']}."),
    ]
    L = ["# Demo script (75 seconds)", "",
         "Generated from `results/` by `uv run python -m near_posterior.build`. Record the "
         "screen; read the line in quotes. Not financial advice.", "",
         "| Time | Screen | Action | Voice |", "|---|---|---|---|"]
    L += [f"| {t} | {s} | {a} | \"{v}\" |" for t, s, a, v in shots]
    return "\n".join(L) + "\n"


def x_post(res: dict) -> str:
    """Return docs/X_POST.md: a draft post for the author to edit and send."""
    h, c = res["headline"], res["coverage"]
    w90 = next(w for w in c["windows"] if w["window"] == "90")
    main = (f"Built at NEAR HACKATHON: NEAR buys back its token with Intents revenue. Does that "
            f"offset new supply? Today it covers {round(100 * w90['C'])}% of net issuance. To "
            f"reach 100% in 24 months, fees must grow {f(h['k_star'], 1)}x. Of {h['entities']} "
            f"DeFi protocols of the same size and age, {round(100 * h['P'])}% did. "
            f"@NEARProtocol #NEARHackathon")
    second = (f"Rules were committed before the data was fetched; the number is rebuilt offline "
              f"from DefiLlama and NearBlocks and checked by one command. Explorer for any growth "
              f"multiple: {PAGES} - code: {REPO}")
    question = ("Question for NEAR builders: which lever would you pull first, a higher capture "
                "rate or a faster issuance cut?")
    return "\n".join([
        "# Draft X post (the author edits and posts it)", "",
        "Generated from `results/` by `uv run python -m near_posterior.build`. Lead with the "
        "problem, one complete moment, what NEAR's public data made possible, a link, a real "
        "question. The Pages link works once the repository is public and Pages is enabled.",
        "", "Post 1 (" + str(len(main)) + " characters):", "", "> " + main, "",
        "Post 2 (reply):", "", "> " + second, "", "Post 3 (reply):", "", "> " + question, ""])
