#!/usr/bin/env python3
"""Pydantic in 30 minutes — everything Lab 1 needs, and nothing else.

    python labs/lab1/pydantic_primer.py              # run the checks
    python labs/lab1/pydantic_primer.py --solutions  # show the answers

You already know Python. This is not a tutorial on classes or type hints. It is
eight exercises covering the exact Pydantic surface Lab 1 uses:

    BaseModel · Field(ge, le, pattern, max_length, default, description)
    Literal · `| None` · field_validator · ValidationError
    model_validate · model_dump · model_json_schema

Nothing else. If you finish these you can start Lab 1 without opening the docs.

Each exercise has a TODO and a check. Run the file; it tells you which ones
pass. No API key needed — this is pure Pydantic and costs nothing.

WHY THIS MATTERS, in one paragraph. In Lab 1 you ask a language model to turn a
messy support ticket into a structured record. The model returns text. Your
program needs a typed object. Pydantic is the thing in between: it is where you
write down what you are willing to accept, and where you find out — loudly and
in one place — that you did not get it. Everything in this file is a tool for
saying "no" precisely.
"""
from __future__ import annotations

import sys
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

PASS, FAIL = "  ok  ", " FAIL "
results: list[tuple[str, bool, str]] = []


def check(name: str, fn) -> None:
    try:
        fn()
        results.append((name, True, ""))
    except AssertionError as e:
        results.append((name, False, str(e) or "assertion failed"))
    except NotImplementedError:
        results.append((name, False, "not implemented yet"))
    except Exception as e:                                       # noqa: BLE001
        results.append((name, False, f"{type(e).__name__}: {e}"))


# ===========================================================================
# 1 — A model is a class. Validation happens on construction.
# ===========================================================================
"""
Pydantic's whole idea: annotate the fields, and it enforces them at runtime.

    class Point(BaseModel):
        x: int
        y: int

    Point(x=1, y=2)        # fine
    Point(x="1", y=2)      # ALSO fine -- "1" is coerced to 1
    Point(x="cat", y=2)    # raises ValidationError

That middle line surprises people. Pydantic coerces where it is unambiguous.
It is a validator, not a type checker.
"""


class Ticket1(BaseModel):
    ticket_id: str
    urgency: int


def _t1():
    t = Ticket1(ticket_id="T0001", urgency=3)
    assert t.ticket_id == "T0001", "ticket_id did not survive construction"
    assert t.urgency == 3, "urgency did not survive construction"
    coerced = Ticket1(ticket_id="T0002", urgency="4")   # note the string
    assert coerced.urgency == 4, "Pydantic should coerce '4' to 4"
    try:
        Ticket1(ticket_id="T0003", urgency="urgent")
        raise AssertionError("'urgent' should not validate as an int")
    except ValidationError:
        pass


# ===========================================================================
# 2 — Field() adds constraints. This is where "no" gets specific.
# ===========================================================================
"""
    Field(ge=1, le=5)          integer range, inclusive
    Field(max_length=200)      string length
    Field(pattern=r"^AUR-\\d{7}$")   regex, must match the WHOLE string
    Field(default=None)        makes it optional

In Lab 1 you will use every one of these. A model that returns urgency 7 is a
validation error you can see and repair, not a mystery three services later.
"""


class Ticket2(BaseModel):
    urgency: int = Field(ge=1, le=5)
    evidence: str = Field(max_length=200)


def _t2():
    ok = Ticket2(urgency=5, evidence="short")
    assert ok.urgency == 5
    for bad in (0, 6, -1):
        try:
            Ticket2(urgency=bad, evidence="x")
            raise AssertionError(f"urgency={bad} should be rejected")
        except ValidationError:
            pass
    try:
        Ticket2(urgency=3, evidence="x" * 201)
        raise AssertionError("a 201-character evidence string should be rejected")
    except ValidationError:
        pass


# ===========================================================================
# 3 — Literal makes illegal states unrepresentable.
# ===========================================================================
"""
    category: Literal["billing", "claims", "technical"]

This is the single highest-value line in a Lab 1 schema. With `str`, a model
that returns "Billing " (capitalised, trailing space) sails through and breaks
something downstream. With `Literal`, it fails HERE, where you can see it and
send it back for repair.
"""

CATEGORIES = Literal["billing", "claims", "policy_change",
                     "technical", "complaint", "information"]


class Ticket3(BaseModel):
    category: CATEGORIES


def _t3():
    assert Ticket3(category="billing").category == "billing"
    for bad in ("Billing", "billing ", "refund", ""):
        try:
            Ticket3(category=bad)
            raise AssertionError(f"category={bad!r} should be rejected")
        except ValidationError:
            pass


# ===========================================================================
# 4 — Optional fields need an explicit way to say "absent".
# ===========================================================================
"""
    policy_number: str | None = Field(default=None, pattern=r"^AUR-\\d{7}$")

Two things at once: the value may be None, and if it is not None it must match
the pattern.

This matters more than it looks. In Lab 1, roughly a quarter of tickets contain
no policy number at all. If your schema gives the model no legal way to say
"there isn't one", it will invent a plausible-looking one — and an invented
identifier is the one error a human reviewer will never catch.
"""


class Ticket4(BaseModel):
    policy_number: str | None = Field(default=None, pattern=r"^AUR-\d{7}$")


def _t4():
    assert Ticket4().policy_number is None, "should default to None"
    assert Ticket4(policy_number="AUR-1234567").policy_number == "AUR-1234567"
    for bad in ("AUR-123", "AUR-12345678", "aur-1234567", "1234567", "AUR1234567"):
        try:
            Ticket4(policy_number=bad)
            raise AssertionError(f"policy_number={bad!r} should be rejected")
        except ValidationError:
            pass


# ===========================================================================
# 5 — description= is not a comment. It is shipped to the model.
# ===========================================================================
"""
`model_json_schema()` turns your class into a JSON Schema, and
`aip.llm.structured` puts that schema into the prompt. So every
`description=` you write is an instruction the model reads, sitting
immediately next to the field it governs.

This is the highest-leverage place to put an instruction in the whole lab.
Write descriptions as instructions to the model, not as documentation for a
human reading your code later.
"""


class Ticket5(BaseModel):
    urgency: int = Field(
        ge=1,
        le=5,
        description="Urgency scale 1 to 5, where 5 is emergency/same-day deadline.",
    )


def _t5():
    schema = Ticket5.model_json_schema()
    desc = schema["properties"]["urgency"].get("description", "")
    assert desc, "urgency has no description -- the model gets no guidance"
    assert len(desc) > 40, f"description is too vague to be useful: {desc!r}"
    assert "urgency" in desc.lower() and "5" in desc, \
        "the description should name the field and anchor the top of the scale"


# ===========================================================================
# 6 — field_validator: rules a type cannot express.
# ===========================================================================
"""
    @field_validator("policy_number", mode="before")
    @classmethod
    def _clean(cls, v):
        ...
        return v

`mode="before"` runs on the RAW value, before Pydantic's own coercion. That is
what you want for cleaning up a model's output, because the model has many ways
of saying "nothing" -- "", "null", "none", "N/A" -- and none of them is None.

Turning those into a real None is the difference between a field that is
correct and a field that is a string containing the word "null".
"""


class Ticket6(BaseModel):
    policy_number: str | None = None

    @field_validator("policy_number", mode="before")
    @classmethod
    def _clean(cls, v):
        if v is None:
            return None
        v = str(v).strip()
        return None if v.lower() in {"", "null", "none", "n/a"} else v


def _t6():
    for junk in ("", "  ", "null", "NULL", "None", "n/a", " N/A "):
        got = Ticket6(policy_number=junk).policy_number
        assert got is None, f"{junk!r} should become None, got {got!r}"
    assert Ticket6(policy_number="  AUR-1234567 ").policy_number == "AUR-1234567", \
        "surrounding whitespace should be stripped"
    assert Ticket6(policy_number=None).policy_number is None


# ===========================================================================
# 7 — Reading a ValidationError is how the repair loop works.
# ===========================================================================
"""
When validation fails, `aip.llm.structured` sends the error text BACK to the
model and asks for a fix. That only works because Pydantic's message names the
field and the constraint. Vague repair prompts do not work; specific ones do.

    e.errors() -> [{'loc': ('urgency',), 'msg': '...', 'type': '...'}, ...]
"""


class Ticket7(BaseModel):
    category: CATEGORIES
    urgency: int = Field(ge=1, le=5)


def failing_fields(payload: dict) -> list[str]:
    """TODO 7: validate `payload` against Ticket7 and return a sorted list of
    the field names that failed. Return [] if it validates.

    Hint: catch ValidationError and read e.errors(); each entry has a 'loc'
    tuple whose first element is the field name.
    """
    try:
        Ticket7.model_validate(payload)
        return []
    except ValidationError as e:
        return sorted({str(err["loc"][0]) for err in e.errors()})


def _t7():
    assert failing_fields({"category": "billing", "urgency": 3}) == []
    assert failing_fields({"category": "nope", "urgency": 3}) == ["category"]
    assert failing_fields({"category": "billing", "urgency": 9}) == ["urgency"]
    assert failing_fields({"category": "nope", "urgency": 9}) == ["category", "urgency"]
    assert failing_fields({}) == ["category", "urgency"], "missing fields count too"


# ===========================================================================
# 8 — Put it together: a small version of the real thing.
# ===========================================================================
"""
This is a cut-down TicketRecord. In Lab 1 you will write the full one with
eight fields. Note the two methods you will use constantly:

    Model.model_validate(some_dict)   dict  -> object   (raises on bad input)
    obj.model_dump()                  object -> dict    (for scoring/JSON)
"""


class TicketRecord(BaseModel):
    evidence: str = Field(
        max_length=200,
        description="The span of the ticket that determined the category, quoted verbatim.",
    )
    category: CATEGORIES = Field(
        description="Category: billing, claims, policy_change, technical, complaint, or information.",
    )
    urgency: int = Field(
        ge=1,
        le=5,
        description="Urgency scale 1 to 5, where 5 is emergency/same-day deadline.",
    )
    policy_number: str | None = Field(
        default=None,
        pattern=r"^AUR-\d{7}$",
        description="Format AUR- followed by exactly 7 digits, or null if no policy number present.",
    )

    @field_validator("policy_number", mode="before")
    @classmethod
    def _clean(cls, v):
        if v is None:
            return None
        v = str(v).strip()
        return None if v.lower() in {"", "null", "none", "n/a"} else v


def _t8():
    raw = {"evidence": "debited twice", "category": "billing",
           "urgency": 3, "policy_number": " AUR-1234567 "}
    rec = TicketRecord.model_validate(raw)
    assert rec.policy_number == "AUR-1234567", "the before-validator should strip"
    d = rec.model_dump()
    assert isinstance(d, dict) and d["category"] == "billing"
    assert set(d) == {"evidence", "category", "urgency", "policy_number"}, \
        f"unexpected field set: {sorted(d)}"

    missing = TicketRecord.model_validate(
        {"evidence": "x", "category": "claims", "urgency": 1})
    assert missing.policy_number is None, "policy_number should be optional"

    props = TicketRecord.model_json_schema()["properties"]
    for f in ("evidence", "category", "urgency", "policy_number"):
        assert props[f].get("description"), f"{f} needs a description -- the model reads it"


# ===========================================================================
SOLUTIONS = '''
1   class Ticket1(BaseModel):
        ticket_id: str
        urgency: int

2   class Ticket2(BaseModel):
        urgency: int = Field(ge=1, le=5)
        evidence: str = Field(max_length=200)

3   class Ticket3(BaseModel):
        category: CATEGORIES

4   class Ticket4(BaseModel):
        policy_number: str | None = Field(default=None, pattern=r"^AUR-\\d{7}$")

5   class Ticket5(BaseModel):
        urgency: int = Field(ge=1, le=5,
            description="Urgency 1-5. 5 = an emergency in progress or a hard "
                        "same-day deadline. 3 = something is already stuck and "
                        "the customer is waiting. 1 = a general question.")

6       @field_validator("policy_number", mode="before")
        @classmethod
        def _clean(cls, v):
            if v is None:
                return None
            v = str(v).strip()
            return None if v.lower() in {"", "null", "none", "n/a"} else v

7   def failing_fields(payload):
        try:
            Ticket7.model_validate(payload)
            return []
        except ValidationError as e:
            return sorted({str(err["loc"][0]) for err in e.errors()})

8   class TicketRecord(BaseModel):
        evidence: str = Field(max_length=200,
            description="The span of the ticket that determined the category, "
                        "quoted verbatim. One sentence at most.")
        category: CATEGORIES = Field(
            description="billing = money in. claims = an actual or intended "
                        "claim. policy_change = altering the contract. "
                        "technical = the app or portal is broken. complaint = "
                        "Aurora's conduct is the subject. information = a "
                        "question with no pending transaction.")
        urgency: int = Field(ge=1, le=5,
            description="Urgency 1-5. 5 = emergency in progress or a same-day "
                        "deadline. 1 = a general question, nothing at stake.")
        policy_number: str | None = Field(default=None, pattern=r"^AUR-\\d{7}$",
            description="Format AUR- followed by exactly 7 digits, copied "
                        "character for character. null if the ticket contains "
                        "no such string. Never invent or reformat one.")

        @field_validator("policy_number", mode="before")
        @classmethod
        def _clean(cls, v):
            if v is None:
                return None
            v = str(v).strip()
            return None if v.lower() in {"", "null", "none", "n/a"} else v
'''


def main() -> None:
    if "--solutions" in sys.argv:
        print(SOLUTIONS)
        return

    for name, fn in [
        ("1 · a model is a class", _t1),
        ("2 · Field() constraints", _t2),
        ("3 · Literal", _t3),
        ("4 · optional with a pattern", _t4),
        ("5 · description reaches the model", _t5),
        ("6 · field_validator(mode='before')", _t6),
        ("7 · reading a ValidationError", _t7),
        ("8 · the whole thing", _t8),
    ]:
        check(name, fn)

    print("\nPydantic primer — everything Lab 1 needs\n")
    for name, ok, msg in results:
        print(f"[{PASS if ok else FAIL}] {name:<38} {msg}")

    done = sum(1 for _, ok, _ in results if ok)
    print(f"\n{done}/{len(results)} passing.")
    if done == len(results):
        print("You are ready for Lab 1. Now go and read five tickets:")
        print("  python -c \"import json,random;"
              "rows=[json.loads(l) for l in open('data/eval/extraction_dev.jsonl')];"
              "[print(r['input'][:400],'\\n---') for r in random.sample(rows,5)]\"")
    else:
        print("Stuck? `python labs/lab1/pydantic_primer.py --solutions`")
        print("Every exercise maps to something you will write in Lab 1, so it is")
        print("worth pushing through rather than skipping.")


if __name__ == "__main__":
    main()
