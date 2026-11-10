"""
stats_utils.py
==============
Small, dependency-light statistical helpers used by analyze.py.

Why these choices (and not a plain t-test):
- Accuracy is a proportion near 100%; the normal approximation breaks
  there, so we use the Wilson score interval.
- MTTR is right-skewed with small n; we use a percentile bootstrap CI and
  non-parametric tests (Mann-Whitney, Kruskal-Wallis).
- LLM vs rule-based diagnoses are PAIRED (same trial, same metrics), so the
  right test for accuracy is an exact McNemar test on discordant pairs.
- Multiple pairwise comparisons are Holm-corrected.
"""
import math
import random
from statistics import mean

from scipy import stats


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def bootstrap_ci(values: list[float], stat=mean, n_boot: int = 5000,
                 alpha: float = 0.05, seed: int = 7) -> tuple[float, float]:
    """Percentile bootstrap CI (deterministic for a given seed)."""
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    k = len(values)
    boots = sorted(stat([values[rng.randrange(k)] for _ in range(k)]) for _ in range(n_boot))
    lo = boots[int((alpha / 2) * n_boot)]
    hi = boots[min(int((1 - alpha / 2) * n_boot), n_boot - 1)]
    return (lo, hi)


def mcnemar_exact(a_correct: list[bool], b_correct: list[bool]) -> dict:
    """
    Exact (binomial) McNemar test for paired binary outcomes.
    b = A right & B wrong, c = A wrong & B right. H0: b and c equally likely.
    """
    if len(a_correct) != len(b_correct):
        raise ValueError("paired samples must have equal length")
    b = sum(1 for x, y in zip(a_correct, b_correct) if x and not y)
    c = sum(1 for x, y in zip(a_correct, b_correct) if not x and y)
    n = b + c
    p = 1.0 if n == 0 else min(1.0, 2 * stats.binom.cdf(min(b, c), n, 0.5))
    return {"a_only_correct": b, "b_only_correct": c, "discordant": n, "p_value": p}


def holm(pvalues: list[float]) -> list[float]:
    """Holm-Bonferroni adjusted p-values, returned in the input order."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvalues[i]))
        adjusted[i] = running
    return adjusted


def cliffs_delta(x: list[float], y: list[float]) -> float:
    """Effect size in [-1, 1]: P(x>y) - P(x<y)."""
    if not x or not y:
        return 0.0
    gt = sum(1 for a in x for b in y if a > b)
    lt = sum(1 for a in x for b in y if a < b)
    return (gt - lt) / (len(x) * len(y))


def mann_whitney(x: list[float], y: list[float]) -> float:
    if len(set(x) | set(y)) < 2:
        return 1.0
    return float(stats.mannwhitneyu(x, y, alternative="two-sided").pvalue)


def kruskal(groups: list[list[float]]) -> float:
    groups = [g for g in groups if g]
    if len(groups) < 2 or len({v for g in groups for v in g}) < 2:
        return 1.0
    return float(stats.kruskal(*groups).pvalue)
