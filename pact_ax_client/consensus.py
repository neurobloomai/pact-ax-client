from __future__ import annotations
from typing import Any, Dict, List, Optional
from ._http import HttpClient
from .models import ConsensusResult


class Vote:
    """A single agent's vote for a consensus round."""
    def __init__(self, agent_id: str, decision: str, confidence: float,
                 reasoning: str = "", abstain: bool = False):
        self.agent_id   = agent_id
        self.decision   = decision
        self.confidence = confidence
        self.reasoning  = reasoning
        self.abstain    = abstain

    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id, "decision": self.decision,
            "confidence": self.confidence, "reasoning": self.reasoning,
            "abstain": self.abstain,
        }


class ConsensusClient:
    def __init__(self, http: HttpClient):
        self._http = http

    def run(self, votes: List[Vote], strategy: str = "weighted_vote",
            trust_scores: Optional[Dict[str, float]] = None,
            round_id: Optional[str] = None,
            min_votes: int = 2) -> ConsensusResult:
        """One-shot stateless consensus round."""
        d = self._http.post("/consensus/run", json={
            "votes": [v.to_dict() for v in votes],
            "strategy": strategy,
            "trust_scores": trust_scores or {},
            "round_id": round_id,
            "min_votes": min_votes,
        })
        return ConsensusResult.from_dict(d)

    def create_session(self, session_id: Optional[str] = None,
                       strategy: str = "weighted_vote") -> str:
        """Create a named session that tracks history. Returns session_id."""
        d = self._http.post("/consensus/sessions", json={
            "session_id": session_id, "strategy": strategy,
        })
        return d["session_id"]

    def vote(self, session_id: str, votes: List[Vote],
             trust_scores: Optional[Dict[str, float]] = None) -> ConsensusResult:
        """Run a round inside an existing session."""
        d = self._http.post(f"/consensus/sessions/{session_id}/vote", json={
            "votes": [v.to_dict() for v in votes],
            "trust_scores": trust_scores or {},
        })
        return ConsensusResult.from_dict(d)

    def session_metrics(self, session_id: str) -> Dict[str, Any]:
        return self._http.get(f"/consensus/sessions/{session_id}")

    def delete_session(self, session_id: str) -> bool:
        return self._http.delete(f"/consensus/sessions/{session_id}").get("deleted", False)
