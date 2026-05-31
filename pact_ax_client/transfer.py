from __future__ import annotations
from typing import Any, Dict
from ._http import HttpClient
from .models import HandoffResult


class TransferClient:
    """StateTransfer: prepare → send → receive handoff lifecycle."""

    def __init__(self, http: HttpClient):
        self._http = http

    def handoff(self, from_agent: str, to_agent: str,
                state_data: Dict[str, Any], reason: str = "escalation") -> HandoffResult:
        """
        Full three-step handoff: prepare → send → receive.
        Returns a HandoffResult with packet_id and received status.
        """
        # Prepare
        prep = self._http.post("/transfer/prepare", json={
            "from_agent_id": from_agent, "to_agent_id": to_agent,
            "reason": reason, "state_data": state_data,
        })
        pid = prep["packet_id"]

        # Send
        sent = self._http.post("/transfer/send", json={
            "agent_id": from_agent, "packet_id": pid,
        })

        # Receive
        recv = self._http.post("/transfer/receive", json={
            "agent_id": to_agent, "packet": sent,
        })

        return HandoffResult(
            packet_id=pid, from_agent=from_agent, to_agent=to_agent,
            sent=True, received=recv.get("success", False),
        )

    def status(self, agent_id: str, packet_id: str) -> Dict:
        return self._http.get(f"/transfer/status/{agent_id}/{packet_id}")

    def checkpoint(self, agent_id: str, state_data: Dict[str, Any],
                   label: str = "") -> str:
        """Save a checkpoint. Returns checkpoint_id."""
        d = self._http.post("/transfer/checkpoint", json={
            "agent_id": agent_id, "state_data": state_data, "label": label,
        })
        return d.get("checkpoint_id", "")
