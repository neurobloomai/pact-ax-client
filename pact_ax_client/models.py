"""
Response dataclasses returned by the SDK.

All models are plain dataclasses — no external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Capabilities ──────────────────────────────────────────────────────────────

@dataclass
class Capability:
    agent_id:    str
    skill:       str
    description: str = ""
    tags:        List[str] = field(default_factory=list)
    version:     str = "1.0"
    updated_at:  str = ""

    @classmethod
    def from_dict(cls, d: Dict) -> "Capability":
        return cls(
            agent_id=d["agent_id"], skill=d["skill"],
            description=d.get("description", ""),
            tags=d.get("tags", []), version=d.get("version", "1.0"),
            updated_at=d.get("updated_at", ""),
        )


# ── Routing ───────────────────────────────────────────────────────────────────

@dataclass
class RouteCandidate:
    agent_id:    str
    skill:       str
    trust_score: float
    description: str = ""
    tags:        List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Dict) -> "RouteCandidate":
        return cls(
            agent_id=d["agent_id"], skill=d["skill"],
            trust_score=d.get("trust_score", 0.5),
            description=d.get("description", ""), tags=d.get("tags", []),
        )


@dataclass
class RouteDecision:
    skill:          str
    from_agent:     str
    best_agent:     Optional[str]
    candidates:     List[RouteCandidate]
    strategy_used:  str
    routed:         bool
    total_capable:  int

    @classmethod
    def from_dict(cls, d: Dict) -> "RouteDecision":
        return cls(
            skill=d["skill"], from_agent=d["from_agent"],
            best_agent=d.get("best_agent"),
            candidates=[RouteCandidate.from_dict(c) for c in d.get("candidates", [])],
            strategy_used=d.get("strategy_used", ""),
            routed=d.get("routed", False),
            total_capable=d.get("total_capable", 0),
        )


# ── Trust ─────────────────────────────────────────────────────────────────────

@dataclass
class TrustScore:
    agent_id:       str
    target_id:      str
    score:          float
    recommendation: str = ""

    @classmethod
    def from_dict(cls, d: Dict) -> "TrustScore":
        return cls(
            agent_id=d["agent_id"], target_id=d["target_id"],
            score=d.get("trust_score", d.get("score", 0.5)),
            recommendation=d.get("recommendation", ""),
        )


# ── Episodic Memory ───────────────────────────────────────────────────────────

@dataclass
class Episode:
    id:         str
    agent_id:   str
    action:     str
    partner_id: str = ""
    outcome:    str = "neutral"
    importance: float = 0.5
    tags:       List[str] = field(default_factory=list)
    context:    Dict[str, Any] = field(default_factory=dict)
    timestamp:  str = ""

    @classmethod
    def from_dict(cls, d: Dict) -> "Episode":
        return cls(
            id=d["id"], agent_id=d["agent_id"], action=d["action"],
            partner_id=d.get("partner_id", ""), outcome=d.get("outcome", "neutral"),
            importance=d.get("importance", 0.5), tags=d.get("tags", []),
            context=d.get("context", {}), timestamp=d.get("timestamp", ""),
        )


@dataclass
class MemorySummary:
    agent_id:          str
    total_episodes:    int
    avg_importance:    float
    outcome_breakdown: Dict[str, int]
    top_partners:      List[Dict]

    @classmethod
    def from_dict(cls, d: Dict) -> "MemorySummary":
        return cls(
            agent_id=d["agent_id"], total_episodes=d.get("total_episodes", 0),
            avg_importance=d.get("avg_importance", 0.0),
            outcome_breakdown=d.get("outcome_breakdown", {}),
            top_partners=d.get("top_partners", []),
        )


# ── Dead Letter Queue ─────────────────────────────────────────────────────────

@dataclass
class DLQEntry:
    id:           str
    packet_id:    str
    from_agent:   str
    to_agent:     str
    status:       str
    attempt:      int
    max_attempts: int
    reason:       str = ""
    next_retry:   Optional[str] = None
    retryable:    bool = False

    @classmethod
    def from_dict(cls, d: Dict) -> "DLQEntry":
        return cls(
            id=d["id"], packet_id=d["packet_id"],
            from_agent=d["from_agent"], to_agent=d["to_agent"],
            status=d["status"], attempt=d["attempt"],
            max_attempts=d["max_attempts"], reason=d.get("reason", ""),
            next_retry=d.get("next_retry"), retryable=d.get("retryable", False),
        )


# ── Consensus ─────────────────────────────────────────────────────────────────

@dataclass
class ConsensusResult:
    round_id:          str
    outcome:           str
    winning_decision:  Optional[str]
    confidence_score:  float
    strategy_used:     str
    vote_breakdown:    Dict[str, float]
    abstentions:       List[str]

    @classmethod
    def from_dict(cls, d: Dict) -> "ConsensusResult":
        return cls(
            round_id=d["round_id"], outcome=d["outcome"],
            winning_decision=d.get("winning_decision"),
            confidence_score=d.get("confidence_score", 0.0),
            strategy_used=d.get("strategy_used", ""),
            vote_breakdown=d.get("vote_breakdown", {}),
            abstentions=d.get("abstentions", []),
        )

    @property
    def reached(self) -> bool:
        return self.outcome == "accepted"


# ── State Transfer ────────────────────────────────────────────────────────────

@dataclass
class HandoffResult:
    packet_id: str
    from_agent: str
    to_agent:   str
    sent:       bool = False
    received:   bool = False

    @classmethod
    def from_dict(cls, d: Dict) -> "HandoffResult":
        return cls(
            packet_id=d.get("packet_id", ""),
            from_agent=d.get("from_agent_id", ""),
            to_agent=d.get("to_agent_id", ""),
            sent=d.get("sent", False),
            received=d.get("received", d.get("success", False)),
        )
