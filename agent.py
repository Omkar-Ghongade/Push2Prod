#!/usr/bin/env python3
"""TraceTalk agent — generic OpenObserve Q&A.

Asks questions about your system by querying live data in OpenObserve.
Uses OpenAI-compatible tool calling through OpenRouter.
"""

import json
import time
import os

from openai import OpenAI

from tools import (
    run_sql,
    list_streams,
    search_logs,
    get_metrics,
    get_service_graph,
)


# ============================================================
# CONFIG
# ============================================================

MAX_TOOL_CALLS = 20

# Use a model available through your OpenRouter account.
MODEL = "meta-llama/llama-3.1-8b-instruct"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """You are an SRE investigating a live system.

You have access to tools that query an OpenObserve instance containing
real observability data for multiple microservices.

IMPORTANT RULES:

1. Only "application_logs" is queryable via SQL.
   Do NOT query metric streams such as:
   - db_query_duration_ms
   - http_latency_*
   - error_rate_percent
   directly with SQL.

2. Do NOT call list_streams on every investigation.
   You already know the data landscape:
   - application_logs = log data
   - metric streams = not queryable via SQL

3. Go STRAIGHT to querying application_logs with targeted SQL.

4. Use aggregations such as:
   - GROUP BY
   - COUNT
   - ORDER BY
   - time-based grouping

   to identify patterns.

5. For time references, compute timestamps relative to the current time.
   Do not hardcode dates such as 2026-01-01.

6. Be efficient.
   You have up to 20 tool calls.
   Spend them on evidence gathering.

7. Never guess.
   Every claim should be grounded in actual observability data.

8. You MUST emit a final answer beginning with:
   ANSWER:

CHAINED INVESTIGATION APPROACH:

- Calls 1-3:
  Query application_logs for relevant ERROR/WARN entries,
  specific services, and relevant message types.

- Calls 4-8:
  Drill into anomalies.
  Group by service, error message, timestamp, and other useful fields.

- Calls 9-12:
  Confirm root cause.
  Cross-reference other services and identify cascading failures.

- Final:
  Emit ANSWER with specific findings supported by evidence.

FINAL ANSWER FORMAT:

ANSWER:
<specific findings with evidence from the logs>
"""


# ============================================================
# TOOL DEFINITIONS
# ============================================================

# Internal tool definitions.
#
# These use the generic:
#
# {
#     "name": "...",
#     "description": "...",
#     "input_schema": {...}
# }
#
# format.
#
# They are converted below into the OpenAI/OpenRouter format.

TOOLS = [
    {
        "name": "run_sql",
        "description": (
            "Execute any SQL query against OpenObserve. "
            "Use for complex queries, aggregations, or when other tools "
            "don't fit."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "SQL query to execute",
                },
                "start_time": {
                    "type": "string",
                    "description": (
                        "ISO8601 start time "
                        "(default: 1 hour ago)"
                    ),
                },
                "end_time": {
                    "type": "string",
                    "description": (
                        "ISO8601 end time "
                        "(default: now)"
                    ),
                },
                "size": {
                    "type": "number",
                    "description": (
                        "Max rows returned "
                        "(default 50, max 200)"
                    ),
                },
            },
            "required": ["sql"],
        },
    },
    {
        "name": "list_streams",
        "description": (
            "List all available data streams in OpenObserve "
            "with document counts. Use first to understand "
            "what data exists."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "search_logs",
        "description": (
            "Search log lines by service, level, and text content. "
            "Returns recent matching logs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Filter by service name",
                },
                "level": {
                    "type": "string",
                    "description": (
                        "Filter by level: INFO, WARN, ERROR, etc."
                    ),
                },
                "text": {
                    "type": "string",
                    "description": "Substring search in message",
                },
                "start_time": {
                    "type": "string",
                    "description": "ISO8601 start",
                },
                "end_time": {
                    "type": "string",
                    "description": "ISO8601 end",
                },
                "size": {
                    "type": "number",
                    "description": (
                        "Max results "
                        "(default 50, max 100)"
                    ),
                },
            },
        },
    },
    {
        "name": "get_metrics",
        "description": (
            "Get time-series metric values from a named metric "
            "stream, for example http_latency_p99_ms or "
            "error_rate_percent."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "metric_stream": {
                    "type": "string",
                    "description": "Name of the metric stream",
                },
                "service": {
                    "type": "string",
                    "description": "Optional service filter",
                },
                "start_time": {
                    "type": "string",
                    "description": "ISO8601 start",
                },
                "end_time": {
                    "type": "string",
                    "description": "ISO8601 end",
                },
                "size": {
                    "type": "number",
                    "description": (
                        "Max data points "
                        "(default 100)"
                    ),
                },
            },
            "required": ["metric_stream"],
        },
    },
    {
        "name": "get_service_graph",
        "description": (
            "Discover services from recent logs. "
            "Returns a list of active services."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


# ============================================================
# OPENAI / OPENROUTER TOOL FORMAT
# ============================================================

# OpenAI-compatible APIs expect:
#
# {
#     "type": "function",
#     "function": {
#         "name": "...",
#         "description": "...",
#         "parameters": {...}
#     }
# }
#
# Your original tools use "input_schema", so convert them.

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        },
    }
    for tool in TOOLS
]


# ============================================================
# TOOL MAP
# ============================================================

TOOL_MAP = {
    "run_sql": run_sql,
    "list_streams": list_streams,
    "search_logs": search_logs,
    "get_metrics": get_metrics,
    "get_service_graph": get_service_graph,
}


# ============================================================
# TOOL EXECUTION
# ============================================================

def execute_tool(name, args):
    """Execute a tool safely and return JSON."""

    fn = TOOL_MAP.get(name)

    if not fn:
        return json.dumps(
            {
                "error": f"Unknown tool: {name}"
            }
        )

    try:
        result = fn(**args)

        return json.dumps(
            result,
            default=str,
        )

    except Exception as e:
        return json.dumps(
            {
                "error": str(e)
            }
        )


# ============================================================
# RESPONSE PARSER
# ============================================================

def _parse_openai_response(message):
    """Parse OpenAI-compatible assistant response."""

    narrations = []
    tool_uses = []
    answer_text = None

    raw_text = message.content or ""

    in_answer = False

    for line in raw_text.split("\n"):
        stripped = line.strip()

        if stripped.startswith("NARRATION:"):
            narrations.append(
                stripped[len("NARRATION:"):].strip()
            )

        elif stripped.startswith("ANSWER:"):
            in_answer = True

            answer_text = (
                stripped[len("ANSWER:"):].strip()
            )

        elif in_answer:
            answer_text = (
                (answer_text or "")
                + "\n"
                + line
            )

    # Parse tool calls.
    if message.tool_calls:

        for tc in message.tool_calls:

            if tc.type != "function":
                continue

            try:
                arguments = json.loads(
                    tc.function.arguments or "{}"
                )
            except json.JSONDecodeError:
                arguments = {}

            tool_uses.append(
                {
                    "name": tc.function.name,
                    "input": arguments,
                    "id": tc.id,
                }
            )

    # If there are no tool calls and the model didn't explicitly
    # provide ANSWER:, use the raw content as the answer.
    if (
        not tool_uses
        and not answer_text
        and raw_text
    ):
        lines = [
            line
            for line in raw_text.split("\n")
            if not line.strip().startswith("NARRATION:")
        ]

        answer_text = "\n".join(lines).strip()

    return narrations, tool_uses, answer_text


# ============================================================
# AGENT LOOP
# ============================================================

def run_agent_stream(question):
    """Streaming-style agent loop yielding event dictionaries."""

    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:

        yield {
            "type": "error",
            "text": (
                "OPENROUTER_API_KEY environment variable "
                "not set"
            ),
        }

        return

    client = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key,
    )

    messages = [
        {
            "role": "user",
            "content": question,
        }
    ]

    tool_call_count = 0

    print(
        f"DEBUG: Using model = {MODEL}",
        flush=True,
    )

    while True:

        # ====================================================
        # CALL LLM
        # ====================================================

        try:

            response = client.chat.completions.create(
                model=MODEL,
                max_tokens=4096,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    }
                ] + messages,
                tools=OPENAI_TOOLS,
                tool_choice="auto",
            )

        except Exception as e:

            yield {
                "type": "error",
                "text": f"API error: {e}",
            }

            return

        # ====================================================
        # PARSE RESPONSE
        # ====================================================

        message = response.choices[0].message

        narrations, tool_uses, answer_text = (
            _parse_openai_response(message)
        )

        # Send narration events.
        for narration in narrations:

            yield {
                "type": "narration",
                "text": narration,
            }

        # ====================================================
        # NO TOOL CALL = FINAL ANSWER
        # ====================================================

        if not tool_uses:

            if answer_text:

                yield {
                    "type": "final_answer",
                    "text": answer_text,
                }

            break

        # ====================================================
        # EXECUTE TOOL CALLS
        # ====================================================

        tool_results = []

        for tool_use in tool_uses:

            tool_call_count += 1

            # Enforce investigation budget.
            if tool_call_count > MAX_TOOL_CALLS:

                yield {
                    "type": "final_answer",
                    "text": (
                        "[Budget exhausted. "
                        "Here's what I found so far — "
                        "evidence may be incomplete.]"
                    ),
                }

                return

            tool_name = tool_use["name"]
            tool_input = tool_use["input"]
            tool_id = tool_use["id"]

            # Execute tool.
            result_json = execute_tool(
                tool_name,
                tool_input,
            )

            # Convert result back to Python for UI events.
            try:
                result_data = json.loads(
                    result_json
                )
            except json.JSONDecodeError:
                result_data = {
                    "result": result_json
                }

            # Emit event for frontend.
            yield {
                "type": "tool_result",
                "tool": tool_name,
                "input": tool_input,
                "result": result_data,
            }

            # OpenAI-compatible tool response.
            tool_results.append(
                {
                    "tool_call_id": tool_id,
                    "role": "tool",
                    "content": result_json,
                }
            )

        # ====================================================
        # APPEND ASSISTANT TOOL CALL MESSAGE
        # ====================================================

        assistant_tool_calls = []

        for tool_use in tool_uses:

            assistant_tool_calls.append(
                {
                    "id": tool_use["id"],
                    "type": "function",
                    "function": {
                        "name": tool_use["name"],
                        "arguments": json.dumps(
                            tool_use["input"]
                        ),
                    },
                }
            )

        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": assistant_tool_calls,
            }
        )

        # ====================================================
        # APPEND TOOL RESULTS
        # ====================================================

        messages.extend(tool_results)


# ============================================================
# NON-STREAMING WRAPPER
# ============================================================

def run_agent(question, verbose=True):
    """Run the agent and return the final result."""

    events = []

    start = time.time()

    for event in run_agent_stream(question):

        events.append(event)

        if (
            verbose
            and event["type"] == "narration"
        ):
            print(
                f"  📋 {event['text']}"
            )

        elif (
            verbose
            and event["type"] == "tool_result"
        ):
            print(
                f"  🔧 {event['tool']}"
            )

        elif (
            verbose
            and event["type"] == "error"
        ):
            print(
                f"  ❌ {event['text']}"
            )

    elapsed = int(
        (time.time() - start) * 1000
    )

    answer = next(
        (
            event["text"]
            for event in events
            if event["type"] == "final_answer"
        ),
        "",
    )

    tool_calls = sum(
        1
        for event in events
        if event["type"] == "tool_result"
    )

    if verbose:

        print(
            f"  ⏱  {elapsed}ms | "
            f"{tool_calls} tool calls"
        )

    return {
        "events": events,
        "answer": answer,
        "tool_calls": tool_calls,
        "elapsed_ms": elapsed,
    }


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:

        print(
            "Usage: python3 agent.py <question>"
        )

        sys.exit(1)

    question = " ".join(
        sys.argv[1:]
    )

    print(
        f"\n🔍 {question}\n"
    )

    result = run_agent(question)

    print(
        f"\n💬 {result['answer']}\n"
    )