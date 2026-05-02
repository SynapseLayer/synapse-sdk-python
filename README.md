# 🧠 Synapse Layer

[![Python SDK](https://img.shields.io/badge/Python_SDK-2.3.1-blue?logo=python&logoColor=white)](https://pypi.org/project/synapse-layer/)
[![A2A Protocol](https://img.shields.io/badge/A2A_Protocol-v1.0-purple)](./site/docs/sdk/a2a-protocol.md)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-6B4FBB?logo=data:image/svg+xml;base64,&logoColor=white)](https://modelcontextprotocol.io/)
[![Zero-Knowledge](https://img.shields.io/badge/Zero--Knowledge-AES--256--GCM-success)](./site/docs/sdk/python.md)
[![Neural Handover™](https://img.shields.io/badge/Neural_Handover™-HMAC--SHA256-blueviolet)](./site/docs/sdk/python.md)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)
[![Tests Passing](https://img.shields.io/badge/Tests-29%2B_Passing-brightgreen)](./sdk/python/tests/)
![Built in São Paulo 🇧🇷](https://img.shields.io/badge/Built_in_São_Paulo-🇧🇷-green)

> *"Giving Agents a Past. Giving Models a Soul."*

**The Long-Term Memory Layer for Every Agent.**  
Persistent · Private · Model-agnostic · Open-source

---

## What It Does

Synapse Layer gives AI agents a persistent, encrypted memory system that works across models and sessions:

```
┌─────────────────────────────────────────────────────────────┐
│                    AGENT SESSION 1                          │
│                 (Claude 3.5 Sonnet)                         │
│                                                             │
│  User: "I prefer Portuguese and dark mode"  ────────────┐  │
│  Agent: "Noted. Storing in memory..."                   │  │
└──────────────────────────────────────────────────────────┼──┘
                                                           │
                              ┌────────────────────────────┘
                              │
                              ▼
                  ┌───────────────────────┐
                  │  SYNAPSE LAYER VAULT  │
                  │                       │
                  │  ✓ AES-256-GCM       │
                  │  ✓ Zero-Knowledge    │
                  │  ✓ TQ: 0.95          │
                  └───────────────────────┘
                              │
                              │
                  ┌───────────┴────────────┐
                  │                        │
                  ▼                        ▼
    ┌──────────────────────┐   ┌──────────────────────┐
    │   SESSION 2          │   │   SESSION 3          │
    │   (GPT-4o)           │   │   (Gemini)           │
    │                      │   │                      │
    │  Agent recalled:     │   │  Agent recalled:     │
    │  "Dark mode ✓"       │   │  "Portuguese ✓"      │
    │  "PT-BR ✓"           │   │  "Dark mode ✓"       │
    └──────────────────────┘   └──────────────────────┘

           CONTINUOUS CONTEXT ACROSS MODELS
```

---

## Features

| Feature | Description | Status |
|---------|-------------|--------|
| **Zero-Knowledge Encryption** | AES-256-GCM, client-side only; server never sees plaintext | ✅ v0.7.0 |
| **Python SDK** | Async client with LangChain & CrewAI adapters | ✅ v0.7.0 |
| **A2A Protocol v1.0** | JSON-RPC 2.0 for agent-to-agent communication | ✅ v0.7.0 |
| **Neural Handover™** | HMAC-SHA256 signed context transfer between models | ✅ v0.6.0 |
| **Trust Quotient (TQ)** | Weighted memory ranking formula (confidence + recency + usage) | ✅ v0.7.0 |
| **Semantic Search** | pgvector HNSW for intelligent memory recall | ✅ v0.6.0 |
| **Conflict Resolution** | Automatic detection & resolution of contradictory memories | ✅ v0.6.0 |
| **GDPR/LGPD Compliant** | Soft-delete with audit trails; data minimization | ✅ v0.6.0 |
| **MCP Compatible** | Works with Claude, LLaMA, and any MCP client | ✅ v0.6.0 |
| **Open Source** | Apache 2.0 license | ✅ v0.1.0 |
| **Plugin System** | Extensible resolvers for domain-specific conflict resolution | ✅ v1.0.0 |

---

## Plugin System

Synapse Layer v1.0.0 introduces an extensible **Plugin System** for domain-specific conflict resolution and memory validation.

### Core Components

**MemoryResolverPlugin** - Abstract base class for plugins:
```python
from synapse_layer.plugins import MemoryResolverPlugin, MemoryCandidate, ResolverDecision

class MyCustomResolver(MemoryResolverPlugin):
    @property
    def name(self) -> str:
        return "my_resolver"
    
    def can_handle(self, candidates: List[MemoryCandidate]) -> bool:
        # Return True if this plugin should handle these candidates
        return any("custom_tag" in c.metadata for c in candidates)
    
    def resolve(self, candidates: List[MemoryCandidate]) -> ResolverDecision:
        # Your domain-specific logic here
        return ResolverDecision(winner_memory_id=candidates[0].memory_id)
```

**PluginRegistry** - Global registry for plugin management:
```python
from synapse_layer.plugins import default_registry, MyCustomResolver

# Register plugin
default_registry.register(MyCustomResolver())

# Find handler for conflict resolution
plugin = default_registry.find_handler(candidates)
if plugin:
    decision = plugin.resolve(candidates)
```

### Example: MedicalTruthResolver

Included with Synapse Layer is the **MedicalTruthResolver** plugin, which validates medical/clinical memories using source priority:

```
Priority Order:
1. Peer-reviewed literature (highest)
2. Clinical guidelines
3. Specialist notes
4. General knowledge
5. Patient self-reports (lowest)
```

When medical memories conflict, the plugin automatically promotes the highest-priority source.

### synapse.json — Protocol Manifest

Synapse Layer exposes a machine-readable `synapse.json` file at the repository root, listing all capabilities:

```json
{
  "protocol": "synapse-layer",
  "version": "1.0.0",
  "capabilities": [
    "persistent_memory",
    "neural_handover",
    "conflict_resolution",
    "plugin_system",
    "zero_knowledge_context"
  ],
  "docs": "https://synapselayer.org/docs"
}
```

Agents can discover and validate Synapse Layer capabilities by reading this file.

---

## Installation

> **Status:** Pre-release. PyPI and npm packages are coming soon (v1.0.0 stable release).
> In the meantime, install directly from the repository.

### Python SDK (pre-release)

```bash
# Install directly from GitHub (works today)
pip install "synapse-layer[langchain] @ git+https://github.com/SynapseLayer/synapse-sdk-python.git"

# Or clone and install locally
git clone https://github.com/SynapseLayer/synapse-sdk-python.git
cd synapse-sdk-python
pip install -e ".[langchain,crewai]"
```

Coming soon (stable):

```bash
pip install synapse-layer
pip install synapse-layer[langchain]
pip install synapse-layer[crewai]
pip install synapse-layer[all]
```

### CLI (pre-release)

```bash
# Install directly from GitHub (works today)
npm install -g github:SynapseLayer/synapse-cli

# Or clone and link locally
git clone https://github.com/SynapseLayer/synapse-cli.git
cd synapse-cli
npm install && npm link
```

Coming soon (stable):

```bash
npm install -g @synapselayer/cli
```

### MCP Server (production — live today)

```bash
# Edge Function (no install needed)
# Endpoint: https://rbeycxzizrrdmxpilepc.supabase.co/functions/v1/mcp-server

# Local MCP Server
# MCP Server source is distributed separately — see synapselayer.org/docs
# (consult official docs for setup)
npm install
npx ts-node src/mcp-server.ts
```

---

## Quick Start

### Python SDK (Async)

```python
import asyncio
from synapse_layer import SynapseA2AClient

async def main():
    client = SynapseA2AClient(api_key="your-api-key")
    
    async with client:
        # Store a memory
        result = await client.store_memory(
            user_id="user-123",
            content="User prefers Portuguese language",
            source_type="user_input",
            confidence=0.95
        )
        print(f"Stored: {result.task_id}")
        
        # Recall memories
        recalled = await client.recall_memory(
            user_id="user-123",
            query="language preference",
            limit=5
        )
        print(f"Found {len(recalled.output)} memories")

asyncio.run(main())
```

### LangChain Integration

```python
from langchain.chains import ConversationChain
from langchain.llms import Anthropic
from synapse_layer import SynapseMemory

# Create persistent memory
memory = SynapseMemory(
    api_key="your-api-key",
    user_id="user-001",
    recall_limit=10
)

# Use in conversation
chain = ConversationChain(
    llm=Anthropic(),
    memory=memory,
    verbose=True
)

response = chain.run(input="What did I tell you last week?")
```

### CrewAI Integration

```python
from crewai import Agent, Task, Crew
from synapse_layer import (
    SynapseStoreMemoryTool,
    SynapseRecallMemoryTool,
    SynapseHandoverTool
)

# Create tools
store = SynapseStoreMemoryTool(api_key="your-api-key")
recall = SynapseRecallMemoryTool(api_key="your-api-key")
handover = SynapseHandoverTool(api_key="your-api-key")

# Create agent
researcher = Agent(
    role="Researcher",
    goal="Gather and store findings",
    tools=[store, recall, handover]
)

# Run crew
crew = Crew(agents=[researcher], tasks=[...])
crew.kickoff()
```

---

## Trust Quotient (TQ) Formula

Memory quality is determined by a **weighted composite score** that combines three dimensions:

TQ = (confidence_score * 0.4) + (recency_score * 0.3) + (usage_normalized * 0.3)

### Breakdown

| Component | Weight | Description |
|-----------|--------|-------------|
| **confidence_score** | 40% | User-provided confidence (0.0-1.0) |
| **recency_score** | 30% | Time-decay based on age; newer = higher |
| **usage_normalized** | 30% | Normalized access frequency |

### Example: High vs Low TQ

**High TQ Memory:**
```
"User purchased premium plan on 2026-04-01"
- confidence = 0.99 (API response)
- recency = 0.99 (stored today)
- usage = 0.85 (accessed 17/20 times)

TQ = (0.99 * 0.4) + (0.99 * 0.3) + (0.85 * 0.3) = 0.948 (Excellent)
```

**Low TQ Memory:**
```
"User might prefer dark mode"
- confidence = 0.35 (uncertain)
- recency = 0.18 (60 days old)
- usage = 0.05 (accessed 1/20 times)

TQ = (0.35 * 0.4) + (0.18 * 0.3) + (0.05 * 0.3) = 0.209 (Poor)
```

Memories are ranked by TQ in recall results, ensuring most reliable and relevant memories appear first.

---

## Neural Handover™

Transfer context between models without losing state:

```python
# Agent A (Claude)
handover = await client.create_handover(
    user_id="user-123",
    target_model="gpt-4o",
    summary="Analyzed Q3 financial data; found 15% revenue growth"
)
# Returns: handover_token (HMAC-SHA256 signed)

# Agent B (GPT-4o) - receives context automatically
# Full context injected via Neural Handover™
```

**How it works:**
1. Source agent packages context + memories into JSON
2. Sign with HMAC-SHA256 for integrity
3. Return handover token
4. Target agent loads context, validates signature, continues session
5. No memory loss between models

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      CLIENT LAYER                           │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Python SDK  │  │ TypeScript   │  │ Any MCP Client   │   │
│  │ (Async)     │  │ SDK          │  │ (Claude, etc)    │   │
│  └──────┬──────┘  └──────┬───────┘  └────────┬─────────┘   │
│         │                │                   │              │
│         └────────────────┼───────────────────┘              │
│                          │                                  │
│                          ▼                                  │
│              ┌────────────────────────┐                    │
│              │ AES-256-GCM Encryption │                    │
│              │ (Client-side only)     │                    │
│              └────────────┬───────────┘                    │
└───────────────────────────┼──────────────────────────────────┘
                            │  encrypted blobs + embeddings
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                      SERVER LAYER                           │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │     Supabase Edge Functions (A2A Protocol)           │   │
│  │                                                      │   │
│  │  store_memory | recall_memory | create_handover      │   │
│  │  resolve_conflict | forget_memory                    │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                   │
│                         ▼                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │        PostgreSQL + pgvector (HNSW)                 │   │
│  │        Region: sa-east-1 (Sao Paulo)                │   │
│  │                                                      │   │
│  │  - Encrypted memory blobs (AES-256-GCM)             │   │
│  │  - 384-dim embeddings (semantic search)             │   │
│  │  - Trust Quotient scores (TQ ranking)               │   │
│  │  - Audit trails (GDPR/LGPD compliance)              │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---
## Discovery & Static Files

**Discovery files** (agent-card.json, agent.json, etc.) are served from `public/.well-known/` 
by the Next.js static file server. This is the canonical source for all agent discovery endpoints. 
Do not edit `.well-known/` at the repository root — it has been removed to maintain a single source of truth.

> **Canonical agent discovery path:** `public/.well-known/agent-card.json`
> Served at: `https://synapselayer.org/.well-known/agent-card.json`


## Core Engine — Trust Quotient (TQ)

Every memory in Synapse Layer has a Trust Quotient score that determines its lifecycle.

### TQ Formula

TQ = (confidence_score * 0.4) + (recency_score * 0.3) + (usage_normalized * 0.3)

Where:
confidence_score    in [0.0, 1.0]  -- source reliability
recency_score       = 1.0 / (1.0 + ln(days_since_created + 1.0))
usage_normalized    = min(usage_count / 100.0, 1.0)


### Memory Lifecycle

[CREATED] --> TQ calculated on write
|
v
[ACTIVE]  --> TQ >= 0.7: promoted as canonical
|         TQ 0.3-0.7: normal active memory
|         TQ < 0.5: credit decremented daily
v
[WEAKENING] --> credit_balance approaches 0
|
v
[DECAYED] --> TQ < 0.3 AND age > 30 days: soft-deleted
(deleted_at set, credit_balance = 0)
Canonical memories are NEVER auto-decayed.


### Conflict Resolution

When two memories conflict (same conflict_group_id), SynapseResolver:
1. Fetches all candidates from active_memories view
2. Calculates TQ for each candidate
3. Promotes the highest-TQ memory as canonical (is_canonical = true)
4. Demotes all others (is_canonical = false)

### Memory Decay Schedule

- Runs automatically via pg_cron at 03:00 UTC daily
- Manual trigger: POST /memory-decay with method: "run_decay"
- Returns JSON: { decayed, decremented, processed, run_at, thresholds }

### SDK Cache

```python
from synapse_layer import SynapseMemory

# Default: 2 second TTL cache (avoids duplicate round-trips)
memory = SynapseMemory(
    supabase_url="...",
    supabase_key="...",
    cache_ttl_seconds=2.0,  # set to 0 to disable
)
```

---

## Neural Handover(TM) v2

Transfer complete AI context between different models — zero context loss.

### How it works

```
Agent A (Claude)                        Agent B (GPT-4o)
|                                       |
| 1. create_handover(target="gpt-4o")  |
|-----> MCP Server                      |
| | 2. handover-initiate               |
| |-----> Supabase                      |
| | (HMAC verified)                     |
| |<----- handover_id                   |
|<----- handover_id                     |
| 3. Share handover_id ------->        |
| 4. handover-complete                  |
| |<----- Supabase                      |
| | (integrity re-verified)             |
| |<----- full context (encrypted)      |
| 5. Inject via MCP                     |
| |-----> Agent B continues             |
```

### Prompt Adapters

Each model family receives context in its optimal format:

| Model Family | Format | Optimized For |
|---|---|---|
| Claude | XML tags | Structured context parsing |
| GPT | Markdown | Header-based navigation |
| Gemini | JSON structured | Structured output mode |
| Llama (large) | [CONTEXT] blocks | Efficient token usage |
| Llama (small) | [CTX] ultra-compact | 8k context windows |
| Mistral | [CONTEXT] blocks | Compact format |

### Security

- **HMAC-SHA256**: Every packet is signed. Tampered packets are automatically revoked.
- **One-time use**: Each handover_id can only be consumed once.
- **TTL**: Packets expire after 24 hours.
- **Zero-Knowledge**: `session_context` and `memories` remain AES-256-GCM encrypted throughout.

### Quick Start

```typescript
import { NeuralHandover } from "@synapse-layer/core";

// Agent A: create handover
const pkg = NeuralHandover.create(memories, "gpt-4o", "Session summary...");
console.log(pkg.id); // Share this with Agent B

// Agent B: verify and use
const isValid = NeuralHandover.verifySignature(pkg);
const context = NeuralHandover.adapter("gpt-4o", pkg.memories, pkg.summary);
```

---

## Repository Structure

```
synapse-layer/
├── sdk/python/                          # Python SDK (0.7.0)
│   ├── synapse_layer/
│   │   ├── __init__.py                  # Public API exports
│   │   ├── a2a_client.py                # JSON-RPC 2.0 client
│   │   ├── langchain_memory.py          # LangChain adapters
│   │   └── crewai_tools.py              # CrewAI tools
│   ├── tests/
│   │   ├── conftest.py                  # Shared fixtures (25+ fixtures)
│   │   ├── test_a2a_client.py           # A2A client tests (29+ tests)
│   │   └── test_langchain_memory.py     # LangChain adapter tests
│   └── pyproject.toml                   # Dependencies + tool config
│
├── site/docs/sdk/                       # SDK Documentation
│   ├── python.md                        # Python SDK guide (0.7.0)
│   └── a2a-protocol.md                  # A2A Protocol reference
│
├── public/.well-known/
│   └── agent-card.json                  # Agent Card (5 skills)
│
├── src/                                 # TypeScript core
│   ├── crypto.ts                        # AES-256-GCM + PBKDF2
│   ├── handover.ts                      # Neural Handover™ v1
│   └── engine/                          # Consensus Engine™
│
├── supabase/                            # Database + Edge Functions
│   ├── functions/mcp-server/            # A2A Protocol endpoint
│   └── migrations/                      # Schema + indexes
│
├── CHANGELOG.md                         # Version history
├── README.md                            # This file (v0.7.0)
├── LICENSE                              # Apache 2.0
└── package.json                         # Dependencies
```

---

## Running Tests

### Python SDK Tests

```bash
# Install dev dependencies (from git)
pip install "synapse-layer[all,dev] @ git+https://github.com/SynapseLayer/synapse-sdk-python.git"

# Run all tests
pytest sdk/python/tests/

# Run with coverage
pytest sdk/python/tests/ --cov=synapse_layer

# Run specific test class
pytest sdk/python/tests/test_a2a_client.py::TestSynapseA2AClientInit
```

**Test Coverage:**
- 29+ test methods
- 0 failures
- Async/await testing with pytest-asyncio
- Mock JSON-RPC responses
- LangChain & CrewAI integration tests
- Edge cases: empty content, special characters, rate limits

---

## Roadmap

| Version | Status | Highlights |
|---------|--------|-----------|
| **v0.5.0** | Complete | Research & architecture design |
| **v0.6.0** | Complete | Core infrastructure (encryption, MCP, Consensus Engine) |
| **v0.7.0** | Complete | Python SDK + A2A Protocol + Test Suite |
| **v0.9.0** | Complete | Neural Handover™ v2 + Edge Functions (D3) |
| **v1.0.0** | **Current** | Plugin System + synapse.json + Ecosystem (D4) |
| **v2.0** | Next | PyPI/npm release; Docs site; Dashboard UI |

---

## Philosophy

> **"The server never sees your data."**

Synapse Layer is built on zero-knowledge principles:

- Security: Privacy is mandatory, not optional
- Infrastructure: Memory is infrastructure, not a plugin
- Portability: Model portability matters - no lock-in
- Trust: Trust is cryptographic, not contractual
- Community: Built in Sao Paulo for Brazilian and global developers

---

## License

**Apache 2.0** - Open-source and free for commercial use.
See [LICENSE](./LICENSE) for details.

---

## Links

| Resource | URL |
|----------|-----|
| Website | [synapselayer.org](https://synapselayer.org) |
| Docs | [synapselayer.org/docs](https://synapselayer.org/docs) |
| GitHub | [github.com/SynapseLayer/synapse-sdk-python](https://github.com/SynapseLayer/synapse-sdk-python) |
| Issues | [github.com/SynapseLayer/synapse-sdk-python/issues](https://github.com/SynapseLayer/synapse-sdk-python/issues) |
| Agent Card | [synapselayer.org/.well-known/agent-card.json](https://synapselayer.org/.well-known/agent-card.json) |
| Email | founder.synapselayer@proton.me |

> **Note:** The canonical `.well-known/` path is served from `public/.well-known/` in this repository.
> Do not edit `.well-known/` at the root — it is a legacy reference only.

---

<p align="center">
  <strong>Synapse Layer v1.0.0</strong><br>
  <em>"Giving Agents a Past. Giving Models a Soul."</em><br><br>
  Built in Sao Paulo by Ismael Marchi<br>
  <a href="https://github.com/SynapseLayer/synapse-sdk-python">GitHub</a> | 
  <a href="https://synapselayer.org/docs">Docs</a> |
  <a href="./LICENSE">Apache 2.0 License</a>
</p>