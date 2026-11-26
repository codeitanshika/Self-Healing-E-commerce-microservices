"""
make_figures.py
===============
Publication figures (PNG + vector PDF) generated straight from the raw
trial CSVs, so they can always be regenerated and never drift from the data.

    python -m experiments.make_figures      # -> docs/results/figures/

Design notes (data-viz rules): one axis per chart, thin marks, recessive
grid, series colours in a fixed validated order (never cycled), every
series direct-labelled or in a legend, and magnitude-on-log shown as dots
(a bar on a log axis misleads because its length has no zero baseline).
"""
import os
import random
import sys
from statistics import mean

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from experiments.analyze import HERE, OUT_DIR, load_trials  # noqa: E402
from experiments.stats_utils import bootstrap_ci, wilson_ci  # noqa: E402

FIG_DIR = os.path.join(OUT_DIR, "figures")

# Validated categorical slots 1-3 (light surface), fixed order.
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
SERIES = [BLUE, ORANGE, AQUA]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e1"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.axisbelow": True, "figure.dpi": 100, "savefig.dpi": 220,
    "legend.frameon": False,
})

NICE = {
    "openai_gpt_oss_120b": "gpt-oss-120b",
    "openai_gpt_oss_20b": "gpt-oss-20b",
    "qwen_qwen3_8_27b": "qwen3-27b",
}


def _save(fig, name):
    os.makedirs(FIG_DIR, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG_DIR, f"{name}.{ext}"), bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", name)


def fig_mttr_by_fault(models):
    faults = sorted({r["fault_type"] for rows in models.values() for r in rows})
    fig, ax = plt.subplots(figsize=(6.4, 3.3))
    width = 0.24
    for mi, (m, rows) in enumerate(models.items()):
        for fi, f in enumerate(faults):
            vals = [r["mttr_seconds"] for r in rows if r["fault_type"] == f and r["recovered"]]
            lo, hi = bootstrap_ci(vals)
            x = fi + (mi - 1) * (width + 0.02)
            ax.bar(x, mean(vals), width, color=SERIES[mi], label=NICE.get(m, m) if fi == 0 else None,
                   yerr=[[mean(vals) - lo], [hi - mean(vals)]], error_kw={"ecolor": INK2, "lw": 0.9, "capsize": 2})
    ax.set_xticks(range(len(faults)), faults)
    ax.set_ylabel("Mean MTTR (s)")
    ax.set_title("Recovery time by fault type and model", loc="left", fontsize=10, fontweight="bold")
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, 4.6)
    ax.legend(ncol=3, loc="upper left", bbox_to_anchor=(0, 1.0))
    ax.text(1.0, -0.2, "Bars: mean; whiskers: 95% bootstrap CI; n=15 per bar. Includes a fixed 2 s validation wait.",
            transform=ax.transAxes, ha="right", fontsize=7, color=INK2)
    _save(fig, "fig1_mttr_by_fault")


def fig_mttr_distribution(models):
    fig, ax = plt.subplots(figsize=(6.4, 3.1))
    rng = random.Random(3)
    for i, (m, rows) in enumerate(models.items()):
        vals = [r["mttr_seconds"] for r in rows if r["recovered"]]
        ax.boxplot(vals, positions=[i], widths=0.45, showfliers=False, patch_artist=True,
                   boxprops={"facecolor": "none", "edgecolor": SERIES[i], "linewidth": 1.4},
                   medianprops={"color": SERIES[i], "linewidth": 2},
                   whiskerprops={"color": SERIES[i]}, capprops={"color": SERIES[i]})
        ax.scatter([i + rng.uniform(-0.17, 0.17) for _ in vals], vals, s=7, color=SERIES[i], alpha=0.45,
                   edgecolors="white", linewidths=0.3)
    ax.set_xticks(range(len(models)), [NICE.get(m, m) for m in models])
    ax.set_ylabel("MTTR (s)")
    ax.set_title("Distribution of recovery times (60 trials per model)", loc="left", fontsize=10, fontweight="bold")
    ax.grid(axis="x", visible=False)
    _save(fig, "fig2_mttr_distribution")


def fig_accuracy(models):
    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    labels, y = [], 0
    for m, rows in models.items():
        for name, key, color, off in (("LLM", "llm_correct", BLUE, 0.12), ("Rules", "rule_correct", ORANGE, -0.12)):
            k = sum(r[key] for r in rows)
            n = len(rows)
            lo, hi = wilson_ci(k, n)
            ax.errorbar(100 * k / n, y + off, xerr=[[max(0.0, 100 * (k / n - lo))], [max(0.0, 100 * (hi - k / n))]], fmt="o",
                        color=color, ms=6, mec="white", mew=1.0, elinewidth=1.4, capsize=3,
                        label=name if y == 0 else None)
        labels.append(NICE.get(m, m))
        y += 1
    ax.set_yticks(range(len(labels)), labels)
    ax.invert_yaxis()
    ax.set_xlim(85, 100.8)
    ax.set_xlabel("Diagnosis accuracy (%) with 95% Wilson interval")
    ax.set_title("LLM vs. rule-based diagnosis accuracy", loc="left", fontsize=10, fontweight="bold")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower left")
    _save(fig, "fig3_accuracy")


def fig_baselines(models):
    pooled = [r["mttr_seconds"] for rows in models.values() for r in rows if r["recovered"]]
    ours = mean(pooled)
    items = [("This system (mean)", ours, BLUE), ("Manual baseline (assumed)", 900, INK2),
             ("Industry avg. (PagerDuty)", 7560, INK2)]
    fig, ax = plt.subplots(figsize=(6.4, 2.4))
    for i, (name, v, c) in enumerate(items):
        ax.hlines(i, 1, v, color=GRID, lw=1.2, zorder=1)
        ax.scatter(v, i, s=70, color=c, zorder=3, edgecolors="white", linewidths=1.2)
        ax.text(v * 1.18, i, f"{v:,.1f} s" if v < 100 else f"{v:,.0f} s", va="center", fontsize=8.5, color=INK)
    ax.set_xscale("log")
    ax.set_xlim(1, 40000)
    ax.set_yticks(range(len(items)), [n for n, _, _ in items])
    ax.invert_yaxis()
    ax.set_xlabel("Time to recovery (s, log scale)")
    ax.set_title("Recovery time vs. manual response", loc="left", fontsize=10, fontweight="bold")
    ax.text(0.0, -0.32, f"{900 / ours:.0f}x faster than the assumed 900 s manual baseline.",
            transform=ax.transAxes, fontsize=7.5, color=INK2)
    ax.grid(axis="y", visible=False)
    _save(fig, "fig4_baselines")


def main():
    models = load_trials(HERE)
    fig_mttr_by_fault(models)
    fig_mttr_distribution(models)
    fig_accuracy(models)
    fig_baselines(models)


if __name__ == "__main__":
    main()
