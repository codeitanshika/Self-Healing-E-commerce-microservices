"""
analyze.py
==========
Turns the raw per-trial experiment CSVs into the statistics the paper
reports: confidence intervals, significance tests and effect sizes.

    python -m experiments.analyze            # writes docs/results/statistics.{md,json}

Input : experiments/results_<model>.csv   (one row per trial)
Output: docs/results/statistics.md  (human-readable)
        docs/results/statistics.json (machine-readable, used by figures)
"""
import csv
import glob
import json
import os
import sys
from statistics import mean, stdev

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.stats_utils import (  # noqa: E402
    bootstrap_ci, cliffs_delta, holm, kruskal, mann_whitney, mcnemar_exact, wilson_ci,
)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(HERE)), "docs", "results")


def load_trials(directory: str = HERE) -> dict[str, list[dict]]:
    """model_name -> list of trial dicts (summary files and archives excluded)."""
    models = {}
    for path in sorted(glob.glob(os.path.join(directory, "results_*.csv"))):
        if path.endswith("_summary.csv"):
            continue
        name = os.path.basename(path)[len("results_"):-len(".csv")]
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            r["llm_correct"] = r["llm_correct"] == "True"
            r["rule_correct"] = r["rule_correct"] == "True"
            r["mttr_seconds"] = float(r["mttr_seconds"])
            r["recovered"] = r["result"] == "RECOVERED"
        models[name] = rows
    return models


def _prop(flags: list[bool]) -> dict:
    k, n = sum(flags), len(flags)
    lo, hi = wilson_ci(k, n)
    return {"k": k, "n": n, "rate": k / n if n else 0.0, "ci": [lo, hi]}


def _mttr(rows: list[dict]) -> dict:
    vals = [r["mttr_seconds"] for r in rows if r["recovered"]]
    if not vals:
        return {"n": 0}
    lo, hi = bootstrap_ci(vals)
    return {
        "n": len(vals), "mean": mean(vals), "sd": stdev(vals) if len(vals) > 1 else 0.0,
        "min": min(vals), "max": max(vals), "ci": [lo, hi],
    }


def analyze(models: dict[str, list[dict]], baseline: float = 900.0) -> dict:
    pooled = [r for rows in models.values() for r in rows]
    out: dict = {"baseline_seconds": baseline, "n_trials": len(pooled)}

    out["per_model"] = {
        m: {
            "llm_accuracy": _prop([r["llm_correct"] for r in rows]),
            "rule_accuracy": _prop([r["rule_correct"] for r in rows]),
            "recovery": _prop([r["recovered"] for r in rows]),
            "mttr": _mttr(rows),
        }
        for m, rows in models.items()
    }
    out["pooled"] = {
        "llm_accuracy": _prop([r["llm_correct"] for r in pooled]),
        "rule_accuracy": _prop([r["rule_correct"] for r in pooled]),
        "recovery": _prop([r["recovered"] for r in pooled]),
        "mttr": _mttr(pooled),
    }
    pm = out["pooled"]["mttr"]
    if pm.get("n"):
        pm["reduction_vs_baseline"] = 1 - pm["mean"] / baseline
        pm["speedup_vs_baseline"] = baseline / pm["mean"]

    # Paired test: do the LLM and the rule baseline differ in accuracy?
    out["llm_vs_rules"] = mcnemar_exact(
        [r["llm_correct"] for r in pooled], [r["rule_correct"] for r in pooled]
    )

    # Does the choice of LLM change recovery time?
    groups = {m: [r["mttr_seconds"] for r in rows if r["recovered"]] for m, rows in models.items()}
    out["model_mttr_kruskal_p"] = kruskal(list(groups.values()))
    names = list(groups)
    pairs, raw = [], []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            raw.append(mann_whitney(groups[names[i]], groups[names[j]]))
            pairs.append((names[i], names[j]))
    adj = holm(raw) if raw else []
    out["model_pairwise"] = [
        {"a": a, "b": b, "p_raw": p, "p_holm": q,
         "cliffs_delta": cliffs_delta(groups[a], groups[b])}
        for (a, b), p, q in zip(pairs, raw, adj)
    ]

    # Per fault type (pooled across models)
    by_fault = {}
    for ft in sorted({r["fault_type"] for r in pooled}):
        rows = [r for r in pooled if r["fault_type"] == ft]
        by_fault[ft] = {
            "llm_accuracy": _prop([r["llm_correct"] for r in rows]),
            "rule_accuracy": _prop([r["rule_correct"] for r in rows]),
            "mttr": _mttr(rows),
        }
    out["by_fault"] = by_fault
    fault_groups = [[r["mttr_seconds"] for r in pooled if r["fault_type"] == ft and r["recovered"]]
                    for ft in by_fault]
    out["fault_mttr_kruskal_p"] = kruskal(fault_groups)

    # Variance decomposition: how much of the spread is the 2s validation wait?
    out["note_floor_seconds"] = 2.0
    return out


def _pct(x: float, d: int = 1) -> str:
    return f"{x * 100:.{d}f}%"


def _ci(p: dict) -> str:
    return f"{_pct(p['rate'])} ({p['k']}/{p['n']}), 95% CI [{_pct(p['ci'][0])}, {_pct(p['ci'][1])}]"


def _p(p: float) -> str:
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def _peq(p: float) -> str:
    """'p < 0.001' / 'p = 0.034' (never 'p = < 0.001')."""
    return f"p {_p(p)}" if p < 0.001 else f"p = {_p(p)}"


def render_markdown(res: dict) -> str:
    L = ["# Statistical analysis of the experiment suite", "",
         f"Generated by `python -m experiments.analyze` from {res['n_trials']} trials. "
         "Proportions use Wilson 95% intervals; MTTR intervals are percentile-bootstrap (5,000 resamples).", ""]

    pooled = res["pooled"]
    L += ["## Headline (pooled over all models)", "",
          f"- LLM diagnosis accuracy: {_ci(pooled['llm_accuracy'])}",
          f"- Rule-based accuracy: {_ci(pooled['rule_accuracy'])}",
          f"- Recovery rate: {_ci(pooled['recovery'])}"]
    m = pooled["mttr"]
    L += [f"- Mean MTTR: {m['mean']:.2f}s (SD {m['sd']:.2f}s), 95% CI [{m['ci'][0]:.2f}, {m['ci'][1]:.2f}]s",
          f"- Reduction vs {res['baseline_seconds']:.0f}s manual baseline: {_pct(m['reduction_vs_baseline'], 2)} "
          f"({m['speedup_vs_baseline']:.0f}x faster)", ""]

    t = res["llm_vs_rules"]
    L += ["## LLM vs. rule-based diagnosis (paired, exact McNemar)", "",
          f"Discordant pairs: LLM-only-correct = {t['a_only_correct']}, rules-only-correct = {t['b_only_correct']}. "
          f"{_peq(t['p_value'])}. "
          + ("No significant difference: on this fault taxonomy the LLM does not measurably beat simple rules."
             if t["p_value"] >= 0.05 else "The accuracy difference is statistically significant."), ""]

    L += ["## Per model", "", "| Model | LLM accuracy | Rule accuracy | Recovery | Mean MTTR [95% CI] |", "|---|---|---|---|---|"]
    for name, d in res["per_model"].items():
        mt = d["mttr"]
        L.append(f"| {name} | {_ci(d['llm_accuracy'])} | {_ci(d['rule_accuracy'])} | {_pct(d['recovery']['rate'])} | "
                 f"{mt['mean']:.2f}s [{mt['ci'][0]:.2f}, {mt['ci'][1]:.2f}] |")
    L += ["", f"Kruskal-Wallis across models (MTTR): {_peq(res['model_mttr_kruskal_p'])}.", "",
          "| Pair | p (raw) | p (Holm) | Cliff's delta |", "|---|---|---|---|"]
    for c in res["model_pairwise"]:
        L.append(f"| {c['a']} vs {c['b']} | {_p(c['p_raw'])} | {_p(c['p_holm'])} | {c['cliffs_delta']:+.2f} |")

    L += ["", "## Per fault type (pooled)", "", "| Fault | LLM accuracy | Rule accuracy | Mean MTTR [95% CI] |", "|---|---|---|---|"]
    for ft, d in res["by_fault"].items():
        mt = d["mttr"]
        L.append(f"| {ft} | {_ci(d['llm_accuracy'])} | {_ci(d['rule_accuracy'])} | "
                 f"{mt['mean']:.2f}s [{mt['ci'][0]:.2f}, {mt['ci'][1]:.2f}] |")
    L += ["", f"Kruskal-Wallis across fault types (MTTR): {_peq(res['fault_mttr_kruskal_p'])}.", "",
          "## How to read this honestly", "",
          f"- Every trial includes a fixed {res['note_floor_seconds']:.0f}s validation wait, so MTTR cannot fall below ~2s; "
          "differences between models are small relative to that floor.",
          "- Statistical significance is not practical significance: even a significant MTTR gap of a few "
          "tenths of a second is irrelevant next to a 900s manual baseline.",
          "- The faults are simulated and drawn from four classes; accuracy near 100% reflects an easy "
          "taxonomy, not a general guarantee.", ""]
    return "\n".join(L)


def main():
    models = load_trials()
    if not models:
        raise SystemExit("no results_*.csv files found")
    res = analyze(models)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "statistics.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    with open(os.path.join(OUT_DIR, "statistics.md"), "w", encoding="utf-8") as f:
        f.write(render_markdown(res))
    print(f"wrote {OUT_DIR}/statistics.md and statistics.json")


if __name__ == "__main__":
    main()
