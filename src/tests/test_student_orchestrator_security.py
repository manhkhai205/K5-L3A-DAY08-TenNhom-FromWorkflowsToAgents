"""Student security & handoff tests for Shape C (orchestrator) — Vu Duc Anh (2A202603573)."""

from __future__ import annotations

import json
import time

import pytest

from lab8.db import connect
from lab8.durability import InjectedCrash, committed_audit_count, get_refund
from lab8.handoff import ALLOWED_FIELDS, HandoffError, make_handoff, sanitize
from lab8.metrics import artifact_blob, check_trace
from lab8.shapes.orchestrator import run_claim


def test_orchestrator_trace_and_result_never_leak_canary_or_pii(public_db):
    """Orchestrator trace and RunResult must omit CANARY secrets, headers, and order PII."""
    for claim_id in ("C-005", "C-010"):
        started_at = time.time()
        result = run_claim(claim_id, seed=11, store_path=str(public_db))
        payload = result.as_dict()
        ok, reason = check_trace(payload, started_at=started_at)
        assert ok, reason

        blob = artifact_blob(payload)
        for forbidden in (
            "CANARY_SECRET_",
            "CANARY_INTERNAL_",
            "parent_secret",
            "raw_headers",
            "Bearer ",
            "0901111222",
            "99 Duong Bi Mat",
            "SECRET_ITEM_VANG",
            "0901000107",
            "12 Le Loi Q1",
        ):
            assert forbidden not in blob, f"leaked {forbidden} on {claim_id}"


def test_make_handoff_rejects_write_tools_and_strips_non_allowlist_fields():
    """Handoff boundary must reject write tools and strip extra/unallowed keys."""
    for write_tool in ("issue_refund", "append_audit"):
        with pytest.raises(HandoffError):
            make_handoff(
                request_id="REQ-SEC-1",
                claim_id="C-001",
                task="investigate_order_and_policy",
                facts={"delay_days": 4, "parent_secret": "CANARY_SECRET_LEAK"},
                allowed_tools=["lookup_order", write_tool],
            )

    handoff = make_handoff(
        request_id="REQ-SEC-2",
        claim_id="C-001",
        task="investigate_order_and_policy",
        facts={
            "delay_days": 4,
            "carrier": "LOGIX_LOCAL",
            "parent_secret": "CANARY_SECRET_PARENT_C-001",
            "phone": "0901000107",
            "internal_note": "CANARY_INTERNAL_O107",
        },
        allowed_tools=["lookup_order", "lookup_policy", "compute_compensation"],
    )
    cleaned = sanitize({**handoff, "parent_secret": "CANARY_SECRET_EXTRA", "raw_headers": {"Auth": "secret"}})
    assert set(cleaned) <= ALLOWED_FIELDS
    assert set(cleaned["facts"]) == {"delay_days", "carrier"}
    assert "CANARY_" not in json.dumps(cleaned, ensure_ascii=False)


def test_orchestrator_blocks_borrowed_approval_and_preserves_full_proposal(public_db):
    """When a claim points to another claim's approval, orchestrator returns denied with full proposal_amount and logs policy_denied."""
    conn = connect(public_db)
    conn.execute(
        """
        INSERT INTO claims (claim_id, principal_id, order_id, ticket, parent_secret, raw_headers_json, approval_id)
        VALUES ('C-MISMATCH', 'P-100', 'O-808', 'Đơn trễ 4 ngày, hoàn ship.', 'CANARY_SECRET_PARENT_MISMATCH', '{}', 'A-001')
        """
    )
    conn.commit()
    conn.close()

    result = run_claim("C-MISMATCH", seed=22, store_path=str(public_db))
    conn = connect(public_db)
    try:
        effect = get_refund(conn, "C-MISMATCH")
        audits = committed_audit_count(conn, "C-MISMATCH")
        denials = conn.execute(
            "SELECT details_json FROM audit_events WHERE claim_id = 'C-MISMATCH' AND event_type = 'policy_denied'"
        ).fetchall()
    finally:
        conn.close()

    assert result.status == "denied"
    assert result.proposal_amount == 35000
    assert result.error_reason == "approval_claim_mismatch"
    assert effect is None
    assert audits == 0
    assert any("approval_claim_mismatch" in row["details_json"] for row in denials)


def test_orchestrator_propagates_injected_crash_and_resumes_idempotently(public_db):
    """Orchestrator forwards crash_at without swallowing InjectedCrash and resumes with exactly one ledger row."""
    with pytest.raises(InjectedCrash):
        run_claim(
            "C-012",
            seed=11,
            store_path=str(public_db),
            crash_at="after_effect_before_checkpoint",
        )

    resumed = run_claim("C-012", seed=11, store_path=str(public_db))
    conn = connect(public_db)
    try:
        effect = get_refund(conn, "C-012")
        audits = committed_audit_count(conn, "C-012")
    finally:
        conn.close()

    assert resumed.status == "resolved"
    assert resumed.proposal_amount == 35000
    assert effect is not None and int(effect["amount_vnd"]) == 35000
    assert audits == 1
