"""
sensitivity.py
==============
Does the strategy comparison depend on our hand-written EFFECTIVE_FIXES table?

The closed loop's fix sequence is deterministic given its diagnosis: the first
fix is the diagnoser's own choice, and under RETRY_POLICY=repeat (how the
incidents were recorded) every retry is FIX_MAP[diagnosis]["retry"].
So the 660 recorded strategy incidents can be REPLAYED under any other
"which fix cures which fault" table without re-running the LLMs:

    closed loop recovers  <=>  first fix or the retry fix is effective
    open loop recovers    <=>  first fix is effective
    blind restart         <=>  restart is effective

Sections of the report:
  0. Validation: replaying the ORIGINAL table must reproduce the measured
     closed-loop outcomes (it does, or this script says so).
  1. Hand-built alternative tables (stricter / more permissive / adversarial).
  2. Monte-Carlo over random tables: how often does the closed loop beat the
     open loop and blind restart?

    python -m experiments.sensitivity
      -> docs/results/sensitivity.md, docs/results/figures/fig9_sensitivity.{png,pdf}
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.analyze import OUT_DIR  # noqa: E402
from experiments.analyze_strategies import load  # noqa: E402
from shared.config import EFFECTIVE_FIXES, FIX_MAP  # noqa: E402

FIXES = ["restart", "clear_memory", "reduce_load", "reroute_traffic", "retry_with_backoff"]
FAULTS = ["crash", "memory", "slow", "error"]
SEED = 20260517
N_RANDOM = 2000

TABLES = {
    "original (used in all experiments)": EFFECTIVE_FIXES,
    "strict: exactly one cure per fault": {
        "crash": {"restart"}, "memory": {"clear_memory"},
        "slow": {"reduce_load"}, "error": {"retry_with_backoff"}},
    "wider: restart also cures slow load": {
        "crash": {"restart"}, "memory": {"clear_memory", "restart"},
        "slow": {"reduce_load", "reroute_traffic", "restart"},
        "error": {"retry_with_backoff", "restart"}},
    "adversarial: restart cures everything": {
        "crash": {"restart"}, "memory": {"restart"}, "slow": {"restart", "reduce_load"},
        "error": {"restart"}},
    "no overlap: restart cures crash only": {
        "crash": {"restart"}, "memory": {"clear_memory"},
        "slow": {"reduce_load", "reroute_traffic"}, "error": {"retry_with_backoff"}},
}


def retry_fix(diagnosed: str) -> str:
    return FIX_MAP.get(diagnosed, FIX_MAP["unknown"])["retry"] if diagnosed else ""


def score(rows: list[dict], table: dict) -> dict:
    n = len(rows)
    blind = open_ = closed = 0
    for r in rows:
        eff = table[r["fault"]]
        first = r["first_fix"]
        has_diag = r["result"] != "TIMEOUT"
        blind += "restart" in eff
        o = bool(first) and first in eff
        c = has_diag and (o or retry_fix(r["diagnosed"]) in eff)
        open_ += o
        closed += c
    return {"n": n, "blind": blind / n, "open": open_ / n, "closed": closed / n}


def random_table(rng: random.Random, p: float = 0.4) -> dict:
    t = {}
    for f in FAULTS:
        s = {x for x in FIXES if rng.random() < p}
        t[f] = s or {rng.choice(FIXES)}
    return t


def monte_carlo(rows: list[dict], n: int = N_RANDOM, seed: int = SEED) -> dict:
    rng = random.Random(seed)
    out = {"closed_ge_open": 0, "closed_gt_open": 0, "closed_ge_blind": 0, "closed_gt_blind": 0,
           "d_open": [], "d_blind": [], "n": n}
    for _ in range(n):
        s = score(rows, random_table(rng))
        d_o, d_b = s["closed"] - s["open"], s["closed"] - s["blind"]
        out["d_open"].append(d_o)
        out["d_blind"].append(d_b)
        out["closed_ge_open"] += d_o >= 0
        out["closed_gt_open"] += d_o > 0
        out["closed_ge_blind"] += d_b >= 0
        out["closed_gt_blind"] += d_b > 0
    return out


def _q(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def llm_rows(data: dict) -> list[dict]:
    return [r for name, rows in data.items() if name != "rule_based" for r in rows]


def validate_replay(data: dict) -> tuple[int, int]:
    """Replaying the original table must reproduce the measured closed-loop outcome."""
    rows = [r for rows in data.values() for r in rows]
    ok = sum(1 for r in rows
             if (r["result"] != "TIMEOUT" and (r["first_fix"] in EFFECTIVE_FIXES[r["fault"]]
                                               or retry_fix(r["diagnosed"]) in EFFECTIVE_FIXES[r["fault"]]))
             == r["closed_recovered"])
    return ok, len(rows)


def render(data: dict) -> tuple[str, dict]:
    rows = llm_rows(data)
    ok, total = validate_replay(data)
    mc = monte_carlo(rows)
    L = ["# Sensitivity of the strategy comparison to the fix-effectiveness table", "",
         "The strategy results use a hand-written table saying which fix cures which fault "
         "(`EFFECTIVE_FIXES`). Because the closed loop's fix sequence is deterministic given its "
         "diagnosis, the recorded incidents can be replayed under other tables without re-querying the LLMs. "
         f"Replayed incidents: {len(rows)} (the three real LLMs; the rule baseline is excluded because it never errs).", "",
         "## 0. Replay validation", "",
         f"Replaying the original table reproduces the measured closed-loop outcome on **{ok}/{total}** recorded incidents "
         "(all three LLMs and the rule baseline).", "",
         "## 1. Hand-built alternative tables", "",
         "| Table | Blind restart | Open loop | Closed loop | Closed - open | Closed - blind |",
         "|---|---|---|---|---|---|"]
    hand = {}
    for name, t in TABLES.items():
        s = score(rows, t)
        hand[name] = s
        L.append(f"| {name} | {s['blind']*100:.1f}% | {s['open']*100:.1f}% | {s['closed']*100:.1f}% | "
                 f"{(s['closed']-s['open'])*100:+.1f} pp | {(s['closed']-s['blind'])*100:+.1f} pp |")
    L += ["", "## 2. Random tables", "",
          f"{mc['n']} random tables (seed {SEED}). For each fault, every one of the 5 fixes is independently effective "
          "with probability 0.4 (at least one cure is guaranteed). Same 600 LLM incidents replayed under each table.", "",
          "| Question | Share of tables |", "|---|---|",
          f"| Closed loop at least as good as open loop | {mc['closed_ge_open']/mc['n']*100:.1f}% |",
          f"| Closed loop strictly better than open loop | {mc['closed_gt_open']/mc['n']*100:.1f}% |",
          f"| Closed loop at least as good as blind restart | {mc['closed_ge_blind']/mc['n']*100:.1f}% |",
          f"| Closed loop strictly better than blind restart | {mc['closed_gt_blind']/mc['n']*100:.1f}% |", "",
          f"Closed minus open (percentage points): median {_q(mc['d_open'],.5)*100:+.1f}, "
          f"5th-95th percentile [{_q(mc['d_open'],.05)*100:+.1f}, {_q(mc['d_open'],.95)*100:+.1f}].  ",
          f"Closed minus blind restart: median {_q(mc['d_blind'],.5)*100:+.1f}, "
          f"5th-95th percentile [{_q(mc['d_blind'],.05)*100:+.1f}, {_q(mc['d_blind'],.95)*100:+.1f}].", "",
          "## Reading this honestly", "",
          "- Closed loop >= open loop holds by construction on every table: the closed loop applies the same first fix, "
          "then more. So that comparison cannot flip sign; only its *size* depends on the table.",
          "- Closed loop vs blind restart is the table-dependent claim. If restart cures every fault "
          "(the adversarial row), a blind restart is perfect and the closed loop has no advantage over it "
          "on recovery rate; the closed loop's remaining value there is diagnosis and an audit trail.",
          "- The replay assumes retries repeat `FIX_MAP[diagnosis]['retry']` (`RETRY_POLICY=repeat`, the policy the "
          "incidents were recorded under, not the application's current default) and ignores timing "
          "(MTTR is not re-estimated).", ""]
    return "\n".join(L), {"mc": mc, "hand": hand, "replay": (ok, total)}


def figure(info: dict):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from experiments.make_figures import AQUA, BLUE, _save

    mc = info["mc"]
    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    bins = [x / 100 for x in range(-30, 41, 2)]
    ax.hist([d for d in mc["d_blind"]], bins=bins, color=BLUE, alpha=0.85, label="Closed - blind restart")
    ax.hist([d for d in mc["d_open"]], bins=bins, color=AQUA, alpha=0.85, label="Closed - open loop")
    ax.axvline(0, color="#52514e", lw=0.9)
    ax.set_xlabel("Recovery-rate difference across random effectiveness tables (fraction of incidents)")
    ax.set_ylabel("Tables")
    ax.set_title("Sensitivity to the fix-effectiveness table", loc="left", fontsize=10, fontweight="bold")
    ax.legend(loc="upper left")
    _save(fig, "fig9_sensitivity")


def main():
    data = load()
    if not data:
        raise SystemExit("no strategies_*.csv found")
    text, info = render(data)
    with open(os.path.join(OUT_DIR, "sensitivity.md"), "w", encoding="utf-8") as f:
        f.write(text)
    figure(info)
    print("wrote sensitivity.md")


if __name__ == "__main__":
    main()
