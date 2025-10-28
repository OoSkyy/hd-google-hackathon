# Agentic Platform for the manufacturer

## Flows

For a detailed description of the interaction flows, see [flows.md](flows.md).

## Project Structure

```
hd-google-hackathon/
├── Dockerfile                  # Container image definition for the web demo + agents
├── app.py                      # FastAPI + HTMX chat demo entrypoint
├── data/
│   └── mock.db                 # Seeded SQLite store backing the demo flows
├── docker-compose.yml          # Local orchestration with live-reload volume mounts
├── scripts/
│   └── seed_mock_db.py         # Utility to reseed / refresh the mock database
├── src/
│   └── hd_google_hackathon/
│       ├── agents/             # ADK agent implementations served via the web UI
│       ├── data/               # Repositories and DB utilities over the mock store
│       ├── domain/             # Domain models shared across agents
│       ├── utils/              # Cross-cutting helpers (tooling, adapters)
│       ├── config.py           # Centralized configuration and settings
│       └── mock_db.py          # Mock data loader for local runs
├── templates/
│   └── index.html              # HTMX chat interface presented by app.py
├── tests/
│   ├── agents/                 # Agent-focused unit tests
│   ├── flows/                  # Flow coverage scenarios
│   ├── mocks/                  # Test doubles and fixture data
│   ├── conftest.py             # Pytest fixtures and shared setup
│   └── test_flows.py           # End-to-end conversation validation
├── flows.md                    # Detailed breakdown of interaction flows
├── gemini.md                   # Notes on Vertex/Gemini integration experiments
├── pyproject.toml              # Project metadata and dependency declarations
└── uv.lock                     # Resolved dependency lockfile
```

Run `python main.py` for a quick smoke check, or `pytest` once additional tests are added (the suite exercises the mock data fixtures).

## Development Setup

Use [uv](https://docs.astral.sh/uv/) for dependency and workflow management.
- Install `uv` (see the linked docs for platform-specific steps).
- Sync dependencies with `uv sync --extra dev` to pull runtime and dev tooling (pytest, pytest-asyncio, etc.).
- Alternatively, install editable dependencies with `uv pip install -e ".[dev]"` if you prefer to control environment activation manually.
- Run project commands through uv, e.g. `uv run python main.py` for a smoke check or `uv run pytest` for the test suite.
- Explore the agent catalog with `uv run adk web src/hd_google_hackathon/agents`, which serves the ADK web UI for local development.

## North Star & Guardrails

* Unify internal support experience around dealer-facing issues without forcing a single dealer tech stack; rely on protocols, data contracts, and lightweight adapters.
* Target measurable reductions in mean time to resolution, cross-region escalation effort, and redundant ERP queries to prove value.
* Design for regional compliance (data residency, consent) by making federation, tenancy controls, and policy-aware routing first-class.

## Key Concept: Privacy Boundaries & Data Ownership

**Privacy Boundaries**
- End customer PII stays with dealers
- Manufacturer sees anonymized/aggregated customer data
- Group-owned dealers share more data than independent dealers
- Dealer performance data visible only to relevant parties

**Data Ownership**
- Dealers control customer data
- Manufacturer gets insights, not raw customer data
- Opt-in sharing for group-owned dealers
- Compliance with data protection regulations

## Layered Architecture

* Interaction Hub: Internal support portal and API routing layer with role-aware workspaces for support agents, account managers, planners.
* Agent Orchestration Fabric: Event-driven hub (e.g., LangGraph/LangChain orchestration or Google Vertex AI Agent Builder) that coordinates specialized agents, enforces guardrails, manages retries, and logs provenance.
* Federated Integration Mesh: Adapters/gateways per ERP cluster or dealer system, using a common protocol (schema contracts, change events, OAuth/service accounts) rather than shared UI; push frequently-needed data into a normalized cache for fast agent access.
* Knowledge Services: Memory layer (short-term conversation state + episodic ticket history), knowledge graph for entities/relationships, vector store for unstructured docs, all wrapped in governance (access policies, retention).
*Observability & Governance: Central policy engine (RBAC/ABAC), audit ledger, cost dashboards, and feature toggles to manage regional rollouts.

## Agents Garden

* Support Triage Agent: Classifies inbound tickets/chats, enriches with dealer context, routes to correct queue, auto-extracts SLA timers.
* Investigation Agent: Pulls order history, production status, shipment telemetry; compares against standards to flag anomalies and propose resolutions.
* ERP Sherpa Agent: Encapsulates knowledge of each ERP variant via tool connectors; translates high-level intents (“update shipment priority”) into correct transactions.
* Policy & Compliance Agent: Checks suggested actions against regional rules, warranty terms, data-sharing agreements before execution.
* Playbook Author Agent: Summarizes resolved cases into reusable playbooks, flags gaps in documentation, suggests knowledge articles.
* Metrics & Insight Agent: Synthesizes operational KPIs, surfacing systemic issues (e.g., recurring part shortages or dealer training gaps).

## Shared Tools & Connectors

* Tool catalog: standardized interfaces for ticket systems (ServiceNow, Zendesk), ERP adapters, logistics APIs, knowledge graph queries, document retrieval, communication channels (email, Teams/Slack).
* Protocol templates: shared schemas for order, shipment, support events; transformation rules so dealers can provide minimal conformance without stack changes.
* Security utilities: consent-as-code checks, PII redaction, regional data routing.
* Simulation/sandbox tooling for testing agents against historical tickets before production.


## Memory & Knowledge Graph

* Short-term memory: conversation/session store with TTL to maintain context per ticket.
* Long-term episodic memory: case notebook capturing prior resolutions, linked to dealers/products; supports personalization and avoids repeat questions.
* Knowledge graph: Entities (Product, Component, Order, Dealer, Region, Claim, Installer) with edges describing dependencies, warranties, responsibilities; fed by ERP snapshots, ticket outcomes, and manually curated data; enables root cause analysis and agent reasoning.
* Vector store: embeddings of manuals, SOPs, regional regulations, dealer agreements; used for retrieval-augmented responses.

## Docker

Build the Docker image:

```bash
docker build -t hd-google-hackathon:latest .
```

Run the container (the project requested startup command):

```bash
docker run --rm -p 8000:8000 hd-google-hackathon:latest
```

Or with docker-compose (maps port 8000 and mounts the repo for live edits):

```bash
docker compose up --build
```

The container starts with the command:

```
adk web src/hd_google_hackathon/agents --host 0.0.0.0 --port 8000
```

The ADK web UI will be available on the host at:

http://localhost:8000/
