import argparse
import asyncio
import logging
import statistics
import time

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"


async def simulate_chat_stream_user(client: httpx.AsyncClient, user_id: int, semaphore: asyncio.Semaphore):
    async with semaphore:
        t0 = time.time()
        try:
            async with client.stream(
                "POST",
                f"{BASE_URL}/api/chat/stream",
                json={"message": "Show me daily message volume for server_001."},
                timeout=60.0,
            ) as response:
                if response.status_code != 200:
                    latency = (time.time() - t0) * 1000
                    return {"status": response.status_code, "latency_ms": latency, "success": False, "error": f"HTTP {response.status_code}"}

                # Fully consume the SSE stream to measure complete delivery time
                async for _ in response.aiter_text():
                    pass

                latency = (time.time() - t0) * 1000
                return {"status": 200, "latency_ms": latency, "success": True}
        except Exception as e:
            latency = (time.time() - t0) * 1000
            return {"status": 500, "latency_ms": latency, "success": False, "error": str(e)}


async def run_load_test(concurrent_users: int = 5, total_requests: int = 20):
    print(f"Starting Load Test with {concurrent_users} concurrent streams ({total_requests} total requests)...")
    semaphore = asyncio.Semaphore(concurrent_users)
    
    # Configure httpx limits for concurrent connections
    limits = httpx.Limits(max_keepalive_connections=concurrent_users, max_connections=concurrent_users * 2)
    
    start_wall_time = time.time()

    async with httpx.AsyncClient(limits=limits, timeout=60.0) as client:
        tasks = [simulate_chat_stream_user(client, i, semaphore) for i in range(total_requests)]
        results = await asyncio.gather(*tasks)

    end_wall_time = time.time()
    total_duration_sec = max(end_wall_time - start_wall_time, 0.001)

    latencies = [r["latency_ms"] for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]

    if not latencies:
        print("\nAll requests failed. Failure diagnostic reasons:")
        sample_errors = set(f.get("error", "Unknown") for f in failures[:5])
        for err in sample_errors:
            print(f" - {err}")
        print("\nEnsure the FastAPI backend is running and LLM API rate limits/keys are valid.")
        return

    latencies.sort()
    n = len(latencies)
    p50 = latencies[int(n * 0.50)]
    p95 = latencies[min(int(n * 0.95), n - 1)]
    p99 = latencies[min(int(n * 0.99), n - 1)]
    avg = statistics.mean(latencies)
    throughput = len(latencies) / total_duration_sec
    error_rate = (len(failures) / len(results)) * 100

    print("\n===============================================================")
    print("                    LOAD TESTING METRICS                       ")
    print("===============================================================")
    print(f"Total Requests Processed:   {len(results)}")
    print(f"Successful Streams:         {len(latencies)}")
    print(f"Failed Streams:             {len(failures)}")
    print(f"Error Rate:                 {round(error_rate, 2)}%")
    print(f"Total Duration:             {round(total_duration_sec, 2)} sec")
    print(f"Throughput:                 {round(throughput, 2)} req/sec")
    print(f"Average Latency:            {round(avg, 2)} ms")
    print(f"p50 Latency:                {round(p50, 2)} ms")
    print(f"p95 Latency:                {round(p95, 2)} ms")
    print(f"p99 Latency:                {round(p99, 2)} ms")
    print("===============================================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run synthetic SSE streaming load test for Agent API")
    parser.add_argument("--concurrency", type=int, default=5, help="Number of concurrent user streams (default: 5)")
    parser.add_argument("--requests", type=int, default=20, help="Total number of requests to send (default: 20)")
    args = parser.parse_args()

    asyncio.run(run_load_test(concurrent_users=args.concurrency, total_requests=args.requests))

