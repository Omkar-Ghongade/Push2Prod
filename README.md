# TraceTalk

> Conversational root-cause analysis for infrastructure observability. Ask questions in plain English, watch an AI agent investigate live, and get evidence-grounded answers.

![Python](https://img.shields.io/badge/Python-3.13%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16.3-000000?style=flat-square&logo=next.js&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)
![Anthropic](https://img.shields.io/badge/Claude-Anthropic-D97757?style=flat-square)
![OpenObserve](https://img.shields.io/badge/OpenObserve-Connected-4EC52F?style=flat-square)

---

## What is TraceTalk?

TraceTalk is a conversational interface for investigating infrastructure incidents.

Instead of switching between PromQL, SQL, log search, dashboards, traces, and service graphs, you simply ask a question in natural language.

TraceTalk uses an AI agent to investigate your observability data, dynamically selecting the right tools, following evidence across multiple services, and producing a root-cause analysis backed by actual query results.

### Example questions

- **"Why did payment-service latency spike around 2pm?"**
- **"What caused the error spike in cart-service?"**
- **"What changed right before things went wrong?"**
- **"Which service is responsible for the increased latency?"**
- **"Did a deployment cause the incident?"**

The goal is simple:

> **Ask a question. Watch the investigation. Get an evidence-grounded answer.**

---

## Key Features

| Feature | Description |
| --- | --- |
| **Natural Language Investigation** | Ask infrastructure questions in plain English without writing query syntax. |
| **Live Investigation Streaming** | Watch the agent's investigation progress in real time using Server-Sent Events (SSE). |
| **Multi-hop Reasoning** | The agent can move from metrics to service dependencies, logs, traces, and other evidence as needed. |
| **Evidence Grounding** | Agent conclusions are based on results returned by observability tools rather than unsupported guesses. |
| **Five Query Tools** | `run_sql`, `list_streams`, `search_logs`, `get_metrics`, and `get_service_graph`. |
| **Tool-use Budget** | Limits the number of tool calls per investigation to prevent runaway execution and cost. |
| **Investigation Timeline** | Displays the tools and investigation steps used to reach the final answer. |
| **Dark Glassmorphism UI** | Modern responsive interface designed around an investigation-first workflow. |

---

# How It Works

A typical TraceTalk investigation looks like this:

```text
┌──────────────────────┐
│        User          │
│                      │
│ "Why is latency up?" │
└──────────┬───────────┘
           │
           │ Natural language
           ▼
┌─────────────────────────────┐
│       TraceTalk API         │
│        Flask :5050          │
│                             │
│     Claude Agent Loop       │
└──────────────┬──────────────┘
               │
               │ Tool calls
               ▼
┌─────────────────────────────┐
│       Query Tools           │
│                             │
│  run_sql                    │
│  list_streams               │
│  search_logs                │
│  get_metrics                │
│  get_service_graph          │
└──────────────┬──────────────┘
               │
               │ SQL / REST
               ▼
┌─────────────────────────────┐
│        OpenObserve          │
│          :5080              │
│                             │
│   Logs │ Metrics │ Traces   │
└─────────────────────────────┘
```

The agent can perform multiple investigation steps before answering.

For example:

```text
Question
   │
   ▼
Check metrics
   │
   ▼
Identify affected service
   │
   ▼
Inspect service dependencies
   │
   ▼
Search relevant logs
   │
   ▼
Inspect traces
   │
   ▼
Correlate evidence
   │
   ▼
Root-cause analysis
```

The important distinction is that **the agent decides what to investigate next based on the evidence it finds**.

---

# Example Investigation

Suppose you ask:

> "Why did payment-service latency spike around 2pm?"

TraceTalk might perform an investigation such as:

```text
1. Query payment-service latency metrics
           │
           ▼
2. Confirm latency increase around 14:00
           │
           ▼
3. Inspect service dependency graph
           │
           ▼
4. Identify inventory-service dependency
           │
           ▼
5. Search payment-service logs
           │
           ▼
6. Inspect traces for slow requests
           │
           ▼
7. Discover downstream timeout
           │
           ▼
8. Correlate timestamps and evidence
           │
           ▼
9. Generate root-cause explanation
```

The final response should explain **what happened, when it happened, which service was involved, and what evidence supports the conclusion**.

---

# Architecture

TraceTalk consists of three primary layers:

```text
┌─────────────────────────────────────────────────────┐
│                    Frontend                         │
│                                                     │
│                 Next.js / React                     │
│                    :3000                            │
│                                                     │
│   Chat Interface        Investigation Panel         │
└──────────────────────────┬──────────────────────────┘
                           │
                           │ HTTP / SSE
                           ▼
┌─────────────────────────────────────────────────────┐
│                    Backend                           │
│                                                     │
│                  Flask :5050                        │
│                                                     │
│  API Endpoint → Claude Agent → Tool Execution       │
└──────────────────────────┬──────────────────────────┘
                           │
                           │ SQL / REST API
                           ▼
┌─────────────────────────────────────────────────────┐
│                  OpenObserve                        │
│                    :5080                            │
│                                                     │
│             Logs │ Metrics │ Traces                 │
└─────────────────────────────────────────────────────┘
```

### Frontend

The frontend provides:

- Conversational chat interface
- Live investigation timeline
- Tool-call visibility
- Markdown rendering
- Syntax-highlighted code
- Responsive dark UI

### Backend

The Flask backend handles:

- API requests
- Claude agent orchestration
- Tool execution
- OpenObserve queries
- SSE streaming
- Investigation state
- Tool-use limits

### Observability Layer

OpenObserve provides the underlying telemetry:

- Logs
- Metrics
- Traces
- Service relationships
- SQL-queryable observability data

---

# Agent Investigation Loop

The core of TraceTalk is the agent loop.

```text
User Question
      │
      ▼
┌──────────────────┐
│   Claude Agent   │
└────────┬─────────┘
         │
         ▼
    Select Tool
         │
         ▼
┌──────────────────┐
│   Query Tool     │
└────────┬─────────┘
         │
         ▼
   OpenObserve
         │
         ▼
    Tool Result
         │
         ▼
┌──────────────────┐
│   Claude Agent   │
└────────┬─────────┘
         │
         ├───────────────┐
         │               │
     More evidence?      │
         │               │
        Yes              No
         │               │
         └──► Tool       ▼
             call     Final Answer
```

The agent can continue investigating until:

1. It has sufficient evidence to answer the question.
2. The investigation reaches the configured tool-call limit.
3. The question cannot be answered from the available telemetry.

---

# Query Tools

TraceTalk exposes five primary tools to the agent.

| Tool | Purpose |
| --- | --- |
| `run_sql` | Execute SQL queries against observability data. |
| `list_streams` | Discover available OpenObserve streams. |
| `search_logs` | Search logs for relevant events, errors, and patterns. |
| `get_metrics` | Retrieve metric information for services and time ranges. |
| `get_service_graph` | Inspect relationships and dependencies between services. |

These tools allow the agent to investigate incidents from multiple angles rather than relying on a single query.

---

# Evidence-First Design

TraceTalk is designed around an **evidence-first** principle.

The agent should not simply produce a plausible explanation.

Instead:

```text
Observation
     │
     ▼
Tool Query
     │
     ▼
Actual Data
     │
     ▼
Evidence
     │
     ▼
Reasoning
     │
     ▼
Conclusion
```

This makes investigations more transparent and makes it easier to understand **why** the agent reached a particular conclusion.

---

# Service Dependency Example

TraceTalk can reason across service dependencies.

```text
                    ┌───────────────┐
                    │  api-gateway  │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ cart-service  │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │payment-service│
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │inventory-     │
                    │service        │
                    └───────────────┘
```

This allows an investigation to move beyond the service where an incident first becomes visible.

For example:

```text
api-gateway
     │
     ▼
cart-service
     │
     ▼
payment-service
     │
     ▼
inventory-service
     │
     ▼
Database / downstream dependency
```

An elevated latency in one service may therefore be caused by a dependency further down the request path.

---

# Tech Stack

## Backend

- **Python 3.13+**
- **Flask**
- **Anthropic Claude API**
- **OpenObserve**
- **Server-Sent Events (SSE)**

## Frontend

- **Next.js**
- **React**
- **TypeScript**
- **Tailwind CSS**
- **react-markdown**
- **react-syntax-highlighter**

---

# Project Structure

```text
TraceTalk/
│
├── server.py                 # Flask backend and SSE endpoint
├── agent.py                  # Claude agent loop
├── tools.py                  # OpenObserve query tools
├── incident.py               # Continuous incident-data generator
├── metrics.py                # Alternative telemetry generator
├── test_acceptance.py        # Acceptance test scenarios
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx      # Main chat page
│   │   │   ├── layout.tsx    # Root layout
│   │   │   └── globals.css   # Global styles
│   │   │
│   │   ├── components/
│   │   │   ├── ChatMessage.tsx
│   │   │   └── MarkdownRenderer.tsx
│   │   │
│   │   ├── hooks/
│   │   │   └── useSSE.ts
│   │   │
│   │   └── types.ts
│   │
│   └── next.config.ts
│
├── static/
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── spec/
│   ├── overview.md
│   ├── datamodel.md
│   ├── toolsapi.md
│   ├── agentbehaviour.md
│   ├── ui.md
│   └── acceptancecriteria.md
│
├── prd.md                    # Product requirements
├── tech.md                   # Technical design
└── plan.md                   # Build plan
```

---

# Prerequisites

Before running TraceTalk, make sure you have:

| Requirement | Details |
| --- | --- |
| Python | 3.13 or later |
| Node.js | 18 or later |
| Anthropic API Key | Required for Claude |
| OpenObserve | Running locally or on an accessible host |
| OpenObserve Telemetry | Logs, metrics, and/or traces available for investigation |

---

# Getting Started

## 1. Configure Environment Variables

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

Configure OpenObserve:

```bash
export OO_BASE_URL="http://localhost:5080"
export OO_ORG="default"
export ZO_ROOT_USER_EMAIL="your-email@example.com"
export ZO_ROOT_USER_PASSWORD="your-password"
```

> Do not commit API keys, passwords, or other credentials to source control.

---

## 2. Start the Backend

From the project root:

```bash
python3 server.py
```

The Flask backend will start on:

```text
http://localhost:5050
```

---

## 3. Start the Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend will start on:

```text
http://localhost:3000
```

The Next.js application proxies API requests to the Flask backend.

---

## 4. Start Investigating

Open:

```text
http://localhost:3000
```

Then ask a question such as:

> Why did payment-service latency spike around 2pm?

You should see the investigation unfold in the UI as TraceTalk queries the available observability data.

---

# Configuration

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | Required | API key used to access Claude. |
| `OO_BASE_URL` | `http://localhost:5080` | OpenObserve server URL. |
| `OO_ORG` | `default` | OpenObserve organization. |
| `ZO_ROOT_USER_EMAIL` | Required | OpenObserve authentication username. |
| `ZO_ROOT_USER_PASSWORD` | Required | OpenObserve authentication password. |

## Agent Configuration

Agent behavior is configured in `agent.py`.

| Setting | Default | Description |
| --- | --- | --- |
| Model | Project configured model | Claude model used for investigation. |
| Max tool calls | `20` | Maximum number of tool calls per investigation. |
| SSE timeout | `5 minutes` | Maximum frontend investigation stream duration. |

---

# Running Tests

Run the acceptance test suite:

```bash
python3 test_acceptance.py
```

The test suite covers five scenarios:

### 1. Latency Spike Investigation

Tests a single-hop investigation:

```text
Metrics → Traces → Root Cause
```

### 2. Error Burst Analysis

Tests discovery of deployment-related errors:

```text
Logs → Deployment Event → Causal Chain
```

### 3. Multi-hop Reasoning

Tests investigation across multiple services:

```text
Initial Scan
     ↓
Service Graph
     ↓
Affected Service
     ↓
Detailed Investigation
```

### 4. Negative Test

Tests how TraceTalk handles ambiguous, irrelevant, or unsupported questions.

### 5. Performance

Tests whether investigations complete within the expected time constraints.

The acceptance tests require a valid `ANTHROPIC_API_KEY` and access to the required observability data.

---

# Demo Questions

Try these questions after starting TraceTalk:

| Question | Example Investigation |
| --- | --- |
| **Why did payment-service latency spike around 2pm?** | Metrics → Traces → Downstream dependency |
| **What caused the error spike in cart-service?** | Logs → Deployment event → Root cause |
| **What changed right before things went wrong?** | Multi-service scan → Service graph → Evidence |
| **Which service is responsible for the latency increase?** | Metrics → Dependencies → Logs |
| **Did a deployment cause the incident?** | Logs → Deployment correlation → Timeline |

---

# Design Principles

## 1. Evidence First

The agent should prefer querying real telemetry over guessing.

## 2. Transparent Investigation

Users should be able to see what the agent is doing instead of receiving only a final answer.

## 3. Multi-hop Reasoning

Incidents rarely respect service boundaries. TraceTalk can follow evidence across dependencies.

## 4. Bounded Execution

Every investigation has a configurable tool-use budget.

## 5. Conversational Interface

Users should be able to investigate infrastructure problems without learning multiple query languages.

---

# Constraints

TraceTalk currently operates under several intentional constraints:

- Investigations are bounded by a maximum tool-call budget.
- Answers depend on the quality and availability of telemetry.
- The agent cannot infer information that is not present in the connected observability data.
- OpenObserve must contain sufficiently relevant logs, metrics, or traces.
- Claude API access is required for AI-powered investigation.

---

# Roadmap

Potential future improvements include:

- [ ] Incident timeline visualization
- [ ] Automatic anomaly detection
- [ ] Historical incident comparison
- [ ] Slack / PagerDuty integration
- [ ] Kubernetes-aware investigations
- [ ] Deployment and Git correlation
- [ ] Alert ingestion
- [ ] Saved investigations
- [ ] Investigation replay
- [ ] Custom agent tools
- [ ] Multi-tenant support
- [ ] Authentication and role-based access control

---

# Why TraceTalk?

Traditional observability tools are extremely powerful, but investigating an incident often means jumping between multiple interfaces:

```text
Metrics
  ↓
Logs
  ↓
Traces
  ↓
Service Graph
  ↓
Deployments
  ↓
Dashboards
  ↓
Back to Logs
  ↓
Try another query
```

TraceTalk turns that workflow into a conversation:

```text
You:
"Why is checkout failing?"

              ↓

TraceTalk:
Investigates metrics
        ↓
Checks dependencies
        ↓
Searches logs
        ↓
Inspects traces
        ↓
Correlates events
        ↓

"checkout-service is failing because
inventory-service is timing out.
The increase began immediately after
the latest deployment."
```

The interface becomes the investigation rather than another dashboard to operate.

---

# License

MIT
