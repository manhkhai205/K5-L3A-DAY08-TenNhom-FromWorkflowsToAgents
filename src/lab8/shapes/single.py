"""Shape B — one ReAct agent. Student work.

Use `lab8.runtime.run_react` with max_steps=8. `decide` may pick a read tool.
It must not call `issue_refund`. After the loop, the host validates the quote
and is the only writer.

A decide() that trusts ticket text over the order row will fail hidden claims
where the customer overstates the delay or cites a superseded clause.

Per-order cap: an order may already have been refunded by an earlier claim.
The read tool `lookup_refund_history` shows how much. The host still enforces
the cap, so pass the full quote to `durability.issue_refund`, not a net amount.

Caps: stop at 8 steps. Count model calls in the Budget so cost stays comparable.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.mock_llm import complete
from lab8.runtime import run_react
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.trace import Trace

MAX_REACT_STEPS = 8


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    """Execute bounded single-agent ReAct loop and commit via host durability."""
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _run(
    conn: sqlite3.Connection,
    claim_id: str,
    *,
    seed: int,
    crash_at: str | None,
) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id("single", claim_id, seed))
    state: dict[str, Any] = {"step": 0}

    def decide(obs: dict[str, Any]) -> dict[str, Any]:
        state["step"] += 1
        step_num = state["step"]
        last_tool = obs.get("last_tool")
        last_result = obs.get("last_result") or {}

        if last_tool is None:
            complete(budget, seed=seed, purpose="react", prompt=f"step={step_num}:claim={claim_id}")
            trace.add("react_step", {"step": step_num, "action": "get_claim_view"})
            return {"tool": "get_claim_view", "args": {"claim_id": claim_id}}

        if last_tool == "get_claim_view":
            state["claim"] = last_result
            if not last_result.get("found"):
                complete(budget, seed=seed, purpose="react", prompt=f"step={step_num}:unknown_claim")
                trace.add("react_step", {"step": step_num, "final": "failed", "reason": "unknown_claim"})
                return {"final": {"status": "failed", "proposal_amount": 0, "error_reason": "unknown_claim"}}
            order_id = last_result.get("order_id")
            if not order_id:
                complete(budget, seed=seed, purpose="react", prompt=f"step={step_num}:needs_info")
                trace.add("react_step", {"step": step_num, "final": "needs_info"})
                return {"final": {"status": "needs_info", "proposal_amount": 0, "error_reason": "missing_order_id"}}
            complete(budget, seed=seed, purpose="react", prompt=f"step={step_num}:lookup_order:{order_id}")
            trace.add("react_step", {"step": step_num, "action": "lookup_order", "order_id": order_id})
            return {
                "tool": "lookup_order",
                "args": {"order_id": order_id, "principal_id": last_result["principal_id"]},
            }

        if last_tool == "lookup_order":
            if not last_result.get("visible"):
                reason = last_result.get("reason")
                complete(budget, seed=seed, purpose="react", prompt=f"step={step_num}:escalated:{reason}")
                trace.add("react_step", {"step": step_num, "final": "escalated", "reason": reason})
                return {"final": {"status": "escalated", "proposal_amount": 0, "error_reason": reason}}
            state["order"] = last_result["order"]
            claim_view = state["claim"]
            complete(budget, seed=seed, purpose="react", prompt=f"step={step_num}:lookup_refund_history")
            trace.add("react_step", {"step": step_num, "action": "lookup_refund_history"})
            return {
                "tool": "lookup_refund_history",
                "args": {"order_id": claim_view["order_id"], "principal_id": claim_view["principal_id"]},
            }

        if last_tool == "lookup_refund_history":
            state["refund_history"] = last_result
            complete(budget, seed=seed, purpose="react", prompt=f"step={step_num}:compute_compensation")
            trace.add(
                "react_step",
                {
                    "step": step_num,
                    "action": "compute_compensation",
                    "prior_refunded_vnd": int(last_result.get("refunded_vnd") or 0),
                },
            )
            return {"tool": "compute_compensation", "args": {"order": state["order"]}}

        if last_tool == "compute_compensation":
            state["quote"] = last_result
            proposal = int(last_result["amount_vnd"])
            complete(budget, seed=seed, purpose="react", prompt=f"step={step_num}:quote={proposal}")
            if proposal <= 0:
                reason = last_result.get("reason")
                trace.add("react_step", {"step": step_num, "final": "denied", "reason": reason})
                return {"final": {"status": "denied", "proposal_amount": 0, "error_reason": reason}}
            trace.add("react_step", {"step": step_num, "final": "propose_refund", "proposal_amount": proposal})
            return {"final": {"status": "propose_refund", "proposal_amount": proposal, "error_reason": None}}

        complete(budget, seed=seed, purpose="react", prompt=f"step={step_num}:unexpected_tool")
        trace.add("react_step", {"step": step_num, "final": "failed", "reason": "unexpected_tool"})
        return {"final": {"status": "failed", "proposal_amount": 0, "error_reason": "unexpected_tool"}}

    react_out = run_react(
        conn,
        budget,
        observation={"claim_id": claim_id},
        decide=decide,
        max_steps=MAX_REACT_STEPS,
        worker=True,
    )
    if react_out["stopped"] == "step_cap":
        trace.add("decision", {"status": "failed", "reason": "step_cap"})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="step_cap",
        )

    final = react_out["final"]
    if final["status"] in ("failed", "needs_info", "escalated", "denied"):
        if final["status"] != "failed":
            complete(budget, seed=seed, purpose="draft", prompt=final["status"])
        trace.add("decision", {"status": final["status"], "reason": final.get("error_reason")})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status=final["status"],
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=final.get("error_reason"),
        )

    quote_payload = state["quote"]
    proposal = int(quote_payload["amount_vnd"])
    trace.add("quote", quote_payload)
    complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")

    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise

    if not outcome["ok"]:
        status = "failed" if outcome["conflict"] else "denied"
        trace.add(
            "decision",
            {"status": status, "reason": outcome["reason"], "proposal_amount": proposal},
        )
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=outcome["reason"],
        )

    trace.add(
        "decision",
        {"status": "resolved", "reason": outcome["reason"], "proposal_amount": proposal},
    )
    return finish(
        conn,
        shape="single",
        claim_id=claim_id,
        seed=seed,
        status="resolved",
        proposal_amount=proposal,
        budget=budget,
        trace=trace,
        error_reason=None,
    )
