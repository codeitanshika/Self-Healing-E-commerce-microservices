"""
analyze_pipeline.py
===================
Summarises the end-to-end pipeline experiments (pipeline_*.csv) written by
run_pipeline.py: where the time goes, and how MTTR behaves as more incidents
run at once.

    python -m experiments.analyze_pipeline
      -> docs/results/pipeline-latency.md
      -> docs/results/figures/fig5_stage_breakdown.{png,pdf}
      -> docs/results/figures/fig6_concurrency.{png,pdf}
"""
import csv
import glob
import os
import sys
from statistics import mean, stdev

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.analyze import HERE, OUT_DIR  # noqa: E402
from experiments.stats_utils import bootstrap_ci  # noqa: E402

STAGES = [("detect_s", "Detect"), ("diagnose_s", "Diagnose"), ("fix_s", "Fix"), ("validate_s", "Validate")]


def load(directory: str = HERE) -> list[dict]:
    rows = []
    for path in sorted(glob.glob(os.path.join(directory, "pipeline_*.csv"))):
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                r["source"] = os.path.basename(path)
                for k in ("detect_s", "diagnose_s", "fix_s", "validate_s", "mttr_s"):
                    r[k] = float(r[k]) if r[k] != "" else None
                r["retries"] = int(r["retries"] or 0)
                r["concurrency"] = int(r["concurrency"]) if r.get("concurrency") else 1
                rows.append(r)
    return rows


def _ok(rows):
    return [r for r in rows if r["result"] == "RECOVERED" and r["mttr_s"] is not None]


def _fmt(vals):
    lo, hi = bootstrap_ci(vals)
    sd = stdev(vals) if len(vals) > 1 else 0.0
    return f"{mean(vals):.2f}s (SD {sd:.2f}), 95% CI [{lo:.2f}, {hi:.2f}]"


def analyze(rows: list[dict]) -> dict:
    real = [r for r in rows if r.get("service") == "nginx" and not r.get("scenario")]
    rows = [r for r in rows if r not in real]
    single = [r for r in rows if not r.get("scenario")]
    scen = [r for r in rows if r.get("scenario")]
    out = {"n": len(rows), "real": {"n": len(real), "recovered": len(_ok(real)),
                                    "mttr": [r["mttr_s"] for r in _ok(real)],
                                    "detect": [r["detect_s"] for r in _ok(real) if r["detect_s"] is not None],
                                    "validate": [r["validate_s"] for r in _ok(real) if r["validate_s"] is not None]}}

    ok = _ok(single)
    out["single"] = {
        "n": len(single), "recovered": len(ok),
        "mttr": [r["mttr_s"] for r in ok],
        "stages": {k: mean(r[k] for r in ok if r[k] is not None) for k, _ in STAGES} if ok else {},
    }
    by_fault = {}
    for ft in sorted({r["fault_type"] for r in single}):
        v = [r["mttr_s"] for r in _ok([r for r in single if r["fault_type"] == ft])]
        by_fault[ft] = v
    out["by_fault"] = by_fault

    # Staggered cascades are not "simultaneous": keep them out of the concurrency curve.
    from fault_injector.scenarios import SCENARIOS
    simult = [r for r in scen if SCENARIOS.get(r["scenario"], {}).get("kind") != "cascade"]
    by_conc = {}
    for c in sorted({r["concurrency"] for r in simult}):
        v = [r["mttr_s"] for r in _ok([r for r in simult if r["concurrency"] == c])]
        by_conc[c] = v
    out["by_concurrency"] = by_conc
    out["by_scenario"] = {
        s: [r["mttr_s"] for r in _ok([r for r in scen if r["scenario"] == s])]
        for s in sorted({r["scenario"] for r in scen})
    }
    out["all_recovered"] = all(r["result"] == "RECOVERED" for r in rows) if rows else False
    out["max_retries"] = max((r["retries"] for r in rows), default=0)
    return out


def render(res: dict, poll: float = 1.0) -> str:
    s = res["single"]
    L = ["# End-to-end pipeline latency", "",
         f"{res['n']} incidents through the real event-bus pipeline (rule-based diagnosis, {poll:g}s monitor poll). "
         "Unlike the diagnosis-only benchmark, MTTR here starts at fault injection and therefore includes "
         "detection latency.", ""]
    if s["mttr"]:
        L += ["## Single faults (all simulated services x all fault types)", "",
              f"- Incidents: {s['n']}, recovered: {s['recovered']}",
              f"- MTTR: {_fmt(s['mttr'])}", "",
              "Where the time goes (mean per stage):", "", "| Stage | Mean (s) | Share |", "|---|---|---|"]
        total = sum(s["stages"].values())
        for key, label in STAGES:
            v = s["stages"][key]
            L.append(f"| {label} | {v:.2f} | {v / total * 100:.0f}% |")
        L += ["", "Detection is bounded by the monitor poll interval (expected ≈ poll/2 plus scheduling) and "
              "validation by a fixed 2s settle wait, so these two stages dominate. With the production default "
              "of a 5s poll, expected detection rises to ≈ 2.5s; the LLM adds its own network latency on top "
              "in `--mode llm`.", "", "| Fault | MTTR |", "|---|---|"]
        for ft, v in res["by_fault"].items():
            if v:
                L.append(f"| {ft} | {_fmt(v)} (n={len(v)}) |")
    if res["by_concurrency"]:
        L += ["", "## Concurrent and cascading incidents", "",
              "Each incident is timed from its own injection (staggered cascades are listed separately, not counted as "
              "simultaneous). If the pipeline serialised work, MTTR would grow roughly linearly with the number "
              "of simultaneous incidents; here it rises only modestly.", "",
              "| Simultaneous incidents | MTTR per incident |", "|---|---|"]
        for c, v in res["by_concurrency"].items():
            L.append(f"| {c} | {_fmt(v)} (n={len(v)}) |")
        L += ["", "| Scenario | MTTR per incident |", "|---|---|"]
        for sc, v in res["by_scenario"].items():
            L.append(f"| {sc} | {_fmt(v)} (n={len(v)}) |")
    rl = res.get("real", {})
    if rl.get("n"):
        L += ["", "## Real container (Nginx under Docker)", "",
              "A real `nginx` container joins as a sixth service. The fault is `docker stop`; the fix is a real "
              "`docker restart`; validation re-reads the container's real health. Rule-based diagnosis, "
              f"{poll:g}s monitor poll. Reported separately from the simulated services above.", "",
              f"- Incidents: {rl['n']}, recovered: {rl['recovered']}",
              f"- MTTR: {_fmt(rl['mttr'])}",
              f"- Detection: {_fmt(rl['detect'])}",
              f"- Validation: {_fmt(rl['validate'])}", "",
              "Caveats: only the `crash` fault has a real equivalent; the real service restarts the container "
              "whichever fix label is chosen, so this run shows the pipeline healing a genuinely stopped process, "
              "not fix-selection quality. Real restart plus a health-check wait makes MTTR several times the "
              "simulated figure."]
    L += ["", f"All incidents recovered: **{res['all_recovered']}**; maximum retries used: **{res['max_retries']}**.",
          "", "## Caveat", "",
          "These runs used any-fix-heals (`STRICT_HEALING=0`, the runner's default), so first-try success on the "
          "simulated services is 100% by construction; the application itself now defaults to strict healing. "
          "Retry and escalation are measured in `verification-under-noise.md` and `strategy-comparison.md`; the "
          "real Nginx container (see `run_pipeline.py --service nginx`) is where a real fix can fail.", ""]
    return "\n".join(L)


def figures(res: dict):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from experiments.make_figures import AQUA, BLUE, FIG_DIR, GRID, INK2, ORANGE, _save  # noqa: F401

    os.makedirs(FIG_DIR, exist_ok=True)
    st = res["single"]["stages"]
    if st:
        fig, ax = plt.subplots(figsize=(6.4, 2.2))
        colors = [BLUE, ORANGE, AQUA, "#6250d6"]
        left = 0.0
        for (key, label), c in zip(STAGES, colors):
            v = st[key]
            ax.barh(0, v, left=left, color=c, edgecolor="white", linewidth=1.5, height=0.5, label=f"{label} {v:.2f}s")
            left += v
        ax.set_yticks([])
        ax.set_xlabel("Seconds from fault injection to verified recovery")
        ax.set_title("Where recovery time goes", loc="left", fontsize=10, fontweight="bold")
        ax.grid(axis="y", visible=False)
        ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.45), fontsize=8)
        _save(fig, "fig5_stage_breakdown")

    conc = res["by_concurrency"]
    if len(conc) > 1:
        fig, ax = plt.subplots(figsize=(6.4, 2.8))
        xs = sorted(conc)
        ys = [mean(conc[x]) for x in xs]
        errs = [[mean(conc[x]) - bootstrap_ci(conc[x])[0] for x in xs], [bootstrap_ci(conc[x])[1] - mean(conc[x]) for x in xs]]
        ax.errorbar(xs, ys, yerr=errs, fmt="o-", color=BLUE, ms=6, mec="white", mew=1.0, lw=1.6, capsize=3)
        ax.set_xticks(xs)
        ax.set_ylim(0, max(ys) * 1.6)
        ax.set_xlabel("Incidents open at the same time")
        ax.set_ylabel("MTTR per incident (s)")
        ax.set_title("Recovery time under concurrent incidents", loc="left", fontsize=10, fontweight="bold")
        _save(fig, "fig6_concurrency")


def main():
    rows = load()
    if not rows:
        raise SystemExit("no pipeline_*.csv files; run experiments.run_pipeline first")
    res = analyze(rows)
    with open(os.path.join(OUT_DIR, "pipeline-latency.md"), "w", encoding="utf-8") as f:
        f.write(render(res))
    figures(res)
    print("wrote pipeline-latency.md")


if __name__ == "__main__":
    main()
