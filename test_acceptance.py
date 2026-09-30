#!/usr/bin/env python3
"""Acceptance criteria tests — Spec 05 (OpenObserve + relative timestamps).

Run with OPENROUTER_API_KEY set:
    export OPENROUTER_API_KEY=sk-or-...
    python3 test_acceptance.py
"""

import json
import time
import sys
from datetime import datetime, timezone

from agent import run_agent_stream

RESULTS = []


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def minutes_ago(m):
    return datetime.fromtimestamp(time.time() - m * 60, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_scenario(name, question, expect_in_answer=None, expect_not_in_answer=None,
                 expect_tool_count_max=6, repetitions=1):
    print(f"\n{'='*60}")
    print(f"SCENARIO: {name}")
    print(f"Question: {question}")
    print(f"{'='*60}")

    timings = []
    all_results = []

    for i in range(repetitions):
        print(f"\n--- Run {i+1}/{repetitions} ---")
        start = time.time()
        events = []
        answer = ""

        for event in run_agent_stream(question):
            events.append(event)
            if event["type"] == "narration":
                print(f"  📋 {event['text']}")
            elif event["type"] not in ("final_answer",):
                print(f"  🔧 {event.get('tool','')} → {event['type']}")
            elif event["type"] == "final_answer":
                answer = event["text"]

        elapsed = time.time() - start
        timings.append(elapsed)

        tool_types = set()
        tool_count = 0
        for e in events:
            if e["type"] not in ("narration", "final_answer"):
                tool_types.add(e["type"])
                tool_count += 1

        result = {
            "answer": answer,
            "tool_types": tool_types,
            "tool_count": tool_count,
            "elapsed": elapsed,
            "events": events,
        }
        all_results.append(result)

        print(f"\n  💬 Answer: {answer[:300]}...")
        print(f"  📊 Tool calls: {tool_count} | Types: {tool_types} | Time: {elapsed:.1f}s")

    # Evaluate
    failures = []

    for i, r in enumerate(all_results):
        if expect_in_answer:
            for phrase in expect_in_answer:
                if phrase.lower() not in r["answer"].lower():
                    failures.append(f"Run {i+1}: missing '{phrase}' in answer")

        if expect_not_in_answer:
            for phrase in expect_not_in_answer:
                if phrase.lower() in r["answer"].lower():
                    failures.append(f"Run {i+1}: unexpected '{phrase}' in answer")

        if r["tool_count"] > expect_tool_count_max:
            failures.append(f"Run {i+1}: {r['tool_count']} tool calls exceeds max {expect_tool_count_max}")

        if r["elapsed"] > 20:
            failures.append(f"Run {i+1}: {r['elapsed']:.1f}s exceeds 20s limit")

    avg_time = sum(timings) / len(timings)
    max_time = max(timings)

    status = "PASS" if not failures else "FAIL"
    print(f"\n  {'✅' if status == 'PASS' else '❌'} {status}")
    if failures:
        for f in failures:
            print(f"    - {f}")
    print(f"  Avg time: {avg_time:.1f}s | Max time: {max_time:.1f}s")

    RESULTS.append({
        "name": name,
        "status": status,
        "failures": failures,
        "avg_time": avg_time,
        "max_time": max_time,
    })

    return all_results


def main():
    print("TraceTalk — Acceptance Criteria Tests (Spec 05)")
    print(f"Current time: {now_iso()}")
    print(f"Incident A window: ~{minutes_ago(70)} → ~{minutes_ago(50)}")
    print(f"Incident B window: ~{minutes_ago(15)} → ~{minutes_ago(2)}")
    print("=" * 60)

    # Scenario 1: Incident A — 3 runs
    run_scenario(
        name="Scenario 1: payment-service latency spike (~1h ago)",
        question="Why did payment-service latency spike about an hour ago?",
        expect_in_answer=["inventory-service", "timeout"],
        repetitions=3,
    )

    # Scenario 2: Incident B — 3 runs
    run_scenario(
        name="Scenario 2: cart-service error spike (~10m ago)",
        question="What caused the error spike in cart-service in the last 10 minutes?",
        expect_in_answer=["deploy", "cart-service"],
        repetitions=3,
    )

    # Scenario 3: Multi-hop
    run_scenario(
        name="Scenario 3: Multi-hop (ambiguous)",
        question="What changed right before things went wrong, and which service is responsible?",
        expect_in_answer=None,
        repetitions=1,
    )

    # Scenario 4: Negative test
    run_scenario(
        name="Scenario 4: Out-of-scope (EU region)",
        question="Why is checkout slow in the EU region?",
        expect_in_answer=None,
        expect_not_in_answer=None,
        repetitions=1,
    )

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for r in RESULTS:
        icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"  {icon} {r['name']}: {r['status']} (avg {r['avg_time']:.1f}s, max {r['max_time']:.1f}s)")
        if r["failures"]:
            for f in r["failures"]:
                print(f"      - {f}")

    all_pass = all(r["status"] == "PASS" for r in RESULTS)
    print(f"\n{'🎉 ALL PASS' if all_pass else '⚠️  SOME FAILURES'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
