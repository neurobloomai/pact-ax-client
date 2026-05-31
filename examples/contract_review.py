#!/usr/bin/env python3
"""
Contract Review Pipeline
========================
A complete end-to-end example using pact-ax-client.

Two agents collaborate to review an NDA:

  orchestrator   — receives the contract, routes and hands it off
  nda-specialist — registered contract reviewer, processes and returns findings

Pipeline:
  1. nda-specialist registers its capability
  2. orchestrator discovers and routes to the best agent
  3. orchestrator checks trust score before handoff
  4. contract + metadata handed off via state transfer
  5. nda-specialist reviews and returns findings
  6. trust updated with positive outcome
  7. both agents record the episode to episodic memory
  8. summary printed

Usage:
  python examples/contract_review.py              # dry run (no server needed)
  python examples/contract_review.py --live       # against http://localhost:8000
  python examples/contract_review.py --live --url http://my-server:8000
"""

import argparse
import sys
import textwrap

from pact_ax_client import Agent

# ── Sample contract ───────────────────────────────────────────────────────────

NDA_TEXT = """
MUTUAL NON-DISCLOSURE AGREEMENT

This Agreement is entered into as of May 31, 2026, between:
  NeuroBloom.ai, Inc. ("Company A")
  ACME Corp. ("Company B")

1. CONFIDENTIAL INFORMATION
   Each party may disclose confidential information to the other solely for
   evaluating a potential business relationship ("Purpose").

2. OBLIGATIONS
   Each party agrees to: (a) hold the other party's Confidential Information
   in strict confidence; (b) not disclose it to third parties without prior
   written consent; (c) use it only for the Purpose.

3. TERM
   This Agreement shall remain in effect for two (2) years from the date above.

4. GOVERNING LAW
   This Agreement shall be governed by the laws of the State of California.
""".strip()


# ── Simulated review logic ────────────────────────────────────────────────────

def review_contract(contract_text: str) -> dict:
    """
    Simulated contract review.
    In production: pass contract_text to an LLM with a review prompt.
    """
    return {
        "risk_level": "low",
        "recommendation": "approved_with_notes",
        "findings": [
            "Standard mutual NDA — both parties are equally bound.",
            "2-year term is within normal range (1–3 years typical).",
            "California governing law — favorable for Company A.",
            "No carve-outs for prior knowledge — recommend adding standard exclusions.",
        ],
    }


# ── Dry-run mock setup ────────────────────────────────────────────────────────

def build_mocks(mock, base_url: str):
    """Wire respx mocks for every API call in the pipeline."""
    import httpx

    mock.post("/capabilities/register").mock(return_value=httpx.Response(200, json={
        "agent_id": "nda-specialist", "skill": "contract_review",
        "description": "Reviews NDAs and MSAs for risk and compliance",
        "tags": ["legal", "nda"], "version": "1.0", "updated_at": "", "registered": True,
    }))

    mock.post("/route").mock(return_value=httpx.Response(200, json={
        "skill": "contract_review", "from_agent": "orchestrator",
        "best_agent": "nda-specialist", "routed": True,
        "strategy_used": "trust_weighted", "total_capable": 1,
        "min_trust": 0.0, "top_k": 5,
        "candidates": [{"agent_id": "nda-specialist", "skill": "contract_review",
                        "trust_score": 0.75, "description": "Reviews NDAs", "tags": ["legal", "nda"]}],
    }))

    mock.get("/trust/orchestrator/nda-specialist").mock(return_value=httpx.Response(200, json={
        "agent_id": "orchestrator", "target_id": "nda-specialist",
        "score": 0.75, "trust_score": 0.75, "recommendation": "proceed",
    }))

    mock.post("/transfer/prepare").mock(return_value=httpx.Response(200, json={
        "packet_id": "pkt-nda-001", "from_agent_id": "orchestrator",
        "to_agent_id": "nda-specialist", "status": "prepared",
    }))
    mock.post("/transfer/send").mock(return_value=httpx.Response(200, json={
        "packet_id": "pkt-nda-001", "sent": True,
    }))
    mock.post("/transfer/receive").mock(return_value=httpx.Response(200, json={
        "success": True,
    }))

    mock.post("/trust/orchestrator/update").mock(return_value=httpx.Response(200, json={
        "agent_id": "orchestrator", "target_id": "nda-specialist",
        "new_score": 0.82, "outcome": "positive", "context_type": "task_knowledge",
    }))

    mock.post("/memory/episodes/orchestrator").mock(return_value=httpx.Response(200, json={
        "id": "ep-orch-001", "agent_id": "orchestrator", "action": "contract_review",
        "partner_id": "nda-specialist", "outcome": "positive", "importance": 0.8,
        "tags": ["legal", "nda"], "context": {}, "timestamp": "2026-05-31T00:00:00Z",
        "valence": "positive", "session_id": "",
    }))
    mock.post("/memory/episodes/nda-specialist").mock(return_value=httpx.Response(200, json={
        "id": "ep-nda-001", "agent_id": "nda-specialist", "action": "contract_review",
        "partner_id": "orchestrator", "outcome": "positive", "importance": 0.85,
        "tags": ["legal", "nda"], "context": {}, "timestamp": "2026-05-31T00:00:00Z",
        "valence": "positive", "session_id": "",
    }))

    mock.get("/memory/summary/orchestrator").mock(return_value=httpx.Response(200, json={
        "agent_id": "orchestrator", "total_episodes": 1, "avg_importance": 0.8,
        "outcome_breakdown": {"positive": 1},
        "top_partners": [{"partner_id": "nda-specialist", "interactions": 1, "avg_importance": 0.8}],
    }))


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run(base_url: str, dry_run: bool):
    W = 62

    def banner(step: str, title: str):
        print(f"\n{'─' * W}")
        print(f"  {step}  {title}")
        print(f"{'─' * W}")

    mode = "[DRY RUN — no server needed]" if dry_run else f"server: {base_url}"
    print(f"\n{'═' * W}")
    print(f"  PACT-AX  ·  Contract Review Pipeline")
    print(f"  {mode}")
    print(f"{'═' * W}")

    with Agent("orchestrator",   base_url=base_url) as orch, \
         Agent("nda-specialist", base_url=base_url) as reviewer:

        # ── 1. Register capability ─────────────────────────────────────────
        banner("1.", "nda-specialist registers its capability")
        cap = reviewer.register_capability(
            "contract_review",
            description="Reviews NDAs and MSAs for risk and compliance",
            tags=["legal", "nda"],
        )
        print(f"  skill  = {cap.skill!r}")
        print(f"  tags   = {cap.tags}")

        # ── 2. Route ───────────────────────────────────────────────────────
        banner("2.", "orchestrator routes: who can review this contract?")
        decision = orch.route("contract_review")
        if not decision.routed:
            print("  No capable agent found — aborting.")
            return
        print(f"  best_agent      = {decision.best_agent!r}")
        print(f"  strategy_used   = {decision.strategy_used}")
        print(f"  candidates      = {len(decision.candidates)}")

        # ── 3. Check trust ─────────────────────────────────────────────────
        banner("3.", "orchestrator checks trust before handoff")
        ts = orch.get_trust(decision.best_agent)
        print(f"  trust_score     = {ts.score:.2f}")
        print(f"  recommendation  = {ts.recommendation}")

        # ── 4. Handoff ─────────────────────────────────────────────────────
        banner("4.", "orchestrator hands off contract to nda-specialist")
        result = orch.handoff(
            decision.best_agent,
            state_data={
                "contract_text": NDA_TEXT,
                "metadata": {
                    "parties":         ["NeuroBloom.ai, Inc.", "ACME Corp."],
                    "type":            "mutual_nda",
                    "effective_date":  "2026-05-31",
                    "priority":        "high",
                },
            },
            reason="contract_review_request",
        )
        print(f"  packet_id       = {result.packet_id}")
        print(f"  received        = {result.received}")

        # ── 5. Review ──────────────────────────────────────────────────────
        banner("5.", "nda-specialist reviews the contract")
        findings = review_contract(NDA_TEXT)
        print(f"  risk_level      = {findings['risk_level'].upper()}")
        print(f"  recommendation  = {findings['recommendation']}")
        print()
        for f in findings["findings"]:
            print(f"    • {textwrap.fill(f, width=56, subsequent_indent='      ')}")

        # ── 6. Update trust ────────────────────────────────────────────────
        banner("6.", "orchestrator updates trust after successful review")
        updated = orch.update_trust(decision.best_agent, outcome="positive", impact=0.8)
        print(f"  trust score     {ts.score:.2f}  →  {updated.score:.2f}")

        # ── 7. Record episodes ─────────────────────────────────────────────
        banner("7.", "both agents record the episode to episodic memory")
        orch_ep = orch.remember(
            "contract_review",
            partner_id="nda-specialist",
            outcome="positive",
            importance=0.8,
            tags=["legal", "nda"],
        )
        rev_ep = reviewer.remember(
            "contract_review",
            partner_id="orchestrator",
            outcome="positive",
            importance=0.85,
            tags=["legal", "nda"],
        )
        print(f"  orchestrator    episode {orch_ep.id!r}")
        print(f"  nda-specialist  episode {rev_ep.id!r}")

        # ── Summary ────────────────────────────────────────────────────────
        banner("✓", "Summary — orchestrator memory")
        s = orch.memory_summary()
        print(f"  total episodes  = {s.total_episodes}")
        print(f"  avg importance  = {s.avg_importance:.2f}")
        print(f"  outcomes        = {s.outcome_breakdown}")
        if s.top_partners:
            p = s.top_partners[0]
            print(f"  top partner     = {p['partner_id']} ({p['interactions']} interaction)")

    print(f"\n{'═' * W}")
    print("  Pipeline complete.")
    print(f"{'═' * W}\n")


# ── Entrypoint ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Contract Review Pipeline — pact-ax-client end-to-end example"
    )
    parser.add_argument("--url",      default="http://localhost:8000", help="pact-ax server URL")
    parser.add_argument("--live",     action="store_true", help="Run against a real server")
    args = parser.parse_args()

    dry_run = not args.live

    if dry_run:
        try:
            import respx
        except ImportError:
            print("respx is required for dry-run mode:")
            print("  pip install pact-ax-client[dev]")
            sys.exit(1)
        import respx
        with respx.mock(base_url=args.url, assert_all_called=False) as mock:
            build_mocks(mock, args.url)
            run(args.url, dry_run=True)
    else:
        run(args.url, dry_run=False)


if __name__ == "__main__":
    main()
