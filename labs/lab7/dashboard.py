#!/usr/bin/env python3
"""Lab 7 — the observability dashboard, read from local traces.

    streamlit run labs/lab7/dashboard.py

`aip.tracing` writes one JSONL file per run to .aip_traces/. This page reads
them back. It is a teaching-scale stand-in for Langfuse / LangSmith / Phoenix;
the concept -- structured spans with a run id and a parent id -- is identical.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from aip.config import settings  # noqa: E402

SLO_P95_MS = 6000            # uncached p95 SLO from the Lab 7 brief
HOURLY_BUDGET_USD = 0.25     # alert threshold for the cost-per-hour condition
REFUSAL_WINDOW = 20          # requests per window for the refusal-rate alert

st.set_page_config(page_title="Aurora Assistant — Ops", layout="wide")
st.title("Aurora Policy Assistant — operations")

runs = sorted(settings.trace_dir.glob("*.jsonl"), reverse=True)
if not runs:
    st.info(f"No traces yet in {settings.trace_dir}. Run some queries first.")
    st.stop()

# Only runs that contain service traffic are interesting by default.
def _has_service_spans(p: Path) -> bool:
    with p.open(encoding="utf-8") as fh:
        return any('"http.ask' in line for line in fh)


service_runs = [p for p in runs[:60] if _has_service_spans(p)]
default = [service_runs[0].stem] if service_runs else [runs[0].stem]
chosen = st.sidebar.multiselect("runs", [p.stem for p in runs], default=default)
rows = [json.loads(l) for p in runs if p.stem in chosen
        for l in p.open(encoding="utf-8") if l.strip()]
if not rows:
    st.stop()

df = pd.DataFrame(rows)
df["ts"] = pd.to_datetime(df["ts"], unit="s")
for col in ("cost_usd", "cached", "refused", "blocked", "status", "error",
            "duration_ms", "cache_layer", "mode", "hit"):
    if col not in df:
        df[col] = None

req = df[df["name"].isin(["http.ask", "http.ask_stream"])].sort_values("ts").copy()
llm = df[df["name"] == "llm.call"]
http_err = df[df["name"] == "http.error"]
# Service requests carry the authoritative cost; fall back to raw model spans
# only when the chosen runs contain no service traffic (never add both).
cost_src = req if len(req) else llm
cost_total = pd.to_numeric(cost_src["cost_usd"], errors="coerce").fillna(0).sum()

c = st.columns(6)
c[0].metric("requests", len(req))
c[1].metric("total cost", f"${cost_total:.4f}")
c[2].metric("cost / query", f"${cost_total / len(req):.5f}" if len(req) else "—")
if len(req):
    c[3].metric("cache hit rate", f"{req['cached'].fillna(False).astype(bool).mean():.0%}")
    c[4].metric("refusal rate", f"{req['refused'].fillna(False).astype(bool).mean():.0%}")
else:
    c[3].metric("model calls", len(llm))
    c[4].metric("model cache hits", f"{llm['cached'].fillna(False).astype(bool).mean():.0%}"
                if len(llm) else "—")
n_err = int((df["status"] == "error").sum())
c[5].metric("errors (spans)", n_err)

# ---------------------------------------------------------------------------
st.subheader("Latency by stage")
# C3: p50/p95 per span name -- the table that answers "which stage should I
#     optimise?" (Lab 7 Part B4) and "why did request X take 9 seconds?".
stage = (df.groupby("name")["duration_ms"]
         .agg(n="count", p50="median",
              p95=lambda s: s.quantile(0.95), total="sum")
         .sort_values("total", ascending=False))
st.dataframe(stage, use_container_width=True)

svc = df[df["name"].str.startswith("svc.", na=False)]
if len(svc):
    st.caption("Per-stage latency over time (ms) — each point is one request")
    piv = (svc.pivot_table(index="ts", columns="name", values="duration_ms", aggfunc="sum")
              .sort_index())
    st.line_chart(piv)

    st.caption("Share of total stage time (uncached requests dominate)")
    share = svc.groupby("name")["duration_ms"].sum()
    st.bar_chart(share / share.sum())

if len(req):
    st.subheader("Request latency: cached vs uncached")
    r2 = req.assign(kind=req["cached"].fillna(False).astype(bool)
                    .map({True: "cached", False: "uncached"}))
    summ = r2.groupby("kind")["duration_ms"].agg(
        n="count", p50="median", p95=lambda s: s.quantile(0.95),
        p99=lambda s: s.quantile(0.99))
    st.dataframe(summ, use_container_width=True)

    st.subheader("Slowest requests — drill into the trace")
    slow = req.nlargest(5, "duration_ms")[["ts", "span_id", "duration_ms", "cached"]]
    st.dataframe(slow.rename(columns={"span_id": "trace_id"}), use_container_width=True)
    pick = st.selectbox("trace_id", slow["span_id"].tolist()) if len(slow) else None
    if pick:
        kids = {pick}
        grew = True
        while grew:                       # collect all descendants of the root span
            new = set(df[df["parent_id"].isin(kids)]["span_id"]) - kids
            grew = bool(new)
            kids |= new
        tree = df[df["span_id"].isin(kids)].sort_values("ts")[
            ["name", "duration_ms", "cached", "cost_usd", "status"]]
        st.dataframe(tree, use_container_width=True)

st.subheader("Cost over time")
if len(cost_src):
    cum = (cost_src.sort_values("ts")
           .assign(cum=lambda d: pd.to_numeric(d["cost_usd"], errors="coerce")
                   .fillna(0).cumsum()))
    st.line_chart(cum.set_index("ts")["cum"])

if len(req):
    st.subheader("Cache hit rate over time (rolling 10 requests)")
    hit = req["cached"].fillna(False).astype(bool).astype(float).rolling(10, min_periods=1).mean()
    st.line_chart(pd.Series(hit.values, index=req["ts"]))

st.subheader("Errors")
errs = df[(df["status"] == "error") | (df["name"] == "http.error")]
cols = [c for c in ("ts", "name", "error", "status", "error_type") if c in errs]
st.dataframe(errs[cols] if len(errs) else pd.DataFrame(), use_container_width=True)
if len(req) or len(http_err):
    rate = len(http_err) / max(1, len(req) + len(http_err))
    st.caption(f"HTTP error rate: {rate:.1%} "
               f"({len(http_err)} errors / {len(req) + len(http_err)} requests)")

# ---------------------------------------------------------------------------
st.subheader("Alerts")
# C4: ONE primary alert -- refusal rate doubling -- plus two supporting ones.
#
#   REFUSAL-RATE DOUBLING  A broken or stale index throws no error, adds no
#     latency and costs nothing; it just stops finding things, and a correctly
#     built RAG system answers by declining. Compare the latest window of
#     requests with the baseline of everything before it.
#     WHEN IT FIRES: (1) open /trace/<id> on three recent refusals and read the
#     svc.retrieve span's top_doc/best score; (2) check .chroma / corpus mtime
#     and `GET /health` chunk count against the expected 300ish; (3) if the
#     index is wrong, roll back the corpus/embedding change and restart the
#     service (the pipeline rebuilds at start-up); (4) run gate.py to confirm.
alerts = []
if len(req) >= 2 * REFUSAL_WINDOW:
    ref = req[~req["blocked"].fillna(False).astype(bool)]["refused"].fillna(False).astype(bool)
    recent, base = ref.tail(REFUSAL_WINDOW).mean(), ref.iloc[:-REFUSAL_WINDOW].mean()
    if base > 0 and recent >= 2 * base and recent > 0.2:
        alerts.append(f"REFUSAL RATE DOUBLED: {recent:.0%} in the last {REFUSAL_WINDOW} "
                      f"requests vs {base:.0%} before — suspect the index.")
    elif base == 0 and recent > 0.3:
        alerts.append(f"REFUSAL RATE JUMPED to {recent:.0%} from 0% — suspect the index.")
unc = req[~req["cached"].fillna(False).astype(bool) & ~req["blocked"].fillna(False).astype(bool)]
if len(unc) >= 5 and unc["duration_ms"].tail(20).quantile(0.95) > SLO_P95_MS:
    alerts.append(f"p95 uncached latency above the {SLO_P95_MS} ms SLO "
                  "(look at svc.generate; check provider status and retries).")
if len(req):
    last_hour = req[req["ts"] > req["ts"].max() - pd.Timedelta(hours=1)]
    spend = pd.to_numeric(last_hour["cost_usd"], errors="coerce").fillna(0).sum()
    if spend > HOURLY_BUDGET_USD:
        alerts.append(f"Cost last hour ${spend:.3f} exceeds ${HOURLY_BUDGET_USD:.2f} "
                      "(look for a retry storm or a loop in mode=tools).")
if alerts:
    for a in alerts:
        st.error(a)
else:
    st.success("No alert conditions met. "
               f"(needs ≥{2 * REFUSAL_WINDOW} requests to evaluate refusal-rate doubling)")
