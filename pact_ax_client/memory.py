from __future__ import annotations
from typing import Any, Dict, List, Optional
from ._http import HttpClient
from .models import Episode, MemorySummary


class MemoryClient:
    def __init__(self, http: HttpClient):
        self._http = http

    def record(self, agent_id: str, action: str, partner_id: str = "",
               outcome: str = "neutral", importance: float = 0.5,
               tags: Optional[List[str]] = None,
               context: Optional[Dict[str, Any]] = None,
               session_id: str = "") -> Episode:
        d = self._http.post(f"/memory/episodes/{agent_id}", json={
            "action": action, "partner_id": partner_id,
            "outcome": outcome, "importance": importance,
            "tags": tags or [], "context": context or {},
            "session_id": session_id,
        })
        return Episode.from_dict(d)

    def recall(self, agent_id: str, partner_id: Optional[str] = None,
               outcome: Optional[str] = None, min_importance: float = 0.0,
               limit: int = 50, offset: int = 0) -> List[Episode]:
        params: dict = {"limit": limit, "offset": offset}
        if partner_id:        params["partner_id"] = partner_id
        if outcome:           params["outcome"] = outcome
        if min_importance:    params["min_importance"] = min_importance
        d = self._http.get(f"/memory/episodes/{agent_id}", **params)
        return [Episode.from_dict(e) for e in d.get("episodes", [])]

    def recall_partner(self, agent_id: str, partner_id: str, limit: int = 20) -> List[Episode]:
        d = self._http.get(f"/memory/episodes/{agent_id}/{partner_id}",
                           limit=limit)
        return [Episode.from_dict(e) for e in d.get("episodes", [])]

    def summary(self, agent_id: str) -> MemorySummary:
        return MemorySummary.from_dict(self._http.get(f"/memory/summary/{agent_id}"))

    def clear(self, agent_id: str) -> int:
        return self._http.delete(f"/memory/episodes/{agent_id}").get("cleared", 0)

    def delete(self, agent_id: str, episode_id: str) -> bool:
        return self._http.delete(
            f"/memory/episodes/{agent_id}/{episode_id}"
        ).get("deleted", False)
