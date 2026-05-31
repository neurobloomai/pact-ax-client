"""
tests/test_agent.py
────────────────────
Tests for the high-level Agent class.
All HTTP calls are mocked with respx.
"""

import pytest
import respx
import httpx

from pact_ax_client import Agent
from pact_ax_client.exceptions import NotFoundError

BASE = "http://localhost:8000"


@pytest.fixture
def agent():
    with Agent("agent-a", base_url=BASE) as a:
        yield a


# ── register_capability ───────────────────────────────────────────────────────

def test_register_capability(agent, mock_api):
    mock_api.post("/capabilities/register").mock(return_value=httpx.Response(200, json={
        "agent_id": "agent-a", "skill": "contract_review",
        "description": "NDA review", "tags": ["legal"],
        "version": "1.0", "updated_at": "", "registered": True,
    }))
    cap = agent.register_capability("contract_review", description="NDA review", tags=["legal"])
    assert cap.agent_id == "agent-a"
    assert cap.skill    == "contract_review"
    assert "legal" in cap.tags


# ── get_trust / update_trust ──────────────────────────────────────────────────

def test_get_trust(agent, mock_api):
    mock_api.get("/trust/agent-a/agent-b").mock(return_value=httpx.Response(200, json={
        "agent_id": "agent-a", "target_id": "agent-b",
        "score": 0.75, "trust_score": 0.75, "recommendation": "proceed",
    }))
    ts = agent.get_trust("agent-b")
    assert ts.score == 0.75
    assert ts.recommendation == "proceed"


def test_update_trust(agent, mock_api):
    mock_api.post("/trust/agent-a/update").mock(return_value=httpx.Response(200, json={
        "agent_id": "agent-a", "target_id": "agent-b", "new_score": 0.65,
        "outcome": "positive", "context_type": "task_knowledge",
    }))
    ts = agent.update_trust("agent-b", outcome="positive", impact=0.8)
    assert ts.score == 0.65


# ── route ─────────────────────────────────────────────────────────────────────

def test_route(agent, mock_api):
    mock_api.post("/route").mock(return_value=httpx.Response(200, json={
        "skill": "contract_review", "from_agent": "agent-a",
        "best_agent": "agent-b", "routed": True, "strategy_used": "trust_weighted",
        "total_capable": 3, "min_trust": 0.0, "top_k": 5,
        "candidates": [
            {"agent_id": "agent-b", "skill": "contract_review",
             "trust_score": 0.8, "description": "", "tags": []},
        ],
    }))
    decision = agent.route("contract_review")
    assert decision.best_agent == "agent-b"
    assert decision.routed is True
    assert decision.strategy_used == "trust_weighted"
    assert len(decision.candidates) == 1


def test_route_no_candidates(agent, mock_api):
    mock_api.post("/route").mock(return_value=httpx.Response(200, json={
        "skill": "unknown", "from_agent": "agent-a",
        "best_agent": None, "routed": False, "strategy_used": "none",
        "total_capable": 0, "min_trust": 0.0, "top_k": 5, "candidates": [],
    }))
    decision = agent.route("unknown")
    assert decision.routed is False
    assert decision.best_agent is None


def test_route_any(agent, mock_api):
    mock_api.post("/route/any").mock(return_value=httpx.Response(200, json={
        "skill": "legal", "from_agent": "agent-a",
        "best_agent": "agent-c", "routed": True, "strategy_used": "capability_only",
        "total_capable": 2, "min_trust": 0.0, "top_k": 5,
        "candidates": [{"agent_id": "agent-c", "skill": "ip_licensing",
                        "trust_score": 0.5, "description": "", "tags": []}],
    }))
    decision = agent.route_any("legal")
    assert decision.best_agent == "agent-c"


# ── remember / recall ─────────────────────────────────────────────────────────

def test_remember(agent, mock_api):
    mock_api.post("/memory/episodes/agent-a").mock(return_value=httpx.Response(200, json={
        "id": "ep-1", "agent_id": "agent-a", "action": "contract_review",
        "partner_id": "agent-b", "outcome": "positive", "importance": 0.9,
        "tags": ["legal"], "context": {}, "timestamp": "2026-05-31T00:00:00Z",
        "valence": "positive", "session_id": "",
    }))
    ep = agent.remember("contract_review", partner_id="agent-b",
                        outcome="positive", importance=0.9, tags=["legal"])
    assert ep.action    == "contract_review"
    assert ep.outcome   == "positive"
    assert ep.partner_id == "agent-b"


def test_recall(agent, mock_api):
    mock_api.get("/memory/episodes/agent-a").mock(return_value=httpx.Response(200, json={
        "agent_id": "agent-a", "count": 1,
        "episodes": [{"id": "ep-1", "agent_id": "agent-a", "action": "review",
                      "partner_id": "agent-b", "outcome": "positive",
                      "importance": 0.8, "tags": [], "context": {},
                      "timestamp": ""}],
    }))
    eps = agent.recall()
    assert len(eps) == 1
    assert eps[0].outcome == "positive"


def test_memory_summary(agent, mock_api):
    mock_api.get("/memory/summary/agent-a").mock(return_value=httpx.Response(200, json={
        "agent_id": "agent-a", "total_episodes": 5, "avg_importance": 0.7,
        "outcome_breakdown": {"positive": 3, "neutral": 2},
        "top_partners": [{"partner_id": "agent-b", "interactions": 3, "avg_importance": 0.8}],
    }))
    s = agent.memory_summary()
    assert s.total_episodes == 5
    assert s.outcome_breakdown["positive"] == 3


# ── handoff ───────────────────────────────────────────────────────────────────

def test_handoff(agent, mock_api):
    mock_api.post("/transfer/prepare").mock(return_value=httpx.Response(200, json={
        "packet_id": "pkt-abc", "from_agent_id": "agent-a", "to_agent_id": "agent-b",
        "status": "prepared",
    }))
    mock_api.post("/transfer/send").mock(return_value=httpx.Response(200, json={
        "packet_id": "pkt-abc", "sent": True,
    }))
    mock_api.post("/transfer/receive").mock(return_value=httpx.Response(200, json={
        "success": True,
    }))
    result = agent.handoff("agent-b", state_data={"task": "review NDA"})
    assert result.packet_id  == "pkt-abc"
    assert result.received   is True
    assert result.to_agent   == "agent-b"


# ── enqueue_failed ────────────────────────────────────────────────────────────

def test_enqueue_failed(agent, mock_api):
    mock_api.post("/dlq/enqueue").mock(return_value=httpx.Response(200, json={
        "id": "dlq-1", "packet_id": "pkt-xyz", "from_agent": "agent-a",
        "to_agent": "agent-b", "status": "pending", "attempt": 0,
        "max_attempts": 3, "reason": "timeout", "next_retry": None,
        "retryable": True, "payload": {},
    }))
    entry = agent.enqueue_failed("pkt-xyz", "agent-b", reason="timeout")
    assert entry.status   == "pending"
    assert entry.retryable is True


# ── vote (consensus) ──────────────────────────────────────────────────────────

def test_vote(agent, mock_api):
    from pact_ax_client import Vote
    mock_api.post("/consensus/run").mock(return_value=httpx.Response(200, json={
        "round_id": "r-1", "outcome": "accepted",
        "winning_decision": "deploy", "confidence_score": 0.8,
        "strategy_used": "weighted_vote", "vote_breakdown": {"deploy": 1.5},
        "abstentions": [], "dissent_map": {}, "total_weight": 1.5,
        "winning_weight": 1.5, "decided_at": "2026-05-31T00:00:00",
        "metadata": {},
    }))
    other = [Vote("agent-b", "deploy", 0.75)]
    result = agent.vote("deploy", 0.85, other_votes=other)
    assert result.reached is True
    assert result.winning_decision == "deploy"


# ── error handling ────────────────────────────────────────────────────────────

def test_404_raises_not_found(agent, mock_api):
    mock_api.get("/trust/agent-a/nobody").mock(
        return_value=httpx.Response(404, json={"detail": "not found"})
    )
    with pytest.raises(NotFoundError):
        agent.get_trust("nobody")


def test_repr(agent):
    assert "agent-a" in repr(agent)
