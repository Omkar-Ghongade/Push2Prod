# TraceTalk

Conversational interface into infrastructure observability data. Ask plain-language questions about system behavior, watch an AI agent investigate live — querying logs, metrics, and traces — and get evidence-grounded root-cause answers.

## Quick Start

### 1. Get an API key

Get one at [console.anthropic.com](https://console.anthropic.com/) → API Keys → Create Key.

### 2. Set the key

**Option A** — Export in your terminal (temporary, lasts until you close the tab):
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Option B** — Add to your shell profile (persists across sessions):
```bash
echo 'export ANTHROPIC_API_KEY=sk-ant-your-key-here' >> ~/.zshrc
source ~/.zshrc
```

**Option C** — Use a `.env` file:
```bash
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" > .env
source .env
```

### 3. Generate synthetic data

```bash
python3 generate_data.py
```

Produces `logs.json`, `metrics.json`, `traces.json`, `service_graph.json`. Deterministic — reruns produce identical output.

### 4. Start the server

```bash
python3 server.py
```

Opens at **http://localhost:5050**

### 5. Ask questions

Type into the chat and watch the agent investigate live in the side panel.

**Try these:**
- "Why did payment-service latency spike around 2pm?"
- "What caused the error spike in cart-service around 3pm?"
- "What changed right before things went wrong, and which service is responsible?"

## Running Tests

```bash
python3 test_acceptance.py
```

Runs all 5 acceptance scenarios with timing and correctness checks. Needs `ANTHROPIC_API_KEY` set.

## Project Structure

```
├── generate_data.py        # Synthetic telemetry generator
├── tools.py                # 4 query tools (metrics, logs, traces, graph)
├── agent.py                # Claude tool-use loop (5-call cap)
├── server.py               # Flask backend + SSE streaming endpoint
├── test_acceptance.py      # Acceptance criteria test suite
├── static/
│   ├── index.html          # Two-pane UI
│   ├── style.css           # Dark theme, minimal styling
│   └── app.js              # SSE client + side panel renderers
├── spec/
│   ├── datamodel.md        # Synthetic data schema
│   ├── toolsapi.md         # Tool function contracts
│   ├── agentbehaviour.md   # Agent behavior rules
│   ├── ui.md               # UI component spec
│   └── acceptancecriteria.md # End-to-end scenarios
├── prd.md                  # Product requirements
├── tech.md                 # Technical design
└── plan.md                 # 5-hour build plan
```

## Architecture

```
Browser                 Flask Server              Claude API
  │                        │                         │
  │  POST /ask             │                         │
  │  {"question":"..."}    │                         │
  │───────────────────────>│                         │
  │                        │  tool_use loop          │
  │                        │────────────────────────>│
  │  SSE: narration        │                         │
  │<───────────────────────│                         │
  │  SSE: metric_query     │                         │
  │<───────────────────────│                         │
  │  SSE: log_query        │                         │
  │<───────────────────────│                         │
  │  SSE: final_answer     │                         │
  │<───────────────────────│                         │
```

## Constraints

- No hallucinated answers — every agent claim traces to a tool result
- No external services — everything is synthetic and local
- Tool calls capped at 5 per question
- Deterministic data — reruns produce identical output

## Demo Questions

| Question | What it tests |
|----------|---------------|
| "Why did payment-service latency spike around 2pm?" | Single-hop: metrics → traces → root cause |
| "What caused the error spike in cart-service around 3pm?" | Deploy log discovery → causal chain |
| "What changed right before things went wrong?" | Multi-hop: scan → graph → drill down |
