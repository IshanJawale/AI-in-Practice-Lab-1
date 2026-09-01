"""Token accounting and hard budget enforcement.

Cost is a first-class metric in this module, not an afterthought. Every lab
asks you to report it. A system that is 2% more accurate for 40x the money is
usually the wrong system, and you cannot know that unless you measure.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field

from aip.config import FREE_PREFIXES, PRICES_PER_MTOK, settings


class BudgetExceeded(RuntimeError):
    """Raised when a call would push spend past the configured ceiling."""


def is_priced(model: str) -> bool:
    """Can we state what this call cost?

    Three cases, and conflating them is how a cost meter lies:
      * a model in PRICES_PER_MTOK  -> priced, report the number
      * ollama/* or local/*         -> genuinely free, $0.00 is CORRECT
      * anything else               -> UNPRICED. We do not know.

    The third case used to return 0.00 like the second. That is a silent,
    confident lie about a paid API -- exactly the class of bug this module
    spends a whole session on. NVIDIA NIM publishes no per-token pricing, so
    it lands here, and the meter now says so out loud.
    """
    return model in PRICES_PER_MTOK or model.startswith(FREE_PREFIXES)


def price_of(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """USD cost of one call, or 0.0 if the model is unpriced.

    Always pair this with is_priced(). A bare 0.0 from this function means
    either "free" or "unknown", and the caller has to know which.
    """
    inp, out = PRICES_PER_MTOK.get(model, (0.0, 0.0))
    return (prompt_tokens * inp + completion_tokens * out) / 1_000_000


@dataclass
class Usage:
    """One row of the ledger."""

    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    cached: bool = False
    calls: int = 0
    priced: bool = True

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            model=self.model or other.model,
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            cost_usd=self.cost_usd + other.cost_usd,
            latency_ms=self.latency_ms + other.latency_ms,
            cached=self.cached and other.cached,
            calls=self.calls + other.calls,
            priced=self.priced and other.priced,
        )


@dataclass
class Budget:
    """A spend ceiling with a ledger. Use as a context manager.

        with Budget(limit_usd=0.25, label="lab1-extraction") as b:
            for ticket in tickets:
                extract(ticket)
        print(b.report())

    The global ceiling (AIP_BUDGET_USD) always applies on top of this. Nested
    budgets are supported; the innermost trips first.
    """

    limit_usd: float = 1.0
    label: str = "unnamed"
    spent_usd: float = 0.0
    calls: int = 0
    cached_calls: int = 0
    unpriced_calls: int = 0
    unpriced_models: set[str] = field(default_factory=set)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record(self, usage: Usage) -> None:
        with self._lock:
            self.calls += 1
            if usage.cached:
                self.cached_calls += 1
            if not usage.priced:
                self.unpriced_calls += 1
                if usage.model:
                    self.unpriced_models.add(usage.model)
            self.prompt_tokens += usage.prompt_tokens
            self.completion_tokens += usage.completion_tokens
            self.spent_usd += usage.cost_usd
            self.latencies_ms.append(usage.latency_ms)
        if self.spent_usd > self.limit_usd:
            raise BudgetExceeded(
                f"[{self.label}] spent ${self.spent_usd:.4f} > limit ${self.limit_usd:.4f} "
                f"after {self.calls} calls. Raise the limit deliberately, or find out "
                f"why the loop is costing more than you expected."
            )

    def percentile(self, p: float) -> float:
        if not self.latencies_ms:
            return 0.0
        xs = sorted(self.latencies_ms)
        idx = min(len(xs) - 1, int(round((p / 100.0) * (len(xs) - 1))))
        return xs[idx]

    def report(self) -> str:
        hit_rate = (self.cached_calls / self.calls * 100) if self.calls else 0.0
        cost = f"cost=${self.spent_usd:.4f}"
        if self.unpriced_calls:
            # Never let an unpriced run masquerade as a free one.
            cost = (f"cost=${self.spent_usd:.4f} + {self.unpriced_calls} UNPRICED "
                    f"call{'s' if self.unpriced_calls != 1 else ''} "
                    f"({', '.join(sorted(self.unpriced_models))})")
        return (
            f"[{self.label}] calls={self.calls} (cache hits {hit_rate:.0f}%) "
            f"tokens={self.prompt_tokens}in/{self.completion_tokens}out "
            f"{cost} "
            f"latency p50={self.percentile(50):.0f}ms p95={self.percentile(95):.0f}ms"
        )

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "calls": self.calls,
            "cached_calls": self.cached_calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost_usd": round(self.spent_usd, 6),
            "unpriced_calls": self.unpriced_calls,
            "unpriced_models": sorted(self.unpriced_models),
            "latency_p50_ms": round(self.percentile(50), 1),
            "latency_p95_ms": round(self.percentile(95), 1),
        }

    def __enter__(self) -> "Budget":
        _ACTIVE.append(self)
        return self

    def __exit__(self, *exc) -> None:
        if _ACTIVE and _ACTIVE[-1] is self:
            _ACTIVE.pop()


_ACTIVE: list[Budget] = []
_GLOBAL = Budget(limit_usd=settings.budget_usd, label="process-total")


def record(usage: Usage) -> None:
    """Called by aip.llm / aip.embed after every model call."""
    _GLOBAL.record(usage)
    for b in _ACTIVE:
        b.record(usage)


def global_budget() -> Budget:
    return _GLOBAL
