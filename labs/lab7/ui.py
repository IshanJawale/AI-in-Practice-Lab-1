#!/usr/bin/env python3
"""Lab 7 — Streamlit front end.

    streamlit run labs/lab7/ui.py

Requires the service to be running:
    uvicorn labs.lab7.service:app --port 8000

The one non-negotiable UI requirement: **citations must be expandable to show
the source text.** Grounding the user cannot check is decoration.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests
import streamlit as st

REVIEW_QUEUE = Path(__file__).resolve().parents[2] / "reports" / "lab7_review_queue.jsonl"

API = st.sidebar.text_input("Service URL", "http://localhost:8000")
stream_mode = st.sidebar.toggle("Stream the answer", value=True)
mode = st.sidebar.radio("Mode", ["rag", "tools"], help="tools = the Lab 6 agent (premium "
                        "calculation, policy lookup). It has no citations.")

st.title("Aurora Policy Assistant")
st.caption("Answers come only from Aurora's policy documents. "
           "Every claim is cited. When the documents do not cover a question, "
           "the assistant says so instead of guessing.")

q = st.text_input("Ask a question",
                  placeholder="How long do I have to file a reimbursement claim?")


def render_answer(data: dict) -> None:
    """Show the answer, then every citation as an expander with the source text."""
    if data.get("refused"):
        st.warning(data["answer"])
    else:
        st.markdown(data["answer"])

    # A4: citations as expanders showing the source excerpt. A citation the
    #     user cannot open is not grounding.
    cites = data.get("citations", [])
    if cites:
        st.markdown("**Sources**")
    for c in cites:
        with st.expander(f"[{c['index']}] {c['doc_id']}"):
            st.text(c["excerpt"])


def feedback(question: str, data: dict) -> None:
    """Stretch: thumbs-down appends the case to a review queue. That queue is
    how real golden sets get built."""
    if st.button("👎 This answer was wrong or unhelpful", key=f"down-{data.get('trace_id')}"):
        REVIEW_QUEUE.parent.mkdir(parents=True, exist_ok=True)
        with REVIEW_QUEUE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": time.time(), "question": question,
                                 "answer": data.get("answer"),
                                 "trace_id": data.get("trace_id"),
                                 "sources": data.get("sources", [])}) + "\n")
        st.toast(f"Added to the review queue ({REVIEW_QUEUE.name}).")


def ask_plain(question: str) -> dict | None:
    with st.spinner("thinking"):
        try:
            r = requests.post(f"{API}/ask", json={"question": question, "mode": mode},
                              timeout=90)
            r.raise_for_status()
            return r.json()
        except requests.HTTPError as exc:
            retry = exc.response.headers.get("Retry-After")
            st.error(f"{exc.response.status_code}: {exc.response.text[:300]}"
                     + (f"  (retry in {retry}s)" if retry else ""))
        except requests.RequestException as exc:
            st.error(f"service unreachable: {exc}")
    return None


def ask_streaming(question: str) -> dict | None:
    """Consume /ask/stream. Prose appears as it is generated; the `validation`
    event arrives last and is authoritative. If it says `replace`, the streamed
    text failed citation validation and is overwritten (B3)."""
    box, text, final = st.empty(), "", None
    event = None
    try:
        with requests.post(f"{API}/ask/stream", json={"question": question},
                           stream=True, timeout=90) as r:
            if r.status_code != 200:
                st.error(f"{r.status_code}: {r.text[:300]}")
                return None
            for raw in r.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                if raw.startswith("event:"):
                    event = raw.split(":", 1)[1].strip()
                elif raw.startswith("data:"):
                    payload = json.loads(raw.split(":", 1)[1].strip())
                    if event == "token":
                        text += payload["text"]
                        box.markdown(text + " ▌")
                    elif event == "validation":
                        final = payload
                    elif event == "error":
                        st.error(f"{payload['status']}: {payload['detail']}")
                        return None
    except requests.RequestException as exc:
        st.error(f"service unreachable: {exc}")
        return None
    box.empty()
    if final is None:
        st.error("stream ended without a validation event")
        return None
    if final["replace"]:
        st.info("The streamed draft failed citation validation and was replaced.")
    final["latency_ms"] = final["total_ms"]
    final["ttft_ms"] = final.get("ttft_ms")
    return final


if st.button("Ask", type="primary") and q:
    data = ask_streaming(q) if (stream_mode and mode == "rag") else ask_plain(q)
    if data:
        render_answer(data)
        cols = st.columns(5)
        cols[0].metric("latency", f"{data.get('latency_ms', 0):.0f} ms")
        cols[1].metric("first token", f"{data['ttft_ms']:.0f} ms" if data.get("ttft_ms") is not None else "—")
        cols[2].metric("cost", f"${data.get('cost_usd', 0):.5f}")
        cols[3].metric("cached", data.get("cache_layer") or ("yes" if data.get("cached") else "no"))
        cols[4].metric("sources", len(data.get("citations", [])))
        st.caption(f"trace: `{data.get('trace_id', '')}`")
        feedback(q, data)
