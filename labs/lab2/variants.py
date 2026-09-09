#!/usr/bin/env python3
"""Lab 2 — the configurations under test.

Each variant is a callable `str -> dict`. `grid.py` runs them all through the
same harness, so the only thing that differs between rows of your table is the
thing you intended to differ.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import Field

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from aip.llm import StructuredOutputError, structured  # noqa: E402
from labs.lab1.extract import (  # noqa: E402
    SYSTEM_PROMPT, TicketRecordC, apply_business_rules, extract_deterministic,
)

# ---------------------------------------------------------------------------
# A1 — your six chosen examples.
# ---------------------------------------------------------------------------
# Chosen dev-set tickets covering the edge cases from T2 §2.2:
#   - T0054: billing/complaint boundary (refund demanded for agent mis-selling is complaint, not billing)
#   - T0048: ticket with no policy number (teaches policy_number=null rather than hallucinating)
#   - T0112: Hinglish ticket with code-mixed Hindi terms ('Kripya', 'Koi solution batayiye') -> hi-en
#   - T0029: satisfied-but-urgent sentiment trap (polite satisfied tone during NCB inquiry, urgency 1)
#   - T0238: ticket with policy reference only in quoted reply (> line) -> policy_number=null
#   - T0200: hospital bill deduction dispute -> claims category, urgency 3, language hi-en
FEW_SHOT_IDS: list[str] = [
    "T0054",  # teaches: billing vs complaint boundary (mis-selling refund dispute -> complaint)
    "T0048",  # teaches: ticket with no policy number yields policy_number=null
    "T0112",  # teaches: transliterated Hindi ('Kripya', 'batayiye') -> language='hi-en'
    "T0029",  # teaches: polite thanks for claim settlement -> sentiment='satisfied', urgency=1
    "T0238",  # teaches: policy number only in quoted thread must be ignored -> policy_number=null
    "T0200",  # teaches: hospital bill deduction inquiry is category='claims' (not complaint or info)
]

EXEMPLAR_EVIDENCE: dict[str, str] = {
    "T0054": "Your agent mis-sold me this policy.",
    "T0048": "Please add my mother as a dependent on my policy.",
    "T0112": "Kripya ADD MY MOTHER AS a dependent on my Aurora Bronze policy.",
    "T0029": "Just wanted to confirm whether my no-claim bonus is affected by this claim.",
    "T0238": "I submitted a portability request 21 days ago and heard nothing.",
    "T0200": "My claim on AUR-9674338 was settled at Rs 41800 but the hospital bill was much higher.",
}

EXEMPLAR_REASONING: dict[str, str] = {
    "T0054": "The customer demands a refund due to agent mis-selling waiting periods. Because Aurora's conduct is the primary subject, category is complaint, urgency is 4, sentiment is angry, and no AUR- policy number is in the body.",
    "T0048": "The customer is asking to add a dependent (altering contract), which is policy_change with urgency 2 and neutral sentiment. No policy number is given, so policy_number is null.",
    "T0112": "The customer wants to add a dependent and uses transliterated Hindi ('Kripya', 'Koi solution batayiye'), so language is hi-en, category is policy_change, product is bronze.",
    "T0029": "The customer expresses satisfaction about fast claim settlement and asks general NCB question, urgency 1, sentiment satisfied.",
    "T0238": "The customer asks about a portability request (policy_change, urgency 3). The live body mentions Bronze plan but no AUR- number (only a reference in quoted reply), so policy_number is null.",
    "T0200": "The customer queries a hospital bill deduction. An actual claim settlement is in question, so category is claims, urgency 3, sentiment frustrated, language hi-en ('Koi solution batayiye').",
}


def load_examples(ids: list[str]) -> list[dict]:
    rows = [json.loads(l) for l in
            (ROOT / "data/eval/extraction_dev.jsonl").open(encoding="utf-8")]
    by_id = {r["id"]: r for r in rows}
    missing = [i for i in ids if i not in by_id]
    if missing:
        raise KeyError(f"unknown example ids: {missing}")
    return [by_id[i] for i in ids]


def few_shot_block(ids: list[str], include_reasoning: bool = False) -> str:
    """TODO A2: render the examples into the prompt.

    The example output format must be byte-identical to the format you are
    asking the model to produce. A mismatch here is a classic own goal.
    """
    examples = load_examples(ids)
    blocks: list[str] = []
    for idx, ex in enumerate(examples, 1):
        tid = ex["id"]
        exp = ex["expected"]
        evidence = EXEMPLAR_EVIDENCE.get(tid, ex["input"].split("\n")[0][:100])

        out: dict = {}
        if include_reasoning:
            out["reasoning"] = EXEMPLAR_REASONING.get(
                tid, f"Reasoning for ticket {tid}: category is {exp['category']}."
            )
        out["evidence"] = evidence
        out["category"] = exp["category"]
        out["urgency"] = exp["urgency"]
        out["sentiment"] = exp["sentiment"]
        out["product"] = exp["product"]
        out["language"] = exp["language"]

        rendered_output = json.dumps(out, indent=2)
        blocks.append(
            f"--- Example {idx} ({tid}) ---\n"
            f"Input Ticket:\n{ex['input'].strip()}\n\n"
            f"Output JSON:\n{rendered_output}"
        )
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# The variants
# ---------------------------------------------------------------------------
def zero_shot(ticket: str, tier: str = "SMALL") -> dict:
    """TODO B: Lab 1 Part C, no examples. This is your baseline."""
    try:
        rec = structured(ticket, schema=TicketRecordC, system=SYSTEM_PROMPT, tier=tier)
        d = rec.model_dump()
    except StructuredOutputError as exc:
        d = {
            "category": "information",
            "urgency": 3,
            "sentiment": "neutral",
            "product": "unknown",
            "language": "en",
            "evidence": "",
            "needs_human_review": True,
            "review_reason": f"Structured output failed: {exc}",
        }
    except Exception as exc:  # noqa: BLE001
        d = {
            "category": "information",
            "urgency": 3,
            "sentiment": "neutral",
            "product": "unknown",
            "language": "en",
            "evidence": "",
            "needs_human_review": True,
            "review_reason": f"Unexpected error: {type(exc).__name__}: {exc}",
        }

    d.update(extract_deterministic(ticket))
    d = apply_business_rules(d, ticket)
    return d


def few_shot(ticket: str, tier: str = "SMALL") -> dict:
    """TODO B: zero_shot + the few-shot block."""
    prompt = (
        "Here are reference examples of correctly extracted tickets:\n\n"
        f"{few_shot_block(FEW_SHOT_IDS)}\n\n"
        "---\n"
        "Now extract the structured record for this ticket:\n\n"
        f"{ticket}"
    )
    try:
        rec = structured(prompt, schema=TicketRecordC, system=SYSTEM_PROMPT, tier=tier)
        d = rec.model_dump()
    except StructuredOutputError as exc:
        d = {
            "category": "information",
            "urgency": 3,
            "sentiment": "neutral",
            "product": "unknown",
            "language": "en",
            "evidence": "",
            "needs_human_review": True,
            "review_reason": f"Structured output failed: {exc}",
        }
    except Exception as exc:  # noqa: BLE001
        d = {
            "category": "information",
            "urgency": 3,
            "sentiment": "neutral",
            "product": "unknown",
            "language": "en",
            "evidence": "",
            "needs_human_review": True,
            "review_reason": f"Unexpected error: {type(exc).__name__}: {exc}",
        }

    d.update(extract_deterministic(ticket))
    d = apply_business_rules(d, ticket)
    return d


class TicketRecordReasoned(TicketRecordC):
    """TODO B: add a `reasoning: str` field FIRST (T2 §3.3).

    Pydantic keeps declaration order, and field order in the JSON Schema
    influences generation order. Putting reasoning first makes it condition the
    answer; putting it last makes it a post-hoc rationalisation. You want the
    first. Measure the difference in output tokens.
    """
    reasoning: str = Field(
        description="Step-by-step reasoning about category, urgency, sentiment, and other fields before committing to values."
    )

    @classmethod
    def model_json_schema(cls, *args, **kwargs):
        s = super().model_json_schema(*args, **kwargs)
        if "properties" in s and "reasoning" in s["properties"]:
            props = s["properties"]
            s["properties"] = {
                "reasoning": props["reasoning"],
                **{k: v for k, v in props.items() if k != "reasoning"},
            }
        return s


def few_shot_reasoned(ticket: str, tier: str = "SMALL") -> dict:
    """TODO B: few_shot with TicketRecordReasoned."""
    prompt = (
        "Here are reference examples of correctly extracted tickets with step-by-step reasoning:\n\n"
        f"{few_shot_block(FEW_SHOT_IDS, include_reasoning=True)}\n\n"
        "---\n"
        "Now extract the structured record with reasoning for this ticket:\n\n"
        f"{ticket}"
    )
    try:
        rec = structured(prompt, schema=TicketRecordReasoned, system=SYSTEM_PROMPT, tier=tier)
        d = rec.model_dump()
    except StructuredOutputError as exc:
        d = {
            "category": "information",
            "urgency": 3,
            "sentiment": "neutral",
            "product": "unknown",
            "language": "en",
            "evidence": "",
            "reasoning": "",
            "needs_human_review": True,
            "review_reason": f"Structured output failed: {exc}",
        }
    except Exception as exc:  # noqa: BLE001
        d = {
            "category": "information",
            "urgency": 3,
            "sentiment": "neutral",
            "product": "unknown",
            "language": "en",
            "evidence": "",
            "reasoning": "",
            "needs_human_review": True,
            "review_reason": f"Unexpected error: {type(exc).__name__}: {exc}",
        }

    d.update(extract_deterministic(ticket))
    d = apply_business_rules(d, ticket)
    return d


def cascade(ticket: str) -> dict:
    """TODO C: SMALL first; escalate to MAIN on a trigger you choose.

    Triggers, roughly in ascending order of how well they work:
      - validation failed                      (free, weak: misses confident errors)
      - evidence field empty or very short     (free, surprisingly decent)
      - urgency >= 4                           (free, but it is not a confidence signal)
      - two SMALL samples at T=0.7 disagree    (2x small cost, much the best)

    Record which path each ticket took -- set rec['_path'] = 'small' | 'large'
    so grid.py can report the escalation rate.
    """
    should_escalate = False
    small_rec = None

    try:
        small_rec = structured(ticket, schema=TicketRecordC, system=SYSTEM_PROMPT, tier="SMALL", temperature=0.0)
        evidence = str(small_rec.evidence or "").strip()
        if len(evidence) < 10:
            should_escalate = True
        else:
            # Check self-consistency disagreement trigger: draw a second sample at T=0.7
            # T>0 changes both sampling and the cache key, avoiding identical cache hits
            sample2 = structured(ticket, schema=TicketRecordC, system=SYSTEM_PROMPT, tier="SMALL", temperature=0.7)
            disagree_fields = ("category", "urgency", "sentiment", "product", "language")
            if any(getattr(small_rec, f) != getattr(sample2, f) for f in disagree_fields):
                should_escalate = True
    except Exception:
        should_escalate = True

    if should_escalate:
        try:
            large_rec = structured(ticket, schema=TicketRecordC, system=SYSTEM_PROMPT, tier="MAIN")
            d = large_rec.model_dump()
        except StructuredOutputError as exc:
            d = {
                "category": "information",
                "urgency": 3,
                "sentiment": "neutral",
                "product": "unknown",
                "language": "en",
                "evidence": "",
                "needs_human_review": True,
                "review_reason": f"Structured output failed on MAIN: {exc}",
            }
        except Exception as exc:  # noqa: BLE001
            d = {
                "category": "information",
                "urgency": 3,
                "sentiment": "neutral",
                "product": "unknown",
                "language": "en",
                "evidence": "",
                "needs_human_review": True,
                "review_reason": f"Unexpected error on MAIN: {type(exc).__name__}: {exc}",
            }
        d["_path"] = "large"
    else:
        d = small_rec.model_dump()
        d["_path"] = "small"

    d.update(extract_deterministic(ticket))
    d = apply_business_rules(d, ticket)
    return d


VARIANTS = {
    "zero_shot": lambda t: zero_shot(t, "SMALL"),
    "zero_shot_main": lambda t: zero_shot(t, "MAIN"),
    "few_shot": lambda t: few_shot(t, "SMALL"),
    "few_shot_main": lambda t: few_shot(t, "MAIN"),
    "few_shot_reasoned": lambda t: few_shot_reasoned(t, "SMALL"),
    "few_shot_reasoned_main": lambda t: few_shot_reasoned(t, "MAIN"),
    "cascade": cascade,
}
