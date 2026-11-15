"""
analyze_noise.py
================
Turns noise_closed_loop.csv (run_noise.py) into the verification-value result:
recovery rate of the closed loop vs. an open-loop "diagnose and hope" system,
as diagnosis quality degrades.

    python -m experiments.analyze_noise
      -> docs/results/verification-under-noise.md
      -> docs/results/figures/fig7_verification_value.{png,pdf}
"""
import csv
import os
import sys
from collections import defaultdict
from statistics import mean

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.analyze import HERE, OUT_DIR  # noqa: E402
from experiments.stats_utils import mcnemar_exact, wilson_ci  # noqa: E402


def load(path: str | None = None) -> list[dict]:
    path = path or os.path.join(HERE, "noise_closed_loop.csv")
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["p_wrong"] = float(r["p_wrong"])
        r["fix_attempts"] = int(r["fix_attempts"])
        for k in ("diagnosis_correct", "closed_recovered", "open_recovered"):
            r[k] = r[k] == "True"
    return rows


def _rate(flags):
    k, n = sum(flags), len(flags)
    lo, hi = wilson_ci(k, n)
    return {"k": k, "n": n, "rate": k / n if n else 0.0, "ci": [lo, hi]}


def analyze(rows: list[dict]) -> dict:
    by = defaultdict(list)
    for r in rows:
        by[r["p_wrong"]].append(r)
    levels = []
    for p in sorted(by):
        rs = by[p]
        levels.append({
            "p_wrong": p,
            "diagnosis_accuracy": _rate([r["diagnosis_correct"] for r in rs]),
            "closed": _rate([r["closed_recovered"] for r in rs]),
            "open": _rate([r["open_recovered"] for r in rs]),
            "escalated": sum(1 for r in rs if r["closed_result"] == "ESCALATED"),
            "mean_attempts": mean(r["fix_attempts"] for r in rs),
            "mcnemar": mcnemar_exact([r["closed_recovered"] for r in rs], [r["open_recovered"] for r in rs]),
        })
    return {
        "levels": levels,
        "pooled": {
            "closed": _rate([r["closed_recovered"] for r in rows]),
            "open": _rate([r["open_recovered"] for r in rows]),
            "mcnemar": mcnemar_exact([r["closed_recovered"] for r in rows], [r["open_recovered"] for r in rows]),
        },
        "wrong_diagnoses": {
            "n": sum(1 for r in rows if not r["diagnosis_correct"]),
            "closed": _rate([r["closed_recovered"] for r in rows if not r["diagnosis_correct"]]),
            "open": _rate([r["open_recovered"] for r in rows if not r["diagnosis_correct"]]),
        },
    }


def _pct(x):
    return f"{x * 100:.0f}%"


def _ci(d):
    return f"{_pct(d['rate'])} ({d['k']}/{d['n']}) [{_pct(d['ci'][0])}, {_pct(d['ci'][1])}]"


def _p(p):
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def render(res: dict) -> str:
    L = ["# Does verify-and-retry help when diagnosis is wrong?", "",
         "Strict healing mode (only effective fixes cure a fault). A diagnoser is forced wrong on a fraction of "
         "incidents; the **closed loop** (real pipeline: validate, retry an alternate fix, escalate after 2 "
         "retries) is compared with an **open loop** that applies the first fix once and trusts it. Both are "
         "scored on the *same* sampled diagnoses (paired). Cells show recovery rate (successes/n) with a 95% "
         "Wilson interval.", "",
         "| Injected diagnosis error | Realised diagnosis accuracy | Open-loop recovery | Closed-loop recovery | "
         "Escalated | Mean fix attempts | Paired McNemar |", "|---|---|---|---|---|---|---|"]
    for lv in res["levels"]:
        m = lv["mcnemar"]
        L.append(f"| {_pct(lv['p_wrong'])} | {_pct(lv['diagnosis_accuracy']['rate'])} | {_ci(lv['open'])} | "
                 f"{_ci(lv['closed'])} | {lv['escalated']} | {lv['mean_attempts']:.2f} | "
                 f"{_p(m['p_value'])} ({m['b_only_correct']} vs {m['a_only_correct']}) |")
    pm = res["pooled"]["mcnemar"]
    w = res["wrong_diagnoses"]
    L += ["", "## Headline", "",
          f"- Pooled: closed loop {_ci(res['pooled']['closed'])} vs open loop {_ci(res['pooled']['open'])}; "
          f"paired exact McNemar {_p(pm['p_value'])} (open-only-correct {pm['b_only_correct']}, "
          f"closed-only-correct {pm['a_only_correct']}).",
          f"- Restricted to the {w['n']} incidents that were *misdiagnosed*: closed loop recovered "
          f"{_ci(w['closed'])}, open loop {_ci(w['open'])}.", "",
          "## Reading this honestly", "",
          "- The diagnoser's errors are synthetic and uniform over wrong root causes; real LLM errors are "
          "correlated with metric patterns, so this shows the *mechanism's* value, not a forecast of production "
          "accuracy.",
          "- Retry picks the alternate fix for the (wrong) diagnosed cause, it does not re-diagnose. Some wrong "
          "diagnoses therefore remain unrecoverable within the retry budget and escalate; that residual is the "
          "honest cost of this simple retry policy and motivates re-diagnosis on failure as future work.",
          "- Whether a fix is 'effective' is defined by the simulator's table (`EFFECTIVE_FIXES`). It encodes "
          "plausible operational knowledge, not measured production behaviour.", ""]
    return "\n".join(L)


def figure(res: dict):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from experiments.make_figures import BLUE, ORANGE, _save

    fig, ax = plt.subplots(figsize=(6.4, 3.3))
    for key, color, label, off in (("closed", BLUE, "Closed loop (verify + retry)", 0.8),
                                   ("open", ORANGE, "Open loop (apply once, trust)", -0.8)):
        xs = [100 * lv["p_wrong"] + off for lv in res["levels"]]
        ys = [100 * lv[key]["rate"] for lv in res["levels"]]
        lo = [max(0, 100 * (lv[key]["rate"] - lv[key]["ci"][0])) for lv in res["levels"]]
        hi = [max(0, 100 * (lv[key]["ci"][1] - lv[key]["rate"])) for lv in res["levels"]]
        ax.errorbar(xs, ys, yerr=[lo, hi], fmt="o-", color=color, ms=6, mec="white", mew=1.0, lw=1.6,
                    capsize=3, label=label)
    ax.set_xlabel("Injected diagnosis error rate (%)")
    ax.set_ylabel("Incidents recovered (%)")
    ax.set_ylim(0, 105)
    ax.set_xticks([100 * lv["p_wrong"] for lv in res["levels"]])
    ax.set_title("Value of verification as diagnosis quality degrades", loc="left", fontsize=10, fontweight="bold")
    ax.legend(loc="lower left")
    _save(fig, "fig7_verification_value")


def main():
    rows = load()
    res = analyze(rows)
    with open(os.path.join(OUT_DIR, "verification-under-noise.md"), "w", encoding="utf-8") as f:
        f.write(render(res))
    figure(res)
    print("wrote verification-under-noise.md")


if __name__ == "__main__":
    main()
