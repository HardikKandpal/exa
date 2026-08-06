import asyncio
import json
import logging
import time
from typing import Any

from app.agent.agent_core import agent_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EVAL_BENCHMARK_QUESTIONS = [
    {"id": 1, "category": "simple_lookup", "question": "What are the names and regions of all Discord servers?", "expected_tools": ["query"], "unanswerable": False},
    {"id": 2, "category": "simple_lookup", "question": "List the top 5 users with the most voice minutes in server_001.", "expected_tools": ["query"], "unanswerable": False},
    {"id": 3, "category": "simple_lookup", "question": "Who is the owner of server_002?", "expected_tools": ["query"], "unanswerable": False},
    {"id": 4, "category": "time_series", "question": "Show me daily message volume for server_001 over the last 30 days.", "expected_tools": ["query"], "unanswerable": False},
    {"id": 5, "category": "time_series", "question": "Compare weekday vs weekend message counts across all servers.", "expected_tools": ["query"], "unanswerable": False},
    {"id": 6, "category": "time_series", "question": "What is the hourly distribution of messages throughout the day?", "expected_tools": ["query"], "unanswerable": False},
    {"id": 7, "category": "ambiguous", "question": "Which channels died after March?", "expected_tools": ["query"], "unanswerable": False},
    {"id": 8, "category": "ambiguous", "question": "Who are the top posters in the gaming server?", "expected_tools": ["query"], "unanswerable": False},
    {"id": 9, "category": "chart", "question": "Chart message volume per channel for server_001.", "expected_tools": ["query", "chart"], "unanswerable": False},
    {"id": 10, "category": "chart", "question": "Render a bar chart of the top 5 servers by member count.", "expected_tools": ["query", "chart"], "unanswerable": False},
    {"id": 11, "category": "file", "question": "Export daily server statistics for server_001 into an Excel workbook.", "expected_tools": ["query", "excel"], "unanswerable": False},
    {"id": 12, "category": "file", "question": "Give me a five-slide engagement summary deck for the top three servers.", "expected_tools": ["query", "powerpoint"], "unanswerable": False},
    {"id": 13, "category": "multi_tool", "question": "Chart message volume per channel for the last quarter, then put it in a PowerPoint deck.", "expected_tools": ["query", "chart", "powerpoint"], "unanswerable": False},
    {"id": 14, "category": "unanswerable", "question": "What is the current stock price of Apple?", "expected_tools": [], "unanswerable": True},
    {"id": 15, "category": "unanswerable", "question": "What was the weather in Tokyo yesterday?", "expected_tools": [], "unanswerable": True},
    {"id": 16, "category": "unanswerable", "question": "What is the user's credit card number?", "expected_tools": [], "unanswerable": True},
]


def estimate_tokens(text: str) -> int:
    """Rough estimation of token count (~4 chars per token)."""
    return max(1, len(text) // 4)


async def run_evaluation() -> dict[str, Any]:
    print("===============================================================")
    print("       EXAQUBE DISCORD ANALYTICS EVALUATION HARNESS            ")
    print("===============================================================")

    results = []
    routing_correct_cnt = 0
    correctness_cnt = 0
    total = len(EVAL_BENCHMARK_QUESTIONS)
    total_tokens_est = 0

    start_total_time = time.time()

    for idx, bench in enumerate(EVAL_BENCHMARK_QUESTIONS, 1):
        q_id = bench["id"]
        question = bench["question"]
        expected_tools = bench["expected_tools"]
        is_unanswerable = bench["unanswerable"]

        print(f"\n[{idx}/{total}] Question: '{question}'")
        t0 = time.time()

        executed_tools = []
        final_answer = ""
        declined = False
        tokens_turn = estimate_tokens(question)

        try:
            async for sse_raw in agent_engine.stream_agent_execution(question):
                line = sse_raw.strip()
                if line.startswith("data: "):
                    payload = json.loads(line[6:])
                    event_stage = payload.get("stage")
                    tokens_turn += estimate_tokens(json.dumps(payload))

                    if event_stage == "tool_call":
                        executed_tools.append(payload.get("plugin"))
                    elif event_stage == "decline":
                        declined = True
                    elif event_stage == "final_answer":
                        final_answer = payload.get("content", "")
        except Exception as e:
            logger.error(f"Eval question {q_id} exception: {e}")

        latency = round(time.time() - t0, 3)
        total_tokens_est += tokens_turn

        if is_unanswerable:
            routing_pass = declined or (len(executed_tools) == 0)
            correctness_pass = declined or "can't answer" in final_answer.lower()
        else:
            routing_pass = all(tool in executed_tools for tool in expected_tools)
            correctness_pass = bool(final_answer and len(final_answer) > 20 and not declined)

        if routing_pass:
            routing_correct_cnt += 1
        if correctness_pass:
            correctness_cnt += 1

        print(f"   -> Latency: {latency}s | Est Tokens: {tokens_turn} | Tools: {executed_tools}")
        print(f"   -> Routing: {'✅ PASS' if routing_pass else '❌ FAIL'} | Correctness: {'✅ PASS' if correctness_pass else '❌ FAIL'}")

        results.append({
            "id": q_id,
            "category": bench["category"],
            "question": question,
            "latency_s": latency,
            "tokens_est": tokens_turn,
            "routing_pass": routing_pass,
            "correctness_pass": correctness_pass,
            "executed_tools": executed_tools
        })

    total_latency = round(time.time() - start_total_time, 2)
    routing_score = round((routing_correct_cnt / total) * 100, 1)
    correctness_score = round((correctness_cnt / total) * 100, 1)
    est_cost_usd = round((total_tokens_est / 1000000) * 0.075, 4)  # $0.075 per 1M tokens for Gemini 2.5 Flash

    summary = {
        "routing_score": routing_score,
        "correctness_score": correctness_score,
        "total_questions": total,
        "total_latency_s": total_latency,
        "avg_latency_s": round(total_latency / total, 2),
        "total_tokens_est": total_tokens_est,
        "est_cost_usd": est_cost_usd,
        "details": results
    }

    print("\n===============================================================")
    print("                    EVALUATION BENCHMARK REPORT                ")
    print("===============================================================")
    print(f"Total Benchmark Questions: {total}")
    print(f"Routing Accuracy Score:     {routing_score}% ({routing_correct_cnt}/{total})")
    print(f"Correctness Accuracy Score: {correctness_score}% ({correctness_cnt}/{total})")
    print(f"Average Turn Latency:       {summary['avg_latency_s']}s")
    print(f"Estimated Total Tokens:     {total_tokens_est}")
    print(f"Estimated API Cost:         ${est_cost_usd} USD")
    print("===============================================================\n")

    return summary


if __name__ == "__main__":
    asyncio.run(run_evaluation())
