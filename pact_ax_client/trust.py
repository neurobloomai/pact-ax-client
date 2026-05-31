from __future__ import annotations
from typing import Dict, List, Optional
from ._http import HttpClient
from .models import TrustScore


class TrustClient:
    def __init__(self, http: HttpClient):
        self._http = http

    def get(self, agent_id: str, target_id: str,
            context_type: Optional[str] = None) -> TrustScore:
        params: dict = {}
        if context_type:
            params["context_type"] = context_type
        d = self._http.get(f"/trust/{agent_id}/{target_id}", **params)
        return TrustScore.from_dict(d)

    def update(self, agent_id: str, target_id: str, outcome: str,
               impact: float = 1.0, context_type: str = "task_knowledge") -> TrustScore:
        d = self._http.post(f"/trust/{agent_id}/update", json={
            "target_id": target_id, "outcome": outcome,
            "impact": impact, "context_type": context_type,
        })
        return TrustScore(
            agent_id=agent_id, target_id=target_id,
            score=d.get("new_score", 0.5),
        )

    def trusted_agents(self, agent_id: str, min_trust: float = 0.6,
                       context_type: Optional[str] = None) -> List[str]:
        body: dict = {"min_trust": min_trust}
        if context_type:
            body["context_type"] = context_type
        d = self._http.post(f"/trust/{agent_id}/agents", json=body)
        return d.get("trusted_agents", [])

    def network_trust(self, agent_id: str, target_id: str) -> float:
        d = self._http.get(f"/trust/{agent_id}/network/{target_id}")
        return d.get("network_trust", 0.5)

    def insights(self, agent_id: str) -> Dict:
        return self._http.get(f"/trust/{agent_id}/insights")

    def reset(self, agent_id: str, target_id: str) -> bool:
        return self._http.delete(f"/trust/{agent_id}/{target_id}").get("reset", False)
