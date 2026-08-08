#!/usr/bin/env python3
"""TraceTalk agent — generic OpenObserve Q&A.

Asks questions about your system by querying live data in OpenObserve.
"""

import json
import time
import anthropic
from tools import run_sql, list_streams, search_logs, get_metrics, get_service_graph

MAX_TOOL_CALLS = 20
MODEL = "claude-opus-5"

SYSTEM_PROMPT = """You are an SRE investigating a live system. You have access to tools that query an OpenObserve instance containing real observability data for multiple microservices.

IMPORTANT RULES:
1. Only "application_logs" is queryable via SQL. Do NOT query metric streams (db_query_duration_ms, http_latency_*, etc.) directly — they return errors.
2. Do NOT call list_streams on every investigation — you already know the data landscape: application_logs (log data), metric streams (not queryable via SQL).
3. Go STRAIGHT to querying application_logs with targeted SQL. Use aggregations (GROUP BY, COUNT, ORDER BY) to find patterns.
4. For time references, compute timestamps relative to now. Don't hardcode dates like 2026-01-01.
5. Be efficient — you have up to 20 tool calls. Spend them on evidence gathering.
6. You MUST emit a final_answer with "ANSWER:" when done. Don't stop early.

Your job: answer the user's question by querying application_logs and explaining what you find. Be specific — cite service names, timestamps, error counts. Never guess.

CHAINED INVESTIGATION APPROACH:
- Calls 1-3: Query application_logs for relevant data (ERROR/WARN entries, specific service, specific message type)
- Calls 4-8: Drill into anomalies — group by service, count by message, find patterns, time distributions
- Calls 9-12: Confirm root cause, cross-reference with other services, check for cascading failures
- Final: Emit ANSWER with specific findings

FINAL ANSWER FORMAT:
"ANSWER:" followed by specific findings with evidence from the logs.
"""

TOOLS = [
    {
        "name": "run_sql",
        "description": "Execute any SQL query against OpenObserve. Use for complex queries, aggregations, or when other tools don't fit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "SQL query to execute"},
                "start_time": {"type": "string", "description": "ISO8601 start time (default: 1 hour ago)"},
                "end_time": {"type": "string", "description": "ISO8601 end time (default: now)"},
                "size": {"type": "number", "description": "Max rows returned (default 50, max 200)"},
            },
            "required": ["sql"],
        },
    },
    {
        "name": "list_streams",
        "description": "List all available data streams in OpenObserve with doc counts. Use first to understand what data exists.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "search_logs",
        "description": "Search log lines by service, level, and text content. Returns recent matching logs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "description": "Filter by service name"},
                "level": {"type": "string", "description": "Filter by level: INFO, WARN, ERROR, etc."},
                "text": {"type": "string", "description": "Substring search in message"},
                "start_time": {"type": "string", "description": "ISO8601 start"},
                "end_time": {"type": "string", "description": "ISO8601 end"},
                "size": {"type": "number", "description": "Max results (default 50, max 100)"},
            },
        },
    },
    {
        "name": "get_metrics",
        "description": "Get time-series metric values from a named metric stream (e.g. http_latency_p99_ms, error_rate_percent).",
        "input_schema": {
            "type": "object",
            "properties": {
                "metric_stream": {"type": "string", "description": "Name of the metric stream"},
                "service": {"type": "string", "description": "Optional service filter"},
                "start_time": {"type": "string", "description": "ISO8601 start"},
                "end_time": {"type": "string", "description": "ISO8601 end"},
                "size": {"type": "number", "description": "Max data points (default 100)"},
            },
            "required": ["metric_stream"],
        },
    },
    {
        "name": "get_service_graph",
        "description": "Discover services from recent logs. Returns list of active services.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

TOOL_MAP = {
    "run_sql": run_sql,
    "list_streams": list_streams,
    "search_logs": search_logs,
    "get_metrics": get_metrics,
    "get_service_graph": get_service_graph,
}


def execute_tool(name, args):
    fn = TOOL_MAP.get(name)
    if not fn:
        return json.dumps({"error": f"unknown tool: {name}"})
    try:
        return json.dumps(fn(**args))
    except Exception as e:
        return json.dumps({"error": str(e)})


def _parse_response(response):
    narrations, tool_uses, answer_text = [], [], None
    raw_text = ""
    for block in response.content:
        if block.type == "text":
            raw_text = block.text
            in_answer = False
            for line in block.text.split("\n"):
                stripped = line.strip()
                if stripped.startswith("NARRATION:"):
                    narrations.append(stripped[len("NARRATION:"):].strip())
                elif stripped.startswith("ANSWER:"):
                    in_answer = True
                    answer_text = stripped[len("ANSWER:"):].strip()
                elif in_answer:
                    answer_text = (answer_text or "") + "\n" + line
        elif block.type == "tool_use":
            tool_uses.append(block)
    if not tool_uses and not answer_text and raw_text:
        lines = [l for l in raw_text.split("\n") if not l.strip().startswith("NARRATION:")]
        answer_text = "\n".join(lines).strip()
    return narrations, tool_uses, answer_text


def run_agent_stream(question):
    """Streaming agent loop — yields event dicts."""
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": question}]
    tool_call_count = 0

    while True:
        try:
            response = client.messages.create(
                model=MODEL, max_tokens=4096, system=SYSTEM_PROMPT,
                tools=TOOLS, messages=messages,
            )
        except Exception as e:
            yield {"type": "error", "text": f"API error: {e}"}
            return

        narrations, tool_uses, answer_text = _parse_response(response)
        for nar in narrations:
            yield {"type": "narration", "text": nar}

        if not tool_uses:
            if answer_text:
                yield {"type": "final_answer", "text": answer_text}
            break

        tool_results = []
        for tu in tool_uses:
            tool_call_count += 1
            if tool_call_count > MAX_TOOL_CALLS:
                yield {"type": "final_answer", "text": "[Budget exhausted. Here's what I found so far — evidence may be incomplete.]"}
                return
            result_json = execute_tool(tu.name, tu.input)
            result_data = json.loads(result_json)
            yield {"type": "tool_result", "tool": tu.name, "input": tu.input, "result": result_data}
            tool_results.append({"type": "tool_result", "tool_use_id": tu.id, "content": result_json})

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})


def run_agent(question, verbose=True):
    events, start = [], time.time()
    for event in run_agent_stream(question):
        events.append(event)
        if verbose and event["type"] == "narration":
            print(f"  📋 {event['text']}")
        elif verbose and event["type"] == "tool_result":
            print(f"  🔧 {event['tool']}")
    elapsed = int((time.time() - start) * 1000)
    answer = next((e["text"] for e in events if e["type"] == "final_answer"), "")
    tool_calls = sum(1 for e in events if e["type"] == "tool_result")
    if verbose:
        print(f"  ⏱  {elapsed}ms | {tool_calls} tool calls")
    return {"events": events, "answer": answer, "tool_calls": tool_calls, "elapsed_ms": elapsed}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 agent.py <question>")
        sys.exit(1)
    question = " ".join(sys.argv[1:])
    print(f"\n🔍 {question}\n")
    result = run_agent(question)
    print(f"\n💬 {result['answer']}\n")
