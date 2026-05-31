"""
pact-ax-client
──────────────
Python SDK for PACT-AX — multi-agent collaboration primitives.

Quickstart
──────────
    from pact_ax_client import Agent

    agent = Agent("my-agent", base_url="http://localhost:8000")
    agent.register_capability("contract_review", description="Reviews NDAs")

    decision = agent.route("contract_review")
    if decision.routed:
        result = agent.handoff(decision.best_agent, state_data={"doc": "..."})
        agent.remember("contract_review", partner_id=decision.best_agent, outcome="positive")
"""

from .agent import Agent
from .capabilities import CapabilityClient
from .consensus import ConsensusClient, Vote
from .dlq import DLQClient
from .exceptions import (
    PactAXError, NotFoundError, ConflictError,
    ValidationError, ServerError,
)
from .memory import MemoryClient
from .models import (
    Capability, ConsensusResult, DLQEntry, Episode,
    HandoffResult, MemorySummary, RouteCandidate, RouteDecision, TrustScore,
)
from .routing import RouterClient
from .transfer import TransferClient
from .trust import TrustClient

__version__ = "0.1.0"

__all__ = [
    # Primary entry point
    "Agent",
    # Resource clients (advanced use)
    "CapabilityClient",
    "TrustClient",
    "RouterClient",
    "MemoryClient",
    "DLQClient",
    "ConsensusClient",
    "TransferClient",
    # Consensus helpers
    "Vote",
    # Models
    "Capability",
    "RouteDecision",
    "RouteCandidate",
    "TrustScore",
    "Episode",
    "MemorySummary",
    "DLQEntry",
    "ConsensusResult",
    "HandoffResult",
    # Exceptions
    "PactAXError",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
    "ServerError",
]
