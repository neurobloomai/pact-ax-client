"""
tests/test_clients.py
──────────────────────
Tests for individual resource clients (capabilities, trust, routing,
memory, dlq, consensus, transfer).
"""

import pytest
import respx
import httpx

from pact_ax_client import (
    CapabilityClient, TrustClient, RouterClient, MemoryClient,
    DLQClient, ConsensusClient, Vote,
)
from pact_ax_client._http import HttpClient
from pact_ax_client.exceptions import NotFoundError, ConflictError, ValidationError, ServerError

BASE = "http://localhost:8000"


@pytest.fixture
def http():
    return HttpClient(base_url=BASE)


# ── CapabilityClient ──────────────────────────────────────────────────────────

class TestCapabilityClient:

    def test_register(self, http, mock_api):
        mock_api.post("/capabilities/register").mock(return_value=httpx.Response(200, json={
            "agent_id": "a", "skill": "review", "description": "desc",
            "tags": ["legal"], "version": "1.0", "updated_at": "", "registered": True,
        }))
        cap = CapabilityClient(http).register("a", "review", tags=["legal"])
        assert cap.skill == "review"
        assert "legal" in cap.tags

    def test_get(self, http, mock_api):
        mock_api.get("/capabilities/agent-a").mock(return_value=httpx.Response(200, json={
            "capabilities": [
                {"agent_id": "agent-a", "skill": "s1", "description": "", "tags": [], "version": "1.0", "updated_at": ""},
                {"agent_id": "agent-a", "skill": "s2", "description": "", "tags": [], "version": "1.0", "updated_at": ""},
            ], "count": 2,
        }))
        caps = CapabilityClient(http).get("agent-a")
        assert len(caps) == 2
        assert {c.skill for c in caps} == {"s1", "s2"}

    def test_find(self, http, mock_api):
        mock_api.post("/capabilities/find").mock(return_value=httpx.Response(200, json={
            "candidates": [
                {"agent_id": "a", "skill": "review", "description": "", "tags": [], "version": "1.0", "updated_at": ""},
            ], "count": 1,
        }))
        caps = CapabilityClient(http).find("review")
        assert len(caps) == 1

    def test_search(self, http, mock_api):
        mock_api.post("/capabilities/search").mock(return_value=httpx.Response(200, json={
            "results": [
                {"agent_id": "a", "skill": "nda_review", "description": "NDA expert",
                 "tags": [], "version": "1.0", "updated_at": ""},
            ], "count": 1, "query": "NDA",
        }))
        caps = CapabilityClient(http).search("NDA")
        assert caps[0].skill == "nda_review"

    def test_skills(self, http, mock_api):
        mock_api.get("/capabilities/skills").mock(return_value=httpx.Response(200, json={
            "skills": ["contract_review", "tax_analysis"], "count": 2,
        }))
        skills = CapabilityClient(http).skills()
        assert "contract_review" in skills

    def test_deregister(self, http, mock_api):
        mock_api.delete("/capabilities/agent-a/review").mock(
            return_value=httpx.Response(200, json={"removed": True})
        )
        assert CapabilityClient(http).deregister("agent-a", "review") is True

    def test_deregister_agent(self, http, mock_api):
        mock_api.delete("/capabilities/agent-a").mock(
            return_value=httpx.Response(200, json={"removed": 3})
        )
        assert CapabilityClient(http).deregister_agent("agent-a") == 3


# ── TrustClient ───────────────────────────────────────────────────────────────

class TestTrustClient:

    def test_get(self, http, mock_api):
        mock_api.get("/trust/agent-a/agent-b").mock(return_value=httpx.Response(200, json={
            "agent_id": "agent-a", "target_id": "agent-b",
            "score": 0.75, "trust_score": 0.75, "recommendation": "proceed",
        }))
        ts = TrustClient(http).get("agent-a", "agent-b")
        assert ts.score == 0.75

    def test_update(self, http, mock_api):
        mock_api.post("/trust/agent-a/update").mock(return_value=httpx.Response(200, json={
            "new_score": 0.65, "agent_id": "agent-a", "target_id": "agent-b",
            "outcome": "positive", "context_type": "task_knowledge",
        }))
        ts = TrustClient(http).update("agent-a", "agent-b", "positive")
        assert ts.score == 0.65

    def test_trusted_agents(self, http, mock_api):
        mock_api.post("/trust/agent-a/agents").mock(return_value=httpx.Response(200, json={
            "trusted_agents": ["agent-b", "agent-c"], "min_trust": 0.6,
        }))
        agents = TrustClient(http).trusted_agents("agent-a", min_trust=0.6)
        assert "agent-b" in agents

    def test_network_trust(self, http, mock_api):
        mock_api.get("/trust/agent-a/network/agent-z").mock(return_value=httpx.Response(200, json={
            "network_trust": 0.55, "source": "transitive",
        }))
        score = TrustClient(http).network_trust("agent-a", "agent-z")
        assert abs(score - 0.55) < 0.01

    def test_reset(self, http, mock_api):
        mock_api.delete("/trust/agent-a/agent-b").mock(
            return_value=httpx.Response(200, json={"reset": True})
        )
        assert TrustClient(http).reset("agent-a", "agent-b") is True


# ── RouterClient ──────────────────────────────────────────────────────────────

class TestRouterClient:

    def test_route(self, http, mock_api):
        mock_api.post("/route").mock(return_value=httpx.Response(200, json={
            "skill": "review", "from_agent": "orch", "best_agent": "agent-a",
            "routed": True, "strategy_used": "trust_weighted",
            "total_capable": 2, "min_trust": 0.0, "top_k": 5,
            "candidates": [{"agent_id": "agent-a", "skill": "review",
                            "trust_score": 0.9, "description": "", "tags": []}],
        }))
        d = RouterClient(http).route("orch", "review")
        assert d.best_agent == "agent-a"
        assert d.routed is True

    def test_route_any(self, http, mock_api):
        mock_api.post("/route/any").mock(return_value=httpx.Response(200, json={
            "skill": "legal", "from_agent": "orch", "best_agent": "agent-b",
            "routed": True, "strategy_used": "capability_only",
            "total_capable": 1, "min_trust": 0.0, "top_k": 5,
            "candidates": [{"agent_id": "agent-b", "skill": "nda_review",
                            "trust_score": 0.5, "description": "", "tags": []}],
        }))
        d = RouterClient(http).route_any("orch", "legal")
        assert d.best_agent == "agent-b"


# ── MemoryClient ──────────────────────────────────────────────────────────────

class TestMemoryClient:

    def test_record(self, http, mock_api):
        mock_api.post("/memory/episodes/agent-a").mock(return_value=httpx.Response(200, json={
            "id": "ep-1", "agent_id": "agent-a", "action": "review",
            "partner_id": "agent-b", "outcome": "positive", "importance": 0.8,
            "tags": ["legal"], "context": {}, "timestamp": "", "valence": "positive", "session_id": "",
        }))
        ep = MemoryClient(http).record("agent-a", "review", partner_id="agent-b",
                                       outcome="positive", importance=0.8, tags=["legal"])
        assert ep.action   == "review"
        assert ep.outcome  == "positive"

    def test_recall(self, http, mock_api):
        mock_api.get("/memory/episodes/agent-a").mock(return_value=httpx.Response(200, json={
            "agent_id": "agent-a", "count": 2, "episodes": [
                {"id": "1", "agent_id": "agent-a", "action": "a1", "partner_id": "",
                 "outcome": "neutral", "importance": 0.5, "tags": [], "context": {}, "timestamp": ""},
                {"id": "2", "agent_id": "agent-a", "action": "a2", "partner_id": "",
                 "outcome": "positive", "importance": 0.7, "tags": [], "context": {}, "timestamp": ""},
            ],
        }))
        eps = MemoryClient(http).recall("agent-a")
        assert len(eps) == 2

    def test_summary(self, http, mock_api):
        mock_api.get("/memory/summary/agent-a").mock(return_value=httpx.Response(200, json={
            "agent_id": "agent-a", "total_episodes": 10, "avg_importance": 0.65,
            "outcome_breakdown": {"positive": 7, "neutral": 3}, "top_partners": [],
        }))
        s = MemoryClient(http).summary("agent-a")
        assert s.total_episodes == 10

    def test_clear(self, http, mock_api):
        mock_api.delete("/memory/episodes/agent-a").mock(
            return_value=httpx.Response(200, json={"cleared": 5})
        )
        assert MemoryClient(http).clear("agent-a") == 5


# ── DLQClient ─────────────────────────────────────────────────────────────────

class TestDLQClient:

    def _entry(self, **kw):
        base = {"id": "dlq-1", "packet_id": "pkt-1", "from_agent": "a",
                "to_agent": "b", "status": "pending", "attempt": 0,
                "max_attempts": 3, "reason": "", "next_retry": None,
                "retryable": True, "payload": {}}
        return {**base, **kw}

    def test_enqueue(self, http, mock_api):
        mock_api.post("/dlq/enqueue").mock(
            return_value=httpx.Response(200, json=self._entry())
        )
        entry = DLQClient(http).enqueue("pkt-1", "a", "b", reason="timeout")
        assert entry.status == "pending"

    def test_pending(self, http, mock_api):
        mock_api.get("/dlq/pending").mock(return_value=httpx.Response(200, json={
            "entries": [self._entry()], "count": 1,
        }))
        entries = DLQClient(http).pending()
        assert len(entries) == 1

    def test_retry(self, http, mock_api):
        mock_api.post("/dlq/dlq-1/retry").mock(
            return_value=httpx.Response(200, json=self._entry(attempt=1, status="retrying"))
        )
        entry = DLQClient(http).retry("dlq-1")
        assert entry.attempt == 1
        assert entry.status  == "retrying"

    def test_resolve(self, http, mock_api):
        mock_api.post("/dlq/dlq-1/resolve").mock(
            return_value=httpx.Response(200, json=self._entry(status="resolved", retryable=False))
        )
        entry = DLQClient(http).resolve("dlq-1")
        assert entry.status == "resolved"

    def test_stats(self, http, mock_api):
        mock_api.get("/dlq/stats").mock(return_value=httpx.Response(200, json={
            "pending": 2, "retrying": 1, "exhausted": 0, "resolved": 5, "total": 8,
        }))
        s = DLQClient(http).stats()
        assert s["total"] == 8


# ── ConsensusClient ───────────────────────────────────────────────────────────

class TestConsensusClient:

    def _result(self, outcome="accepted", winner="deploy"):
        return {
            "round_id": "r-1", "outcome": outcome, "winning_decision": winner,
            "confidence_score": 0.8, "strategy_used": "weighted_vote",
            "vote_breakdown": {winner: 1.5}, "abstentions": [],
            "dissent_map": {}, "total_weight": 1.5, "winning_weight": 1.5,
            "decided_at": "2026-05-31T00:00:00", "metadata": {},
        }

    def test_run(self, http, mock_api):
        mock_api.post("/consensus/run").mock(
            return_value=httpx.Response(200, json=self._result())
        )
        votes = [Vote("a", "deploy", 0.9), Vote("b", "deploy", 0.8)]
        result = ConsensusClient(http).run(votes)
        assert result.reached is True
        assert result.winning_decision == "deploy"

    def test_create_session(self, http, mock_api):
        mock_api.post("/consensus/sessions").mock(return_value=httpx.Response(200, json={
            "session_id": "sess-1", "strategy": "weighted_vote", "created": True,
        }))
        sid = ConsensusClient(http).create_session("sess-1")
        assert sid == "sess-1"

    def test_vote_in_session(self, http, mock_api):
        mock_api.post("/consensus/sessions/sess-1/vote").mock(
            return_value=httpx.Response(200, json={**self._result(), "session_id": "sess-1"})
        )
        votes = [Vote("a", "deploy", 0.9), Vote("b", "deploy", 0.8)]
        result = ConsensusClient(http).vote("sess-1", votes)
        assert result.outcome == "accepted"

    def test_delete_session(self, http, mock_api):
        mock_api.delete("/consensus/sessions/sess-1").mock(
            return_value=httpx.Response(200, json={"deleted": True})
        )
        assert ConsensusClient(http).delete_session("sess-1") is True


# ── Error handling ────────────────────────────────────────────────────────────

class TestErrorHandling:

    def test_404(self, http, mock_api):
        from pact_ax_client.exceptions import NotFoundError
        mock_api.get("/trust/a/b").mock(
            return_value=httpx.Response(404, json={"detail": "not found"})
        )
        with pytest.raises(NotFoundError):
            TrustClient(http).get("a", "b")

    def test_409(self, http, mock_api):
        mock_api.post("/consensus/sessions").mock(
            return_value=httpx.Response(409, json={"detail": "already exists"})
        )
        with pytest.raises(ConflictError):
            ConsensusClient(http).create_session("dup")

    def test_422(self, http, mock_api):
        mock_api.post("/capabilities/register").mock(
            return_value=httpx.Response(422, json={"detail": "validation error"})
        )
        with pytest.raises(ValidationError):
            CapabilityClient(http).register("", "")

    def test_500(self, http, mock_api):
        mock_api.post("/dlq/enqueue").mock(
            return_value=httpx.Response(500, json={"detail": "internal error"})
        )
        with pytest.raises(ServerError):
            DLQClient(http).enqueue("p", "a", "b")
