"""
pact_ax_client/agent.py
────────────────────────
Agent — the primary high-level entry point for the SDK.

30-second quickstart
────────────────────
    from pact_ax_client import Agent

    agent = Agent("my-agent", base_url="http://localhost:8000")
    agent.register_capability("contract_review", description="Reviews NDAs")

    decision = agent.route("contract_review")
    print(f"Best agent: {decision.best_agent}")

    agent.remember("contract_review", partner_id=decision.best_agent, outcome="positive")

Full handoff
────────────
    result = agent.handoff("agent-b", state_data={"task": "review this NDA"})
    print(f"Handed off: {result.packet_id}, received: {result.received}")
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ._http import HttpClient
from .capabilities import CapabilityClient
from .consensus import ConsensusClient, Vote
from .dlq import DLQClient
from .memory import MemoryClient
from .models import (
    Capability, ConsensusResult, DLQEntry, Episode,
    HandoffResult, MemorySummary, RouteDecision, TrustScore,
)
from .routing import RouterClient
from .transfer import TransferClient
from .trust import TrustClient


class Agent:
    """
    High-level SDK entry point for a PACT-AX agent.

    All methods are scoped to this agent's ID — you don't need to pass
    agent_id to every call.

    Parameters
    ----------
    agent_id : str
        Unique identifier for this agent.
    base_url : str
        URL of the running pact-ax server.
        Default: "http://localhost:8000"
    api_key : str, optional
        API key if the server has auth enabled.
    timeout : float
        HTTP request timeout in seconds. Default: 30.
    """

    def __init__(
        self,
        agent_id: str,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.agent_id = agent_id
        self._http = HttpClient(base_url=base_url, api_key=api_key, timeout=timeout)

        # Resource clients (also accessible directly for advanced use)
        self.capabilities = CapabilityClient(self._http)
        self.trust        = TrustClient(self._http)
        self.router       = RouterClient(self._http)
        self.memory       = MemoryClient(self._http)
        self.dlq          = DLQClient(self._http)
        self.consensus    = ConsensusClient(self._http)
        self.transfer     = TransferClient(self._http)

    # ── Capabilities ──────────────────────────────────────────────────────────

    def register_capability(
        self,
        skill: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        version: str = "1.0",
    ) -> Capability:
        """Declare that this agent has a skill."""
        return self.capabilities.register(
            self.agent_id, skill, description=description,
            tags=tags, version=version,
        )

    def my_capabilities(self) -> List[Capability]:
        """List all capabilities registered for this agent."""
        return self.capabilities.get(self.agent_id)

    def deregister_capability(self, skill: str) -> bool:
        return self.capabilities.deregister(self.agent_id, skill)

    # ── Trust ─────────────────────────────────────────────────────────────────

    def get_trust(self, target_id: str, context_type: Optional[str] = None) -> TrustScore:
        """Get this agent's trust score for target_id."""
        return self.trust.get(self.agent_id, target_id, context_type=context_type)

    def update_trust(
        self,
        target_id: str,
        outcome: str,
        impact: float = 1.0,
        context_type: str = "task_knowledge",
    ) -> TrustScore:
        """Record a collaboration outcome and update trust score."""
        return self.trust.update(self.agent_id, target_id, outcome,
                                 impact=impact, context_type=context_type)

    def trusted_agents(self, min_trust: float = 0.6) -> List[str]:
        """Return agent IDs this agent trusts above min_trust."""
        return self.trust.trusted_agents(self.agent_id, min_trust=min_trust)

    # ── Routing ───────────────────────────────────────────────────────────────

    def route(
        self,
        skill: str,
        min_trust: float = 0.0,
        top_k: int = 5,
    ) -> RouteDecision:
        """Find the best trusted+capable agent for a skill."""
        return self.router.route(
            from_agent=self.agent_id, skill=skill,
            min_trust=min_trust, top_k=top_k,
        )

    def route_any(
        self,
        query: str,
        min_trust: float = 0.0,
        top_k: int = 5,
    ) -> RouteDecision:
        """Find the best agent by fuzzy keyword search."""
        return self.router.route_any(
            from_agent=self.agent_id, query=query,
            min_trust=min_trust, top_k=top_k,
        )

    # ── Episodic Memory ───────────────────────────────────────────────────────

    def remember(
        self,
        action: str,
        partner_id: str = "",
        outcome: str = "neutral",
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Episode:
        """Record an interaction episode."""
        return self.memory.record(
            self.agent_id, action, partner_id=partner_id,
            outcome=outcome, importance=importance,
            tags=tags, context=context,
        )

    def recall(
        self,
        partner_id: Optional[str] = None,
        outcome: Optional[str] = None,
        min_importance: float = 0.0,
        limit: int = 50,
    ) -> List[Episode]:
        """Recall past episodes, optionally filtered."""
        return self.memory.recall(
            self.agent_id, partner_id=partner_id,
            outcome=outcome, min_importance=min_importance, limit=limit,
        )

    def memory_summary(self) -> MemorySummary:
        """Aggregate stats on this agent's episodic history."""
        return self.memory.summary(self.agent_id)

    # ── Handoff ───────────────────────────────────────────────────────────────

    def handoff(
        self,
        to_agent: str,
        state_data: Dict[str, Any],
        reason: str = "escalation",
    ) -> HandoffResult:
        """
        Hand off state to another agent (prepare → send → receive).
        Returns HandoffResult with packet_id and received status.
        """
        return self.transfer.handoff(
            from_agent=self.agent_id, to_agent=to_agent,
            state_data=state_data, reason=reason,
        )

    def checkpoint(self, state_data: Dict[str, Any], label: str = "") -> str:
        """Save a checkpoint of current state. Returns checkpoint_id."""
        return self.transfer.checkpoint(self.agent_id, state_data, label=label)

    # ── Dead Letter Queue ─────────────────────────────────────────────────────

    def enqueue_failed(
        self,
        packet_id: str,
        to_agent: str,
        payload: Optional[Dict[str, Any]] = None,
        reason: str = "",
    ) -> DLQEntry:
        """Park a failed delivery in the DLQ for retry."""
        return self.dlq.enqueue(
            packet_id=packet_id, from_agent=self.agent_id,
            to_agent=to_agent, payload=payload, reason=reason,
        )

    # ── Consensus ─────────────────────────────────────────────────────────────

    def vote(
        self,
        decision: str,
        confidence: float,
        other_votes: Optional[List[Vote]] = None,
        strategy: str = "weighted_vote",
        trust_scores: Optional[Dict[str, float]] = None,
    ) -> ConsensusResult:
        """
        Cast this agent's vote and run a one-shot consensus round.
        Convenience wrapper for simple yes/no decisions.
        """
        my_vote = Vote(self.agent_id, decision, confidence)
        all_votes = [my_vote] + (other_votes or [])
        return self.consensus.run(all_votes, strategy=strategy,
                                  trust_scores=trust_scores)

    # ── Context manager ───────────────────────────────────────────────────────

    def close(self):
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def __repr__(self):
        return f"Agent(id={self.agent_id!r}, base_url={self._http._client.base_url!r})"
