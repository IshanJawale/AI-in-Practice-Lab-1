"""Lab 2 — the statistics you are required to run before making a claim.

Two functions. Both are short. Neither is optional.
"""
from __future__ import annotations

import math


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% CI for a proportion, Wilson score interval.

    Preferred over the normal approximation because it does not go outside
    [0, 1] and stays sane at small n and extreme p -- both of which describe
    your 60-case dev set at 0.95 accuracy.
    """
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def paired_test(a_correct: list[bool], b_correct: list[bool]) -> dict:
    """McNemar's test on two systems scored over the SAME items.

    Returns b, c, and an exact two-sided binomial p-value.

    Why paired: item difficulty is the dominant source of variance. Comparing
    two independent proportions makes you fight that variance; comparing the
    same items removes it entirely, and you detect real differences at a
    sample size where unpaired comparison cannot.

        b = A right, B wrong
        c = B right, A wrong
        Under H0, each discordant pair is a fair coin.
    """
    if len(a_correct) != len(b_correct):
        raise ValueError("paired test needs the same items in the same order")
    b = sum(1 for x, y in zip(a_correct, b_correct) if x and not y)
    c = sum(1 for x, y in zip(a_correct, b_correct) if y and not x)
    n = b + c
    if n == 0:
        return {"b": 0, "c": 0, "n_discordant": 0, "p_value": 1.0,
                "verdict": "identical on every item"}

    # Exact two-sided binomial: P(X <= min(b,c)) * 2, clipped at 1.
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    p = min(1.0, 2 * tail)
    better = "B" if c > b else "A"
    return {
        "b": b, "c": c, "n_discordant": n, "p_value": p,
        "verdict": (f"{better} better, p={p:.4f}" if p < 0.05
                    else f"no significant difference (p={p:.4f}) -- choose on cost"),
    }


if __name__ == "__main__":
    print("60 cases, 54 correct ->", wilson_interval(54, 60))
    print("60 cases, 53 correct ->", wilson_interval(53, 60))
    print("  the intervals overlap almost completely. This is why you pair.\n")
    a = [True] * 50 + [False] * 10
    b = [True] * 46 + [False] * 4 + [True] * 8 + [False] * 2
    print(paired_test(a, b))
