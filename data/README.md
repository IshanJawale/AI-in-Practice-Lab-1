# Datasets

Four datasets, all shipped, all reproducible.

| Path | Used by | Contents |
|---|---|---|
| `tickets/tickets.jsonl` | Labs 1–2 | 240 support tickets, raw text only |
| `eval/extraction_{dev,test,blind}.jsonl` | Labs 1–2 | 60 / 120 / 60 split; dev and test labelled |
| `corpus/` | Labs 3–7 | 30 documents: 16 Aurora Health policy docs + 14 distractors |
| `eval/rag_golden.jsonl` | Labs 3–5, 7 | 45 questions with document-level relevance and gold answers |
| `attacks/attack_suite.jsonl` | Lab 6 | 21 cases: 17 attacks + 4 innocent controls |

Regenerate the tickets with `python scripts/make_tickets.py` — deterministic,
so everyone's numbers are comparable.

---

## Annotation guidelines — ticket extraction

**Read this before you design your prompt.** These are the rules the labels
were produced from. They are published for the same reason a real project
publishes its annotation guide: *a label the annotator cannot derive from a
written rule is a label nobody can hit.*

Two of these fields were reworked after the reference solution was measured
against them, because the first version of the dataset contained labels that
were literally unachievable. That story is in "Known limitations" below, and it
is the most useful thing on this page.

### `category`

| Value | Rule |
|---|---|
| `billing` | Money in: premium, debits, refunds, invoices, the 80D tax certificate, instalment options |
| `claims` | An actual or intended claim: cashless, reimbursement, settlement amount, deduction, rejection |
| `policy_change` | Altering the contract: add or remove a member, upgrade, port, change contact details |
| `technical` | The app, portal, OTP, login, locator, or document upload is broken |
| `complaint` | The subject is **Aurora's conduct** — mis-selling, being kept on hold, an ignored grievance |
| `information` | A question with no pending transaction behind it |

**The boundary that matters.** An angry message about a claim is `claims` if the
customer still wants the claim processed. It is `complaint` only when Aurora's
conduct is itself the subject. Roughly a third of the errors any system makes
on this dataset are on this one boundary.

### `urgency`

| Value | Rule | Example |
|---|---|---|
| 1 | Answerable from general product knowledge or a self-service how-to. Aurora need not look anything up | "What is the waiting period for cataract surgery?"; "Where do I download my e-card?" |
| 2 | Requires Aurora to look up **this customer's** account, act on it, or fix a defect — or a transaction is in flight | "How many wellness points do I have?"; "Please add my newborn"; "the app crashes on upload" |
| 3 | Something has already gone wrong or is stuck, and the customer is waiting | "debited twice"; "portability request, heard nothing" |
| 4 | Repeated failure to resolve, money or access at risk now, or an explicit escalation threat | "THIS IS THE THIRD TIME"; "standing at the hospital desk and your portal is down" |
| 5 | An emergency in progress, a formal denial demanding immediate reversal, or the customer states they **are** escalating to the Ombudsman | "father is in ICU and cashless is DENIED"; "I am filing a complaint with the ombudsman" |

**Modifier:** +1 (capped at 5) if the message states a same-day or next-morning
deadline.

**The 1/2 boundary** is where most errors land, and it is not about politeness
or length. Ask: *can this be answered without opening the customer's record?*
If yes it is 1, however long the message. If Aurora must look something up, do
something, or fix something, it is 2.

**The 4/5 boundary** turns on tense. *Threatening* to go to the Ombudsman
("refund it or I am going to the ombudsman") is 4. *Stating that you are* going
("I am filing a complaint with the ombudsman") is 5.

**Judge the situation, not the volume.** Shouting is a `sentiment` signal, not
an urgency signal. A calm message about an ICU admission is 5; a furious
message about a tax certificate is 2.

### `sentiment`

`angry` (hostile, shouting, threatening) · `frustrated` (unhappy and tired of
trying, still civil) · `neutral` (matter-of-fact) · `satisfied` (thanks or
praise). Tone only — independent of urgency.

**The neutral/frustrated boundary**, which is the other place errors cluster:
`frustrated` requires the message to reference **a prior failure** — a repeat
attempt, an unanswered request, a delay, or something that is not working. A
first-time request, however terse, is `neutral`.

### `product`

`bronze` · `silver` · `gold` · `platinum` · `unknown`. The plan must be **named**
in the message. Never infer it from the sum insured or from context.

### `policy_number`

`AUR-` followed by exactly 7 digits, copied verbatim, or `null`.

**Only from the live message.** Lines beginning with `>` are a quoted reply from
an earlier thread and may carry a different, stale number. Signature blocks
likewise. A ticket whose only policy-shaped string is inside a quoted reply is
labelled `null`.

### `contains_pii`

True if the text contains a phone number, or an email address that is **not**
one of Aurora's own published addresses (`support@aurorahealth.example`,
`grievance@aurorahealth.example`). A personal name alone does not count.

This is a deliberately narrow definition: it answers "is there a direct
identifier that should not leave our process?" It is **not** sufficient for
DPDP Act purposes, where a name plus a policy number is already personal data.
Say so in your report if you use this field for anything.

### `language`

`hi-en` if Hindi words are mixed into the English, including transliterated
Hindi in Latin script (`kripya`, `jaldi`, `bahut`, `turant`). `en` otherwise.

### `escalate`

Not a model output. A business rule, computed in code:

```python
escalate = urgency >= 4 or "ombudsman" in ticket.lower()
```

---

## Known limitations — read these, and be suspicious of your own datasets

**1. Labels are exact by construction.** The text is generated *from* the label,
so there is no annotation noise at all. Real support queues do not look like
this: inter-annotator agreement on `urgency` and `sentiment` in a real queue is
typically 0.60–0.75, not 1.00. That gap is the difference between a benchmark
score and a production expectation. A system reaching 0.95 field accuracy here
would not reach 0.95 on real tickets, and part of the shortfall would be the
labels, not the system.

**2. Two label bugs were found by running a correct solution against them.**
Both punished correct behaviour, and both are worth studying because they are
the most common way a golden set goes wrong:

- *Policy numbers that were not in the text.* The generator assigned a policy
  number to every ticket, including those whose template had no slot to print
  one in. A system correctly returning `null` was marked wrong.
- *PII labels that contradicted the text.* `contains_pii` was tracked as a flag
  while the ticket was assembled, and the quoted auto-reply tail — added
  afterwards — contains `support@aurorahealth.example`. 14% of labels said
  "no PII" about text containing an email address.

The fix in both cases was the same and is the general rule:

> **Derive the label from the finished artefact, never from the process that
> built it.** `scripts/make_tickets.py::detect_pii` now scans the final text.

`tests/test_aip.py` has a regression test for each. When you build a golden
set, write the equivalent test first.

**3. The urgency scale was unlearnable until it was written down.** The
reference solution scored ~0.55 on `urgency` against an unpublished scale and
~0.85 once the table above existed — with no change to the model. If your
annotators cannot state the rule, your labels are noise wearing a number.

---

## The RAG corpus

30 markdown documents. 16 are Aurora Health policy documents; 14 are
distractors — motor claim timelines, travel exclusions, a group corporate plan,
a life-insurance grace period, a senior-citizen product, an app guide, an
ombudsman office list. They exist because a corpus without competing documents
makes every retrieval method look equally good.

Deliberate traps:

| Trap | Where | Tests |
|---|---|---|
| Superseded document with different numbers | `claims-timelines-2024-ARCHIVED.md` | Q29–Q31: does the system quote the retired figures? |
| Near-identical plan documents | `plan-{bronze,silver,gold}.md` | Q24: the no-claim-bonus rule differs between Silver and Gold |
| Cross-product lexical competition | `motor-claims-timelines.md` vs `claims-timelines.md` | Both are "claim timelines" with different deadlines |
| A referenced document that does not exist | `plan-platinum-addendum` | Q37: partial refusal — confirm the benefit, refuse the detail |

Question kinds in the golden set: `single_hop` (18), `multi_hop` (10),
`paraphrase` (5), `aggregation` (4), `trap_archived` (3), `unanswerable` (5).

**Three questions have no relevant document at all.** Exclude them from
retrieval metrics — you cannot compute recall against an empty relevant set —
and say in your report that you did. They belong to Lab 4, where refusal is
measured.
