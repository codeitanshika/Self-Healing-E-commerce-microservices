import math

from experiments import analyze
from experiments.stats_utils import (
    bootstrap_ci, cliffs_delta, holm, kruskal, mann_whitney, mcnemar_exact, wilson_ci,
)


def test_wilson_matches_known_value():
    lo, hi = wilson_ci(59, 60)
    assert math.isclose(lo, 0.911, abs_tol=0.002) and math.isclose(hi, 0.997, abs_tol=0.002)
    assert wilson_ci(0, 0) == (0.0, 0.0)
    assert math.isclose(wilson_ci(60, 60)[1], 1.0)


def test_bootstrap_ci_brackets_the_mean_and_is_deterministic():
    vals = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    lo, hi = bootstrap_ci(vals)
    assert lo < 3.5 < hi
    assert bootstrap_ci(vals) == (lo, hi)
    assert bootstrap_ci([]) == (0.0, 0.0)


def test_mcnemar_exact():
    r = mcnemar_exact([True] * 10, [True] * 10)
    assert r["discordant"] == 0 and r["p_value"] == 1.0
    strong = mcnemar_exact([True] * 12 + [False] * 0, [False] * 12)
    assert strong["p_value"] < 0.01 and strong["a_only_correct"] == 12


def test_holm_is_monotone_and_never_below_raw():
    raw = [0.01, 0.04, 0.03]
    adj = holm(raw)
    assert all(a >= r for a, r in zip(adj, raw))
    assert math.isclose(adj[0], 0.03) and all(a <= 1 for a in adj)


def test_cliffs_delta_and_rank_tests():
    assert cliffs_delta([5, 6, 7], [1, 2, 3]) == 1.0
    assert cliffs_delta([1, 2], [1, 2]) == 0.0
    assert mann_whitney([1, 1, 1], [1, 1, 1]) == 1.0
    assert mann_whitney([1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12]) < 0.05
    assert kruskal([[1, 2], []]) == 1.0


def _trial(model_ok=True, mttr=3.0, fault="crash"):
    return {"llm_correct": model_ok, "rule_correct": True, "mttr_seconds": mttr,
            "recovered": True, "fault_type": fault}


def test_analyze_end_to_end_and_markdown_wording():
    models = {"a": [_trial(mttr=2.0 + i / 10) for i in range(10)],
              "b": [_trial(mttr=5.0 + i / 10) for i in range(10)]}
    res = analyze.analyze(models)
    assert res["n_trials"] == 20
    assert res["pooled"]["llm_accuracy"]["rate"] == 1.0
    assert res["model_mttr_kruskal_p"] < 0.05
    md = analyze.render_markdown(res)
    assert "p = <" not in md and "Wilson" in md
