"""
The statistics behind the Keith study, written out by hand so every step is visible
(no SciPy needed).

The question for each position: the Keith count says "take" or "pass".
Do the dice let us reject that verdict?

    Keith says TAKE  ->  H0: p <= T   (roller wins at most T, so taking is right)
    Keith says PASS  ->  H0: p >= T
    where p is the roller's true win probability and T is the take point (0.75).

Each position gives an exact one-sided binomial p-value. Because we test hundreds
of positions at once, some would look significant by luck alone, so we control
the family-wise error rate with Holm's (1979) step-down procedure.
"""
from __future__ import annotations

import math


def _log_pmf(k: int, n: int, p: float) -> float:
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
            + k * math.log(p) + (n - k) * math.log1p(-p))


def _tail_sum(ks: range, n: int, p: float) -> float:
    logs = [_log_pmf(i, n, p) for i in ks]
    if not logs:
        return 0.0
    m = max(logs)
    return math.exp(m) * sum(math.exp(x - m) for x in logs)


def binom_sf(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p). Sums whichever tail is shorter."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    if n - k < k:
        return min(1.0, _tail_sum(range(k, n + 1), n, p))
    return max(0.0, 1.0 - _tail_sum(range(0, k), n, p))


def binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p)."""
    if k >= n:
        return 1.0
    return 1.0 - binom_sf(k + 1, n, p)


def p_value_against_verdict(wins: int, n: int, says_take: bool, threshold: float) -> float:
    """Small p-value = strong evidence that the rule's verdict is wrong."""
    if says_take:                       # rule says take; evidence against = many roller wins
        return binom_sf(wins, n, threshold)
    return binom_cdf(wins, n, threshold)


def holm(p_values: list[float], alpha: float = 0.05) -> tuple[list[bool], list[float]]:
    """
    Holm step-down. Sort p-values ascending; compare the i-th smallest (i = 0..m-1)
    with alpha / (m - i); stop at the first failure. Returns (rejected, adjusted p).
    """
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    rejected = [False] * m
    adjusted = [1.0] * m
    running_max = 0.0
    still_rejecting = True
    for rank, i in enumerate(order):
        adj = min(1.0, (m - rank) * p_values[i])
        running_max = max(running_max, adj)          # adjusted p-values must be monotone
        adjusted[i] = running_max
        if still_rejecting and p_values[i] <= alpha / (m - rank):
            rejected[i] = True
        else:
            still_rejecting = False
    return rejected, adjusted
