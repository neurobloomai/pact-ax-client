from __future__ import annotations
from typing import List, Optional
from ._http import HttpClient
from .models import Capability


class CapabilityClient:
    def __init__(self, http: HttpClient):
        self._http = http

    def register(self, agent_id: str, skill: str, description: str = "",
                 tags: Optional[List[str]] = None, version: str = "1.0") -> Capability:
        d = self._http.post("/capabilities/register", json={
            "agent_id": agent_id, "skill": skill,
            "description": description, "tags": tags or [], "version": version,
        })
        return Capability.from_dict(d)

    def get(self, agent_id: str) -> List[Capability]:
        d = self._http.get(f"/capabilities/{agent_id}")
        return [Capability.from_dict(c) for c in d.get("capabilities", [])]

    def find(self, skill: str, requester: Optional[str] = None,
             min_trust: Optional[float] = None) -> List[Capability]:
        body: dict = {"skill": skill}
        if requester:  body["requester"] = requester
        if min_trust is not None:  body["min_trust"] = min_trust
        d = self._http.post("/capabilities/find", json=body)
        return [Capability.from_dict(c) for c in d.get("candidates", [])]

    def search(self, query: str) -> List[Capability]:
        d = self._http.post("/capabilities/search", json={"query": query})
        return [Capability.from_dict(c) for c in d.get("results", [])]

    def skills(self) -> List[str]:
        return self._http.get("/capabilities/skills").get("skills", [])

    def deregister(self, agent_id: str, skill: str) -> bool:
        return self._http.delete(f"/capabilities/{agent_id}/{skill}").get("removed", False)

    def deregister_agent(self, agent_id: str) -> int:
        return self._http.delete(f"/capabilities/{agent_id}").get("removed", 0)
