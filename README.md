# pact-ax-client

Python SDK for [PACT-AX](https://github.com/neurobloomai/pact-ax) — multi-agent collaboration primitives.

```
pip install pact-ax-client
```

## 30-second quickstart

```python
from pact_ax_client import Agent

agent = Agent("my-agent", base_url="http://localhost:8000")

# Declare what this agent can do
agent.register_capability("contract_review", description="Reviews NDAs and MSAs")

# Find the best trusted agent for a task
decision = agent.route("contract_review")
if decision.routed:
    # Hand off state and wait for acknowledgment
    result = agent.handoff(decision.best_agent, state_data={"doc": "..."})

    # Record the outcome so trust scores update
    agent.remember("contract_review",
                   partner_id=decision.best_agent,
                   outcome="positive")
```

## What's inside

| Primitive | What it does |
|-----------|-------------|
| **Capabilities** | Register/discover agent skills |
| **Trust** | Weighted, persistent trust scores between agents |
| **Router** | Route tasks to the best trusted+capable agent |
| **Episodic Memory** | Record and recall past interactions |
| **Handoff / Transfer** | Prepare → send → receive state packets |
| **Dead Letter Queue** | Park failed deliveries for retry |
| **Consensus** | Weighted-vote consensus across agents |

## Resource clients (advanced)

The `Agent` class is a façade over seven focused clients. Use them directly when you need full control:

```python
from pact_ax_client import (
    CapabilityClient, TrustClient, RouterClient,
    MemoryClient, DLQClient, ConsensusClient, TransferClient,
    HttpClient, Vote,
)

http = HttpClient(base_url="http://localhost:8000")

# Capabilities
caps = CapabilityClient(http)
caps.register("agent-a", "tax_analysis", tags=["finance"])
candidates = caps.find("tax_analysis")

# Trust
trust = TrustClient(http)
ts = trust.get("agent-a", "agent-b")
print(ts.score, ts.recommendation)

# Routing
router = RouterClient(http)
decision = router.route(from_agent="orch", skill="contract_review", min_trust=0.6)
print(decision.best_agent, decision.strategy_used)

# Episodic Memory
mem = MemoryClient(http)
ep = mem.record("agent-a", "reviewed_nda", partner_id="agent-b", outcome="positive")
episodes = mem.recall("agent-a", outcome="positive", limit=10)

# Dead Letter Queue
dlq = DLQClient(http)
entry = dlq.enqueue("pkt-xyz", "agent-a", "agent-b", reason="timeout")
dlq.retry(entry.id)

# Consensus
consensus = ConsensusClient(http)
votes = [Vote("agent-a", "deploy", 0.9), Vote("agent-b", "deploy", 0.75)]
result = consensus.run(votes)
print(result.reached, result.winning_decision)
```

## Error handling

```python
from pact_ax_client.exceptions import NotFoundError, ConflictError, ValidationError, ServerError

try:
    ts = agent.get_trust("unknown-agent")
except NotFoundError:
    print("agent not found")
```

| Exception | HTTP status |
|-----------|-------------|
| `NotFoundError` | 404 |
| `ConflictError` | 409 |
| `ValidationError` | 422 |
| `ServerError` | 500 |

## Async support

```python
from pact_ax_client._http import AsyncHttpClient
from pact_ax_client.capabilities import CapabilityClient

async with AsyncHttpClient(base_url="http://localhost:8000") as http:
    caps = CapabilityClient(http)
    result = await caps.register_async("agent-a", "contract_review")
```

## Development

```bash
git clone https://github.com/neurobloomai/pact-ax-client
cd pact-ax-client
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT © [NeuroBloom.ai](https://neurobloom.ai)
