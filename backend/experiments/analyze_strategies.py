"""
analyze_strategies.py
=====================
Summarises strategies_*.csv (run_strategies.py): blind restart vs open loop vs
closed loop under strict healing, per diagnoser (rule-based and each real LLM).

    python -m experiments.analyze_strategies
      -> docs/results/strategy-comparison.md
      -> docs/results/figures/fig8_strategies.{png,pdf}
"""
import csv
import glob
import os
import sys
from statistics import mean

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.analyze import HERE, OUT_DIR  # noqa: E402
from experiments.stats_utils import mcnemar_exact, wilson_ci  # noqa: E402

NICE = {"rule_based": "rule-based", "openai_gpt_oss_120b": "gpt-oss-120b",
        "openai_gpt_oss_20b": "gpt-oss-20b", "qwen_qwen3_8_27b": "qwen3-27b"}
ORDER = ["rule_based", "openai_gpt_oss_120b", "openai_gpt_oss_20b", "qwen_qwen3_8_27b"]


def load(directory: str = HERE) -> dict[str, list[dict]]:
    out = {}
    for path in glob.glob(os.path.join(directory, "strategies_*.csv")):
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            for k in ("diagnosis_correct", "closed_recovered", "open_recovered", "blind_restart_recovered"):
                r[k] = r[k] == "True"
            r["attempts"] = int(r["attempts"] or 0)
            r["mttr_s"] = float(r["mttr_s"]) if r["mttr_s"] != "" else None
        out[rows[0]["name"]] = rows
    return dict(sorted(out.items(), key=lambda kv: ORDER.index(kv[0]) if kv[0] in ORDER else 99))


def _rate(flags):
    k, n = sum(flags), len(flags)
    lo, hi = wilson_ci(k, n)
    return {"k": k, "n": n, "rate": k / n if n else 0.0, "ci": [lo, hi]}


def analyze(data: dict[str, list[dict]]) -> dict:
    res = {"by_diagnoser": {}}
    for name, rows in data.items():
        by_fault = {}
        for f in sorted({r["fault"] for r in rows}):
            rs = [r for r in rows if r["fault"] == f]
            by_fault[f] = {"blind": _rate([r["blind_restart_recovered"] for r in rs]),
                           "open": _rate([r["open_recovered"] for r in rs]),
                           "closed": _rate([r["closed_recovered"] for r in rs])}
        ok = [r["mttr_s"] for r in rows if r["closed_recovered"] and r["mttr_s"] is not None]
        res["by_diagnoser"][name] = {
            "n": len(rows),
            "diagnosis": _rate([r["diagnosis_correct"] for r in rows]),
            "blind": _rate([r["blind_restart_recovered"] for r in rows]),
            "open": _rate([r["open_recovered"] for r in rows]),
            "closed": _rate([r["closed_recovered"] for r in rows]),
            "closed_vs_open": mcnemar_exact([r["closed_recovered"] for r in rows], [r["open_recovered"] for r in rows]),
            "closed_vs_blind": mcnemar_exact([r["closed_recovered"] for r in rows], [r["blind_restart_recovered"] for r in rows]),
            "mean_attempts": mean(r["attempts"] for r in rows),
            "needed_retry": sum(1 for r in rows if r["attempts"] > 1),
            "escalated": sum(1 for r in rows if r["result"] == "ESCALATED"),
            "mean_mttr_closed": mean(ok) if ok else None,
            "by_fault": by_fault,
        }
    all_rows = [r for rows in data.values() for r in rows]
    res["pooled"] = {
        "n": len(all_rows),
        "blind": _rate([r["blind_restart_recovered"] for r in all_rows]),
        "open": _rate([r["open_recovered"] for r in all_rows]),
        "closed": _rate([r["closed_recovered"] for r in all_rows]),
        "closed_vs_open": mcnemar_exact([r["closed_recovered"] for r in all_rows], [r["open_recovered"] for r in all_rows]),
        "closed_vs_blind": mcnemar_exact([r["closed_recovered"] for r in all_rows], [r["blind_restart_recovered"] for r in all_rows]),
    }
    return res


def _pct(x):
    return f"{x * 100:.1f}%"


def _ci(d):
    return f"{_pct(d['rate'])} ({d['k']}/{d['n']}) [{_pct(d['ci'][0])}, {_pct(d['ci'][1])}]"


def _p(p):
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def render(res: dict) -> str:
    L = ["# Strategy comparison under strict healing", "",
         "Every fault below is one of the 20 (service, fault) scenarios, repeated per diagnoser (trials per diagnoser are in the table: n/20), with "
         "`STRICT_HEALING=1` (a fix only cures a fault it is effective against). Recovery is reported for:", "",
         "- **Blind restart**: always restart, no diagnosis, no verification (a Kubernetes liveness-probe analogue; analytic).",
         "- **Open loop**: apply the diagnoser's first fix once and trust it (paired with the closed loop's diagnosis).",
         "- **Closed loop**: the real pipeline: validate, retry an alternate fix, escalate after 2 retries (measured with `RETRY_POLICY=repeat`: both retries use the same alternate).", "",
         "Cells: recovery rate (successes/n) with a 95% Wilson interval.", "",
         "| Diagnoser | Diagnosis accuracy | Blind restart | Open loop | Closed loop | Needed a retry | Escalated | Closed vs open (McNemar) |",
         "|---|---|---|---|---|---|---|---|"]
    for name, d in res["by_diagnoser"].items():
        m = d["closed_vs_open"]
        L.append(f"| {NICE.get(name, name)} | {_ci(d['diagnosis'])} | {_ci(d['blind'])} | {_ci(d['open'])} | "
                 f"{_ci(d['closed'])} | {d['needed_retry']} | {d['escalated']} | {_p(m['p_value'])} "
                 f"({m['b_only_correct']} open-only, {m['a_only_correct']} closed-only) |")
    p = res["pooled"]
    L += ["", "## Pooled over all diagnosers", "",
          f"- Blind restart: {_ci(p['blind'])}",
          f"- Open loop: {_ci(p['open'])}",
          f"- Closed loop: {_ci(p['closed'])}",
          f"- Closed vs blind restart: {_p(p['closed_vs_blind']['p_value'])} "
          f"({p['closed_vs_blind']['b_only_correct']} blind-only, {p['closed_vs_blind']['a_only_correct']} closed-only)",
          f"- Closed vs open loop: {_p(p['closed_vs_open']['p_value'])} "
          f"({p['closed_vs_open']['b_only_correct']} open-only, {p['closed_vs_open']['a_only_correct']} closed-only)",
          "", "## By fault type (closed loop / open loop / blind restart)", "",
          "| Diagnoser | crash | error | memory | slow |", "|---|---|---|---|---|"]
    for name, d in res["by_diagnoser"].items():
        cells = []
        for f in ("crash", "error", "memory", "slow"):
            b = d["by_fault"].get(f)
            cells.append("-" if not b else f"{b['closed']['k']}/{b['closed']['n']} / {b['open']['k']}/{b['open']['n']} / {b['blind']['k']}/{b['blind']['n']}")
        L.append(f"| {NICE.get(name, name)} | " + " | ".join(cells) + " |")
    L += ["", "## Reading this honestly", "",
          "- Blind restart is modelled analytically from the simulator's `EFFECTIVE_FIXES` table (a restart does not cure "
          "a sustained overload, so it fails the *slow* class). This encodes plausible operations knowledge; it is not a "
          "measurement of a real Kubernetes cluster.",
          "- Open and closed loop are scored on the same incidents, and open/closed on the same diagnosis, so the "
          "comparisons are paired.",
          "- Where an LLM's *diagnosis* is right but its own chosen *fix* is not effective (the paper's Section 6.1 "
          "observation), the closed loop's retry is what recovers it; this table counts those cases.",
          "- Validation wait is shortened to 0.5 s for these runs; it does not change which fixes are effective.", ""]
    return "\n".join(L)


def figure(res: dict):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from experiments.make_figures import AQUA, BLUE, ORANGE, _save

    names = list(res["by_diagnoser"])
    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    w = 0.26
    for j, (key, color, label) in enumerate((("blind", ORANGE, "Blind restart"), ("open", AQUA, "Open loop"),
                                             ("closed", BLUE, "Closed loop"))):
        xs = [i + (j - 1) * (w + 0.02) for i in range(len(names))]
        ys = [100 * res["by_diagnoser"][n][key]["rate"] for n in names]
        lo = [max(0, 100 * (res["by_diagnoser"][n][key]["rate"] - res["by_diagnoser"][n][key]["ci"][0])) for n in names]
        hi = [max(0, 100 * (res["by_diagnoser"][n][key]["ci"][1] - res["by_diagnoser"][n][key]["rate"])) for n in names]
        ax.bar(xs, ys, w, color=color, label=label, yerr=[lo, hi], error_kw={"ecolor": "#52514e", "lw": 0.9, "capsize": 2})
    ax.set_xticks(range(len(names)), [NICE.get(n, n) for n in names])
    ax.set_ylim(0, 112)
    ax.set_ylabel("Incidents recovered (%)")
    ax.set_title("Recovery by remediation strategy (strict healing)", loc="left", fontsize=10, fontweight="bold")
    ax.grid(axis="x", visible=False)
    ax.legend(ncol=3, loc="upper left", bbox_to_anchor=(0, 1.0))
    _save(fig, "fig8_strategies")


def main():
    data = load()
    if not data:
        raise SystemExit("no strategies_*.csv found; run experiments.run_strategies first")
    res = analyze(data)
    with open(os.path.join(OUT_DIR, "strategy-comparison.md"), "w", encoding="utf-8") as f:
        f.write(render(res))
    figure(res)
    print("wrote strategy-comparison.md")


if __name__ == "__main__":
    main()
