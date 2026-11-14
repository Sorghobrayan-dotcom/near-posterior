"""Material for the author, generated from results/: a 75-second demo script and a draft X post.

The author records the demo and posts; nothing here is sent anywhere.
"""

from near_posterior import thesis
from near_posterior.thesis import f, interval

REPO = "https://github.com/Sorghobrayan-dotcom/near-posterior"
PAGES = "https://sorghobrayan-dotcom.github.io/near-posterior/site/"


def scoreboard(res: dict) -> dict:
    """Return the number of other theses on the scoreboard and the range of their k and P."""
    rows = [r for r in res["forward_claims_rows"] if r["h"] == "24"]
    ks, ps = [float(r["k"]) for r in rows], [float(r["P"]) for r in rows]
    return {"theses": len({r["thesis"] for r in rows}), "k": (min(ks), max(ks)),
            "P": (min(ps), max(ps))}


def demo_script(res: dict) -> str:
    """Return docs/DEMO_SCRIPT.md: a 75-second demo, shot by shot."""
    h = res["headline"]
    sb = scoreboard(res)
    hit = [r for r in res["entities_R_rows"] if r["h"] == "24"
           and int(r["successes_at_k_star"]) > 0]
    b = thesis.largest_bin(res["validation"], "24")
    first = res["milestones"]["milestones"][0]["date"]
    shots = [
        ("0:00-0:12", "Page, scoreboard", "Open the page, scroll to the scoreboard.",
         f"{sb['theses']} public NEAR theses say NEAR Intents fees must multiply for buybacks to "
         f"offset new supply. None says how often that happened. This table does: between "
         f"{f(sb['P'][1])} and {f(sb['P'][0])} of comparable protocols."),
        ("0:12-0:24", "Page, simulator", f"Type {sb['k'][1]:.2f} in the multiple box, then clear "
         "it and move one slider.",
         f"Type the multiple any thesis needs and read its odds. For NEAR today the bar is "
         f"{f(h['k_star'], 2)}x, and {f(h['P'])} of {h['entities']} comparable protocols did it "
         f"(90 percent interval {interval(h['interval'])})."),
        ("0:24-0:33", "Page, table 'Who reached k*'", "Scroll to the table.",
         f"{len(hit)} protocols ever made it; their best runs started between "
         f"{min(r['largest_growth_origin'][:4] for r in hit)} and "
         f"{max(r['largest_growth_origin'][:4] for r in hit)}."
         if hit else "No protocol of the class reached it."),
        ("0:33-0:42", "Page, milestones", "Scroll to the milestones table.",
         f"Nothing has to wait for 2028: from {first}, dated milestones say whether coverage is "
         f"on the line to the target."),
        ("0:42-0:55", "NEAR explorer", "Click the contract link, show its transactions and keys.",
         "The forecasts, the scoreboard and the milestones sit in a NEAR contract. Its account "
         "holds no full-access key, so nobody can change them, and after the date any account "
         "can write its own reading of the outcome."),
        ("0:55-1:05", "Page, calibration chart", "Point at the C0 and B2 dots.",
         f"We tested the method on {res['validation']['S1']['12']['scored']} past forecasts: it "
         f"beats trend extrapolation, and it was if anything too optimistic "
         f"({f(b['mean_forecast'], 2)} forecast, {f(b['observed'], 2)} observed)."),
        ("1:05-1:15", "Terminal",
         "`uv run python -m near_posterior.verify` scrolling to the last PASS line.",
         "Every number is rebuilt offline by one command, and the rules were committed before "
         f"the data was downloaded. It resolves on "
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
    h = res["headline"]
    sb = scoreboard(res)
    main = (f"Built at NEAR HACKATHON: {sb['theses']} NEAR theses say Intents fees must grow "
            f"{sb['k'][0]:.1f}x to {sb['k'][1]:.1f}x for buybacks to offset new supply. How often "
            f"did protocols of that size do it? {round(100 * sb['P'][0])}% to "
            f"{round(100 * sb['P'][1])}% of the time. NEAR today: {f(h['k_star'], 1)}x, "
            f"{round(100 * h['P'])}%. @NEARProtocol #NEARHackathon")
    second = (f"Forecasts, scoreboard and dated milestones are written in a NEAR contract whose "
              f"account holds no full-access key: nobody, the author included, can change them. "
              f"Score any multiple: {PAGES} - code: {REPO}")
    question = ("Question for NEAR builders: which lever would you pull first, a higher capture "
                "rate or a faster issuance cut?")
    return "\n".join([
        "# Draft X post (the author edits and posts it)", "",
        "Generated from `results/` by `uv run python -m near_posterior.build`. Lead with the "
        "problem, one complete moment, what NEAR's public data made possible, a link, a real "
        "question. The Pages link works once the repository is public and Pages is enabled.",
        "", "Post 1 (" + str(len(main)) + " characters):", "", "> " + main, "",
        "Post 2 (reply):", "", "> " + second, "", "Post 3 (reply):", "", "> " + question, ""])
