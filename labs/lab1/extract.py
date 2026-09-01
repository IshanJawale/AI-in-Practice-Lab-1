#!/usr/bin/env python3
"""Lab 1, Parts B and C — the extractor you actually ship.

Complete the TODOs. `run_eval.py` imports `extract_b` and `extract_c` from
here, so keep those two function names.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from aip.guards import _PII_PATTERNS  # noqa: E402
from aip.llm import StructuredOutputError, structured  # noqa: E402

CATEGORIES = Literal["billing", "claims", "policy_change",
                     "technical", "complaint", "information"]


# ===========================================================================
# PART B — the schema
# ===========================================================================
class TicketRecord(BaseModel):
    """The contract. Everything the model is allowed to say, and nothing else.

    Remember from T2 §3.2: field `description`s are shipped to the model as
    part of the JSON Schema. They are the highest-leverage place to put an
    instruction, because they sit next to the thing they govern. Write them as
    instructions to the model, not as documentation for a human.
    """

    # TODO B1a: `evidence` placed BEFORE category to act as Chain-of-Thought (T2 §3.3),
    # forcing the model to quote verbatim justification before committing to a label.
    evidence: str = Field(
        max_length=200,
        description="The span of the ticket that determined the category, quoted verbatim. One sentence at most."
    )

    category: CATEGORIES = Field(
        description="billing: money in (premiums, debits, refunds, 80D tax cert, invoices, instalments). "
                    "claims: actual or intended claim (cashless, reimbursement, settlement, deduction, rejection). "
                    "policy_change: altering contract (add/remove member, upgrade, port, contact details). "
                    "technical: app, portal, OTP, login, doc upload broken. "
                    "complaint: Aurora's conduct is the subject (mis-selling, hold times, rude staff, ignored grievance). "
                    "An angry message about a claim or billing dispute is still claims or billing unless Aurora's conduct itself is the primary subject. "
                    "information: question with no pending transaction behind it."
    )

    urgency: int = Field(
        ge=1, le=5,
        description="Urgency 1-5 scale. 1: Answerable from general product knowledge/how-to without opening customer record. "
                    "2: Requires looking up customer account, action in flight, or fixing a defect. "
                    "3: Something already went wrong or is stuck, and customer is waiting. "
                    "4: Repeated failure (e.g. 3rd time), money/access at risk now, standing at hospital desk, or threatening ombudsman. "
                    "5: Emergency in progress (ICU), formal denial demanding immediate reversal, or actively filing complaint with ombudsman. "
                    "Modifier: +1 (cap 5) if stating same-day or tomorrow morning deadline."
    )

    sentiment: Literal["angry", "frustrated", "neutral", "satisfied"] = Field(
        description="angry: hostile, shouting, threatening. "
                    "frustrated: unhappy about prior failure, delay, or unanswered request, but still civil. "
                    "neutral: matter-of-fact first-time inquiry or request. "
                    "satisfied: thanks or praise."
    )

    product: Literal["bronze", "silver", "gold", "platinum", "unknown"] = Field(
        description="The Aurora plan tier named explicitly in the message ('bronze', 'silver', 'gold', 'platinum'). "
                    "Must be 'unknown' if no plan tier is explicitly named. Never infer from sum insured or context."
    )

    language: Literal["en", "hi-en"] = Field(
        description="'hi-en' if Hindi words or transliterated Hindi in Latin script "
                    "(e.g. jaldi, kripya, paisa, karo, batayiye, bahut, turant) are mixed into English; 'en' otherwise."
    )

    # Part B only: the model decides these. In Part C you will delete them
    # from this schema and compute them in code instead.
    policy_number: str | None = Field(
        default=None,
        pattern=r"^AUR-\d{7}$",
        description="Format AUR- followed by exactly 7 digits (e.g. AUR-1234567), copied verbatim from the live message body. "
                    "Must be null if no policy number is present or if it only appears in quoted reply (> lines). "
                    "Never invent or reformat one."
    )
    contains_pii: bool = Field(
        default=False,
        description="True if ticket contains a phone number (e.g. 10-digit mobile) or customer email address "
                    "(excluding @aurorahealth.example). Personal names alone do not count."
    )

    # Set by our code, never by the model.
    needs_human_review: bool = False
    review_reason: str = ""

    @field_validator("policy_number", mode="before")
    @classmethod
    def _policy_format(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v_str = str(v).strip()
        if v_str.lower() in {"", "null", "none", "n/a", "unknown", "not present", "none present", "null/none"}:
            return None
        m = re.search(r"\bAUR-\d{7}\b", v_str)
        if m:
            return m.group(0)
        return None


SYSTEM_PROMPT = """\
You are an expert insurance support classifier for Aurora Health Insurance in India.
Extract structured records strictly following Aurora's official annotation guidelines:

1. EVIDENCE:
   - Quote verbatim the exact short sentence/span from the ticket that decided the category.

2. CATEGORY:
   - 'billing': Premiums, payments, debits/double debits, refund requests, 80D tax certificates, invoices, payment instalments.
   - 'claims': Any active or intended claim: cashless pre-auth/denial, reimbursement, hospital bills, settlement amount, deduction query, claim rejection, post-hospitalisation bills.
   - 'policy_change': Altering contract: adding/removing member/dependent/newborn, policy upgrade, portability/port request, contact details update.
   - 'technical': App or portal issues: app crash, login, OTP, document upload failure, portal down, locating e-card in app.
   - 'complaint': Aurora's service conduct is the primary subject: agent mis-selling, long hold times, rude staff, ignored grievance. (Note: an angry message about a claim or billing dispute is still 'claims' or 'billing' if the customer wants it resolved).
   - 'information': General questions with no pending transaction behind them (e.g., asking if no-claim bonus is affected after claim settlement, general waiting period questions).

3. URGENCY (1 to 5):
   - 1: General self-service/product knowledge answerable without opening customer account.
   - 2: Requires opening/acting on this customer's account, policy, or in-flight transaction (e.g., checking wellness points on policy, adding dependent, claim document requirements, app error).
   - 3: Something already stuck, delayed, or gone wrong and customer is waiting (e.g., double debit, portability heard nothing, unexplained deduction).
   - 4: Repeated failure ('THIRD TIME', 45 days waiting), standing at hospital desk, mis-sold policy refund, or threatening ombudsman ('refund or I am going to ombudsman').
   - 5: Emergency in progress (ICU admission), formal cashless denial requiring immediate reversal, or actively stating filing complaint with ombudsman ('I am filing a complaint with the ombudsman').
   - MODIFIER: Add +1 (max 5) ONLY IF stating an explicit same-day or next-morning deadline ('before tomorrow morning', 'today itself').

4. SENTIMENT:
   - 'satisfied': Thanks or praise.
   - 'neutral': Matter-of-fact first-time inquiry or request.
   - 'frustrated': Mentions a prior failure, delay, repeated attempt, or unanswered request, but still civil.
   - 'angry': Hostile tone, shouting (ALL CAPS), mis-selling, threatening ombudsman.

5. PRODUCT:
   - Named plan tier: 'bronze', 'silver', 'gold', 'platinum'. If no plan tier is explicitly named in the text, return 'unknown'.

6. LANGUAGE:
   - 'hi-en' if Hindi words (jaldi, karo, kripya, paisa, batayiye, bahut, turant, koi) appear; 'en' otherwise.
"""


def extract_b(ticket: str) -> TicketRecord:
    """Part B: the model decides everything."""
    try:
        return structured(ticket, schema=TicketRecord, system=SYSTEM_PROMPT, tier="SMALL")
    except StructuredOutputError as exc:
        return TicketRecord(
            category="information",
            urgency=3,
            sentiment="neutral",
            product="unknown",
            language="en",
            evidence="",
            policy_number=None,
            contains_pii=False,
            needs_human_review=True,
            review_reason=f"Structured output failed: {exc}",
        )
    except Exception as exc:  # noqa: BLE001
        return TicketRecord(
            category="information",
            urgency=3,
            sentiment="neutral",
            product="unknown",
            language="en",
            evidence="",
            policy_number=None,
            contains_pii=False,
            needs_human_review=True,
            review_reason=f"Unexpected error: {type(exc).__name__}: {exc}",
        )


# ===========================================================================
# PART C — move the deterministic work out of the model
# ===========================================================================
POLICY_RE = re.compile(r"\bAUR-\d{7}\b")

# The quoted-reply marker. Everything after this is history, not the current
# message. Part C3 asks you to decide what that means for policy extraction.
QUOTE_MARKER = re.compile(r"^\s*>", re.MULTILINE)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
PHONE_RE = re.compile(r"\b(?:\+?91[\s-]?)?[6-9]\d{9}\b")


def extract_deterministic(ticket: str) -> dict:
    """TODO C1: return {'policy_number', 'contains_pii'} without a model call.

    policy_number:
        Find AUR-<7 digits>.

    TODO C3 -- the trap. Some tickets contain TWO policy-number-shaped strings:
        one in the live body, and one in a quoted reply below a '>' line from
        an earlier thread. They are not always the same number.

        Rule: Split the message at the first quoted-reply line (`^\\s*>`).
        Search ONLY the live message body before any quote marker for policy numbers.
        If a policy number only appears in the quoted thread, return None.
        Rationale: Quoted threads reflect historical interactions, while the live
        ticket body contains the active customer transaction.

    contains_pii:
        True if the ticket contains a phone number or an email address not belonging
        to Aurora's own support domains (@aurorahealth.example).
    """
    # Split live body from quoted thread
    quote_match = QUOTE_MARKER.search(ticket)
    live_body = ticket[: quote_match.start()] if quote_match else ticket

    # 1. Policy Number from live body only
    pn_match = POLICY_RE.search(live_body)
    policy_number = pn_match.group(0) if pn_match else None

    # 2. PII Detection across ticket
    has_pii = False
    if PHONE_RE.search(ticket):
        has_pii = True
    else:
        for m in EMAIL_RE.finditer(ticket):
            email = m.group(0).lower()
            if not email.endswith("@aurorahealth.example"):
                has_pii = True
                break

    return {
        "policy_number": policy_number,
        "contains_pii": has_pii,
    }


def apply_business_rules(rec_fields: dict, ticket: str) -> dict:
    """TODO C1b: compute `escalate` in code.

        escalate = urgency >= 4 or 'ombudsman' appears in the ticket

    This is a business rule. It belongs in code where it can be read by a
    compliance officer, changed without touching a prompt, and unit-tested.
    """
    urgency = rec_fields.get("urgency", 1)
    escalate = bool(urgency >= 4 or "ombudsman" in ticket.lower())
    return {**rec_fields, "escalate": escalate}


class TicketRecordC(BaseModel):
    """TODO C2: the reduced schema the model sees in Part C.

    Copy TicketRecord and delete the fields you now compute in code. Fewer
    fields means a shorter prompt, fewer output tokens, and three fields at
    100% accuracy.
    """

    evidence: str = Field(
        max_length=200,
        description="The span of the ticket that determined the category, quoted verbatim. One sentence at most."
    )

    category: CATEGORIES = Field(
        description="billing: money in (premiums, debits, refunds, 80D tax cert, invoices, instalments). "
                    "claims: actual or intended claim (cashless, reimbursement, settlement, deduction, rejection). "
                    "policy_change: altering contract (add/remove member, upgrade, port, contact details). "
                    "technical: app, portal, OTP, login, doc upload broken. "
                    "complaint: Aurora's conduct is the subject (mis-selling, hold times, rude staff, ignored grievance). "
                    "An angry message about a claim or billing dispute is still claims or billing unless Aurora's conduct itself is the primary subject. "
                    "information: question with no pending transaction behind it."
    )

    urgency: int = Field(
        ge=1, le=5,
        description="Urgency 1-5 scale. 1: Answerable from general product knowledge/how-to without opening customer record. "
                    "2: Requires looking up customer account, action in flight, or fixing a defect. "
                    "3: Something already went wrong or is stuck, and customer is waiting. "
                    "4: Repeated failure (e.g. 3rd time), money/access at risk now, standing at hospital desk, or threatening ombudsman. "
                    "5: Emergency in progress (ICU), formal denial demanding immediate reversal, or actively filing complaint with ombudsman. "
                    "Modifier: +1 (cap 5) if stating same-day or tomorrow morning deadline."
    )

    sentiment: Literal["angry", "frustrated", "neutral", "satisfied"] = Field(
        description="angry: hostile, shouting, threatening. "
                    "frustrated: unhappy about prior failure, delay, or unanswered request, but still civil. "
                    "neutral: matter-of-fact first-time inquiry or request. "
                    "satisfied: thanks or praise."
    )

    product: Literal["bronze", "silver", "gold", "platinum", "unknown"] = Field(
        description="The Aurora plan tier named explicitly in the message ('bronze', 'silver', 'gold', 'platinum'). "
                    "Must be 'unknown' if no plan tier is explicitly named. Never infer from sum insured or context."
    )

    language: Literal["en", "hi-en"] = Field(
        description="'hi-en' if Hindi words or transliterated Hindi in Latin script "
                    "(e.g. jaldi, kripya, paisa, karo, batayiye, bahut, turant) are mixed into English; 'en' otherwise."
    )

    # Set by our code, never by the model.
    needs_human_review: bool = False
    review_reason: str = ""


def extract_c(ticket: str) -> dict:
    """Part C: model for judgement, code for everything else.

    Returns a plain dict (model fields + deterministic fields + business rules)
    so that run_eval.py can score it against the gold labels directly.
    """
    try:
        rec = structured(ticket, schema=TicketRecordC, system=SYSTEM_PROMPT, tier="SMALL")
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

    # Merge deterministic fields
    det = extract_deterministic(ticket)
    d.update(det)

    # Apply business rules (e.g. escalate)
    d = apply_business_rules(d, ticket)
    return d


if __name__ == "__main__":
    import json

    root = Path(__file__).resolve().parents[2]
    sample = json.loads(
        (root / "data/eval/extraction_dev.jsonl").open(encoding="utf-8").readline()
    )
    print("--- ticket ---")
    print(sample["input"][:600])
    print("\n--- gold ---")
    print(sample["expected"])
    print("\n--- yours ---")
    print(extract_c(sample["input"]))
