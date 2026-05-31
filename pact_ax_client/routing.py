from __future__ import annotations
from ._http import HttpClient
from .models import RouteDecision


class RouterClient:
    def __init__(self, http: HttpClient):
        self._http = http

    def route(self, from_agent: str, skill: str,
              min_trust: float = 0.0, top_k: int = 5) -> RouteDecision:
        d = self._http.post("/route", json={
            "from_agent": from_agent, "skill": skill,
            "min_trust": min_trust, "top_k": top_k,
        })
        return RouteDecision.from_dict(d)

    def route_any(self, from_agent: str, query: str,
                  min_trust: float = 0.0, top_k: int = 5) -> RouteDecision:
        d = self._http.post("/route/any", json={
            "from_agent": from_agent, "query": query,
            "min_trust": min_trust, "top_k": top_k,
        })
        return RouteDecision.from_dict(d)
