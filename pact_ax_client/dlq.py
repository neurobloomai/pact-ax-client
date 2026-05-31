from __future__ import annotations
from typing import Any, Dict, List, Optional
from ._http import HttpClient
from .models import DLQEntry


class DLQClient:
    def __init__(self, http: HttpClient):
        self._http = http

    def enqueue(self, packet_id: str, from_agent: str, to_agent: str,
                payload: Optional[Dict[str, Any]] = None, reason: str = "",
                max_attempts: Optional[int] = None) -> DLQEntry:
        body: dict = {
            "packet_id": packet_id, "from_agent": from_agent,
            "to_agent": to_agent, "payload": payload or {}, "reason": reason,
        }
        if max_attempts is not None:
            body["max_attempts"] = max_attempts
        return DLQEntry.from_dict(self._http.post("/dlq/enqueue", json=body))

    def pending(self) -> List[DLQEntry]:
        return [DLQEntry.from_dict(e) for e in
                self._http.get("/dlq/pending").get("entries", [])]

    def exhausted(self) -> List[DLQEntry]:
        return [DLQEntry.from_dict(e) for e in
                self._http.get("/dlq/exhausted").get("entries", [])]

    def get(self, entry_id: str) -> DLQEntry:
        return DLQEntry.from_dict(self._http.get(f"/dlq/{entry_id}"))

    def retry(self, entry_id: str, reason: str = "") -> DLQEntry:
        return DLQEntry.from_dict(
            self._http.post(f"/dlq/{entry_id}/retry", json={"reason": reason})
        )

    def resolve(self, entry_id: str) -> DLQEntry:
        return DLQEntry.from_dict(self._http.post(f"/dlq/{entry_id}/resolve"))

    def delete(self, entry_id: str) -> bool:
        return self._http.delete(f"/dlq/{entry_id}").get("deleted", False)

    def stats(self) -> Dict[str, int]:
        return self._http.get("/dlq/stats")
